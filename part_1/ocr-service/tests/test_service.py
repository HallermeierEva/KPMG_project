"""
Unit tests for OCR Service
"""
import pytest
import hashlib
import json
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from service import OCRService
from shared.models import OCRResponse


class TestOCRService:
    """Test OCR Service functionality"""

    @pytest.mark.unit
    def test_service_initialization(self, temp_env_vars):
        """Test OCR service initializes correctly"""
        with patch('service.DocumentAnalysisClient'):
            with patch('service.redis.Redis') as mock_redis:
                mock_redis.return_value.ping.return_value = True

                service = OCRService()

                assert service.endpoint is not None
                assert service.key is not None
                assert service.client is not None

    @pytest.mark.unit
    def test_cache_key_generation(self, temp_env_vars, mock_redis):
        """Test cache key generation from file content"""
        with patch('service.DocumentAnalysisClient'):
            service = OCRService()

            test_content = b"test file content"
            expected_key = f"ocr:{hashlib.sha256(test_content).hexdigest()}"

            cache_key = service._generate_cache_key(test_content)

            assert cache_key == expected_key

    @pytest.mark.unit
    def test_cache_storage_and_retrieval(self, temp_env_vars, mock_redis):
        """Test caching mechanism"""
        with patch('service.DocumentAnalysisClient'):
            service = OCRService()

            cache_key = "test:cache:key"
            test_data = {
                "full_text": "Sample text",
                "structured_content": {"pages": []}
            }

            # Store in cache
            service._store_in_cache(cache_key, test_data)

            # Retrieve from cache
            cached = service._get_from_cache(cache_key)

            assert cached is not None
            assert cached["full_text"] == test_data["full_text"]

    @pytest.mark.unit
    def test_process_document_success(self, temp_env_vars, mock_redis, sample_pdf_content):
        """Test successful document processing"""
        with patch('service.DocumentAnalysisClient') as mock_client:
            # Mock Azure DI response
            mock_result = Mock()
            mock_result.content = "Sample OCR text\nשם משפחה: טננהוים\nשם פרטי: יהודה"
            mock_result.pages = []
            mock_result.paragraphs = []
            mock_result.tables = []

            mock_poller = Mock()
            mock_poller.result.return_value = mock_result

            mock_client.return_value.begin_analyze_document.return_value = mock_poller

            service = OCRService()

            # Process document
            response = service.process_document(
                file_content=sample_pdf_content,
                filename="test.pdf",
                document_id="test-doc-123"
            )

            assert response.success is True
            assert response.document_id == "test-doc-123"
            assert len(response.full_text) > 0
            assert "טננהוים" in response.full_text or "Sample" in response.full_text
            assert response.processing_time_ms > 0

    @pytest.mark.unit
    def test_process_document_with_cache_hit(self, temp_env_vars, mock_redis, sample_pdf_content):
        """Test document processing uses cache when available"""
        with patch('service.DocumentAnalysisClient') as mock_client:
            service = OCRService()

            # Pre-populate cache
            cache_key = service._generate_cache_key(sample_pdf_content)
            cached_data = {
                "full_text": "Cached text",
                "structured_content": {"pages": []}
            }
            service._store_in_cache(cache_key, cached_data)

            # Process document (should use cache)
            response = service.process_document(
                file_content=sample_pdf_content,
                filename="test.pdf",
                document_id="test-doc-456"
            )

            assert response.success is True
            assert response.full_text == "Cached text"

            # Verify Azure DI was NOT called
            mock_client.return_value.begin_analyze_document.assert_not_called()

    @pytest.mark.unit
    def test_process_document_error_handling(self, temp_env_vars, mock_redis, sample_pdf_content):
        """Test error handling in document processing"""
        with patch('service.DocumentAnalysisClient') as mock_client:
            # Mock Azure DI to raise exception
            mock_client.return_value.begin_analyze_document.side_effect = Exception("Azure DI error")

            service = OCRService()

            response = service.process_document(
                file_content=sample_pdf_content,
                filename="test.pdf",
                document_id="test-doc-error"
            )

            assert response.success is False
            assert response.error is not None
            assert "Azure DI error" in response.error

    @pytest.mark.unit
    def test_extract_structured_content_with_tables(self, temp_env_vars, mock_redis):
        """Test extraction of structured content including tables"""
        with patch('service.DocumentAnalysisClient'):
            service = OCRService()

            # Mock analyze result with tables
            mock_result = Mock()
            mock_result.pages = []
            mock_result.paragraphs = []

            # Create mock table
            mock_table = Mock()
            mock_table.row_count = 2
            mock_table.column_count = 3

            mock_cell1 = Mock()
            mock_cell1.row_index = 0
            mock_cell1.column_index = 0
            mock_cell1.content = "רחוב"

            mock_cell2 = Mock()
            mock_cell2.row_index = 1
            mock_cell2.column_index = 0
            mock_cell2.content = "הרמבם"

            mock_table.cells = [mock_cell1, mock_cell2]
            mock_result.tables = [mock_table]

            structured = service._extract_structured_content(mock_result)

            assert "tables" in structured
            assert len(structured["tables"]) == 1
            assert structured["tables"][0]["row_count"] == 2
            assert structured["tables"][0]["column_count"] == 3
            assert len(structured["tables"][0]["cells"]) == 2
            assert structured["tables"][0]["cells"][0]["content"] == "רחוב"


@pytest.mark.integration
class TestOCRServiceIntegration:
    """Integration tests with real Azure DI (requires credentials)"""

    def test_real_pdf_processing(self, sample_pdf_path, sample_pdf_content):
        """Test processing real PDF with Azure DI"""
        # Skip if no real credentials
        from shared.config import Config
        if not Config.AZURE_DI_ENDPOINT or not Config.AZURE_DI_KEY:
            pytest.skip("Azure credentials not configured")

        try:
            service = OCRService()

            response = service.process_document(
                file_content=sample_pdf_content,
                filename="283_ex1.pdf",
                document_id="integration-test-1"
            )

            assert response.success is True
            assert len(response.full_text) > 100
            assert response.processing_time_ms > 0

            # Check for Hebrew content
            assert any(char in response.full_text for char in "אבגדהוזחטיכלמנסעפצקרשת")

            print(f"\n✓ OCR extracted {len(response.full_text)} characters")
            print(f"✓ Processing time: {response.processing_time_ms:.2f}ms")
            print(f"✓ Pages: {len(response.structured_content.get('pages', []))}")
            print(f"✓ Tables: {len(response.structured_content.get('tables', []))}")

        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")