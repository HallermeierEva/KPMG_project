"""
Azure OpenAI GPT-4o Field Extraction Service
Refactored for high modularity and Israeli-specific business logic.
"""

import os
import json
import re
import sys
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from openai import AzureOpenAI

# Maintain shared package accessibility
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import Config
from shared.logging_config import get_logger
from shared.models import OCRResponse, ExtractedData, ExtractionResponse

load_dotenv()
logger = get_logger("extraction-service")

# --- Constants ---
VALID_HEALTH_FUNDS = ["כללית", "מכבי", "מאוחדת", "לאומית"]
DATE_FIELDS = ["dateOfBirth", "dateOfInjury", "formFillingDate", "formReceiptDateAtClinic"]
PHONE_KEYS = ["landlinePhone", "mobilePhone"]


class DataRefiner:
    """Consolidated Israeli-specific business logic and OCR cleanup."""

    @staticmethod
    def refine(data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrates all refinement steps."""
        data = DataRefiner._fix_id_number(data)
        data = DataRefiner._fix_phones(data)
        data = DataRefiner._fix_dates(data)
        data = DataRefiner._fix_medical_section(data)
        data = DataRefiner._cleanup_noise(data)
        data = DataRefiner._fix_signature(data)
        return data

    @staticmethod
    def _fix_id_number(data: Dict[str, Any]) -> Dict[str, Any]:
        ident = str(data.get("idNumber") or "")
        digits = re.sub(r"\D", "", ident)

        if len(digits) == 8:
            digits = "0" + digits

        data["idNumber"] = digits[:9] if digits else ""
        return data

    @staticmethod
    def _fix_phones(data: Dict[str, Any]) -> Dict[str, Any]:
        for key in PHONE_KEYS:
            val = str(data.get(key) or "")
            clean = re.sub(r"\D", "", val)

            # Fix common OCR leading '6' instead of '0'
            if key == "mobilePhone" and clean.startswith("65"):
                clean = "0" + clean[1:]

            # Fix missing leading zero for 9-digit phones
            if len(clean) == 9 and clean.startswith("5"):
                clean = "0" + clean

            data[key] = clean
        return data

    @staticmethod
    def _fix_dates(data: Dict[str, Any]) -> Dict[str, Any]:
        for field in DATE_FIELDS:
            d = data.get(field)
            if isinstance(d, dict) and d.get("day") and d.get("month"):
                try:
                    day_val = int(re.sub(r"\D", "", str(d["day"])))
                    month_val = int(re.sub(r"\D", "", str(d["month"])))

                    # Logic: If month > 12, it's definitely the day
                    if month_val > 12 and day_val <= 12:
                        d["day"], d["month"] = str(month_val).zfill(2), str(day_val).zfill(2)
                    else:
                        d["day"], d["month"] = str(day_val).zfill(2), str(month_val).zfill(2)
                except (ValueError, TypeError):
                    continue
        return data

    @staticmethod
    def _fix_medical_section(data: Dict[str, Any]) -> Dict[str, Any]:
        medical = data.get("medicalInstitutionFields") or {}
        fund = medical.get("healthFundMember")

        # Recovery logic: if fund is empty, search text fields
        if not fund or fund not in VALID_HEALTH_FUNDS:
            search_blob = f"{medical.get('medicalDiagnoses', '')} {data.get('jobType', '')}"
            for f in VALID_HEALTH_FUNDS:
                if f in search_blob:
                    medical["healthFundMember"] = f
                    break
            else:
                medical["healthFundMember"] = ""  # Clear hallucinations

        # Heuristic for Form 283 Accident Location
        if data.get("accidentLocation") == "ת. דרכים בעבודה":
            desc = str(data.get("accidentDescription", "")).lower()
            if any(word in desc for word in ["נשרף", "מפעל", "מכונה", "במהלך העבודה"]):
                data["accidentLocation"] = "במפעל"

        data["medicalInstitutionFields"] = medical
        return data

    @staticmethod
    def _cleanup_noise(data: Dict[str, Any]) -> Dict[str, Any]:
        """Removes stray single characters (OCR artifacts)."""
        target_keys = PHONE_KEYS + ["idNumber", "jobType"]
        for key in target_keys:
            if len(str(data.get(key) or "").strip()) <= 1:
                data[key] = ""
        return data

    @staticmethod
    def _fix_signature(data: Dict[str, Any]) -> Dict[str, Any]:
        sig = str(data.get("signature") or "")
        if sig.upper() == "X" or len(sig) < 2:
            full_name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
            data["signature"] = full_name if full_name else sig
        return data


class FieldExtractionService:
    """Service for extracting structured fields using Azure OpenAI GPT-4o."""

    def __init__(self):
        self._setup_config()
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
        )
        self.prompt_template = self._load_prompt_template()
        logger.info("field_extraction_service_initialized", endpoint=self.endpoint)

    def _setup_config(self):
        self.endpoint = Config.AZURE_OPENAI_ENDPOINT
        self.api_key = Config.AZURE_OPENAI_KEY
        self.api_version = Config.AZURE_OPENAI_API_VERSION
        self.deployment = Config.AZURE_OPENAI_DEPLOYMENT

        if not self.endpoint or not self.api_key:
            raise ValueError("Azure OpenAI credentials missing.")

    def _load_prompt_template(self) -> str:
        try:
            prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "extraction_prompt.txt")
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Clean python wrapper if exists
                match = re.search(r'"""(.*?)"""', content, re.DOTALL)
                return match.group(1).strip() if match else content
            return self._get_default_prompt()
        except Exception as e:
            logger.error("prompt_load_failed", error=str(e))
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        return "Extract fields from OCR text as JSON:\n{ocr_text}"

    def extract_fields(self, ocr_text: str, temperature: float = 0.0, max_retries: int = 3) -> Dict[str, Any]:
        """Core extraction logic."""
        logger.info("field_extraction_started", text_len=len(ocr_text))
        prompt = self.prompt_template.replace("{ocr_text}", ocr_text)

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {"role": "system", "content": "Return only valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )

                raw_json = json.loads(response.choices[0].message.content)

                # Validation and Refinement
                data = self._validate_and_fill_schema(raw_json)
                refined_data = DataRefiner.refine(data)

                return {
                    "success": True,
                    "phase2_data": refined_data,
                    "raw_response": response.choices[0].message.content,
                    "error": None,
                }

            except Exception as e:
                logger.warning("extraction_attempt_failed", attempt=attempt + 1, error=str(e))
                if attempt == max_retries - 1:
                    return {"success": False, "phase2_data": self._get_empty_schema(), "error": str(e)}

    def _validate_and_fill_schema(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge extracted data into a blank schema template."""
        base = self._get_empty_schema()

        def merge(target, source):
            for k, v in source.items():
                if k in target and isinstance(target[k], dict) and isinstance(v, dict):
                    merge(target[k], v)
                elif k in target and v is not None:
                    target[k] = v
            return target

        return merge(base, extracted_data)

    def process_ocr_response(self, ocr_response: OCRResponse) -> ExtractionResponse:
        """High-level helper to go from OCRResponse → ExtractionResponse.

        This is what the FastAPI microservice uses so that all services share
        the same pydantic models defined in ``shared.models``.
        """
        import time
        start_time = time.time()

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

        # Calculate duration to satisfy the Pydantic requirement
        duration_ms = (time.time() - start_time) * 1000

        # Construct ExtractedData object
        # Using .get() with a default empty dict to prevent key errors
        phase2_data = result.get("phase2_data", {})
        data_model = ExtractedData(**phase2_data)

        # Explicitly pass processing_time_ms to the model
        return ExtractionResponse(
            success=result.get("success", False),
            document_id=ocr_response.document_id,
            data=data_model,
            confidence=result.get("confidence", {}),
            processing_time_ms=duration_ms,  # <--- This fixes the validation error
            error=result.get("error"),
        )

    def extract_from_file(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy support for dictionary-based OCR results."""
        if not ocr_result.get("success"):
            return {"success": False, "phase2_data": self._get_empty_schema(), "error": "OCR failed"}
        return self.extract_fields(ocr_result.get("full_text", ""))

    def batch_extract(self, ocr_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.extract_from_file(res) for res in ocr_results]

    def _get_empty_schema(self) -> Dict[str, Any]:
        return {
            "lastName": "", "firstName": "", "idNumber": "", "gender": "",
            "dateOfBirth": {"day": "", "month": "", "year": ""},
            "address": {"street": "", "houseNumber": "", "entrance": "", "apartment": "", "city": "", "postalCode": "",
                        "poBox": ""},
            "landlinePhone": "", "mobilePhone": "", "jobType": "",
            "dateOfInjury": {"day": "", "month": "", "year": ""},
            "timeOfInjury": "", "accidentLocation": "", "accidentAddress": "", "accidentDescription": "",
            "injuredBodyPart": "",
            "signature": "",
            "formFillingDate": {"day": "", "month": "", "year": ""},
            "formReceiptDateAtClinic": {"day": "", "month": "", "year": ""},
            "medicalInstitutionFields": {"healthFundMember": "", "natureOfAccident": "", "medicalDiagnoses": ""}
        }


if __name__ == "__main__":
    # Test script remains similar...
    service = FieldExtractionService()
    print("Service Ready.")