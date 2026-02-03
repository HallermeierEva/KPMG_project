"""
Shared data models for all microservices
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class DateField(BaseModel):
    """Date field model"""
    day: str = ""
    month: str = ""
    year: str = ""


class AddressField(BaseModel):
    """Address field model"""
    street: str = ""
    houseNumber: str = ""
    entrance: str = ""
    apartment: str = ""
    city: str = ""
    postalCode: str = ""
    poBox: str = ""


class MedicalInstitutionFields(BaseModel):
    """Medical institution fields"""
    healthFundMember: str = ""
    natureOfAccident: str = ""
    medicalDiagnoses: str = ""


class ExtractedData(BaseModel):
    """Main extracted data model"""
    lastName: str = ""
    firstName: str = ""
    idNumber: str = ""
    gender: str = ""
    dateOfBirth: DateField = Field(default_factory=DateField)
    address: AddressField = Field(default_factory=AddressField)
    landlinePhone: str = ""
    mobilePhone: str = ""
    jobType: str = ""
    dateOfInjury: DateField = Field(default_factory=DateField)
    timeOfInjury: str = ""
    accidentLocation: str = ""
    accidentAddress: str = ""
    accidentDescription: str = ""
    injuredBodyPart: str = ""
    signature: str = ""
    formFillingDate: DateField = Field(default_factory=DateField)
    formReceiptDateAtClinic: DateField = Field(default_factory=DateField)
    medicalInstitutionFields: MedicalInstitutionFields = Field(default_factory=MedicalInstitutionFields)


class OCRResponse(BaseModel):
    """OCR service response"""
    success: bool
    document_id: str
    full_text: str = ""
    structured_content: Dict[str, Any] = {}
    processing_time_ms: float
    error: Optional[str] = None


class ExtractionResponse(BaseModel):
    """Extraction service response"""
    success: bool
    document_id: str
    data: ExtractedData
    confidence: Dict[str, float] = {}
    processing_time_ms: float
    error: Optional[str] = None


class ValidationResponse(BaseModel):
    """Validation service response"""
    valid: bool
    document_id: str
    errors: List[str] = []
    warnings: List[str] = []
    field_validations: Dict[str, Any] = {}
    completeness: Dict[str, Any] = {}
    accuracy_score: float = 0.0
    processing_time_ms: float


class PipelineResponse(BaseModel):
    """Complete pipeline response"""
    document_id: str
    ocr_result: OCRResponse
    extraction_result: ExtractionResponse
    validation_result: ValidationResponse
    total_processing_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)