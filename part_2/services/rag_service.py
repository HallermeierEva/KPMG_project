"""
RAG Service - Handles knowledge base retrieval and context building
"""
import os
from typing import List, Optional
from bs4 import BeautifulSoup
from logger import logger
from knowledge_base.ingest import get_ingestor, Document
from knowledge_base.vector_store import get_vector_store, VectorStore
from functools import lru_cache


class RAGService:
    """Service for Retrieval-Augmented Generation from knowledge base"""

    def __init__(self, data_dir: str = "phase2_data"):
        self.data_dir = data_dir
        self._cached_context: Optional[str] = None

        try:
            self.ingestor = get_ingestor(data_dir)
        except Exception as e:
            logger.error(f"Failed to initialize ingestor: {e}")
            # Do NOT return the error string. Just assign a fallback or raise.
            self.ingestor = None

        self.vector_store: Optional[VectorStore] = get_vector_store()

    @lru_cache(maxsize=1)
    def get_all_medical_context(self, use_cache: bool = True) -> str:
        """
        Load all medical context with caching.

        Args:
            use_cache: Whether to use cached context if available

        Returns:
            Combined context string from all HTML files
        """
        # 1. Check manual cache
        if use_cache and self._cached_context:
            return self._cached_context

        # 2. Check path existence
        if not os.path.exists(self.data_dir):
            error_msg = f"Knowledge base directory '{self.data_dir}' not found."
            logger.error(error_msg)
            return error_msg

        # 3. Ingest documents
        documents = self.ingestor.ingest_all()

        if not documents:
            error_msg = f"No supported files found in '{self.data_dir}' directory."
            logger.warning(error_msg)
            return error_msg

        logger.info(f"Loaded {len(documents)} documents from {self.data_dir}")

        # 4. Optionally populate vector store
        if self.vector_store:
            for doc in documents:
                self.vector_store.add_document(
                    content=doc.content,
                    doc_id=doc.filename,
                    metadata=doc.metadata,
                    generate_embedding=True
                )

        # 5. Build and store combined context
        combined_context = [doc.to_context_string() for doc in documents]

        if not combined_context:
            return "Error: Could not load any knowledge base files."

        self._cached_context = "\n".join(combined_context)
        return self._cached_context

    def _get_html_files(self) -> List[str]:
        """Legacy compatibility method"""
        return [doc.filename for doc in self.ingestor.get_documents()]

    def _parse_html_file(self, filename: str) -> Optional[str]:
        """Legacy compatibility method"""
        doc = self.ingestor.get_document_by_filename(filename)
        return doc.to_context_string() if doc else None

    def is_context_valid(self, context: str) -> bool:
        """Check if the context was loaded successfully"""
        return (
                "SOURCE FILE" in context
                and "not found" not in context
                and "Error" not in context
        )

    def clear_cache(self) -> None:
        """Clear the cached context and reset lru_cache"""
        self._cached_context = None
        self.get_all_medical_context.cache_clear()

    def get_available_files(self) -> List[str]:
        """Get list of available knowledge base files"""
        return self._get_html_files()

    def semantic_search(self, query: str, top_k: int = 5) -> List[tuple[str, float]]:
        """Semantic search over knowledge base using embeddings"""
        if not self.vector_store:
            logger.warning("Vector store not initialized; returning empty results")
            return []
        results = self.vector_store.semantic_search(query, top_k=top_k)
        return [(doc.metadata.get("source_file", doc.doc_id), score) for doc, score in results]


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service(data_dir: str = "phase2_data") -> RAGService:
    """Get or create the RAG service singleton"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(data_dir)
    return _rag_service