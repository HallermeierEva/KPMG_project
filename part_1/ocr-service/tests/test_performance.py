"""
Performance and load tests for OCR Service
"""
import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.slow
class TestOCRPerformance:
    """Performance tests for OCR service"""

    def test_single_document_performance(self, sample_pdf_content):
        """Test single document processing performance"""
        from shared.config import Config
        if not Config.AZURE_DI_ENDPOINT or not Config.AZURE_DI_KEY:
            pytest.skip("Azure credentials not configured")

        from service import OCRService
        service = OCRService()

        # Warm up
        service.process_document(sample_pdf_content, "warmup.pdf", "warmup-1")

        # Measure 5 runs
        times = []
        for i in range(5):
            start = time.time()
            result = service.process_document(
                sample_pdf_content,
                f"test-{i}.pdf",
                f"perf-test-{i}"
            )
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

            assert result.success is True

        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)

        print(f"\n📊 Performance Metrics:")
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Min: {min_time:.2f}ms")
        print(f"   Max: {max_time:.2f}ms")
        print(f"   Std Dev: {statistics.stdev(times):.2f}ms")

        # Performance assertions
        assert avg_time < 8000, "Average processing time should be under 8 seconds"

    def test_cache_performance(self, sample_pdf_content):
        """Test cache improves performance"""
        from shared.config import Config
        if not Config.AZURE_DI_ENDPOINT or not Config.AZURE_DI_KEY:
            pytest.skip("Azure credentials not configured")

        from service import OCRService
        service = OCRService()

        # First request (no cache)
        start = time.time()
        result1 = service.process_document(
            sample_pdf_content,
            "cache-test.pdf",
            "cache-1"
        )
        time_no_cache = (time.time() - start) * 1000

        # Second request (should use cache)
        start = time.time()
        result2 = service.process_document(
            sample_pdf_content,
            "cache-test.pdf",
            "cache-2"
        )
        time_with_cache = (time.time() - start) * 1000

        print(f"\n🚀 Cache Performance:")
        print(f"   Without cache: {time_no_cache:.2f}ms")
        print(f"   With cache: {time_with_cache:.2f}ms")
        print(f"   Speedup: {time_no_cache / time_with_cache:.1f}x")

        # Cache should be significantly faster
        assert time_with_cache < time_no_cache * 0.1, "Cache should be at least 10x faster"

    @pytest.mark.slow
    def test_concurrent_requests(self, sample_pdf_content):
        """Test handling concurrent OCR requests"""
        from shared.config import Config
        if not Config.AZURE_DI_ENDPOINT or not Config.AZURE_DI_KEY:
            pytest.skip("Azure credentials not configured")

        from service import OCRService
        service = OCRService()

        def process_one(index):
            return service.process_document(
                sample_pdf_content,
                f"concurrent-{index}.pdf",
                f"concurrent-{index}"
            )

        # Process 5 documents concurrently
        start = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_one, range(5)))
        total_time = (time.time() - start) * 1000

        # All should succeed
        assert all(r.success for r in results)

        print(f"\n🔄 Concurrent Processing:")
        print(f"   Total time for 5 docs: {total_time:.2f}ms")
        print(f"   Average per doc: {total_time / 5:.2f}ms")