import streamlit as st
import json
import os
from datetime import datetime

import sys
import httpx

# Make shared package importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.config import Config
from shared.logging_config import get_logger

logger = get_logger("ui-service")

# --- CONFIGURATION ---
st.set_page_config(
    page_title="National Insurance Form Extractor",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .field-section {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    .field-label {
        font-weight: 600;
        color: #333;
        font-size: 0.9rem;
        margin-bottom: 0.3rem;
    }
    .field-value {
        color: #1f77b4;
        font-size: 1.1rem;
        font-weight: 500;
        padding: 0.5rem;
        background-color: #f8f9fa;
        border-radius: 0.3rem;
        margin-bottom: 0.8rem;
    }
    .empty-field {
        color: #999;
        font-style: italic;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2c3e50;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #1f77b4;
    }
    .stDownloadButton button {
        background-color: #1f77b4;
        color: white;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown('<p class="main-header">📋 National Insurance Form Extractor</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-Powered Field Extraction from Bituah Leumi Forms</p>', unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("ℹ️ About")
    st.info("""
    This system uses:
    - **Azure Document Intelligence** for OCR
    - **GPT-4o** for intelligent field extraction
    - **Advanced validation** for data quality
    """)

    st.header("📊 Capabilities")
    st.success("""
    ✅ Hebrew & English support
    ✅ Date normalization
    ✅ ID validation
    ✅ Phone validation
    """)


# --- HTTP CLIENT ---
@st.cache_resource
def get_http_client():
    return httpx.Client(timeout=60.0)


client = get_http_client()


def call_ocr_service(uploaded_file):
    """Call OCR microservice with uploaded file and return JSON result."""
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream",
        )
    }
    url = f"{Config.OCR_SERVICE_URL}/api/v1/ocr"
    logger.info("ui_call_ocr", url=url)
    resp = client.post(url, files=files)
    resp.raise_for_status()
    return resp.json()


def call_extraction_service(ocr_result: dict):
    """Call extraction microservice with OCRResponse JSON."""
    url = f"{Config.EXTRACTION_SERVICE_URL}/api/v1/extract"
    logger.info("ui_call_extraction", url=url)

    # --- ADD TRUNCATION LOGIC HERE ---
    full_text = ocr_result.get("full_text", "")

    # Stop processing once we reach the "Instructions" keywords
    # This prevents GPT from seeing the back of the form
    stop_keywords = ["עצמאי נכבד", "דברי הסבר", "עמוד 2 מתוך 2"]

    for word in stop_keywords:
        if word in full_text:
            full_text = full_text.split(word)[0]
            break  # Stop at the first keyword found

    # Update the dictionary with the cleaned text
    ocr_result["full_text"] = full_text
    # ---------------------------------

    resp = client.post(url, json=ocr_result)
    resp.raise_for_status()
    return resp.json()


def call_validation_service(extraction_result: dict):
    """Call validation microservice with ExtractionResponse JSON."""
    url = f"{Config.VALIDATION_SERVICE_URL}/api/v1/validate"
    logger.info("ui_call_validation", url=url)
    resp = client.post(url, json=extraction_result)
    resp.raise_for_status()
    return resp.json()

# --- FILE UPLOAD ---
st.markdown("### 📤 Upload Form")
uploaded_file = st.file_uploader(
    "Upload work injury form",
    type=["pdf", "jpg", "png", "jpeg"],
    help="Upload a filled National Insurance work injury form",
    label_visibility="collapsed",
)

if uploaded_file:
    # Display file info
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"📄 File: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
    with col2:
        if st.button("🔄 Process New File"):
            st.rerun()

    st.divider()

    # --- PROCESSING PIPELINE ---
    try:
        with st.spinner("🚀 Running AI Pipeline: OCR → GPT-4o Extraction → Validation..."):
            # 1. Run Azure OCR microservice
            ocr_result = call_ocr_service(uploaded_file)

            if not ocr_result.get("success"):
                st.error(f"❌ OCR Failed: {ocr_result.get('error')}")
                st.stop()

            # 2. Run GPT-4o Field Extraction microservice
            extraction_result = call_extraction_service(ocr_result)

            if not extraction_result.get("success"):
                st.error(f"❌ Extraction Failed: {extraction_result.get('error')}")
                st.stop()

            extracted_data = extraction_result["data"]

            # 3. Run Validation microservice
            val_result = call_validation_service(extraction_result)
            comp = val_result["completeness"]

        st.success("✅ Processing Complete!")

        # --- METRICS DISPLAY ---
        st.markdown("### 📊 Extraction Summary")

        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

        with metric_col1:
            st.metric(
                label="Completeness",
                value=f"{comp['percentage']}%",
                delta=f"{comp['filled_fields']} fields"
            )

        with metric_col2:
            st.metric(
                label="Fields Extracted",
                value=f"{comp['filled_fields']}/{comp['total_fields']}"
            )

        with metric_col3:
            validation_status = "Valid ✅" if val_result["valid"] else "Issues ⚠️"
            st.metric(
                label="Validation",
                value=validation_status
            )

        with metric_col4:
            ocr_chars = len(ocr_result['full_text'])
            st.metric(
                label="OCR Characters",
                value=f"{ocr_chars:,}"
            )

        st.divider()

        # --- TABBED VIEW ---
        tab1, tab2, tab3, tab4 = st.tabs(["📝 Structured View", "🔍 Raw JSON", "📄 OCR Text", "✅ Validation"])

        # TAB 1: BEAUTIFUL STRUCTURED VIEW
        with tab1:
            st.markdown("### 📋 Extracted Fields")


            def display_field(label, value, hebrew_label=None):
                """Display a single field beautifully with error styling if missing"""
                display_label = f"{label}"
                if hebrew_label:
                    display_label += f" / {hebrew_label}"

                st.markdown(f'<p class="field-label">{display_label}</p>', unsafe_allow_html=True)

                if value and str(value).strip():
                    # Standard display for existing values
                    st.markdown(f'<p class="field-value">{value}</p>', unsafe_allow_html=True)
                else:
                    # Red styling for missing values
                    st.markdown(
                        f'<p style="color: #d32f2f; background-color: #ffebee; padding: 0.5rem; border-radius: 0.3rem; font-style: italic;">Missing / לא צוין</p>',
                        unsafe_allow_html=True)

            def display_date(label, date_obj, hebrew_label=None):
                """Display a date field"""
                if date_obj.get("day") or date_obj.get("month") or date_obj.get("year"):
                    day = date_obj.get("day", "")
                    month = date_obj.get("month", "")
                    year = date_obj.get("year", "")
                    date_str = f"{day}/{month}/{year}" if all([day, month, year]) else f"{day} {month} {year}".strip()
                    display_field(label, date_str, hebrew_label)


            # Personal Information
            st.markdown('<p class="section-header">👤 Personal Information / מידע אישי</p>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                display_field("First Name", extracted_data.get("firstName"), "שם פרטי")
                display_field("ID Number", extracted_data.get("idNumber"), "מספר זהות")
                display_date("Date of Birth", extracted_data.get("dateOfBirth", {}), "תאריך לידה")

            with col2:
                display_field("Last Name", extracted_data.get("lastName"), "שם משפחה")
                display_field("Gender", extracted_data.get("gender"), "מין")

            # Contact Information
            st.markdown('<p class="section-header">📞 Contact Information / פרטי התקשרות</p>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                display_field("Mobile Phone", extracted_data.get("mobilePhone"), "טלפון נייד")
            with col2:
                display_field("Landline Phone", extracted_data.get("landlinePhone"), "טלפון קווי")

            # Address
            st.markdown('<p class="section-header">🏠 Address / כתובת</p>', unsafe_allow_html=True)

            address = extracted_data.get("address", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                display_field("Street", address.get("street"), "רחוב")
                display_field("Apartment", address.get("apartment"), "דירה")
                display_field("Postal Code", address.get("postalCode"), "מיקוד")

            with col2:
                display_field("House Number", address.get("houseNumber"), "מספר בית")
                display_field("City", address.get("city"), "ישוב")

            with col3:
                display_field("Entrance", address.get("entrance"), "כניסה")
                display_field("PO Box", address.get("poBox"), "תא דואר")

            # Work & Injury Details
            st.markdown('<p class="section-header">💼 Work & Injury Details / פרטי עבודה ופגיעה</p>',
                        unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                display_field("Job Type", extracted_data.get("jobType"), "סוג העבודה")
                display_date("Date of Injury", extracted_data.get("dateOfInjury", {}), "תאריך הפגיעה")
                display_field("Accident Location", extracted_data.get("accidentLocation"), "מקום התאונה")
                display_field("Injured Body Part", extracted_data.get("injuredBodyPart"), "האיבר שנפגע")

            with col2:
                display_field("Time of Injury", extracted_data.get("timeOfInjury"), "שעת הפגיעה")
                display_field("Accident Address", extracted_data.get("accidentAddress"), "כתובת מקום התאונה")
                display_field("Accident Description", extracted_data.get("accidentDescription"), "תיאור התאונה")

            # Form Information
            st.markdown('<p class="section-header">📄 Form Information / פרטי הטופס</p>', unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                display_date("Form Filling Date", extracted_data.get("formFillingDate", {}), "תאריך מילוי הטופס")
            with col2:
                display_date("Form Receipt Date", extracted_data.get("formReceiptDateAtClinic", {}), "תאריך קבלת הטופס")
            with col3:
                display_field("Signature", extracted_data.get("signature"), "חתימה")

            # Medical Institution Fields
            st.markdown('<p class="section-header">🏥 Medical Institution / למילוי ע״י המוסד הרפואי</p>',
                        unsafe_allow_html=True)

            medical = extracted_data.get("medicalInstitutionFields", {})
            display_field("Health Fund Member", medical.get("healthFundMember"), "חבר בקופת חולים")
            display_field("Nature of Accident", medical.get("natureOfAccident"), "מהות התאונה")
            display_field("Medical Diagnoses", medical.get("medicalDiagnoses"), "אבחנות רפואיות")

        # TAB 2: RAW JSON
        with tab2:
            st.markdown("### 📋 Complete JSON Output")

            # Pretty print JSON
            st.json(extracted_data)

            # Download button
            json_str = json.dumps(extracted_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"extracted_{uploaded_file.name.split('.')[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

        # TAB 3: OCR TEXT
        with tab3:
            st.markdown("### 📄 Extracted OCR Text")
            st.text_area(
                "Full OCR Output",
                ocr_result["full_text"],
                height=400,
                help="Raw text extracted by Azure Document Intelligence"
            )

            # OCR Statistics
            st.markdown("#### 📊 OCR Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Characters", f"{len(ocr_result['full_text']):,}")
            with col2:
                st.metric("Lines", len(ocr_result['full_text'].split('\n')))
            with col3:
                st.metric("Pages", len(ocr_result["structured_content"]["pages"]))

        # TAB 4: VALIDATION
        with tab4:
            st.markdown("### ✅ Validation Report")

            # Overall Status
            if val_result["valid"]:
                st.success("✅ All validations passed!")
            else:
                st.warning("⚠️ Some validation issues found")

            # Completeness
            st.markdown("#### 📊 Completeness")
            progress_val = comp['percentage'] / 100
            st.progress(progress_val)
            st.write(
                f"**{comp['filled_fields']}** out of **{comp['total_fields']}** fields filled ({comp['percentage']}%)")

            # Errors
            if val_result["errors"]:
                st.markdown("#### ❌ Validation Errors")
                for error in val_result["errors"]:
                    st.error(error)

            # Warnings
            if val_result["warnings"]:
                st.markdown("#### ⚠️ Warnings")
                for warning in val_result["warnings"]:
                    st.warning(warning)

            # Field Validations
            if val_result["field_validations"]:
                st.markdown("#### 🔍 Field-Level Validation")

                for field, result in val_result["field_validations"].items():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if result["valid"]:
                            st.success(f"✅ {field}")
                        else:
                            st.error(f"❌ {field}")
                    with col2:
                        st.write(result["message"])

    except Exception as e:
        st.error(f"❌ An error occurred during processing:")
        with st.expander("See error details"):
            st.exception(e)

else:
    # Instructions when no file is uploaded
    st.info("👆 Please upload a work injury form to begin extraction")

    st.markdown("### 🎯 How it works:")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        #### 1️⃣ Upload
        Upload a PDF or image of a filled National Insurance work injury form
        """)

    with col2:
        st.markdown("""
        #### 2️⃣ Process
        AI extracts text via OCR, then GPT-4o intelligently maps fields
        """)

    with col3:
        st.markdown("""
        #### 3️⃣ Download
        View results in structured format and download as JSON
        """)

    st.divider()

    st.markdown("### 📝 Sample Output Fields")
    st.code("""
{
  "lastName": "כהן",
  "firstName": "דוד",
  "idNumber": "123456789",
  "dateOfBirth": {"day": "15", "month": "03", "year": "1985"},
  "address": {
    "street": "הרצל",
    "houseNumber": "25",
    "city": "תל אביב"
  },
  "mobilePhone": "0501234567",
  "dateOfInjury": {"day": "10", "month": "06", "year": "2023"},
  "accidentDescription": "נפילה מגובה",
  ...
}
    """, language="json")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <small>
        Built with Azure Document Intelligence + GPT-4o | 
        Supports Hebrew & English
    </small>
</div>
""", unsafe_allow_html=True)