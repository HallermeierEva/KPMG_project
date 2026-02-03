"""
API endpoint tests for OCR Service
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import sys
from pathlib import Path
import io

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import app
from shared.models import OCRResponse


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_ocr_service():
    """Mock OCR service for API tests"""
    with patch('app.ocr_service') as mock:
        yield mock


class TestOCRAPI:
    """Test OCR API endpoints"""

    @pytest.mark.unit
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "ocr"

    @pytest.mark.unit
    def test_ocr_endpoint_success(self, client, mock_ocr_service, sample_pdf_content):
        """Test successful OCR request"""
        # Mock service response
        mock_response = OCRResponse(
            success=True,
            document_id="test-123",
            full_text="Sample extracted text",
            structured_content={"pages": []},
            processing_time_ms=123.45
        )
        mock_ocr_service.process_document.return_value = mock_response

        # Create file upload
        files = {
            'file': ('test.pdf', io.BytesIO(sample_pdf_content), 'application/pdf')
        }

        response = client.post("/api/v1/ocr", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["document_id"] == "test-123"
        assert "full_text" in data

    @pytest.mark.unit
    def test_ocr_endpoint_invalid_file_type(self, client):
        """Test OCR with invalid file type"""
        files = {
            'file': ('test.txt', io.BytesIO(b"text content"), 'text/plain')
        }

        response = client.post("/api/v1/ocr", files=files)

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    @pytest.mark.unit
    def test_ocr_endpoint_no_file(self, client):
        """Test OCR without file"""
        response = client.post("/api/v1/ocr")

        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_ocr_endpoint_file_too_large(self, client, mock_ocr_service):
        """Test OCR with file exceeding size limit"""
        # Create 11MB file (exceeds 10MB limit)
        large_content = b"x" * (11 * 1024 * 1024)

        files = {
            'file': ('large.pdf', io.BytesIO(large_content), 'application/pdf')
        }

        response = client.post("/api/v1/ocr", files=files)

        assert response.status_code == 400
        assert "File too large" in response.json()["detail"]

    @pytest.mark.unit
    def test_ocr_endpoint_processing_error(self, client, mock_ocr_service, sample_pdf_content):
        """Test OCR when service returns error"""
        # Mock service to return error
        mock_response = OCRResponse(
            success=False,
            document_id="test-error",
            processing_time_ms=50.0,
            error="Azure DI service error"
        )
        mock_ocr_service.process_document.return_value = mock_response

        files = {
            'file': ('test.pdf', io.BytesIO(sample_pdf_content), 'application/pdf')
        }

        response = client.post("/api/v1/ocr", files=files)

        assert response.status_code == 500
        assert "Azure DI service error" in response.json()["detail"]


@pytest.mark.integration
class TestOCRAPIIntegration:
    """Integration tests for OCR API"""

    def test_real_pdf_upload(self, client, sample_pdf_path):
        """Test uploading real PDF file"""
        from shared.config import Config
        if not Config.AZURE_DI_ENDPOINT or not Config.AZURE_DI_KEY:
            pytest.skip("Azure credentials not configured")

        with open(sample_pdf_path, 'rb') as f:
            files = {
                'file': ('283_ex1.pdf', f, 'application/pdf')
            }

            response = client.post("/api/v1/ocr", files=files)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert len(data["full_text"]) > 100
            assert data["processing_time_ms"] > 0

            print(f"\n✓ API processed PDF successfully")
            print(f"✓ Extracted {len(data['full_text'])} characters")
            print(f"✓ Processing time: {data['processing_time_ms']:.2f}ms")