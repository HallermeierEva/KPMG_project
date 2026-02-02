import json
import os
from ocr_service import DocumentOCRService
from extraction_service import FieldExtractionService

# --- TEST DATASET (Remains the same) ---
TEST_SUITE = {
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
    }
}


class MockFile:
    def __init__(self, path):
        self.name = os.path.basename(path)
        with open(path, "rb") as f: self.content = f.read()

    def read(self): return self.content

    def seek(self, pos): pass


def compare_json(expected, actual, path=""):
    errors = []
    for key, val_exp in expected.items():
        curr_path = f"{path}.{key}" if path else key
        if key not in actual:
            errors.append(f"MISSING: {curr_path}")
            continue
        val_act = actual[key]
        if isinstance(val_exp, dict):
            errors.extend(compare_json(val_exp, val_act, curr_path))
        else:
            if str(val_exp).strip() != str(val_act).strip():
                errors.append(f"MISMATCH at {curr_path}: Expected '{val_exp}', Got '{val_act}'")
    return errors


def run_benchmark():
    ocr = DocumentOCRService()
    extractor = FieldExtractionService()
    total_fields_all = 0
    total_errors_all = 0
    file_reports = []

    print("🚀 Starting Pipeline Accuracy Benchmark...")

    for file_path, ground_truth in TEST_SUITE.items():
        print(f"\n--- Processing: {file_path} ---")
        try:
            # 1. OCR Process
            ocr_res = ocr.process_uploaded_file(MockFile(file_path))
            raw_ocr_text = ocr_res.get("full_text", "")  # Added for debugging

            # 2. Extraction Process
            ext_res = extractor.extract_from_file(ocr_res)
            extracted_json = ext_res.get("data", {})

            # 3. Validation
            diffs = compare_json(ground_truth, extracted_json)
            file_total_fields = 35
            file_errors = len(diffs)

            total_fields_all += file_total_fields
            total_errors_all += file_errors

            acc = ((file_total_fields - file_errors) / file_total_fields) * 100
            file_reports.append({
                "file": file_path,
                "accuracy": acc,
                "errors": diffs,
                "raw_ocr": raw_ocr_text,  # Store for report
                "extracted": extracted_json  # Store for report
            })
            print(f"Result: {acc:.2f}% accuracy")

        except Exception as e:
            print(f"❌ Failed to process {file_path}: {e}")

    # Final Summary Rendering
    overall_acc = ((total_fields_all - total_errors_all) / total_fields_all) * 100
    print("\n" + "=" * 60)
    print(f"📊 FINAL BENCHMARK SUMMARY")
    print(f"Overall Accuracy: {overall_acc:.2f}%")
    print(f"Total Fields Scored: {total_fields_all}")
    print(f"Total Mismatches Found: {total_errors_all}")
    print("=" * 60)

    # Detailed Debug Output
    for report in file_reports:
        if report["errors"]:
            print(f"\n" + "!" * 20 + f" DEBUG: {report['file']} " + "!" * 20)
            print(f"Accuracy: {report['accuracy']:.2f}%")

            print("\n❌ Errors Identified:")
            for err in report["errors"]:
                print(f"  - {err}")

            # Show extracted vs ground truth for error fields
            print("\n🔍 OCR Context Snippet (First 500 chars):")
            print("-" * 40)
            print(report["raw_ocr"][:500] + "...")
            print("-" * 40)

            # Helpful for identifying missing Job Type or misread Dates
            if any("jobType" in e for e in report["errors"]):
                print("\n💡 TIP: Check the OCR text around 'סוג העבודה' or 'מלצרות' to see why Job Type failed.")

    # Save full run to JSON for deep analysis
    with open("benchmark_debug_log.json", "w", encoding="utf-8") as f:
        json.dump(file_reports, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Full debug log saved to benchmark_debug_log.json")


if __name__ == "__main__":
    run_benchmark()