"""
Language Service - Detects user language and provides language-aware utilities
"""
import re
from typing import Literal
from logger import logger


LanguageCode = Literal["he", "en"]


class LanguageService:
    """Service for language detection and handling"""
    
    # Hebrew Unicode range
    HEBREW_PATTERN = re.compile(r'[\u0590-\u05FF]')
    # Latin/English pattern
    LATIN_PATTERN = re.compile(r'[a-zA-Z]')
    
    def detect_language(self, text: str) -> LanguageCode:
        """
        Detect if text is primarily Hebrew or English.
        
        Args:
            text: Text to analyze
            
        Returns:
            'he' for Hebrew, 'en' for English
        """
        if not text:
            return "en"
        
        hebrew_count = len(self.HEBREW_PATTERN.findall(text))
        latin_count = len(self.LATIN_PATTERN.findall(text))
        
        # If more Hebrew characters, return Hebrew
        if hebrew_count > latin_count:
            return "he"
        return "en"
    
    def is_hebrew(self, text: str) -> bool:
        """Check if text is primarily Hebrew"""
        return self.detect_language(text) == "he"
    
    def is_english(self, text: str) -> bool:
        """Check if text is primarily English"""
        return self.detect_language(text) == "en"
    
    def get_language_instruction(self, language: LanguageCode) -> str:
        """
        Get explicit instruction for responding in the detected language.
        
        Args:
            language: Detected language code
            
        Returns:
            Instruction string to append to prompts
        """
        if language == "he":
            return """
CRITICAL LANGUAGE INSTRUCTION:
The user is writing in HEBREW. You MUST respond ENTIRELY in Hebrew (עברית).
Do NOT respond in English. Every word of your response must be in Hebrew.
Example greeting: "שלום", "היי", "בוקר טוב"
"""
        else:
            return """
CRITICAL LANGUAGE INSTRUCTION:
The user is writing in ENGLISH. You MUST respond ENTIRELY in English.
Do NOT respond in Hebrew. Every word of your response must be in English.
"""
    
    def get_language_name(self, language: LanguageCode) -> str:
        """Get human-readable language name"""
        return "Hebrew (עברית)" if language == "he" else "English"


# Singleton instance
_language_service = None


def get_language_service() -> LanguageService:
    """Get or create the language service singleton"""
    global _language_service
    if _language_service is None:
        _language_service = LanguageService()
    return _language_service


def detect_language(text: str) -> LanguageCode:
    """Convenience function for language detection"""
    return get_language_service().detect_language(text)
