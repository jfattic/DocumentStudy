import argparse
import json
import os
import re
import csv
from collections import defaultdict
from difflib import SequenceMatcher
import pandas as pd

# c:\src\DocumentStudy\python\evaluate.py
"""
Evaluate document-intelligence key-value outputs against ground-truth stored in an Excel/CSV file.

Usage:
    python evaluate.py --ground-truth truth.xlsx --predictions predictions.jsonl --id-column DocId --report report.csv

Predictions supported formats:
    - JSON: either a list of objects or an object mapping id -> fields
    - JSONL: one JSON object per line (each object can contain raw JSON string of fields)
    - CSV / XLSX: contains id column and one column per field (same layout as ground-truth)
Ground truth formats: XLSX, XLS, CSV

Metrics produced per field:
    - total compared (non-empty ground truth)
    - exact matches
    - exact match rate
    - average normalized string similarity (0..1)
    - numeric within-tolerance rate (when both values parse as numbers)
Outputs a CSV summary and optionally a per-document diff CSV.
"""

# -----------------------
# Utilities
# -----------------------
# regex to remove non-alphanumeric characters (keeps underscores and unicode word characters)
_NON_ALNUM_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
# regex to collapse multiple whitespace into a single space
_WS_RE = re.compile(r"\s+")


def normalize_text(s):
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    # trim and lower-case for normalization
    s = s.strip().lower()
    # replace punctuation with space to avoid merging words
    s = _NON_ALNUM_RE.sub(" ", s)
    # collapse runs of whitespace into a single space
    s = _WS_RE.sub(" ", s)
    return s.strip()


def similarity(a, b):
    a_n = normalize_text(a)
    b_n = normalize_text(b)
    # if both empty, treat as perfect similarity
    if not a_n and not b_n:
        return 1.0
    # if only one is empty, similarity is zero
    if not a_n or not b_n:
        return 0.0
    # use SequenceMatcher on normalized strings
    return SequenceMatcher(None, a_n, b_n).ratio()


