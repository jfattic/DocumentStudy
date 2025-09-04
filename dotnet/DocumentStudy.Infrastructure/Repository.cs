using Azure;
using Azure.AI.DocumentIntelligence;
using Azure.Storage.Blobs;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.SemanticKernel;
using System.Text;

namespace DocumentStudy.Infrastructure;

public class Repository(
    [FromKeyedServices("rules")] BlobContainerClient rulesContainerClient,
    DocumentIntelligenceClient documentIntelligenceClient,
    Kernel kernel)
{
    public async ValueTask<string> UploadDocumentAsync(
    string campaignId,
    string fileName,
    Stream fileContent,
    CancellationToken cancellation = default)
    {
        string blobPath = $"{campaignId}/raw/{fileName}";
        var blobClient = rulesContainerClient.GetBlobClient(blobPath);
        await blobClient.UploadAsync(fileContent, overwrite: true, cancellationToken: cancellation);

        // Get the blob's URL for linking
        string rawDocumentUrl = blobClient.Uri.ToString();

        // Analyze only the first ten pages using Document Intelligence
        AnalyzeDocumentOptions docIntelOptions = new("prebuilt-layout", new Uri(rawDocumentUrl))
        {
            //Pages = "1-10", // Only analyze the first ten pages
            OutputContentFormat = DocumentContentFormat.Markdown
        };
        var analysis = await documentIntelligenceClient.AnalyzeDocumentAsync(
            WaitUntil.Completed, docIntelOptions, cancellation);

        string markdown = analysis.Value.Content ?? string.Empty;

        // Use the analysis result to get accurate page information
        var chunks = ChunkMarkdownByHeadingsWithActualPageNumbers(markdown, analysis.Value);

        // Write each chunk to the cooked folder, capturing metadata
        int chunkIndex = 0;
        foreach (var (Content, PageNumber) in chunks)
        {
            string cookedPath = $"{campaignId}/cooked/{fileName}_{chunkIndex:D7}.md";
            var cookedBlob = rulesContainerClient.GetBlobClient(cookedPath);
            using var chunkStream = new MemoryStream(Encoding.UTF8.GetBytes(Content));
            await cookedBlob.UploadAsync(chunkStream, overwrite: true, cancellationToken: cancellation);

            var tags = new Dictionary<string, string>
            {
                ["campaignId"] = campaignId,
                ["isActive"] = "true", // Default to active
            };
            await cookedBlob.SetTagsAsync(tags, cancellationToken: cancellation);

            var metadata = new Dictionary<string, string>
            {
                ["pageNumber"] = PageNumber.ToString(),
                ["sourceDocument"] = rawDocumentUrl
            };
            await cookedBlob.SetMetadataAsync(metadata, cancellationToken: cancellation);
            chunkIndex++;
        }

        return blobPath;
    }

    // Helper to chunk markdown by headings using actual page numbers from Document Intelligence
    private static List<(string Content, int PageNumber)> ChunkMarkdownByHeadingsWithActualPageNumbers(
        string markdown, AnalyzeResult analyzeResult)
    {
        var lines = markdown.Split('\n');
        var chunks = new List<(string Content, int PageNumber)>();
        var currentChunk = new List<string>();
        int currentCharOffset = 0;
        int currentPage = 1;

        // Build a lookup of character offset to page number using paragraphs
        var offsetToPageMap = BuildOffsetToPageMap(analyzeResult);

        foreach (var line in lines)
        {
            if (line.StartsWith('#'))
            {
                if (currentChunk.Count > 0)
                {
                    chunks.Add((string.Join("\n", currentChunk), currentPage));
                    currentChunk.Clear();
                }

                // Determine the page number for this heading based on character offset
                if (offsetToPageMap.TryGetValue(currentCharOffset, out int pageAtOffset))
                {
                    currentPage = pageAtOffset;
                }
                else
                {
                    // Find the closest offset that's less than or equal to currentCharOffset
                    var closestOffset = offsetToPageMap.Keys
                        .Where(offset => offset <= currentCharOffset)
                        .DefaultIfEmpty(0)
                        .Max();

                    if (offsetToPageMap.TryGetValue(closestOffset, out int closestPage))
                    {
                        currentPage = closestPage;
                    }
                }
            }

            currentChunk.Add(line);
            currentCharOffset += line.Length + 1; // +1 for the newline character
        }

        if (currentChunk.Count > 0)
            chunks.Add((string.Join("\n", currentChunk), currentPage));

        return chunks;
    }

    // Build a map of character offsets to page numbers using paragraphs from Document Intelligence
    private static Dictionary<int, int> BuildOffsetToPageMap(AnalyzeResult analyzeResult)
    {
        var offsetToPageMap = new Dictionary<int, int>();

        // Use paragraphs to map character spans to page numbers
        if (analyzeResult.Paragraphs != null)
        {
            foreach (var paragraph in analyzeResult.Paragraphs)
            {
                if (paragraph.Spans != null && paragraph.BoundingRegions != null && paragraph.BoundingRegions.Count > 0)
                {
                    foreach (var span in paragraph.Spans)
                    {
                        // Use the page number from the first bounding region
                        var firstBoundingRegion = paragraph.BoundingRegions[0];
                        offsetToPageMap[span.Offset] = firstBoundingRegion.PageNumber;
                    }
                }
            }
        }

        return offsetToPageMap;
    }
}
