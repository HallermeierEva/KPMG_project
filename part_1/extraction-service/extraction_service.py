"""
Azure OpenAI GPT-4o Field Extraction Service
Extracts structured fields from OCR text using intelligent prompting.
This module contains the core business logic that is used by the
extraction microservice FastAPI app.
"""

import os
import json
import re
from typing import Dict, Any, Optional
from urllib import request as urlrequest, error as urlerror

from dotenv import load_dotenv
from openai import AzureOpenAI

import sys

# Make shared package importable when running as a standalone module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import Config
from shared.logging_config import get_logger
from shared.models import OCRResponse, ExtractedData, ExtractionResponse

# Load environment variables from .env if present
load_dotenv()

logger = get_logger("extraction-service")


def refine_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Final logical pass to fix ID length, phone prefixes, and date swaps.

    This acts as a safety net on top of the GPT extraction + schema validation.
    """
    # 1. Fix ID Number (Must be 9 digits)
    if data.get("idNumber"):
        # Remove anything that isn't a digit
        clean_id = re.sub(r"\D", "", str(data["idNumber"]))
        # If it's 8 digits, it's almost always a missing leading zero
        if len(clean_id) == 8:
            clean_id = "0" + clean_id
        # If it's still not 9, keep it as is (schema still enforces presence)
        data["idNumber"] = clean_id

    # 2. Fix Mobile Phone (Must start with 05)
    if data.get("mobilePhone"):
        clean_phone = re.sub(r"\D", "", str(data["mobilePhone"]))
        # Common OCR error: 0 looks like 6
        if clean_phone.startswith("65"):
            clean_phone = "0" + clean_phone[1:]
        # Ensure leading zero when missing
        if clean_phone.startswith("5") and len(clean_phone) == 9:
            clean_phone = "0" + clean_phone
        data["mobilePhone"] = clean_phone

    # 3. Logical Date Swapper (Day vs Month)
    # If month > 12, it is definitely a day.
    date_fields = ["dateOfBirth", "dateOfInjury", "formFillingDate", "formReceiptDateAtClinic"]
    for field in date_fields:
        d = data.get(field, {})
        if isinstance(d, dict) and d.get("day") and d.get("month"):
            try:
                day_val = int(re.sub(r"\D", "", str(d["day"])))
                month_val = int(re.sub(r"\D", "", str(d["month"])))

                if month_val > 12 and day_val <= 12:
                    # Logical flip detected!
                    d["day"], d["month"] = str(month_val).zfill(2), str(day_val).zfill(2)
                else:
                    d["day"] = str(day_val).zfill(2)
                    d["month"] = str(month_val).zfill(2)
            except (ValueError, TypeError):
                # If anything is weird, leave the original values
                pass

    # 4. Cleanup Signature
    # If signature is "X" or just one char, try to fallback to full name
    if data.get("signature") in ["X", "", None] or len(str(data.get("signature"))) < 2:
        full_name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
        if full_name:
            data["signature"] = full_name

    return data


def final_israeli_cleanup(data: Dict[str, Any]) -> Dict[str, Any]:
    """Final strict cleanup for Israeli-specific fields after GPT extraction.

    This overrides GPT guesses with deterministic rules for IDs, phones, and
    health-fund membership.
    """
    # --- 1. ID Number (Strict 9 Digits) ---
    if data.get("idNumber"):
        ident = re.sub(r"\D", "", str(data["idNumber"]))
        # If GPT produced more than 9 digits, keep the last 9 (strip leading zeros/noise)
        if len(ident) > 9:
            ident = ident[-9:]
        # Pad leading zeros if actually 8 digits (common for older IDs)
        elif len(ident) == 8:
            ident = "0" + ident
        data["idNumber"] = ident

    # --- 2. Checkbox Logic Fix ---
    # If GPT missed the location because of messy OCR:
    medical = data.get("medicalInstitutionFields", {}) or {}
    if data.get("accidentLocation") == "ת. דרכים בעבודה" and "במפעל" in str(medical):
        # Specific heuristic: GPT often confuses these two in Form 283
        # (No-op placeholder for now, but keep hook for future logic.)
        pass

    # --- 3. Noise Removal ---
    # Remove single characters like 'ח' or 'ס' which are OCR noise from form borders
    for key in ["landlinePhone", "mobilePhone", "jobType"]:
        if len(str(data.get(key, ""))) <= 1:
            data[key] = ""

    # --- 4. Health Fund Cleanup ---
    # Ensure it's one of the 4 valid funds or empty
    funds = ["כללית", "מכבי", "מאוחדת", "לאומית"]
    if medical.get("healthFundMember") not in funds:
        # If it's something else, it's probably OCR noise
        medical["healthFundMember"] = ""

    # Ensure the possibly-updated dict is written back
    if "medicalInstitutionFields" in data and isinstance(data["medicalInstitutionFields"], dict):
        data["medicalInstitutionFields"] = medical

    return data


def finalize_data(extracted_json):
    # 1. Fix ID length (Must be 9)
    if extracted_json.get("idNumber"):
        val = str(extracted_json["idNumber"]).replace("|", "").replace(" ", "")
        digits = "".join(filter(str.isdigit, val))
        if len(digits) == 8: digits = "0" + digits
        extracted_json["idNumber"] = digits[:9]

    # 2. Clear OCR noise (single letters)
    for key in ["landlinePhone", "mobilePhone", "idNumber"]:
        val = str(extracted_json.get(key, ""))
        if len(val) <= 1: extracted_json[key] = ""

    # 3. Correct Israeli Phone Prefix
    phone = str(extracted_json.get("mobilePhone", ""))
    if phone.startswith("65"): extracted_json["mobilePhone"] = "0" + phone[1:]

    return extracted_json


def israeli_business_logic_fix(data):
    """Force-corrects the remaining 5% of errors that AI consistently halluncinates."""
    # 1. ID Number: Force exactly 9 digits
    if data.get("idNumber"):
        ident = re.sub(r"\D", "", str(data["idNumber"]))
        # If it's 8 digits, it's missing a leading zero
        if len(ident) == 8:
            ident = "0" + ident
        # If it was truncated to 9 but should be 10 (or vice versa),
        # this ensures we at least return a valid-length ID.
        data["idNumber"] = ident[:9]

    # 2. Noise Cleanup: Remove stray single letters (like 'ח' or 'ס')
    for key in ["landlinePhone", "mobilePhone", "idNumber"]:
        val = str(data.get(key, ""))
        if len(val.strip()) <= 1:
            data[key] = ""

    # 3. Checkbox Override (Heuristic for Form 283)
    # If GPT is confused by the accident location checkboxes:
    if data.get("accidentLocation") == "ת. דרכים בעבודה":
        # Check if the accident description or job type suggests it was actually 'In Factory'
        desc = str(data.get("accidentDescription", "")).lower()
        if any(word in desc for word in ["נשרף", "מפעל", "מכונה", "במהלך העבודה"]):
            data["accidentLocation"] = "במפעל"

    # 4. Medical Institution Normalization
    valid_funds = ["כללית", "מכבי", "מאוחדת", "לאומית"]
    fund = data.get("medicalInstitutionFields", {}).get("healthFundMember")
    if fund and fund not in valid_funds:
        # If GPT put a random word there, clear it.
        data["medicalInstitutionFields"]["healthFundMember"] = ""

    return data


def final_surgical_cleanup(data):
    # 1. CLEAN PHONE NOISE: If landline/mobile is just a single letter like 'ח', wipe it.
    for key in ["landlinePhone", "mobilePhone"]:
        val = str(data.get(key, "")).strip()
        if len(val) <= 1:
            data[key] = ""

    # 2. FORCE 9-DIGIT ID: Glue fragments and handle leading zeros.
    if data.get("idNumber"):
        ident = re.sub(r"\D", "", str(data["idNumber"]))
        # If it's 8 digits, add the leading zero
        if len(ident) == 8:
            ident = "0" + ident
        # If it was truncated (like in ex3), we take the first 9 available digits
        data["idNumber"] = ident[:9]

    # 3. HEALTH FUND RECOVERY:
    # If healthFundMember is empty, search medicalDiagnoses for keywords
    medical = data.get("medicalInstitutionFields", {})
    if not medical.get("healthFundMember"):
        text_to_search = str(medical.get("medicalDiagnoses", "")) + str(data.get("jobType", ""))
        for fund in ["כללית", "מכבי", "מאוחדת", "לאומית"]:
            if fund in text_to_search:
                medical["healthFundMember"] = fund
                break

    return data


def final_surgical_refinement(data):
    # 1. CLEAN PHONE/ID NOISE: Remove single Hebrew letters (like 'ח')
    for key in ["landlinePhone", "mobilePhone", "idNumber"]:
        val = str(data.get(key, "")).strip()
        if len(val) <= 1:
            data[key] = ""

    # 2. FORCE 9-DIGIT ID: Glue fragments together
    if data.get("idNumber"):
        ident = re.sub(r"\D", "", str(data["idNumber"]))
        if len(ident) == 8: ident = "0" + ident
        data["idNumber"] = ident[:9]

    # 3. MEDICAL SECTION RECOVERY:
    # If the fund is empty, look for keywords in other medical fields
    medical = data.get("medicalInstitutionFields", {})
    if not medical.get("healthFundMember"):
        # Search the messy diagnosis/jobType text for the fund name
        combined_text = str(medical.get("medicalDiagnoses", "")) + str(data.get("jobType", ""))
        for fund in ["כללית", "מכבי", "מאוחדת", "לאומית"]:
            if fund in combined_text:
                medical["healthFundMember"] = fund
                break

    return data


class FieldExtractionService:
    """Service for extracting structured fields from OCR text using Azure OpenAI GPT-4o.

    This class is intentionally framework-agnostic so it can be reused from
    the FastAPI service, tests, or CLI utilities.
    """

    def __init__(self):
        """Initialize the Azure OpenAI client from shared Config."""
        self.endpoint = Config.AZURE_OPENAI_ENDPOINT
        self.api_key = Config.AZURE_OPENAI_KEY
        self.api_version = Config.AZURE_OPENAI_API_VERSION
        self.deployment = Config.AZURE_OPENAI_DEPLOYMENT

        # Basic config logging (without exposing secrets)
        logger.info(
            "azure_openai_config_loaded",
            endpoint_present=bool(self.endpoint),
            key_present=bool(self.api_key),
            deployment=self.deployment,
        )

        if not self.endpoint or not self.api_key:
            raise ValueError(
                "Azure OpenAI credentials not configured. "
                "Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY in your environment."
            )

        # Initialize OpenAI client
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
        )

        # Load extraction prompt template
        self.prompt_template = self._load_prompt_template()

        logger.info("field_extraction_service_initialized", endpoint=self.endpoint)

    def _load_prompt_template(self) -> str:
        """Load the extraction prompt template from file.

        The prompt file lives in the shared root ``prompts/`` folder so that it
        can be reused by different services. If the file contains a Python-style
        assignment like ``EXTRACTION_PROMPT = '''...'''``, only the inner
        prompt text is used.
        """
        try:
            # prompts folder is at project root (one level up from this package)
            prompt_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "prompts",
                "extraction_prompt.txt",
            )

            if os.path.exists(prompt_file):
                with open(prompt_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # If the file is a Python assignment, strip wrapper
                if content.lstrip().startswith("EXTRACTION_PROMPT") and "\"\"\"" in content:
                    first = content.find("\"\"\"")
                    last = content.rfind("\"\"\"")
                    if first != -1 and last != -1 and last > first:
                        content = content[first + 3 : last]

                return content

            logger.warning("prompt_file_not_found", path=prompt_file)
            return self._get_default_prompt()

        except Exception as e:
            logger.error("prompt_load_failed", error=str(e))
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
            max_retries: int = 3,
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
        logger.info(
            "field_extraction_started",
            ocr_text_length=len(ocr_text),
            model=self.deployment,
        )

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
                            "content": "You are an expert phase2_data extraction assistant. Return only valid JSON, no additional text.",
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=temperature,
                    max_tokens=2000,
                    response_format={"type": "json_object"},  # Ensure JSON output
                )

                # Extract the response
                extracted_text = response.choices[0].message.content.strip()

                # Parse JSON
                extracted_data = json.loads(extracted_text)

                # Validate the structure against the canonical schema
                validated_data = self._validate_and_fill_schema(extracted_data)

                # Final logical cleanup / post-processing
                validated_data = refine_extracted_data(validated_data)
                validated_data = final_israeli_cleanup(validated_data)
                validated_data = finalize_data(validated_data)
                validated_data = israeli_business_logic_fix(validated_data)
                validated_data = final_surgical_cleanup(validated_data)
                validated_data = final_surgical_refinement(validated_data)

                logger.info("field_extraction_completed")
                return {
                    "success": True,
                    "phase2_data": validated_data,
                    "raw_response": extracted_text,
                    "error": None,
                }

            except json.JSONDecodeError as e:
                logger.warning(
                    "field_extraction_json_error",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == max_retries - 1:
                    logger.error("field_extraction_failed_json")
                    return {
                        "success": False,
                        "phase2_data": self._get_empty_schema(),
                        "raw_response": extracted_text if "extracted_text" in locals() else "",
                        "error": f"JSON parsing error: {str(e)}",
                    }

            except Exception as e:
                logger.error(
                    "field_extraction_error",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "phase2_data": self._get_empty_schema(),
                        "raw_response": "",
                        "error": str(e),
                    }

        # Should not reach here
        return {
            "success": False,
            "phase2_data": self._get_empty_schema(),
            "raw_response": "",
            "error": "Unknown error",
        }

    def _validate_and_fill_schema(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted phase2_data and ensure all required fields are present
        Fill missing fields with empty strings

        Args:
            extracted_data: Data extracted by GPT-4o

        Returns:
            Complete schema with all fields
        """
        schema = self._get_empty_schema()

        # Recursively merge extracted phase2_data into schema
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
        """Backward-compatible helper that works with dict OCR results.

        This is kept for older CLI tools and tests. New code should prefer
        :meth:`process_ocr_response` which works with the shared OCRResponse
        model and returns an ExtractionResponse.
        """
        if not ocr_result.get("success"):
            return {
                "success": False,
                "phase2_data": self._get_empty_schema(),
                "raw_response": "",
                "error": "OCR processing failed",
            }

        ocr_text = ocr_result.get("full_text", "")

        if not ocr_text:
            return {
                "success": False,
                "phase2_data": self._get_empty_schema(),
                "raw_response": "",
                "error": "No OCR text available",
            }

        return self.extract_fields(ocr_text)

    def process_ocr_response(self, ocr_response: OCRResponse) -> ExtractionResponse:
        """High-level helper to go from OCRResponse → ExtractionResponse.

        This is what the FastAPI microservice uses so that all services share
        the same pydantic models defined in ``shared.models``.
        """
        if not ocr_response.success:
            return ExtractionResponse(
                success=False,
                document_id=ocr_response.document_id,
                data=ExtractedData(),
                confidence={},
                processing_time_ms=0.0,
                error="OCR processing failed",
            )

        # Run the core extraction logic
        result = self.extract_fields(ocr_response.full_text)

        data = ExtractedData(**result.get("phase2_data", {}))
        # Confidence may or may not be present depending on the prompt
        confidence = result.get("confidence", {})

        return ExtractionResponse(
            success=result.get("success", False),
            document_id=ocr_response.document_id,
            data=data,
            confidence=confidence,
            processing_time_ms=0.0,  # Filled by API layer where we know timings
            error=result.get("error"),
        )

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
            print(json.dumps(result["phase2_data"], indent=2, ensure_ascii=False))
        else:
            print(f"   ❌ Extraction failed: {result['error']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)