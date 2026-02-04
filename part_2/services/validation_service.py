"""
Validation Service - Handles all input validation logic
"""
from typing import Tuple, Dict, Any
from logger import logger


# Valid values for HMO and Insurance Tier
VALID_HMOS_HEBREW = ["מכבי", "מאוחדת", "כללית"]
VALID_HMOS_ENGLISH = ["Maccabi", "Meuhedet", "Clalit"]
VALID_HMOS = VALID_HMOS_HEBREW + VALID_HMOS_ENGLISH

VALID_TIERS_HEBREW = ["זהב", "כסף", "ארד"]
VALID_TIERS_ENGLISH = ["Gold", "Silver", "Bronze"]
VALID_TIERS = VALID_TIERS_HEBREW + VALID_TIERS_ENGLISH

VALID_GENDERS = ["Male", "Female", "זכר", "נקבה", "M", "F"]

# Mappings for normalization
HMO_MAPPING = {
    "Maccabi": "מכבי",
    "Meuhedet": "מאוחדת",
    "Clalit": "כללית"
}

TIER_MAPPING = {
    "Gold": "זהב",
    "Silver": "כסף",
    "Bronze": "ארד"
}

REQUIRED_PROFILE_FIELDS = [
    "Full Name",
    "ID",
    "Gender",
    "Age",
    "HMO",
    "HMO Card Number",
    "Insurance Tier"
]


class ValidationService:
    """Service for validating user input and profiles"""
    
    def validate_user_profile(self, profile: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates user profile data.
        
        Args:
            profile: Dictionary containing user profile fields
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check all required fields exist
        for field in REQUIRED_PROFILE_FIELDS:
            if field not in profile or not profile[field]:
                return False, f"Missing required field: {field}"
        
        # Validate ID number (9 digits)
        if not self._is_valid_id(profile["ID"]):
            return False, "ID must be exactly 9 digits"
        
        # Validate HMO Card Number (9 digits)
        if not self._is_valid_card_number(profile["HMO Card Number"]):
            return False, "HMO Card Number must be exactly 9 digits"
        
        # Validate Age (0-120)
        valid_age, age_error = self._validate_age(profile["Age"])
        if not valid_age:
            return False, age_error
        
        # Validate HMO name
        if not self._is_valid_hmo(profile["HMO"]):
            return False, f"HMO must be one of: {', '.join(VALID_HMOS)}"
        
        # Validate Insurance Tier
        if not self._is_valid_tier(profile["Insurance Tier"]):
            return False, f"Insurance Tier must be one of: {', '.join(VALID_TIERS)}"
        
        # Validate Gender
        if not self._is_valid_gender(profile["Gender"]):
            return False, f"Gender must be one of: {', '.join(VALID_GENDERS)}"
        
        return True, ""
    
    def normalize_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize profile values to Hebrew for consistency.
        
        Args:
            profile: User profile dictionary
            
        Returns:
            Normalized profile dictionary
        """
        normalized = profile.copy()
        
        # Normalize HMO to Hebrew
        if normalized.get("HMO") in HMO_MAPPING:
            normalized["HMO"] = HMO_MAPPING[normalized["HMO"]]
        
        # Normalize tier to Hebrew
        if normalized.get("Insurance Tier") in TIER_MAPPING:
            normalized["Insurance Tier"] = TIER_MAPPING[normalized["Insurance Tier"]]
        
        return normalized
    
    def validate_and_normalize(self, profile: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate and normalize a user profile.
        
        Args:
            profile: User profile dictionary
            
        Returns:
            Tuple of (is_valid, error_message, normalized_profile)
        """
        is_valid, error = self.validate_user_profile(profile)
        if not is_valid:
            return False, error, profile
        
        normalized = self.normalize_profile(profile)
        return True, "", normalized
    
    @staticmethod
    def _is_valid_id(id_value: str) -> bool:
        """Check if ID is exactly 9 digits"""
        return id_value.isdigit() and len(id_value) == 9
    
    @staticmethod
    def _is_valid_card_number(card_number: str) -> bool:
        """Check if card number is exactly 9 digits"""
        return card_number.isdigit() and len(card_number) == 9
    
    @staticmethod
    def _validate_age(age_value: Any) -> Tuple[bool, str]:
        """Validate age is between 0 and 120"""
        try:
            age = int(age_value)
            if age < 0 or age > 120:
                return False, "Age must be between 0 and 120"
            return True, ""
        except ValueError:
            return False, "Age must be a valid number"
    
    @staticmethod
    def _is_valid_hmo(hmo: str) -> bool:
        """Check if HMO is valid"""
        return hmo in VALID_HMOS
    
    @staticmethod
    def _is_valid_tier(tier: str) -> bool:
        """Check if insurance tier is valid"""
        return tier in VALID_TIERS
    
    @staticmethod
    def _is_valid_gender(gender: str) -> bool:
        """Check if gender is valid"""
        return gender in VALID_GENDERS


# Singleton instance
_validation_service = None


def get_validation_service() -> ValidationService:
    """Get or create the validation service singleton"""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service


# Legacy function for backward compatibility
def validate_user_profile(profile: dict) -> Tuple[bool, str]:
    """
    Legacy function for backward compatibility.
    Use get_validation_service().validate_user_profile() instead.
    """
    service = get_validation_service()
    return service.validate_user_profile(profile)
