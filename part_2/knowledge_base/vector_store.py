"""
Vector Store Module - Manages document embeddings and similarity search
Uses Azure OpenAI text-embedding-ada-002 for semantic search
"""
import os
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import hashlib
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from logger import logger

load_dotenv()

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("NumPy not available - vector operations will be limited")


# ADA-002 embedding dimension
ADA_002_DIMENSION = 1536


class EmbeddingService:
    """
    Service for generating embeddings using Azure OpenAI text-embedding-ada-002
    """
    
    def __init__(self):
        self.client: Optional[AzureOpenAI] = None
        self.deployment_name: Optional[str] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Azure OpenAI client for embeddings"""
        try:
            self.client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION")
            )
            # Use embedding deployment name, fallback to env var
            self.deployment_name = os.getenv(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", 
                "text-embedding-ada-002"
            )
            logger.info(f"Embedding service initialized with deployment: {self.deployment_name}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {str(e)}")
            self.client = None
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (1536 dimensions for ada-002) or None if failed
        """
        if not self.client:
            logger.warning("Embedding client not initialized")
            return None
        
        try:
            # Clean and truncate text (ada-002 has 8191 token limit)
            clean_text = text.replace("\n", " ").strip()
            if len(clean_text) > 30000:  # Approximate char limit
                clean_text = clean_text[:30000]
            
            response = self.client.embeddings.create(
                input=clean_text,
                model=self.deployment_name
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            return None
    
    def get_embeddings_batch(self, texts: List[str], batch_size: int = 16) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call
            
        Returns:
            List of embedding vectors (None for failed texts)
        """
        if not self.client:
            logger.warning("Embedding client not initialized")
            return [None] * len(texts)
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                # Clean texts
                clean_batch = [
                    t.replace("\n", " ").strip()[:30000] 
                    for t in batch
                ]
                
                response = self.client.embeddings.create(
                    input=clean_batch,
                    model=self.deployment_name
                )
                
                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(f"Generated {len(batch_embeddings)} embeddings (batch {i // batch_size + 1})")
                
            except Exception as e:
                logger.error(f"Batch embedding failed: {str(e)}")
                all_embeddings.extend([None] * len(batch))
        
        return all_embeddings
    
    def is_available(self) -> bool:
        """Check if embedding service is available"""
        return self.client is not None


# Singleton embedding service
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


@dataclass
class VectorDocument:
    """Document with embedding vector"""
    doc_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorDocument":
        """Deserialize from dictionary"""
        return cls(
            doc_id=data["doc_id"],
            content=data["content"],
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {})
        )


class VectorStore:
    """
    In-memory vector store with Azure OpenAI ADA-002 embeddings.
    Supports semantic search via cosine similarity.
    """
    
    def __init__(self, persist_path: Optional[str] = None, auto_embed: bool = True):
        """
        Initialize vector store.
        
        Args:
            persist_path: Optional path to persist/load the store
            auto_embed: Whether to automatically generate embeddings when adding documents
        """
        self.documents: Dict[str, VectorDocument] = {}
        self.persist_path = persist_path
        self.auto_embed = auto_embed
        self.embedding_service = get_embedding_service()
        
        if persist_path and os.path.exists(persist_path):
            self._load()
    
    def add_document(
        self, 
        content: str, 
        doc_id: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        generate_embedding: Optional[bool] = None
    ) -> str:
        """
        Add a document to the store.
        
        Args:
            content: Document text content
            doc_id: Optional document ID (auto-generated if not provided)
            embedding: Optional pre-computed embedding vector
            metadata: Optional metadata dictionary
            generate_embedding: Whether to generate embedding (overrides auto_embed)
            
        Returns:
            Document ID
        """
        if doc_id is None:
            doc_id = self._generate_id(content)
        
        # Generate embedding if needed
        should_embed = generate_embedding if generate_embedding is not None else self.auto_embed
        if embedding is None and should_embed:
            embedding = self.embedding_service.get_embedding(content)
        
        doc = VectorDocument(
            doc_id=doc_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {}
        )
        
        self.documents[doc_id] = doc
        logger.debug(f"Added document {doc_id} to vector store (has_embedding={embedding is not None})")
        
        return doc_id
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple documents to the store.
        
        Args:
            documents: List of dicts with 'content', optional 'doc_id', 'embedding', 'metadata'
            
        Returns:
            List of document IDs
        """
        doc_ids = []
        for doc_data in documents:
            doc_id = self.add_document(
                content=doc_data["content"],
                doc_id=doc_data.get("doc_id"),
                embedding=doc_data.get("embedding"),
                metadata=doc_data.get("metadata")
            )
            doc_ids.append(doc_id)
        
        logger.info(f"Added {len(doc_ids)} documents to vector store")
        return doc_ids
    
    def get_document(self, doc_id: str) -> Optional[VectorDocument]:
        """Get document by ID"""
        return self.documents.get(doc_id)
    
    def get_all_documents(self) -> List[VectorDocument]:
        """Get all documents"""
        return list(self.documents.values())
    
    def get_all_content(self) -> str:
        """Get combined content of all documents (for simple RAG)"""
        return "\n\n".join(doc.content for doc in self.documents.values())
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document by ID"""
        if doc_id in self.documents:
            del self.documents[doc_id]
            logger.debug(f"Deleted document {doc_id}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all documents"""
        self.documents.clear()
        logger.info("Cleared vector store")
    
    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> List[Tuple[VectorDocument, float]]:
        """
        Semantic search using ADA-002 embeddings.
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of (document, similarity_score) tuples
        """
        # Generate query embedding
        query_embedding = self.embedding_service.get_embedding(query)
        if query_embedding is None:
            logger.warning("Failed to generate query embedding, falling back to keyword search")
            # Fallback to keyword search
            keyword_results = self.search_by_keyword(query)
            return [(doc, 1.0) for doc in keyword_results[:top_k]]
        
        return self.search_by_embedding(query_embedding, top_k, min_similarity)
    
    def search_by_embedding(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> List[Tuple[VectorDocument, float]]:
        """
        Search for similar documents using pre-computed embedding.
        
        Args:
            query_embedding: Query vector (1536 dimensions for ada-002)
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of (document, similarity_score) tuples
        """
        if not HAS_NUMPY:
            logger.warning("NumPy required for embedding search")
            return []
        
        results = []
        query_vec = np.array(query_embedding)
        
        for doc in self.documents.values():
            if doc.embedding is None:
                continue
            
            doc_vec = np.array(doc.embedding)
            similarity = self._cosine_similarity(query_vec, doc_vec)
            
            if similarity >= min_similarity:
                results.append((doc, similarity))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def search_by_keyword(self, keyword: str, case_sensitive: bool = False) -> List[VectorDocument]:
        """
        Simple keyword search in document content.
        
        Args:
            keyword: Search term
            case_sensitive: Whether search is case-sensitive
            
        Returns:
            List of matching documents
        """
        results = []
        search_term = keyword if case_sensitive else keyword.lower()
        
        for doc in self.documents.values():
            content = doc.content if case_sensitive else doc.content.lower()
            if search_term in content:
                results.append(doc)
        
        return results
    
    def _generate_id(self, content: str) -> str:
        """Generate document ID from content hash"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    @staticmethod
    def _cosine_similarity(vec1: "np.ndarray", vec2: "np.ndarray") -> float:
        """Calculate cosine similarity between two vectors"""
        if not HAS_NUMPY:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def persist(self) -> bool:
        """Save store to disk"""
        if not self.persist_path:
            logger.warning("No persist path configured")
            return False
        
        try:
            data = {
                doc_id: doc.to_dict() 
                for doc_id, doc in self.documents.items()
            }
            
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Persisted {len(data)} documents to {self.persist_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to persist vector store: {str(e)}")
            return False
    
    def _load(self) -> bool:
        """Load store from disk"""
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.documents = {
                doc_id: VectorDocument.from_dict(doc_data)
                for doc_id, doc_data in data.items()
            }
            
            logger.info(f"Loaded {len(self.documents)} documents from {self.persist_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load vector store: {str(e)}")
            return False
    
    def embed_all_documents(self) -> int:
        """
        Generate embeddings for all documents that don't have one.
        
        Returns:
            Number of documents embedded
        """
        docs_to_embed = [
            doc for doc in self.documents.values() 
            if doc.embedding is None
        ]
        
        if not docs_to_embed:
            logger.info("All documents already have embeddings")
            return 0
        
        logger.info(f"Generating embeddings for {len(docs_to_embed)} documents...")
        
        texts = [doc.content for doc in docs_to_embed]
        embeddings = self.embedding_service.get_embeddings_batch(texts)
        
        embedded_count = 0
        for doc, embedding in zip(docs_to_embed, embeddings):
            if embedding is not None:
                doc.embedding = embedding
                embedded_count += 1
        
        logger.info(f"Successfully embedded {embedded_count}/{len(docs_to_embed)} documents")
        return embedded_count
    
    def stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        docs_with_embeddings = sum(1 for doc in self.documents.values() if doc.embedding)
        
        return {
            "total_documents": len(self.documents),
            "documents_with_embeddings": docs_with_embeddings,
            "embedding_coverage": f"{docs_with_embeddings}/{len(self.documents)}",
            "embedding_model": "text-embedding-ada-002",
            "embedding_dimensions": ADA_002_DIMENSION,
            "total_content_length": sum(len(doc.content) for doc in self.documents.values())
        }


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store(persist_path: Optional[str] = None, auto_embed: bool = True) -> VectorStore:
    """Get or create the vector store singleton"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(persist_path, auto_embed)
    return _vector_store
