"""
Configuration file for Part 1 - Field Extraction System
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""

    # Azure Document Intelligence
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    AZURE_OPENAI_GPT4O_DEPLOYMENT = os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT", "gpt-4o")
    AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT = os.getenv("AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT", "gpt-4o-mini")

    # Application settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MAX_FILE_SIZE_MB = 10
    SUPPORTED_FILE_TYPES = ['pdf', 'jpg', 'jpeg', 'png']

    # Form field schema
    FORM_SCHEMA = {
        "lastName": "",
        "firstName": "",
        "idNumber": "",
        "gender": "",
        "dateOfBirth": {
            "day": "",
            "month": "",
            "year": ""
        },
        "address": {
            "street": "",
            "houseNumber": "",
            "entrance": "",
            "apartment": "",
            "city": "",
            "postalCode": "",
            "poBox": ""
        },
        "landlinePhone": "",
        "mobilePhone": "",
        "jobType": "",
        "dateOfInjury": {
            "day": "",
            "month": "",
            "year": ""
        },
        "timeOfInjury": "",
        "accidentLocation": "",
        "accidentAddress": "",
        "accidentDescription": "",
        "injuredBodyPart": "",
        "signature": "",
        "formFillingDate": {
            "day": "",
            "month": "",
            "year": ""
        },
        "formReceiptDateAtClinic": {
            "day": "",
            "month": "",
            "year": ""
        },
        "medicalInstitutionFields": {
            "healthFundMember": "",
            "natureOfAccident": "",
            "medicalDiagnoses": ""
        }
    }

    # Hebrew field names mapping
    HEBREW_FIELD_MAPPING = {
        "שם משפחה": "lastName",
        "שם פרטי": "firstName",
        "מספר זהות": "idNumber",
        "מין": "gender",
        "תאריך לידה": "dateOfBirth",
        "יום": "day",
        "חודש": "month",
        "שנה": "year",
        "כתובת": "address",
        "רחוב": "street",
        "מספר בית": "houseNumber",
        "כניסה": "entrance",
        "דירה": "apartment",
        "ישוב": "city",
        "מיקוד": "postalCode",
        "תא דואר": "poBox",
        "טלפון קווי": "landlinePhone",
        "טלפון נייד": "mobilePhone",
        "סוג העבודה": "jobType",
        "תאריך הפגיעה": "dateOfInjury",
        "שעת הפגיעה": "timeOfInjury",
        "מקום התאונה": "accidentLocation",
        "כתובת מקום התאונה": "accidentAddress",
        "תיאור התאונה": "accidentDescription",
        "האיבר שנפגע": "injuredBodyPart",
        "חתימה": "signature",
        "תאריך מילוי הטופס": "formFillingDate",
        "תאריך קבלת הטופס בקופה": "formReceiptDateAtClinic",
        "למילוי ע\"י המוסד הרפואי": "medicalInstitutionFields",
        "חבר בקופת חולים": "healthFundMember",
        "מהות התאונה": "natureOfAccident",
        "אבחנות רפואיות": "medicalDiagnoses"
    }

    @classmethod
    def validate(cls):
        """Validate that all required configurations are set"""
        errors = []

        if not cls.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT:
            errors.append("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT is not set")

        if not cls.AZURE_DOCUMENT_INTELLIGENCE_KEY:
            errors.append("AZURE_DOCUMENT_INTELLIGENCE_KEY is not set")

        if not cls.AZURE_OPENAI_ENDPOINT:
            errors.append("AZURE_OPENAI_ENDPOINT is not set")

        if not cls.AZURE_OPENAI_KEY:
            errors.append("AZURE_OPENAI_KEY is not set")

        if errors:
            raise ValueError(
                "Missing required configuration:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        return True


# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    print(f"⚠️  Configuration Warning: {e}")
    print("Please ensure your .env file is properly configured")