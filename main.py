"""
This Add-On uses Azure's Document Intelligence API
to perform OCR on documents within DocumentCloud
"""
import os
import re
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from documentcloud.addon import AddOn


class DocumentIntelligence(AddOn):
    """Class for Document Intelligence Add-On"""

    def validate(self):
        """Validate that we can run the OCR"""
        if self.get_document_count() is None:
            self.set_message(
                "It looks like no documents were selected. Search for some or "
                "select them and run again."
            )
            return False
        elif not self.org_id:
            self.set_message("No organization to charge.")
            return False
        else:
            num_pages = 0
            for document in self.get_documents():
                num_pages += document.page_count
            resp = self.client.post(
                f"organizations/{self.org_id}/ai_credits/",
                json={"ai_credits": num_pages},
            )
            if resp.status_code != 200:
                self.set_message("Error charging AI credits.")
                return False
        return True

    def convert_coordinates(self, polygon, page_width, page_height):
        """Converts Azure's absolute coordinates to relative
        page coordinates used by Documentcloud
        """
        x_values = [point.x for point in polygon]
        y_values = [point.y for point in polygon]

        x1 = min(x_values)
        x2 = max(x_values)
        y1 = min(y_values)
        y2 = max(y_values)

        x1_percentage = max(0, min(1, (x1 / page_width)))
        x2_percentage = max(0, min(1, (x2 / page_width)))
        y1_percentage = max(0, min(1, (y1 / page_height)))
        y2_percentage = max(0, min(1, (y2 / page_height)))

        return x1_percentage, x2_percentage, y1_percentage, y2_percentage

    def main(self):
        """The main add-on functionality goes here."""
        if not self.validate():
            # if not validated, return immediately
            return
        key = os.environ.get("KEY")
        endpoint = os.environ.get("TOKEN")
        document_analysis_client = DocumentAnalysisClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )
        for document in self.get_documents():
            if document.access != "public":
                self.set_message("Document must be public")
                return
            form_url = document.pdf_url
            poller = document_analysis_client.begin_analyze_document_from_url(
                "prebuilt-read", form_url
            )
            result = poller.result()
            pages = []
            for i, page in enumerate(result.pages):
                dc_page = {
                    "page_number": i,
                    "text": "\n".join(
                        [
                            ""
                            if re.match(r"^[:.\-]*$", line.content.strip())
                            else line.content
                            for line in page.lines
                        ]
                    ),
                    "ocr": "azuredi",
                    "positions": [],
                }
                for word in page.words:
                    x1, x2, y1, y2 = self.convert_coordinates(
                        word.polygon, page.width, page.height
                    )
                    position_info = {
                        "text": word.content,
                        "x1": x1,
                        "x2": x2,
                        "y1": y1,
                        "y2": y2,
                    }
                    dc_page["positions"].append(position_info)

                pages.append(dc_page)

            resp = self.client.patch(f"documents/{document.id}/", json={"pages": pages})
            resp.raise_for_status()


if __name__ == "__main__":
    DocumentIntelligence().main()
