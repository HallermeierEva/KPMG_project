"""
Azure Document Intelligence OCR Service
Handles PDF/Image processing and text extraction
"""

import os
import base64
from typing import Dict, List, Optional, Any
from io import BytesIO
from dotenv import load_dotenv
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentOCRService:
    """
    Service for extracting text and layout from documents using Azure Document Intelligence
    Supports both Hebrew and English text
    """

    def __init__(self):
        """Initialize the Document Analysis client"""
        self.endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not self.endpoint or not self.key:
            raise ValueError(
                "Missing Azure Document Intelligence credentials. "
                "Please set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and "
                "AZURE_DOCUMENT_INTELLIGENCE_KEY in your .env file"
            )

        # Initialize client with stable API
        self.client = DocumentAnalysisClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )

        logger.info("Document Intelligence OCR Service initialized successfully")

    def analyze_document(
            self,
            file_content: bytes,
            content_type: str = "application/pdf"
    ) -> Any:
        """
        Analyze document using Azure Document Intelligence Layout model

        Args:
            file_content: Binary content of the document (PDF or image)
            content_type: MIME type of the document
                         (application/pdf, image/jpeg, image/png)

        Returns:
            AnalyzeResult object containing extracted text and layout
        """
        logger.info(f"Starting document analysis with content type: {content_type}")

        try:
            # Use the layout model (prebuilt-layout) for text extraction
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-layout",
                document=file_content
            )

            # Wait for the analysis to complete
            result = poller.result()

            logger.info("Document analysis completed successfully")
            return result

        except Exception as e:
            logger.error(f"Error during document analysis: {str(e)}")
            raise

    def extract_text(self, analyze_result: Any) -> str:
        """
        Extract all text content from the analysis result

        Args:
            analyze_result: Result from Document Intelligence analysis

        Returns:
            Concatenated text from all pages
        """
        try:
            full_text = ""

            if analyze_result.content:
                full_text = analyze_result.content

            logger.info(f"Extracted text length: {len(full_text)} characters")
            return full_text

        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            return ""

    def extract_structured_content(self, analyze_result: Any) -> Dict[str, Any]:
        """
        Extract structured content including pages, paragraphs, tables, and key-value pairs

        Args:
            analyze_result: Result from Document Intelligence analysis

        Returns:
            Dictionary with structured content
        """
        try:
            structured_data = {
                "pages": [],
                "paragraphs": [],
                "tables": [],
                "key_value_pairs": [],
                "full_text": ""
            }

            # Extract full text
            if analyze_result.content:
                structured_data["full_text"] = analyze_result.content

            # Extract pages information
            if analyze_result.pages:
                for page_num, page in enumerate(analyze_result.pages, start=1):
                    page_info = {
                        "page_number": page_num,
                        "width": page.width,
                        "height": page.height,
                        "angle": page.angle if hasattr(page, 'angle') else 0,
                        "unit": page.unit if hasattr(page, 'unit') else "pixel",
                        "lines": []
                    }

                    # Extract lines from the page
                    if hasattr(page, 'lines') and page.lines:
                        for line in page.lines:
                            page_info["lines"].append({
                                "content": line.content,
                                "bounding_box": line.polygon if hasattr(line, 'polygon') else []
                            })

                    structured_data["pages"].append(page_info)

            # Extract paragraphs
            if analyze_result.paragraphs:
                for para in analyze_result.paragraphs:
                    structured_data["paragraphs"].append({
                        "content": para.content,
                        "role": para.role if hasattr(para, 'role') else None,
                        "bounding_regions": para.bounding_regions if hasattr(para, 'bounding_regions') else []
                    })

            # Extract tables
            if analyze_result.tables:
                for table_idx, table in enumerate(analyze_result.tables):
                    table_data = {
                        "table_index": table_idx,
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells": []
                    }

                    if table.cells:
                        for cell in table.cells:
                            table_data["cells"].append({
                                "row_index": cell.row_index,
                                "column_index": cell.column_index,
                                "content": cell.content,
                                "row_span": cell.row_span if hasattr(cell, 'row_span') else 1,
                                "column_span": cell.column_span if hasattr(cell, 'column_span') else 1
                            })

                    structured_data["tables"].append(table_data)

            # Extract key-value pairs (if available)
            if hasattr(analyze_result, 'key_value_pairs') and analyze_result.key_value_pairs:
                for kv_pair in analyze_result.key_value_pairs:
                    if kv_pair.key and kv_pair.value:
                        structured_data["key_value_pairs"].append({
                            "key": kv_pair.key.content if hasattr(kv_pair.key, 'content') else str(kv_pair.key),
                            "value": kv_pair.value.content if hasattr(kv_pair.value, 'content') else str(kv_pair.value)
                        })

            logger.info(
                f"Extracted structured content: "
                f"{len(structured_data['pages'])} pages, "
                f"{len(structured_data['paragraphs'])} paragraphs, "
                f"{len(structured_data['tables'])} tables"
            )

            return structured_data

        except Exception as e:
            logger.error(f"Error extracting structured content: {str(e)}")
            return {
                "pages": [],
                "paragraphs": [],
                "tables": [],
                "key_value_pairs": [],
                "full_text": ""
            }

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a file (PDF or image) and extract all content

        Args:
            file_path: Path to the file to process

        Returns:
            Dictionary containing extracted text and structured content
        """
        try:
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Determine content type
            if file_path.lower().endswith('.pdf'):
                content_type = "application/pdf"
            elif file_path.lower().endswith(('.jpg', '.jpeg')):
                content_type = "image/jpeg"
            elif file_path.lower().endswith('.png'):
                content_type = "image/png"
            else:
                raise ValueError(f"Unsupported file type: {file_path}")

            # Analyze document
            result = self.analyze_document(file_content, content_type)

            # Extract content
            full_text = self.extract_text(result)
            structured_content = self.extract_structured_content(result)

            return {
                "success": True,
                "full_text": full_text,
                "structured_content": structured_content,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return {
                "success": False,
                "full_text": "",
                "structured_content": {},
                "error": str(e)
            }

    def process_uploaded_file(self, uploaded_file) -> Dict[str, Any]:
        """
        Process an uploaded file from Streamlit

        Args:
            uploaded_file: Streamlit UploadedFile object

        Returns:
            Dictionary containing extracted text and structured content
        """
        try:
            # Read file content
            file_content = uploaded_file.read()

            # Determine content type based on file name
            file_name = uploaded_file.name.lower()
            if file_name.endswith('.pdf'):
                content_type = "application/pdf"
            elif file_name.endswith(('.jpg', '.jpeg')):
                content_type = "image/jpeg"
            elif file_name.endswith('.png'):
                content_type = "image/png"
            else:
                raise ValueError(f"Unsupported file type: {file_name}")

            # Analyze document
            result = self.analyze_document(file_content, content_type)

            # Extract content
            full_text = self.extract_text(result)
            structured_content = self.extract_structured_content(result)

            return {
                "success": True,
                "full_text": full_text,
                "structured_content": structured_content,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error processing uploaded file: {str(e)}")
            return {
                "success": False,
                "full_text": "",
                "structured_content": {},
                "error": str(e)
            }


# Test function
if __name__ == "__main__":
    """Test the OCR service with a sample file"""

    # Initialize service
    ocr_service = DocumentOCRService()

    # Test with a sample file (update path as needed)
    test_file = "sample_form.pdf"

    if os.path.exists(test_file):
        print(f"Processing {test_file}...")
        result = ocr_service.process_file(test_file)

        if result["success"]:
            print("\n✅ OCR Successful!")
            print(f"Extracted text length: {len(result['full_text'])} characters")
            print(f"\nFirst 500 characters:\n{result['full_text'][:500]}")
        else:
            print(f"\n❌ OCR Failed: {result['error']}")
    else:
        print(f"Test file {test_file} not found")
        print("\nOCR Service initialized successfully!")
        print("Ready to process documents.")