def try_parse_number(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    if s == "":
        return None
    # remove thousands separators and convert parentheses to negative sign
    s = s.replace(",", "")
    s = s.replace("(", "-").replace(")", "")
    # keep digits, decimal point, exponent marker, percent sign, and minus
    s = re.sub(r"[^\d\.\-eE%]", "", s)
    # detect percentage values and adjust after parsing
    is_percent = s.endswith("%")
    if is_percent:
        s = s[:-1]
    try:
        val = float(s)
        if is_percent:
            val = val / 100.0
        return val
    except Exception:
        # if anything fails, return None to indicate non-numeric
        return None


def _try_parse_json_string(val):
    """
    If val is a string that looks like a JSON object/array, try to json.loads it.
    Return the parsed value on success, otherwise return the original val.
    """
    if not isinstance(val, str):
        return val
    s = val.strip()
    if not s:
        return val
    # quick heuristic: if it starts/ends with { } or [ ] attempt to parse
    if (s[0] == "{" and s[-1] == "}") or (s[0] == "[" and s[-1] == "]"):
        try:
            parsed = json.loads(s)
            return parsed
        except Exception:
            return val
    return val

# Load ground truth from XLSX/XLS/CSV into dict docid -> fields dict.
def load_ground_truth(path, id_column):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    elif ext == ".csv":
        df = pd.read_csv(path, dtype=str)
    else:
        raise ValueError(f"Unsupported ground-truth extension: {ext}")
    if id_column not in df.columns:
        raise ValueError(f"id column '{id_column}' not found in ground-truth file. Columns: {list(df.columns)}")
    df = df.fillna("")
    records = {}
    for _, row in df.iterrows():
        docid = str(row[id_column]).strip()
        if not docid:
            continue
        # preserve empty strings; convert to python types where possible (but keep as strings)
        fields = {k: ("" if pd.isna(v) else v) for k, v in row.items() if k != id_column}
        records[docid] = fields
    return records


def load_predictions(path, id_column):
    """
    Load predictions from JSON/JSONL/CSV/XLSX into dict docid -> fields dict.
    This function tolerates values that are raw JSON strings inside cells and expands them.
    """
    ext = os.path.splitext(path)[1].lower()
    # JSON file
    if ext in (".json", ".jsn"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # mapping id -> fields
        if isinstance(data, dict):
            records = {}
            for k, v in data.items():
                docid = str(k).strip()
                v_parsed = _try_parse_json_string(v)
                if isinstance(v_parsed, dict):
                    records[docid] = v_parsed
                else:
                    # store raw value under a generic key
                    records[docid] = {"prediction": v_parsed}
            return records
        # list of objects
        if isinstance(data, list):
            records = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                docid = str(item.get(id_column) or item.get("id") or item.get("document_id") or item.get("doc_id", "")).strip()
                # try other common variants
                if not docid:
                    for candidate in ("documentId", "docId", "doc_id"):
                        if candidate in item:
                            docid = str(item[candidate]).strip()
                            break
                if not docid:
                    # cannot associate; skip
                    continue
                # prefer nested 'fields' if present
                if "fields" in item and isinstance(item["fields"], dict):
                    records[docid] = item["fields"]
                else:
                    fields = {}
                    for k, v in item.items():
                        if k in (id_column, "id", "document_id", "doc_id"):
                            continue
                        v_parsed = _try_parse_json_string(v)
                        if isinstance(v_parsed, dict):
                            # merge into fields, avoid overwrite
                            for fk, fv in v_parsed.items():
                                if fk in fields:
                                    continue
                                fields[fk] = fv
                        else:
                            fields[k] = v_parsed
                    records[docid] = fields
            return records
        raise ValueError("Unsupported JSON prediction structure")
    # JSONL file: one JSON object per line
    elif ext == ".jsonl":
        records = {}
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if not isinstance(item, dict):
                    continue
                docid = str(item.get(id_column) or item.get("id") or item.get("document_id") or item.get("doc_id", "")).strip()
                if not docid:
                    for candidate in ("documentId", "docId", "doc_id"):
                        if candidate in item:
                            docid = str(item[candidate]).strip()
                            break
                if not docid:
                    continue
                if "fields" in item and isinstance(item["fields"], dict):
                    records[docid] = item["fields"]
                else:
                    fields = {}
                    for k, v in item.items():
                        if k in (id_column, "id", "document_id", "doc_id"):
                            continue
                        v_parsed = _try_parse_json_string(v)
                        if isinstance(v_parsed, dict):
                            for fk, fv in v_parsed.items():
                                if fk in fields:
                                    continue
                                fields[fk] = fv
                        else:
                            fields[k] = v_parsed
                    records[docid] = fields
        return records
    # Spreadsheet formats mirror ground truth
    elif ext in (".csv", ".xlsx", ".xls"):
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(path, dtype=str)
        else:
            df = pd.read_csv(path, dtype=str)
        df = df.fillna("")
        if id_column not in df.columns:
            raise ValueError(f"id column '{id_column}' not found in predictions file. Columns: {list(df.columns)}")
        records = {}
        for _, row in df.iterrows():
            docid = str(row[id_column]).strip()
            if not docid:
                continue
            fields = {}
            for k, v in row.items():
                if k == id_column:
                    continue
                v_clean = "" if pd.isna(v) else v
                v_parsed = _try_parse_json_string(v_clean)
                if isinstance(v_parsed, dict):
                    for fk, fv in v_parsed.items():
                        if fk in fields:
                            continue
                        fields[fk] = fv
                else:
                    fields[k] = v_parsed
            records[docid] = fields
        return records
    else:
        raise ValueError(f"Unsupported predictions extension: {ext}")


# -----------------------
# Evaluation logic
# -----------------------
def evaluate(ground_truth, predictions, numeric_tolerance=1e-6, relative_tolerance=False, verbose=False):
    """
    ground_truth: dict docid -> dict(field -> value)
    predictions: dict docid -> dict(field -> value)
    Returns: (report_rows_list, overall_summary_dict, per_doc_diffs_list)
    """
    # per-field statistics container with default counters
    field_stats = defaultdict(lambda: {
        "total": 0,
        "exact_matches": 0,
        "similarity_sum": 0.0,
        "numeric_comparable": 0,
        "numeric_within_tol": 0,
        "missing_predictions": 0,
    })

    # collect per-document diffs when verbose to inspect near-misses
    per_doc_diffs = []

    for docid, gt_fields in ground_truth.items():
        pred_fields = predictions.get(docid, {})
        for field, gt_val in gt_fields.items():
            # skip empty ground truth entries (nothing to evaluate)
            if gt_val is None or (isinstance(gt_val, str) and gt_val.strip() == ""):
                continue
            stats = field_stats[field]
            stats["total"] += 1

            pred_val = pred_fields.get(field, "")
            # bookkeeping for missing predictions
            if pred_val is None or (isinstance(pred_val, str) and pred_val.strip() == ""):
                stats["missing_predictions"] += 1

            # simple exact string match check after trimming
            if str(gt_val).strip() == str(pred_val).strip():
                stats["exact_matches"] += 1

            # compute normalized string similarity
            sim = similarity(gt_val, pred_val)
            stats["similarity_sum"] += sim

            # attempt numeric parsing for numeric comparison
            gt_num = try_parse_number(gt_val)
            pred_num = try_parse_number(pred_val)
            if (gt_num is not None) and (pred_num is not None):
                stats["numeric_comparable"] += 1
                if relative_tolerance:
                    diff = abs(gt_num - pred_num)
                    tol = max(numeric_tolerance, numeric_tolerance * abs(gt_num))
                    if diff <= tol:
                        stats["numeric_within_tol"] += 1
                else:
                    if abs(gt_num - pred_num) <= numeric_tolerance:
                        stats["numeric_within_tol"] += 1

            # add diffs for suspicious items if verbose:
            if verbose:
                numeric_bad = False
                if (gt_num is not None) and (pred_num is not None):
                    if relative_tolerance:
                        tol = max(numeric_tolerance, numeric_tolerance * abs(gt_num))
                    else:
                        tol = numeric_tolerance
                    numeric_bad = abs(gt_num - pred_num) > tol
                if sim < 0.999 or numeric_bad:
                    per_doc_diffs.append({
                        "docid": docid,
                        "field": field,
                        "ground_truth": gt_val,
                        "prediction": pred_val,
                        "similarity": round(sim, 4),
                        "gt_num": gt_num,
                        "pred_num": pred_num,
                    })

    # Aggregate into report
    report = []
    overall = {
        "total_fields": 0,
        "exact_matches": 0,
        "similarity_sum": 0.0,
        "numeric_comparable": 0,
        "numeric_within_tol": 0,
        "missing_predictions": 0,
    }

    for field, stats in field_stats.items():
        total = stats["total"]
        exact = stats["exact_matches"]
        sim_avg = stats["similarity_sum"] / total if total > 0 else 0.0
        num_comp = stats["numeric_comparable"]
        num_within = stats["numeric_within_tol"]
        missing = stats["missing_predictions"]

        report.append({
            "field": field,
            "total": total,
            "exact_matches": exact,
            "exact_match_rate": exact / total if total > 0 else 0.0,
            "avg_similarity": sim_avg,
            "numeric_comparable": num_comp,
            "numeric_within_tolerance": num_within,
            "numeric_within_tolerance_rate": num_within / num_comp if num_comp > 0 else None,
            "missing_predictions": missing,
            "missing_rate": missing / total if total > 0 else 0.0,
        })

        # accumulate overall counters
        overall["total_fields"] += total
        overall["exact_matches"] += exact
        overall["similarity_sum"] += stats["similarity_sum"]
        overall["numeric_comparable"] += num_comp
        overall["numeric_within_tol"] += num_within
        overall["missing_predictions"] += missing

    # compute overall summary metrics (guard against zero totals)
    overall_report = {
        "total_fields": overall["total_fields"],
        "exact_matches": overall["exact_matches"],
        "exact_match_rate": overall["exact_matches"] / overall["total_fields"] if overall["total_fields"] > 0 else 0.0,
        "avg_similarity": overall["similarity_sum"] / overall["total_fields"] if overall["total_fields"] > 0 else 0.0,
        "numeric_comparable": overall["numeric_comparable"],
        "numeric_within_tolerance": overall["numeric_within_tol"],
        "numeric_within_tolerance_rate": overall["numeric_within_tol"] / overall["numeric_comparable"] if overall["numeric_comparable"] > 0 else None,
        "missing_predictions": overall["missing_predictions"],
        "missing_rate": overall["missing_predictions"] / overall["total_fields"] if overall["total_fields"] > 0 else 0.0,
    }

    # sort report by total desc so most frequent fields appear first
    report = sorted(report, key=lambda r: r["total"], reverse=True)
    return report, overall_report, per_doc_diffs


def write_csv_report(report_rows, overall, out_path):
    fieldnames = [
        "field", "total", "exact_matches", "exact_match_rate",
        "avg_similarity", "numeric_comparable", "numeric_within_tolerance",
        "numeric_within_tolerance_rate", "missing_predictions", "missing_rate"
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in report_rows:
            writer.writerow(row)
        # blank row for separation then overall summary row
        writer.writerow({})
        overall_row = {
            "field": "__overall__",
            "total": overall["total_fields"],
            "exact_matches": overall["exact_matches"],
            "exact_match_rate": overall["exact_match_rate"],
            "avg_similarity": overall["avg_similarity"],
            "numeric_comparable": overall["numeric_comparable"],
            "numeric_within_tolerance": overall["numeric_within_tolerance"],
            "numeric_within_tolerance_rate": overall["numeric_within_tolerance_rate"],
            "missing_predictions": overall["missing_predictions"],
            "missing_rate": overall["missing_rate"],
        }
        writer.writerow(overall_row)


def write_diffs(diffs, out_path):
    if not diffs:
        return
    keys = ["docid", "field", "ground_truth", "prediction", "similarity", "gt_num", "pred_num"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in diffs:
            writer.writerow(r)


def main():
    parser = argparse.ArgumentParser(description="Evaluate document-intelligence key-value outputs against Excel ground-truth.")
    parser.add_argument("--ground-truth", "-g", required=True, help="Path to ground-truth spreadsheet (xlsx/xls/csv)")
    parser.add_argument("--predictions", "-p", required=True, help="Path to predictions (json/jsonl/csv/xlsx)")
    parser.add_argument("--id-column", "-i", default="Field", help="Name of the id column in both files (default: Field)")
    parser.add_argument("--numeric-tolerance", "-t", type=float, default=1e-6, help="Absolute numeric tolerance for numeric comparison")
    parser.add_argument("--relative-tolerance", action="store_true", help="Use relative tolerance (tolerance * abs(gt)) when comparing numbers")
    parser.add_argument("--report", "-r", default="evaluation_report.csv", help="Path to write per-field report CSV")
    parser.add_argument("--diffs", "-d", default="differences.csv", help="Path to write per-document differences CSV (only when verbose)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Include per-document diffs for suspicious items")
    args = parser.parse_args()

    gt = load_ground_truth(args.ground_truth, args.id_column)
    preds = load_predictions(args.predictions, args.id_column)

    report, overall, diffs = evaluate(gt, preds, numeric_tolerance=args.numeric_tolerance,
                                     relative_tolerance=args.relative_tolerance,
                                     verbose=args.verbose)

    write_csv_report(report, overall, args.report)
    if args.verbose:
        write_diffs(diffs, args.diffs)

    print(f"Report written to: {args.report}")
    if args.verbose:
        print(f"Differences written to: {args.diffs}")
    print(f"Overall exact match rate: {overall['exact_match_rate']:.3f}")
    print(f"Overall avg similarity: {overall['avg_similarity']:.3f}")


if __name__ == "__main__":
    main()