"""End-to-end evaluation script for part_1.

This script:
- Runs Azure Document Intelligence OCR on each PDF in TEST_SUITE
- Runs the GPT-4o field extraction on the OCR text
- Compares the extracted fields with the ground-truth labels (TEST_SUITE)
- Prints per-file accuracy and overall accuracy

Run from the part_1 directory with:

    python evaluate_ground_truth_accuracy.py

Requirements:
- Valid Azure DI and Azure OpenAI credentials in your .env (same as the services)
- The PDF files must exist at the paths specified in TEST_SUITE
"""

import os
import sys
from typing import Dict, Any, Tuple, List

# ---------------------------------------------------------------------------
# Imports from local services (OCR + Extraction)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Allow importing `service.py` from ocr-service and `extraction_service.py` from extraction-service
sys.path.insert(0, os.path.join(BASE_DIR, "ocr-service"))
sys.path.insert(0, os.path.join(BASE_DIR, "extraction-service"))
sys.path.insert(0, os.path.join(BASE_DIR, "validation-service"))
sys.path.insert(0, BASE_DIR)  # for shared package

from service import OCRService  # type: ignore
from extraction_service import FieldExtractionService  # type: ignore
from validation_service import ValidationService, robust_post_processor  # type: ignore


# ---------------------------------------------------------------------------
# Ground-truth labels
# ---------------------------------------------------------------------------
TEST_SUITE: Dict[str, Dict[str, Any]] = {
    "data/283_ex1.pdf": {
        "lastName": "טננהוים", "firstName": "יהודה", "idNumber": "877524563", "gender": "זכר",
        "dateOfBirth": {"day": "02", "month": "02", "year": "1995"},
        "address": {"street": "הרמבם", "houseNumber": "16", "entrance": "1", "apartment": "12", "city": "אבן יהודה",
                    "postalCode": "312422", "poBox": ""},
        "landlinePhone": "", "mobilePhone": "0502474947", "jobType": "מלצרות",
        "dateOfInjury": {"day": "16", "month": "04", "year": "2022"},
        "timeOfInjury": "19:00", "accidentLocation": "במפעל", "accidentAddress": "הורדים 8, תל אביב",
        "accidentDescription": "החלקתי בגלל שהרצפה הייתה רטובה ולא היה שום שלט שמזהיר.",
        "injuredBodyPart": "יד שמאל", "signature": "טננהוים יהודה",
        "formFillingDate": {"day": "25", "month": "01", "year": "2023"},
        "formReceiptDateAtClinic": {"day": "02", "month": "02", "year": "1999"},
        "medicalInstitutionFields": {"healthFundMember": "מאוחדת", "natureOfAccident": "", "medicalDiagnoses": ""}
    },
    "data/283_ex2.pdf": {
        "lastName": "הלוי", "firstName": "שלמה", "idNumber": "022456120", "gender": "זכר",
        "dateOfBirth": {"day": "14", "month": "10", "year": "1990"},
        "address": {"street": "חיים ויצמן", "houseNumber": "6", "entrance": "", "apartment": "34", "city": "יוקנעם",
                    "postalCode": "4454124", "poBox": ""},
        "landlinePhone": "097656054", "mobilePhone": "0554412742", "jobType": "מאפיית האחים",
        "dateOfInjury": {"day": "12", "month": "08", "year": "2005"},
        "timeOfInjury": "12:00", "accidentLocation": "במפעל", "accidentAddress": "האופים 17 בני ברק",
        "accidentDescription": "במהלך העבודה נשרף ממגש לוהט.", "injuredBodyPart": "הפנים במיוחד הלחי הימנית",
        "signature": "שלמה הלוי", "formFillingDate": {"day": "14", "month": "09", "year": "2006"},
        "formReceiptDateAtClinic": {"day": "03", "month": "07", "year": "2001"},
        "medicalInstitutionFields": {"healthFundMember": "כללית", "natureOfAccident": "", "medicalDiagnoses": ""}
    },
    "data/283_ex3.pdf": {
        "lastName": "יוחננוף", "firstName": "רועי", "idNumber": "0334521567", "gender": "זכר",
        "dateOfBirth": {"day": "03", "month": "03", "year": "1974"},
        "address": {"street": "המאיר", "houseNumber": "15", "entrance": "1", "apartment": "16", "city": "אלוני הבשן",
                    "postalCode": "445412", "poBox": ""},
        "landlinePhone": "0975423541", "mobilePhone": "0502451645", "jobType": "ירקנייה",
        "dateOfInjury": {"day": "14", "month": "04", "year": "1999"},
        "timeOfInjury": "15:30", "accidentLocation": "במפעל", "accidentAddress": "לוונברג 173 כפר סבא",
        "accidentDescription": "במהלך העבודה הרמתי משקל כבד וכתוצאה מכך הייתי צריך ניתוח קילה",
        "injuredBodyPart": "קילה", "signature": "רועי יוחננוף",
        "formFillingDate": {"day": "20", "month": "05", "year": "1999"},
        "formReceiptDateAtClinic": {"day": "30", "month": "06", "year": "1999"},
        "medicalInstitutionFields": {"healthFundMember": "", "natureOfAccident": "", "medicalDiagnoses": ""}
    },
    "data/283_raw.pdf": {
        "lastName": "", "firstName": "", "idNumber": "", "gender": "",
        "dateOfBirth": {"day": "", "month": "", "year": ""},
        "address": {"street": "", "houseNumber": "", "entrance": "", "apartment": "", "city": "", "postalCode": "",
                    "poBox": ""},
        "landlinePhone": "", "mobilePhone": "", "jobType": "",
        "dateOfInjury": {"day": "", "month": "", "year": ""},
        "timeOfInjury": "", "accidentLocation": "", "accidentAddress": "", "accidentDescription": "",
        "injuredBodyPart": "",
        "signature": "", "formFillingDate": {"day": "", "month": "", "year": ""},
        "formReceiptDateAtClinic": {"day": "", "month": "", "year": ""},
        "medicalInstitutionFields": {"healthFundMember": "", "natureOfAccident": "", "medicalDiagnoses": ""}
    },
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _flatten_dict(d: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
    """Flatten a nested dict using dot-separated keys.

    Example:
        {"dateOfBirth": {"day": "02"}} -> {"dateOfBirth.day": "02"}
    """

    items: Dict[str, Any] = {}
    for key, value in d.items():
        new_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(_flatten_dict(value, new_key))
        else:
            items[new_key] = value
    return items


def compare_dicts(actual: Dict[str, Any], expected: Dict[str, Any]) -> Tuple[float, int, int, List[Tuple[str, str, str]]]:
    """Compare two (possibly nested) dicts and compute accuracy.

    Returns:
        accuracy_percentage, correct_count, total_count, mismatches
    """

    actual_flat = _flatten_dict(actual)
    expected_flat = _flatten_dict(expected)

    correct = 0
    total = 0
    mismatches: List[Tuple[str, str, str]] = []

    for key, expected_value in expected_flat.items():
        total += 1
        actual_value = actual_flat.get(key, "")

        exp_str = ("" if expected_value is None else str(expected_value)).strip()
        act_str = ("" if actual_value is None else str(actual_value)).strip()

        if exp_str == act_str:
            correct += 1
        else:
            mismatches.append((key, exp_str, act_str))

    accuracy = (correct / total * 100.0) if total > 0 else 0.0
    return accuracy, correct, total, mismatches


# ---------------------------------------------------------------------------
# Main evaluation routine
# ---------------------------------------------------------------------------

def run_evaluation() -> None:
    print("=" * 80)
    print("🧪  E2E EVALUATION: OCR + GPT-4o FIELD EXTRACTION + VALIDATION VS GROUND TRUTH")
    print("=" * 80)

    # Initialize services (will use credentials from .env via shared.config)
    try:
        print("\n[1/3] Initializing OCR service (Azure Document Intelligence)...")
        ocr_service = OCRService()
        print("   ✅ OCR service initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize OCR service: {e}")
        return

    try:
        print("\n[2/4] Initializing Extraction service (Azure OpenAI GPT-4o)...")
        extraction_service = FieldExtractionService()
        print("   ✅ Extraction service initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize extraction service: {e}")
        return

    try:
        print("\n[3/4] Initializing Validation service...")
        validator = ValidationService()
        print("   ✅ Validation service initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize validation service: {e}")
        return

    overall_correct = 0
    overall_total = 0
    overall_val_accuracy_sum = 0.0
    evaluated_docs = 0

    print("\n[4/4] Running evaluation on all labeled PDFs...\n")

    for rel_path, expected in TEST_SUITE.items():
        pdf_path = os.path.join(BASE_DIR, rel_path)
        print("-" * 80)
        print(f"📄 File: {rel_path}")

        if not os.path.exists(pdf_path):
            print(f"   ❌ File not found on disk: {pdf_path}")
            continue

        # OCR step
        try:
            with open(pdf_path, "rb") as f:
                file_bytes = f.read()

            ocr_response = ocr_service.process_document(
                file_content=file_bytes,
                filename=os.path.basename(pdf_path),
                document_id=rel_path,
            )
        except Exception as e:
            print(f"   ❌ OCR failed with exception: {e}")
            continue

        if not ocr_response.success:
            print(f"   ❌ OCR failed: {ocr_response.error}")
            continue

        # Extraction step
        try:
            extraction_response = extraction_service.process_ocr_response(ocr_response)
        except Exception as e:
            print(f"   ❌ Extraction failed with exception: {e}")
            continue

        if not extraction_response.success:
            print(f"   ❌ Extraction failed: {extraction_response.error}")
            continue

        # Convert pydantic model to plain dict
        actual = extraction_response.data.model_dump()

        # Apply robust post-processing before any evaluation/comparison
        actual = robust_post_processor(actual)

        # Compare with ground truth (field-level accuracy)
        accuracy, correct, total, mismatches = compare_dicts(actual, expected)

        overall_correct += correct
        overall_total += total

        print(f"   ✅ Fields correctly extracted: {correct}/{total} ({accuracy:.1f}% accuracy)")

        if mismatches:
            print("   ⚠️  Field mismatches (expected vs actual):")
            for key, exp, act in mismatches:
                print(f"      - {key}: expected='{exp}' | actual='{act}'")
        else:
            print("   🎯 All fields match ground truth")

        # Validation step (uses robust_post_processor internally)
        # For the raw template file, we skip validation scoring since it's just
        # checking that the model correctly finds "nothing".
        if rel_path.endswith("283_raw.pdf"):
            print("   🧪 Validation result: (raw template file, score ignored)")
            val_result = validator.validate(actual)
            completeness = val_result["completeness"]
            print(f"      - valid: {val_result['valid']}")
            print(f"      - completeness: {completeness['filled_fields']}/{completeness['total_fields']} "
                  f"({completeness['percentage']}%)")
            print(f"      - errors: {len(val_result['errors'])}, warnings: {len(val_result['warnings'])}")
        else:
            val_result = validator.validate(actual)
            completeness = val_result["completeness"]
            base_score = completeness["percentage"] / 100.0
            error_penalty = min(len(val_result["errors"]) * 0.05, 0.5)  # same logic as validation API
            val_accuracy_score = max(base_score - error_penalty, 0.0) * 100

            overall_val_accuracy_sum += val_accuracy_score
            evaluated_docs += 1

            print("   🧪 Validation result:")
            print(f"      - valid: {val_result['valid']}")
            print(f"      - completeness: {completeness['filled_fields']}/{completeness['total_fields']} "
                  f"({completeness['percentage']}%)")
            print(f"      - errors: {len(val_result['errors'])}, warnings: {len(val_result['warnings'])}")
            print(f"      - validation accuracy score: {val_accuracy_score:.1f}%")

        # OCR text dump to help debug mismatches and validation issues
        print("   📝 OCR text (first 40 lines):")
        print("   " + "-" * 72)
        lines = ocr_response.full_text.splitlines()
        for line in lines[:40]:
            print("   " + line)
        if len(lines) > 40:
            print("   ... [truncated]")

    print("\n" + "=" * 80)
    if overall_total == 0 or evaluated_docs == 0:
        print("No fields were evaluated (check that PDF files exist and services are configured).")
        return

    overall_accuracy = overall_correct / overall_total * 100.0
    avg_validation_accuracy = overall_val_accuracy_sum / evaluated_docs

    print("📈 OVERALL ACCURACY SUMMARY")
    print("=" * 80)
    print(f"Total correct fields (ground truth match): {overall_correct}/{overall_total}")
    print(f"Overall extraction accuracy: {overall_accuracy:.1f}%")
    print(f"Average validation accuracy score: {avg_validation_accuracy:.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()
