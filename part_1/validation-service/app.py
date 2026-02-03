"""FastAPI application for the Validation microservice.

This service accepts extracted data (ExtractionResponse) and returns a
ValidationResponse with errors, warnings, completeness and an
approximate accuracy score.
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
from shared.models import ExtractionResponse, ValidationResponse
from validation_service import ValidationService

logger = get_logger("validation-api")

app = FastAPI(
    title="Validation Service",
    description="Validates extracted fields (ID, dates, phones, completeness)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

validator = ValidationService()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "validation"}


@app.post("/api/v1/validate", response_model=ValidationResponse)
async def validate_extraction(extraction: ExtractionResponse):
    """Validate extracted data coming from the extraction service."""
    start_time = time.time()

    logger.info(
        "validation_request_received",
        document_id=extraction.document_id,
    )

    try:
        result = validator.validate(extraction.data.model_dump())
    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        logger.error(
            "validation_processing_failed",
            document_id=extraction.document_id,
            error=str(e),
            processing_time_ms=processing_time_ms,
        )
        raise HTTPException(status_code=500, detail=str(e))

    processing_time_ms = (time.time() - start_time) * 1000

    # Derive a rough accuracy score from completeness and the number of errors
    completeness = result["completeness"]
    base_score = completeness["percentage"] / 100.0
    error_penalty = min(len(result["errors"]) * 0.05, 0.5)  # up to -50%
    accuracy_score = max(base_score - error_penalty, 0.0) * 100

    logger.info(
        "validation_completed_api",
        document_id=extraction.document_id,
        valid=result["valid"],
        errors=len(result["errors"]),
        warnings=len(result["warnings"]),
        completeness_percentage=completeness["percentage"],
        accuracy_score=accuracy_score,
        processing_time_ms=processing_time_ms,
    )

    return ValidationResponse(
        valid=result["valid"],
        document_id=extraction.document_id,
        errors=result["errors"],
        warnings=result["warnings"],
        field_validations=result["field_validations"],
        completeness=completeness,
        accuracy_score=round(accuracy_score, 1),
        processing_time_ms=processing_time_ms,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
