import hashlib
import json
import time
from typing import Dict, Any
from urllib import request as urlrequest, error as urlerror

# Use only the modern SDK
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential
import redis

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import Config
from shared.logging_config import get_logger
from shared.models import OCRResponse

logger = get_logger("ocr-service")


class OCRService:
    def __init__(self):
        self.endpoint = Config.AZURE_DI_ENDPOINT
        self.key = Config.AZURE_DI_KEY

        if not self.endpoint or not self.key:
            raise ValueError("Azure Document Intelligence credentials not configured")

        # Initialize MODERN client with the correct API version for High-Res
        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key),
            api_version="2024-11-30"
        )

        # Restore the connectivity check
        self._check_azure_di_connectivity()

        try:
            self.cache = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                decode_responses=False
            )
            self.cache.ping()
        except Exception as e:
            logger.warning("redis_connection_failed", error=str(e))
            self.cache = None

        logger.info("ocr_service_initialized", endpoint=self.endpoint)

    def _check_azure_di_connectivity(self) -> None:
        """Lightweight GET request to verify connectivity."""
        try:
            base = (self.endpoint or "").rstrip("/")
            if not base: return
            info_url = f"{base}/formrecognizer/info?api-version=2023-07-31"
            req = urlrequest.Request(
                info_url,
                headers={"Ocp-Apim-Subscription-Key": self.key},
                method="GET",
            )
            with urlrequest.urlopen(req, timeout=5) as resp:
                logger.info("azure_di_connectivity_ok", status_code=resp.getcode())
        except Exception as e:
            logger.error("azure_di_connectivity_exception", error=str(e))

    def _generate_cache_key(self, file_content: bytes) -> str:
        return f"ocr:{hashlib.sha256(file_content).hexdigest()}"

    def _get_from_cache(self, cache_key: str) -> Dict[str, Any]:
        if not self.cache: return None
        try:
            cached = self.cache.get(cache_key)
            if cached: return json.loads(cached)
        except:
            return None
        return None

    def _store_in_cache(self, cache_key: str, data: Dict[str, Any]):
        if not self.cache: return
        try:
            self.cache.setex(cache_key, Config.CACHE_TTL_SECONDS, json.dumps(data, ensure_ascii=False))
        except:
            pass

    def process_document(self, file_content: bytes, filename: str, document_id: str) -> OCRResponse:
        start_time = time.time()
        cache_key = self._generate_cache_key(file_content)

        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return OCRResponse(
                success=True,
                document_id=document_id,
                full_text=cached_result["full_text"],
                structured_content=cached_result["structured_content"],
                processing_time_ms=(time.time() - start_time) * 1000
            )

        try:
            # CORRECTED: model_id as 1st positional, analyze_request for bytes
            poller = self.client.begin_analyze_document(
                "prebuilt-layout",
                analyze_request=file_content,
                features=[DocumentAnalysisFeature.OCR_HIGH_RESOLUTION],
                content_type="application/octet-stream"
            )
            result = poller.result()

            full_text = result.content if result.content else ""
            structured_content = self._extract_structured_content(result)

            self._store_in_cache(cache_key, {"full_text": full_text, "structured_content": structured_content})

            return OCRResponse(
                success=True,
                document_id=document_id,
                full_text=full_text,
                structured_content=structured_content,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return OCRResponse(success=False, error=str(e), document_id=document_id)

    def _extract_structured_content(self, analyze_result) -> Dict[str, Any]:
        # Your existing logic for tables/pages/paragraphs goes here
        structured_data = {"pages": [], "paragraphs": [], "tables": []}
        # ... (keep your existing implementation of this method)
        return structured_data