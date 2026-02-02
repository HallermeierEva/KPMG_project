"""
Validation Service for Extracted Fields
Validates Israeli ID numbers, dates, and required fields
"""

import re
from typing import Dict, Any, List, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationService:
    """
    Service for validating extracted field data
    Includes Israeli ID validation, date validation, and completeness checks
    """

    def __init__(self):
        """Initialize validation service"""
        self.validation_rules = {
            "idNumber": self._validate_israeli_id,
            "dateOfBirth": self._validate_date,
            "dateOfInjury": self._validate_date,
            "formFillingDate": self._validate_date,
            "formReceiptDateAtClinic": self._validate_date,
            "mobilePhone": self._validate_phone,
            "landlinePhone": self._validate_phone,
        }

        logger.info("Validation Service initialized")

    def validate(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted data and return validation report

        Args:
            extracted_data: Dictionary containing extracted fields

        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "field_validations": {},
            "completeness": {
                "filled_fields": 0,
                "total_fields": 0,
                "percentage": 0.0
            }
        }

        # Validate each field
        for field_name, validator in self.validation_rules.items():
            if field_name in extracted_data:
                value = extracted_data[field_name]
                is_valid, message = validator(value)

                results["field_validations"][field_name] = {
                    "valid": is_valid,
                    "message": message,
                    "value": value
                }

                if not is_valid and value:  # Only error if value exists but invalid
                    results["errors"].append(f"{field_name}: {message}")
                    results["valid"] = False

        # Check completeness
        completeness = self._check_completeness(extracted_data)
        results["completeness"] = completeness

        # Add warnings for critical missing fields
        critical_fields = ["firstName", "lastName", "idNumber"]
        for field in critical_fields:
            value = extracted_data.get(field, "")
            if not value or value == "":
                results["warnings"].append(f"Critical field missing: {field}")
        filling_date = extracted_data.get("formFillingDate", {})
        receipt_date = extracted_data.get("formReceiptDateAtClinic", {})

        # 2. Convert to datetime objects for comparison
        try:
            if self._is_complete_date(filling_date) and self._is_complete_date(receipt_date):
                d_fill = datetime(int(filling_date['year']), int(filling_date['month']), int(filling_date['day']))
                d_receipt = datetime(int(receipt_date['year']), int(receipt_date['month']), int(receipt_date['day']))

                # 3. Apply your logic
                if d_receipt < d_fill:
                    results["valid"] = False
                    results["errors"].append(
                        f"Logic Error: Receipt date ({d_receipt.strftime('%d/%m/%Y')}) "
                        f"cannot be before filling date ({d_fill.strftime('%d/%m/%Y')})"
                    )
        except ValueError:
            pass  # Handle invalid dates elsewhere

        return results



        return results

    def _is_complete_date(self, d):
        return d and all(k in d and str(d[k]).isdigit() for k in ['day', 'month', 'year'])

    def _validate_israeli_id(self, id_number: str) -> Tuple[bool, str]:
        """
        Validate Israeli ID number (9 digits with check digit)

        Args:
            id_number: ID number string

        Returns:
            Tuple of (is_valid, message)
        """
        if not id_number or id_number == "":
            return True, "No ID provided"

        # Remove any spaces or dashes
        id_clean = re.sub(r'[^0-9]', '', str(id_number))

        # Must be 9 digits
        if len(id_clean) != 9:
            return False, f"Israeli ID must be 9 digits (got {len(id_clean)})"

        # Validate check digit using Luhn algorithm variant
        try:
            total = 0
            for i, digit in enumerate(id_clean):
                num = int(digit)

                # Multiply odd positions by 1, even positions by 2
                if i % 2 == 0:
                    num = num * 1
                else:
                    num = num * 2

                # If result > 9, sum the digits
                if num > 9:
                    num = num // 10 + num % 10

                total += num

            if total % 10 == 0:
                return True, "Valid Israeli ID"
            else:
                return False, "Invalid Israeli ID check digit"

        except ValueError:
            return False, "ID must contain only digits"

    def _validate_date(self, date_obj: Dict[str, str]) -> Tuple[bool, str]:
        """
        Validate date object with day, month, year

        Args:
            date_obj: Dictionary with 'day', 'month', 'year' keys

        Returns:
            Tuple of (is_valid, message)
        """
        if not date_obj:
            return True, "No date provided"

        if not isinstance(date_obj, dict):
            return False, "Date must be an object with day, month, year"

        day = date_obj.get("day", "")
        month = date_obj.get("month", "")
        year = date_obj.get("year", "")

        # If all empty, consider valid (optional field)
        if not day and not month and not year:
            return True, "No date provided"

        # If partial, that's a warning
        if not (day and month and year):
            return False, "Incomplete date (missing day, month, or year)"

        try:
            # Parse and validate
            day_int = int(day)
            month_int = int(month)
            year_int = int(year)

            # Basic range checks
            if not (1 <= day_int <= 31):
                return False, f"Invalid day: {day_int}"

            if not (1 <= month_int <= 12):
                return False, f"Invalid month: {month_int}"

            if not (1900 <= year_int <= 2100):
                return False, f"Invalid year: {year_int}"

            # Try to create actual date (will catch invalid dates like Feb 31)
            datetime(year_int, month_int, day_int)

            return True, "Valid date"

        except ValueError as e:
            return False, f"Invalid date: {str(e)}"

    def _validate_phone(self, phone: str) -> Tuple[bool, str]:
        """
        Validate Israeli phone number

        Args:
            phone: Phone number string

        Returns:
            Tuple of (is_valid, message)
        """
        if not phone or phone == "":
            return True, "No phone provided"
        if not phone or str(phone).strip() == "":
            # Changed: Return False instead of True to trigger the red UI state
            return False, "Phone number is required but missing"

        # Remove spaces, dashes, parentheses
        phone_clean = re.sub(r'[^0-9]', '', str(phone))

        # Israeli mobile: 05X-XXXXXXX (10 digits starting with 05)
        # Israeli landline: 0X-XXXXXXX (9-10 digits starting with 0)

        if len(phone_clean) < 9 or len(phone_clean) > 10:
            return False, f"Invalid phone length: {len(phone_clean)} digits"

        if not phone_clean.startswith('0'):
            return False, "Israeli phone must start with 0"

        # Mobile phones start with 05
        if phone_clean.startswith('05'):
            if len(phone_clean) == 10:
                return True, "Valid mobile phone"
            else:
                return False, "Mobile phone must be 10 digits"

        # Landline (02, 03, 04, 08, 09, etc.)
        if len(phone_clean) >= 9:
            return True, "Valid phone number"

        return False, "Invalid phone number format"

    def _check_completeness(self, data: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """
        Check how many fields are filled vs empty

        Args:
            data: Dictionary to check
            path: Current path in nested structure

        Returns:
            Dictionary with completeness statistics
        """
        filled = 0
        total = 0

        for key, value in data.items():
            if isinstance(value, dict):
                # Recursive for nested objects
                sub_result = self._check_completeness(value, f"{path}.{key}" if path else key)
                filled += sub_result["filled_fields"]
                total += sub_result["total_fields"]
            else:
                total += 1
                if value and str(value).strip() != "":
                    filled += 1

        percentage = (filled / total * 100) if total > 0 else 0

        return {
            "filled_fields": filled,
            "total_fields": total,
            "percentage": round(percentage, 1)
        }

    def generate_report(self, validation_result: Dict[str, Any]) -> str:
        """
        Generate human-readable validation report

        Args:
            validation_result: Result from validate() method

        Returns:
            Formatted string report
        """
        lines = []
        lines.append("=" * 60)
        lines.append("VALIDATION REPORT")
        lines.append("=" * 60)

        # Overall status
        status = "✅ VALID" if validation_result["valid"] else "❌ INVALID"
        lines.append(f"\nOverall Status: {status}")

        # Completeness
        comp = validation_result["completeness"]
        lines.append(f"\nCompleteness: {comp['filled_fields']}/{comp['total_fields']} fields ({comp['percentage']}%)")

        # Errors
        if validation_result["errors"]:
            lines.append(f"\n❌ Errors ({len(validation_result['errors'])}):")
            for error in validation_result["errors"]:
                lines.append(f"   - {error}")

        # Warnings
        if validation_result["warnings"]:
            lines.append(f"\n⚠️  Warnings ({len(validation_result['warnings'])}):")
            for warning in validation_result["warnings"]:
                lines.append(f"   - {warning}")

        # Field validations
        if validation_result["field_validations"]:
            lines.append(f"\n📋 Field Validations:")
            for field, result in validation_result["field_validations"].items():
                icon = "✅" if result["valid"] else "❌"
                lines.append(f"   {icon} {field}: {result['message']}")

        lines.append("\n" + "=" * 60)

        return "\n".join(lines)


# Test function
if __name__ == "__main__":
    """Test the validation service"""

    print("=" * 70)
    print("🧪  TESTING VALIDATION SERVICE")
    print("=" * 70)

    # Sample data
    test_data = {
        "lastName": "כהן",
        "firstName": "דוד",
        "idNumber": "123456789",  # Valid Israeli ID
        "dateOfBirth": {
            "day": "15",
            "month": "03",
            "year": "1985"
        },
        "address": {
            "street": "הרצל",
            "houseNumber": "25",
            "city": "תל אביב"
        },
        "mobilePhone": "0501234567",
        "dateOfInjury": {
            "day": "10",
            "month": "06",
            "year": "2023"
        }
    }

    # Test validation
    validator = ValidationService()
    result = validator.validate(test_data)

    # Print report
    report = validator.generate_report(result)
    print(report)

    # Test invalid ID
    print("\n\n" + "=" * 70)
    print("🧪  TESTING WITH INVALID ID")
    print("=" * 70)

    test_data["idNumber"] = "000000000"  # Invalid check digit
    result = validator.validate(test_data)
    report = validator.generate_report(result)
    print(report)