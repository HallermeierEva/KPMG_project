# Part 1: Field Extraction from National Insurance Forms

## Overview

Part 1 is a small microservice-based system that extracts structured data from Israeli National Insurance Institute (ביטוח לאומי) work injury forms (Form 283).

It consists of:
- An OCR service using Azure Document Intelligence
- A field-extraction service using Azure OpenAI GPT-4o
- A validation service that checks IDs, dates, phones, and completeness
- A Streamlit UI that orchestrates the pipeline and visualises results
- An offline evaluation script that compares against labeled ground truth

## Project structure (actual layout)

```
part_1/
├── run_part1.sh                    # Orchestrator: starts all services + Streamlit UI
├── evaluate_ground_truth_accuracy.py  # E2E evaluation against labeled PDFs in data/
├── requirements.txt
├── pytest.ini                       # Root pytest config (targets ocr-service/tests)
├── data/
│   ├── 283_ex1.pdf
│   ├── 283_ex2.pdf
│   ├── 283_ex3.pdf
│   └── 283_raw.pdf
├── prompts/
│   └── extraction_prompt.txt       # GPT-4o prompt template
├── shared/
│   ├── config.py                   # Shared configuration (endpoints, Redis, service URLs)
│   ├── logging_config.py           # Structured JSON logging
│   └── models.py                   # Pydantic models used by all services
├── ocr-service/
│   ├── app.py                      # FastAPI HTTP API (uvicorn ocr-service.app:app --port 8001)
│   ├── service.py                  # OCRService wrapper around Azure Document Intelligence
│   ├── tests/                      # HTTP- and service-level tests
│   │   ├── test_api.py
│   │   ├── test_service.py
│   │   ├── test_performance.py
│   │   └── test_data/283_ex1.pdf
│   └── pytest.ini
├── extraction-service/
│   ├── app.py                      # FastAPI HTTP API (uvicorn extraction-service.app:app --port 8002)
│   └── extraction_service.py       # GPT-4o field extraction + post-processing
├── validation-service/
│   ├── app.py                      # FastAPI HTTP API (uvicorn validation-service.app:app --port 8003)
│   └── validation_service.py       # Core validation logic and scoring
└── ui-service/
    └── app.py                      # Streamlit UI (streamlit run ui-service/app.py)
```

## Setup

### 1. Create environment and install dependencies

From the `part_1` directory:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

All services read configuration from environment variables via `shared/config.py` (and `dotenv` if a `.env` file is present on the Python path).

Required values:

```env
# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=your-di-endpoint
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-di-key

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=your-aoai-endpoint
AZURE_OPENAI_KEY=your-aoai-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_GPT4O_DEPLOYMENT=gpt-4o

# Optional: service URLs when calling from the UI (defaults shown)
OCR_SERVICE_URL=http://localhost:8001
EXTRACTION_SERVICE_URL=http://localhost:8002
VALIDATION_SERVICE_URL=http://localhost:8003

# Optional: Redis cache for OCR results (used by ocr-service/service.py)
REDIS_HOST=localhost
REDIS_PORT=6379
```

You can either:
- Export these directly in your shell, or
- Place them in a `.env` file that is loaded by `python-dotenv` before starting the services.

## Running the system

### Option A: One-step run (recommended during development)

From `part_1`:

```bash
chmod +x run_part1.sh      # first time only
./run_part1.sh
```

This script will:
1. Start the OCR FastAPI service on port 8001
2. Start the Extraction FastAPI service on port 8002
3. Start the Validation FastAPI service on port 8003
4. Launch the Streamlit UI in your browser (backed by those three services)

Press Ctrl+C in the terminal to stop all services.

### Option B: Run each service manually

In separate terminals from `part_1`:

```bash
# OCR service
uvicorn ocr-service.app:app --host 0.0.0.0 --port 8001 --reload

# Extraction service
uvicorn extraction-service.app:app --host 0.0.0.0 --port 8002 --reload

# Validation service
uvicorn validation-service.app:app --host 0.0.0.0 --port 8003 --reload
```

Then run the UI:

```bash
streamlit run ui-service/app.py
```

## Testing

### 1. OCR service test suite

From `part_1` (uses the root `pytest.ini`, which points to `ocr-service/tests`):

```bash
pytest
```

This runs:
- `ocr-service/tests/test_api.py` – HTTP-level tests
- `ocr-service/tests/test_service.py` – direct service tests
- `ocr-service/tests/test_performance.py` – basic performance checks

