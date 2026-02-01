import streamlit as st
import json
import os
# --- STEP 1: IMPORT YOUR SERVICES ---
from ocr_service import DocumentOCRService
from extraction_service import FieldExtractionService
from validation_service import ValidationService

# --- CONFIGURATION ---
st.set_page_config(page_title="Work Injury Extraction Lab", page_icon="🧪", layout="wide")
st.title("🧪 OCR + GPT-4o Extraction Lab")
st.subheader("Israeli National Insurance Institute Forms")


# --- INITIALIZE SERVICES ---
@st.cache_resource
def init_services():
    return DocumentOCRService(), FieldExtractionService(), ValidationService()


ocr_service, extractor, validator = init_services()

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Work Injury Form (PDF/JPG)", type=['pdf', 'jpg', 'png', 'jpeg'])

if uploaded_file:
    # --- STEP 2: PROCESSING PIPELINE ---
    with st.spinner("🚀 AI Pipeline: Running OCR -> GPT-4o Extraction -> Validation..."):

        # 1. Run Azure OCR
        ocr_result = ocr_service.process_uploaded_file(uploaded_file)

        if ocr_result["success"]:
            # 2. Run GPT-4o Field Extraction
            extraction_result = extractor.extract_from_file(ocr_result)

            if extraction_result["success"]:
                extracted_data = extraction_result["data"]

                # 3. Run Validation Logic (Accuracy & Correctness)
                val_result = validator.validate(extracted_data)
                comp = val_result["completeness"]

                # --- STEP 3: DISPLAY METRICS ---
                st.divider()
                m1, m2, m3 = st.columns(3)

                # Accuracy Score is now the percentage of fields actually filled
                m1.metric("Completeness (Recall)", f"{comp['percentage']}%")
                m2.metric("Fields Filled", f"{comp['filled_fields']}/{comp['total_fields']}")
                m3.metric("Validation", "✅ Valid" if val_result["valid"] else "⚠️ Issues Found")

                # --- STEP 4: BEAUTIFUL JSON VIEW ---
                st.write("### 📊 Extracted Data Structure")
                st.json(extracted_data, expanded=True)

                # Optional: Show validation errors if any
                if val_result["errors"]:
                    st.error("### ❌ Validation Errors")
                    for err in val_result["errors"]:
                        st.write(f"- {err}")
            else:
                st.error(f"Extraction failed: {extraction_result['error']}")
        else:
            st.error(f"OCR failed: {ocr_result['error']}")

else:
    st.info("Upload one of your test forms (ex1, ex2, or ex3) to see the full 29-field extraction.")