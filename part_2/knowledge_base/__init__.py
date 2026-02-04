"""
Knowledge Base package for Medical Chatbot
Handles document ingestion, storage, and retrieval with ADA-002 embeddings
"""
from .ingest import Document, DocumentIngestor, get_ingestor
from .vector_store import (
    VectorDocument, 
    VectorStore, 
    get_vector_store,
    EmbeddingService,
    get_embedding_service,
    ADA_002_DIMENSION
)

__all__ = [
    "Document",
    "DocumentIngestor",
    "get_ingestor",
    "VectorDocument",
    "VectorStore",
    "get_vector_store",
    "EmbeddingService",
    "get_embedding_service",
    "ADA_002_DIMENSION"
]