### 2. End-to-end evaluation against ground truth

The script `evaluate_ground_truth_accuracy.py` runs the full in-process pipeline (OCR → extraction → validation) for the labeled PDFs in `data/`, and compares predictions to the ground-truth labels embedded in the script.

From `part_1`:

```bash
python evaluate_ground_truth_accuracy.py
```

You will see per-document accuracy, mismatches per field, validation completeness, and an overall accuracy summary.

## How the pipeline works

High-level flow when using the Streamlit UI:

1. The user uploads a filled Form 283 PDF or image in `ui-service/app.py`.
2. The UI calls the OCR microservice (`ocr-service/app.py`), which wraps `OCRService` in `ocr-service/service.py`.
3. The OCR service calls Azure Document Intelligence (prebuilt-layout model with high-resolution OCR) and returns an `OCRResponse` (see `shared/models.py`).
4. The UI forwards the `OCRResponse` JSON to the extraction microservice (`extraction-service/app.py`).
5. `FieldExtractionService` in `extraction-service/extraction_service.py`:
   - Loads the prompt template from `prompts/extraction_prompt.txt`.
   - Calls Azure OpenAI GPT-4o with `response_format={"type": "json_object"}`.
   - Normalizes and post-processes the JSON (ID, phone, and date fixes, health fund heuristics, etc.).
   - Returns an `ExtractionResponse` with a fully-populated `ExtractedData` model.
6. The UI then calls the validation microservice (`validation-service/app.py`) with that `ExtractionResponse`.
7. `ValidationService` in `validation-service/validation_service.py`:
   - Runs `robust_post_processor` to normalize phones, IDs, and dates.
   - Validates Israeli ID numbers, phone numbers, and date ranges.
   - Computes completeness (filled vs total leaf fields).
   - Derives an accuracy score from completeness and the number of errors.
8. The UI displays:
   - A structured, bilingual (Hebrew/English) view of the extracted fields.
   - Raw JSON output and OCR text.
   - Validation errors, warnings, and completeness metrics.

## Output format (core schema)

The `ExtractedData` model in `shared/models.py` defines the canonical output. A typical JSON instance looks like:

```json
{
  "lastName": "כהן",
  "firstName": "דוד",
  "idNumber": "123456789",
  "gender": "זכר",
  "dateOfBirth": {
    "day": "15",
    "month": "03",
    "year": "1985"
  },
  "address": {
    "street": "הרצל",
    "houseNumber": "25",
    "apartment": "10",
    "city": "תל אביב",
    "postalCode": "6688201",
    "entrance": "",
    "poBox": ""
  },
  "landlinePhone": "",
  "mobilePhone": "0501234567",
  "jobType": "מלצרות",
  "dateOfInjury": {
    "day": "10",
    "month": "06",
    "year": "2023"
  },
  "timeOfInjury": "14:30",
  "accidentLocation": "במפעל",
  "accidentAddress": "הורדים 8, תל אביב",
  "accidentDescription": "נפילה מגובה",
  "injuredBodyPart": "יד ימין",
  "signature": "דוד כהן",
  "formFillingDate": {
    "day": "12",
    "month": "06",
    "year": "2023"
  },
  "formReceiptDateAtClinic": {
    "day": "20",
    "month": "06",
    "year": "2023"
  },
  "medicalInstitutionFields": {
    "healthFundMember": "כללית",
    "natureOfAccident": "פגיעה בעבודה",
    "medicalDiagnoses": "כוויות מדרגה שנייה"
  }
}
```

## Troubleshooting

- OCR fails with authentication/404 errors
  - Check `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` and `AZURE_DOCUMENT_INTELLIGENCE_KEY`.
  - Ensure there is no trailing slash in the endpoint.
- Extraction returns empty or low-quality fields
  - Verify your Azure OpenAI endpoint, key, and deployment name.
  - Confirm that `prompts/extraction_prompt.txt` exists and is readable.
  - Inspect OCR quality via the "OCR Text" tab in the UI or by running the evaluation script.
- Validation shows many errors
  - Make sure IDs and phones in the ground truth are correct.
  - Remember that the validator is strict about phone length and leading zeros.

## Notes

- Python bytecode caches (`__pycache__`) and ad-hoc debug logs are intentionally not part of the core implementation.
- The removed legacy single-file scripts (`config.py`, top-level `test_ocr.py` / `test_extraction.py`, etc.) have been replaced by the microservice layout described above.
