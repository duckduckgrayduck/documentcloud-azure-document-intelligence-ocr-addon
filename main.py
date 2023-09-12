"""
This Add-On uses Azure's Document Intelligence API
to perform OCR on documents within DocumentCloud
"""
import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from documentcloud.addon import AddOn

class DocumentIntelligence(AddOn):
    """Class for Document Intelligence Add-On"""

    def main(self):
        """The main add-on functionality goes here."""
        key = os.environ.get('KEY')
        endpoint = os.environ.get('TOKEN')
        document_analysis_client = DocumentAnalysisClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )
        for document in self.get_documents():
            if document.access != "public":
                self.set_message("Document must be public")
                return
            formUrl = document.pdf_url
            poller = document_analysis_client.begin_analyze_document_from_url(
                "prebuilt-read", formUrl
            )
            result = poller.result()
            pages = []
            for i,page in enumerate(result.pages):
                dc_page = {
                    "page_number": i,
                    "text": '\n'.join([line.content for line in page.lines]),
                    "ocr": "azuredi",
                    "positions": [],
                }
                pages.append(dc_page)
        resp = self.client.patch(f"documents/{document.id}/", json={"pages": pages})
        resp.raise_for_status()

if __name__ == "__main__":
    DocumentIntelligence().main()
