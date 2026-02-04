"""
Services package for Medical Chatbot
"""


"""
Service initialization for the Medical Chatbot.

STATELESS ARCHITECTURE NOTE:
----------------------------
Services are initialized once at startup for efficiency, but they are
completely STATELESS. They do not store any user-specific data.

- llm_service: Only stores Azure OpenAI client (shared resource)
- rag_service: Loads knowledge base once (shared, read-only data)
- validation_service: Pure functions, no state
- language_service: Pure functions, no state

User data and conversation history are ONLY stored client-side in
Streamlit's session_state and passed with every request.

This allows multiple concurrent users without any state conflicts.
"""

from .llm_service import LLMService, get_llm_service
from .rag_service import RAGService, get_rag_service
from .validation_service import ValidationService, get_validation_service, validate_user_profile
from .language_service import LanguageService, get_language_service, detect_language

__all__ = [
    "LLMService",
    "get_llm_service",
    "RAGService", 
    "get_rag_service",
    "ValidationService",
    "get_validation_service",
    "validate_user_profile",
    "LanguageService",
    "get_language_service",
    "detect_language"
]
