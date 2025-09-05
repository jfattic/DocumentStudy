import os

def analyze_query_fields():
    # [START analyze_query_fields]
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentAnalysisFeature, AnalyzeResult
    import json
    
    endpoint = "https://docintelgmcopilot.cognitiveservices.azure.com/"
    key = "60bd3ea71602420ea4bbef6904ab2c5c"

    path_to_sample_documents = "C://Users//jfattic//Desktop//Daggerheart//Quickstart-Adventure-5-20-2025.pdf"

    document_intelligence_client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

     # Analyze a document at a URL:
    formUrl = "https://stgfaxes.blob.core.windows.net/raw/Quickstart-Adventure-5-20-2025.pdf"
    # Replace with your actual formUrl:
    # If you use the URL of a public website, to find more URLs, please visit: https://aka.ms/more-URLs 
    # If you analyze a document in Blob Storage, you need to generate Public SAS URL, please visit: https://aka.ms/create-sas-tokens
    poller = document_intelligence_client.begin_analyze_document(
        "prebuilt-layout",
        AnalyzeDocumentRequest(url_source=formUrl), 
        pages="7",
        features=[DocumentAnalysisFeature.QUERY_FIELDS],    # Specify which add-on capabilities to enable.
        query_fields=["Name", "Pronouns", "Heritage", "Subclass", "Evasion", "Armor"],  # Set the features and provide a comma-separated list of field names.
    )       
    
    # # If analyzing a local document, remove the comment markers (#) at the beginning of these 11 lines.
    # # Delete or comment out the part of "Analyze a document at a URL" above.
    # # Replace <path to your sample file>  with your actual file path.
    # path_to_sample_document = "<path to your sample file>"
    # with open(path_to_sample_document, "rb") as f:
    #   poller = document_intelligence_client.begin_analyze_document(
    #       "prebuilt-layout",
    #       analyze_request=f,  
    #       features=[DocumentAnalysisFeature.QUERY_FIELDS],    # Specify which add-on capabilities to enable.
    #       query_fields=["Address", "InvoiceNumber"],  # Set the features and provide a comma-separated list of field names.
    #       content_type="application/octet-stream",
    # Fetch the result, emit JSONL to stdout and write to predictions.jsonl, then return to skip original prints.
    result = poller.result()
    output_path = os.path.join(os.getcwd(), "predictions.jsonl")
    with open(output_path, "w", encoding="utf-8") as out_f:
        if result.documents:
            for doc in result.documents:
                obj = {}
                if doc.fields:
                    for key in ["Name", "Pronouns", "Heritage", "Subclass", "Evasion", "Armor"]:
                        field = doc.fields.get(key)
                        if field:
                            # Prefer string representation if available, otherwise fallback to generic value
                            value = getattr(field, "value_string", None)
                            if value is None:
                                value = getattr(field, "value", None)
                            obj[key] = value
                line = json.dumps(obj, ensure_ascii=False)
                out_f.write(line + "\n")
                print(line)
    return
    # [END analyze_query_fields]

analyze_query_fields()