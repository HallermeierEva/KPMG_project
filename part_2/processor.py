from bs4 import BeautifulSoup
import os
import logging

logger = logging.getLogger("MedicalChatBot")


def get_all_medical_context():
    """Reads all HTML files from phase2_data and formats them for the LLM context."""
    data_dir = "phase2_data"  # FIXED: Correct directory per requirements
    combined_context = []

    if not os.path.exists(data_dir):
        error_msg = f"Knowledge base directory '{data_dir}' not found."
        logger.error(error_msg)
        return error_msg

    html_files = [f for f in os.listdir(data_dir) if f.endswith(".html")]

    if not html_files:
        error_msg = f"No HTML files found in '{data_dir}' directory."
        logger.warning(error_msg)
        return error_msg

    logger.info(f"Loading {len(html_files)} HTML files from {data_dir}")

    for filename in html_files:
        file_path = os.path.join(data_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
                # Clean up the text while keeping structure
                text = soup.get_text(separator=' ', strip=True)
                combined_context.append(f"=== SOURCE FILE: {filename} ===\n{text}\n")
        except Exception as e:
            logger.error(f"Error reading {filename}: {str(e)}")
            continue

    if not combined_context:
        return "Error: Could not load any knowledge base files."

    logger.info(f"Successfully loaded {len(combined_context)} files")
    return "\n".join(combined_context)


def validate_user_profile(profile: dict) -> tuple[bool, str]:
    """
    Validates user profile phase2_data.
    Returns: (is_valid, error_message)
    """
    required_fields = ["Full Name", "ID", "Gender", "Age", "HMO", "HMO Card Number", "Insurance Tier"]

    # Check all required fields exist
    for field in required_fields:
        if field not in profile or not profile[field]:
            return False, f"Missing required field: {field}"

    # Validate ID number (9 digits)
    if not profile["ID"].isdigit() or len(profile["ID"]) != 9:
        return False, "ID must be exactly 9 digits"

    # Validate HMO Card Number (9 digits)
    if not profile["HMO Card Number"].isdigit() or len(profile["HMO Card Number"]) != 9:
        return False, "HMO Card Number must be exactly 9 digits"

    # Validate Age (0-120)
    try:
        age = int(profile["Age"])
        if age < 0 or age > 120:
            return False, "Age must be between 0 and 120"
    except ValueError:
        return False, "Age must be a valid number"

    # Validate HMO name (Hebrew or English)
    valid_hmos = ["מכבי", "מאוחדת", "כללית", "Maccabi", "Meuhedet", "Clalit"]
    if profile["HMO"] not in valid_hmos:
        return False, f"HMO must be one of: {', '.join(valid_hmos)}"

    # Normalize HMO to Hebrew for consistency
    hmo_mapping = {
        "Maccabi": "מכבי",
        "Meuhedet": "מאוחדת",
        "Clalit": "כללית"
    }
    if profile["HMO"] in hmo_mapping:
        profile["HMO"] = hmo_mapping[profile["HMO"]]

    # Validate Insurance Tier (Hebrew or English)
    valid_tiers = ["זהב", "כסף", "ארד", "Gold", "Silver", "Bronze"]
    if profile["Insurance Tier"] not in valid_tiers:
        return False, f"Insurance Tier must be one of: {', '.join(valid_tiers)}"

    # Normalize tier to Hebrew for consistency
    tier_mapping = {
        "Gold": "זהב",
        "Silver": "כסף",
        "Bronze": "ארד"
    }
    if profile["Insurance Tier"] in tier_mapping:
        profile["Insurance Tier"] = tier_mapping[profile["Insurance Tier"]]

    # Validate Gender
    valid_genders = ["Male", "Female", "זכר", "נקבה", "M", "F"]
    if profile["Gender"] not in valid_genders:
        return False, f"Gender must be one of: {', '.join(valid_genders)}"

    return True, ""