"""
Shared configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Shared configuration"""

    # Azure Document Intelligence
    AZURE_DI_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    AZURE_DI_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT", "gpt-4o")

    # Service URLs (for Docker)
    OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://ocr-service:8001")
    EXTRACTION_SERVICE_URL = os.getenv("EXTRACTION_SERVICE_URL", "http://extraction-service:8002")
    VALIDATION_SERVICE_URL = os.getenv("VALIDATION_SERVICE_URL", "http://validation-service:8003")

    # Redis (for caching)
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    # Performance
    MAX_FILE_SIZE_MB = 10
    CACHE_TTL_SECONDS = 3600  # 1 hour