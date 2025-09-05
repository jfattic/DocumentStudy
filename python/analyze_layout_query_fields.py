import os

def analyze_query_fields():
    # [START analyze_query_fields]
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentAnalysisFeature, AnalyzeResult
    
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
    #   )
    result: AnalyzeResult = poller.result()
    print("Here are extra fields in result:\n")
    if result.documents:
        for doc in result.documents:
            if doc.fields and doc.fields["Name"]:
                print(f"Address: {doc.fields['Name'].value_string}")
            if doc.fields and doc.fields["Pronouns"]:
                print(f"Invoice number: {doc.fields['Pronouns'].value_string}")
            if doc.fields and doc.fields["Heritage"]:
                print(f"Heritage: {doc.fields['Heritage'].value_string}")
            if doc.fields and doc.fields["Subclass"]:
                print(f"Subclass: {doc.fields['Subclass'].value_string}")
            if doc.fields and doc.fields["Evasion"]:
                print(f"Evasion: {doc.fields['Evasion'].value_string}")
            if doc.fields and doc.fields["Armor"]:
                print(f"Armor: {doc.fields['Armor'].value_string}")
    # [END analyze_query_fields]

analyze_query_fields()