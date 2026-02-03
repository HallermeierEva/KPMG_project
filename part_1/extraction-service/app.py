"""FastAPI application for the Field Extraction microservice.

This service accepts OCR results (as the shared OCRResponse model) and
returns structured fields using the ExtractionResponse model.
"""
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import sys
import os

# Make both the project root and this service directory importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.dirname(BASE_DIR))

from shared.logging_config import get_logger
from shared.models import OCRResponse, ExtractionResponse
from extraction_service import FieldExtractionService

logger = get_logger("extraction-api")

app = FastAPI(
    title="Field Extraction Service",
    description="Extracts structured fields from OCR text using Azure OpenAI GPT-4o",
    version="1.0.0",
)

# CORS middleware (allow everything for local/dev use)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize extraction service
extraction_service = FieldExtractionService()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "extraction"}


@app.post("/api/v1/extract", response_model=ExtractionResponse)
async def extract_fields(ocr_result: OCRResponse):
    """Run field extraction on an OCRResponse.

    The OCR service should first be called to obtain an OCRResponse, which is
    then POSTed here as JSON.
    """
    start_time = time.time()

    logger.info(
        "extraction_request_received",
        document_id=ocr_result.document_id,
    )

    try:
        result = extraction_service.process_ocr_response(ocr_result)
    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        logger.error(
            "extraction_processing_failed",
            document_id=ocr_result.document_id,
            error=str(e),
            processing_time_ms=processing_time_ms,
        )
        raise HTTPException(status_code=500, detail=str(e))

    processing_time_ms = (time.time() - start_time) * 1000
    result.processing_time_ms = processing_time_ms

    if not result.success:
        logger.error(
            "extraction_failed",
            document_id=result.document_id,
            error=result.error,
            processing_time_ms=processing_time_ms,
        )
        raise HTTPException(status_code=500, detail=result.error or "Extraction failed")

    logger.info(
        "extraction_completed",
        document_id=result.document_id,
        processing_time_ms=processing_time_ms,
    )

    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
