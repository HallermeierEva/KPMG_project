"""
Azure OpenAI GPT-4o Field Extraction Service
Extracts structured fields from OCR text using intelligent prompting
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FieldExtractionService:
    """
    Service for extracting structured fields from OCR text using Azure OpenAI GPT-4o
    Handles both Hebrew and English forms
    """

    def __init__(self):
        """Initialize the Azure OpenAI client"""
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.deployment = os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT", "gpt-4o")

        if not self.endpoint or not self.api_key:
            raise ValueError(
                "Missing Azure OpenAI credentials. "
                "Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY in your .env file"
            )

        # Initialize OpenAI client
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint
        )

        # Load extraction prompt template
        self.prompt_template = self._load_prompt_template()

        logger.info("Field Extraction Service initialized successfully")

    def _load_prompt_template(self) -> str:
        """Load the extraction prompt template from file"""
        try:
            prompt_file = os.path.join(
                os.path.dirname(__file__),
                "prompts",
                "extraction_prompt.txt"
            )

            if os.path.exists(prompt_file):
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"Prompt file not found: {prompt_file}, using default prompt")
                return self._get_default_prompt()

        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Get default extraction prompt if file not found"""
        return """Extract all fields from the following OCR text and return as JSON.
Use empty strings for missing fields.

OCR Text:
{ocr_text}

Return only valid JSON in this format:
{
  "lastName": "",
  "firstName": "",
  "idNumber": "",
  ...
}
"""

    def extract_fields(
            self,
            ocr_text: str,
            temperature: float = 0.0,
            max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Extract structured fields from OCR text using GPT-4o

        Args:
            ocr_text: Raw text extracted from OCR
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_retries: Maximum number of retry attempts

        Returns:
            Dictionary containing extracted fields in the required JSON format
        """
        logger.info(f"Extracting fields from OCR text ({len(ocr_text)} characters)")

        # Prepare the prompt
        prompt = self.prompt_template.replace("{ocr_text}", ocr_text)

        for attempt in range(max_retries):
            try:
                # Call Azure OpenAI
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert data extraction assistant. Return only valid JSON, no additional text."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=temperature,
                    max_tokens=2000,
                    response_format={"type": "json_object"}  # Ensure JSON output
                )

                # Extract the response
                extracted_text = response.choices[0].message.content.strip()

                # Parse JSON
                extracted_data = json.loads(extracted_text)

                # Validate the structure
                validated_data = self._validate_and_fill_schema(extracted_data)

                logger.info("Field extraction completed successfully")
                return {
                    "success": True,
                    "data": validated_data,
                    "raw_response": extracted_text,
                    "error": None
                }

            except json.JSONDecodeError as e:
                logger.warning(f"Attempt {attempt + 1}: JSON parsing error: {e}")
                if attempt == max_retries - 1:
                    logger.error("Failed to parse JSON after all retries")
                    return {
                        "success": False,
                        "data": self._get_empty_schema(),
                        "raw_response": extracted_text if 'extracted_text' in locals() else "",
                        "error": f"JSON parsing error: {str(e)}"
                    }

            except Exception as e:
                logger.error(f"Attempt {attempt + 1}: Extraction error: {e}")
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "data": self._get_empty_schema(),
                        "raw_response": "",
                        "error": str(e)
                    }

        # Should not reach here
        return {
            "success": False,
            "data": self._get_empty_schema(),
            "raw_response": "",
            "error": "Unknown error"
        }

    def _validate_and_fill_schema(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted data and ensure all required fields are present
        Fill missing fields with empty strings

        Args:
            extracted_data: Data extracted by GPT-4o

        Returns:
            Complete schema with all fields
        """
        schema = self._get_empty_schema()

        # Recursively merge extracted data into schema
        def merge_dict(target: dict, source: dict) -> dict:
            for key, value in source.items():
                if key in target:
                    if isinstance(target[key], dict) and isinstance(value, dict):
                        merge_dict(target[key], value)
                    else:
                        # Only update if value is not None
                        if value is not None:
                            target[key] = value
            return target

        result = merge_dict(schema, extracted_data)
        return result

    def _get_empty_schema(self) -> Dict[str, Any]:
        """Get the empty schema template with all fields"""
        return {
            "lastName": "",
            "firstName": "",
            "idNumber": "",
            "gender": "",
            "dateOfBirth": {
                "day": "",
                "month": "",
                "year": ""
            },
            "address": {
                "street": "",
                "houseNumber": "",
                "entrance": "",
                "apartment": "",
                "city": "",
                "postalCode": "",
                "poBox": ""
            },
            "landlinePhone": "",
            "mobilePhone": "",
            "jobType": "",
            "dateOfInjury": {
                "day": "",
                "month": "",
                "year": ""
            },
            "timeOfInjury": "",
            "accidentLocation": "",
            "accidentAddress": "",
            "accidentDescription": "",
            "injuredBodyPart": "",
            "signature": "",
            "formFillingDate": {
                "day": "",
                "month": "",
                "year": ""
            },
            "formReceiptDateAtClinic": {
                "day": "",
                "month": "",
                "year": ""
            },
            "medicalInstitutionFields": {
                "healthFundMember": "",
                "natureOfAccident": "",
                "medicalDiagnoses": ""
            }
        }

    def extract_from_file(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract fields from an OCR result dictionary

        Args:
            ocr_result: Result from OCR service containing 'full_text' key

        Returns:
            Extraction result dictionary
        """
        if not ocr_result.get("success"):
            return {
                "success": False,
                "data": self._get_empty_schema(),
                "raw_response": "",
                "error": "OCR processing failed"
            }

        ocr_text = ocr_result.get("full_text", "")

        if not ocr_text:
            return {
                "success": False,
                "data": self._get_empty_schema(),
                "raw_response": "",
                "error": "No OCR text available"
            }

        return self.extract_fields(ocr_text)

    def batch_extract(self, ocr_results: list) -> list:
        """
        Extract fields from multiple OCR results

        Args:
            ocr_results: List of OCR result dictionaries

        Returns:
            List of extraction results
        """
        results = []

        for i, ocr_result in enumerate(ocr_results):
            logger.info(f"Processing document {i + 1}/{len(ocr_results)}")
            result = self.extract_from_file(ocr_result)
            results.append(result)

        return results


# Test function
if __name__ == "__main__":
    """Test the extraction service"""

    # Sample OCR text for testing
    sample_ocr_text = """
    עמוד 1 מתוך 2
    המוסד לביטוח לאומי מינהל הגמלאות

    בקשה למתן טיפול רפואי לנפגע עבודה - עצמאי

    שם משפחה: כהן
    שם פרטי: דוד
    מספר זהות: 123456789
    מין: זכר
    תאריך לידה: 15 03 1985

    כתובת:
    רחוב: הרצל
    מספר בית: 25
    דירה: 10
    ישוב: תל אביב
    מיקוד: 6688201

    טלפון נייד: 0501234567

    תאריך הפגיעה: 10 06 2023
    שעת הפגיעה: 14:30
    מקום התאונה: אתר בנייה
    תיאור התאונה: נפילה מגובה
    האיבר שנפגע: יד ימין

    תאריך מילוי הטופס: 12 06 2023
    """

    print("=" * 70)
    print("🧪  TESTING FIELD EXTRACTION SERVICE")
    print("=" * 70)

    try:
        # Initialize service
        print("\n1. Initializing extraction service...")
        extractor = FieldExtractionService()
        print("   ✅ Service initialized")

        # Extract fields
        print("\n2. Extracting fields from sample text...")
        result = extractor.extract_fields(sample_ocr_text)

        if result["success"]:
            print("   ✅ Extraction successful!")
            print("\n📊 Extracted Data:")
            print(json.dumps(result["data"], indent=2, ensure_ascii=False))
        else:
            print(f"   ❌ Extraction failed: {result['error']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)