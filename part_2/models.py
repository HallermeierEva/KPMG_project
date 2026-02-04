"""
Pydantic models for the Medical Chatbot API
"""
from pydantic import BaseModel, validator
from typing import List, Optional


class ChatRequest(BaseModel):
    """Incoming chat request from frontend"""
    message: str
    history: List[dict]
    user_profile: Optional[dict] = None
    phase: str
    preferred_language: Optional[str] = None  # 'he' or 'en' to maintain language consistency

    @validator('phase')
    def validate_phase(cls, v):
        if v not in ["collection", "qa"]:
            raise ValueError("Phase must be 'collection' or 'qa'")
        return v

    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class ChatResponse(BaseModel):
    """Chat response to frontend"""
    response: str
    extracted_profile: Optional[dict] = None
    phase: str
    error: Optional[str] = None


class UserProfile(BaseModel):
    """User profile data structure"""
    full_name: str
    id_number: str
    gender: str
    age: int
    hmo: str
    hmo_card_number: str
    insurance_tier: str

    class Config:
        # Allow field population by alias (for JSON keys with spaces)
        populate_by_name = True
