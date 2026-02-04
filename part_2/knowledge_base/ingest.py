"""
Ingest Module - Process and parse HTML files from the knowledge base
"""
import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from bs4 import BeautifulSoup
from logger import logger


@dataclass
class Document:
    """Represents a parsed document from the knowledge base"""
    filename: str
    content: str
    metadata: Dict[str, Any]
    
    def to_context_string(self) -> str:
        """Format document for LLM context"""
        return f"=== SOURCE FILE: {self.filename} ===\n{self.content}\n"


class DocumentIngestor:
    """Handles ingestion and parsing of HTML documents"""
    
    SUPPORTED_EXTENSIONS = [".html", ".htm"]
    
    def __init__(self, data_dir: str = "phase2_data"):
        self.data_dir = data_dir
        self._documents: List[Document] = []
    
    def ingest_all(self) -> List[Document]:
        """
        Ingest all supported files from the data directory.
        
        Returns:
            List of parsed Document objects
        """
        if not os.path.exists(self.data_dir):
            logger.error(f"Data directory '{self.data_dir}' not found")
            return []
        
        files = self._get_supported_files()
        if not files:
            logger.warning(f"No supported files found in '{self.data_dir}'")
            return []
        
        logger.info(f"Ingesting {len(files)} files from {self.data_dir}")
        
        self._documents = []
        for filename in files:
            doc = self._parse_file(filename)
            if doc:
                self._documents.append(doc)
        
        logger.info(f"Successfully ingested {len(self._documents)} documents")
        return self._documents
    
    def _get_supported_files(self) -> List[str]:
        """Get list of supported files in the data directory"""
        try:
            return [
                f for f in os.listdir(self.data_dir) 
                if any(f.endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)
            ]
        except Exception as e:
            logger.error(f"Error listing directory: {str(e)}")
            return []
    
    def _parse_file(self, filename: str) -> Optional[Document]:
        """
        Parse a single file and create a Document object.
        
        Args:
            filename: Name of the file to parse
            
        Returns:
            Document object or None if parsing fails
        """
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()
            
            # Parse HTML
            soup = BeautifulSoup(raw_content, "html.parser")
            
            # Extract text content
            text_content = soup.get_text(separator=' ', strip=True)
            
            # Extract metadata
            metadata = self._extract_metadata(soup, filename)
            
            return Document(
                filename=filename,
                content=text_content,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error parsing {filename}: {str(e)}")
            return None
    
    def _extract_metadata(self, soup: BeautifulSoup, filename: str) -> Dict[str, Any]:
        """Extract metadata from HTML document"""
        metadata = {
            "source_file": filename,
            "title": None,
            "tables_count": 0,
            "has_hebrew": False
        }
        
        # Extract title if available
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)
        
        # Count tables (useful for medical service data)
        metadata["tables_count"] = len(soup.find_all("table"))
        
        # Check for Hebrew content
        text = soup.get_text()
        metadata["has_hebrew"] = any('\u0590' <= char <= '\u05FF' for char in text)
        
        return metadata
    
    def get_documents(self) -> List[Document]:
        """Get previously ingested documents"""
        return self._documents
    
    def get_document_by_filename(self, filename: str) -> Optional[Document]:
        """Find a document by filename"""
        for doc in self._documents:
            if doc.filename == filename:
                return doc
        return None


# Singleton instance
_ingestor: Optional[DocumentIngestor] = None


def get_ingestor(data_dir: str = "phase2_data") -> DocumentIngestor:
    """Get or create the document ingestor singleton"""
    global _ingestor
    if _ingestor is None:
        _ingestor = DocumentIngestor(data_dir)
    return _ingestor
