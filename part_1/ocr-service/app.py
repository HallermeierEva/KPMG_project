"""
OCR Service FastAPI Application
"""
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import sys
import os

# Make both the project root and this service directory importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.dirname(BASE_DIR))

from shared.logging_config import get_logger
from shared.models import OCRResponse
from shared.config import Config
from service import OCRService

logger = get_logger("ocr-api")

app = FastAPI(
    title="OCR Service",
    description="Document OCR using Azure Document Intelligence",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OCR service
ocr_service = OCRService()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ocr"}


@app.post("/api/v1/ocr", response_model=OCRResponse)
async def process_document(file: UploadFile = File(...)):
    """
    Process document with OCR

    Args:
        file: Uploaded PDF or image file

    Returns:
        OCRResponse with extracted text and structure
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = file.filename.lower().split('.')[-1]
    if file_ext not in ['pdf', 'jpg', 'jpeg', 'png']:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}"
        )

    # Read file content
    file_content = await file.read()

    # Check file size
    file_size_mb = len(file_content) / (1024 * 1024)
    if file_size_mb > Config.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size_mb:.2f}MB (max {Config.MAX_FILE_SIZE_MB}MB)"
        )

    # Generate document ID
    document_id = str(uuid.uuid4())

    logger.info("ocr_request_received",
                document_id=document_id,
                filename=file.filename,
                file_size_mb=file_size_mb)

    # Process document
    result = ocr_service.process_document(
        file_content=file_content,
        filename=file.filename,
        document_id=document_id
    )

    if not result.success:
        logger.error("ocr_processing_failed",
                     document_id=document_id,
                     error=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)