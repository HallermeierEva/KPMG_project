"""
Pytest fixtures and configuration
"""
import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import Config


@pytest.fixture
def sample_pdf_path():
    """Path to sample PDF file"""
    # Use the test data from phase1_data
    test_file = Path(__file__).parent / "test_data" / "283_ex1.pdf"

    # If not exists, try to find in project root
    if not test_file.exists():
        project_root = Path(__file__).parent.parent.parent.parent
        test_file = project_root / "data" / "283_ex1.pdf"

    if not test_file.exists():
        pytest.skip("Test PDF file not found")

    return str(test_file)


@pytest.fixture
def sample_pdf_content(sample_pdf_path):
    """Read sample PDF as bytes"""
    with open(sample_pdf_path, 'rb') as f:
        return f.read()


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis for testing without actual Redis"""

    class MockRedis:
        def __init__(self, *args, **kwargs):
            self.data = {}

        def ping(self):
            return True

        def get(self, key):
            return self.data.get(key)

        def setex(self, key, ttl, value):
            self.data[key] = value
            return True

        def delete(self, key):
            if key in self.data:
                del self.data[key]
            return True

    import redis
    monkeypatch.setattr(redis, "Redis", MockRedis)
    return MockRedis


@pytest.fixture
def temp_env_vars(monkeypatch):
    """Set temporary environment variables for testing"""
    # Only set if not already set
    if not os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"):
        monkeypatch.setenv(
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
            "https://test-endpoint.cognitiveservices.azure.com"
        )

    if not os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"):
        monkeypatch.setenv(
            "AZURE_DOCUMENT_INTELLIGENCE_KEY",
            "test-key-12345"
        )