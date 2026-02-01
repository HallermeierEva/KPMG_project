# Part 1: Field Extraction using Document Intelligence & Azure OpenAI

## 📋 Overview

This system extracts structured information from ביטוח לאומי (National Insurance Institute) forms using:
- **Azure Document Intelligence** for OCR (text extraction)
- **Azure OpenAI GPT-4o** for intelligent field extraction
- **Streamlit** for the user interface

---

## 🏗️ Project Structure

```
part1_field_extraction/
├── config.py                  # Configuration and settings
├── ocr_service.py             # Azure Document Intelligence OCR
├── extraction_service.py      # GPT-4o field extraction (coming next)
├── validation_service.py      # Data validation (coming next)
├── app.py                     # Streamlit UI (coming next)
├── test_ocr.py               # OCR test script
└── prompts/
    └── extraction_prompt.txt  # LLM prompt for field extraction
```

---

## 🚀 Quick Start

### Step 1: Install Dependencies

Make sure you have these packages installed:

```bash
pip install azure-ai-documentintelligence
pip install azure-ai-formrecognizer
pip install openai
pip install streamlit
pip install python-dotenv
pip install Pillow
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root with:

```env
# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key-here

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_GPT4O_DEPLOYMENT=gpt-4o
```

### Step 3: Test OCR Service

Run the test script to verify OCR is working:

```bash
cd part1_field_extraction
python test_ocr.py
```

Expected output:
```
✅ OCR Service initialized successfully!
✅ OCR Processing Successful!
📄 Extracted Text Statistics:
   - Total characters: 2450
   - Total pages: 2
   - Paragraphs: 45
```

---

## 📖 How It Works

### 1. **OCR with Document Intelligence**

The `DocumentOCRService` class in `ocr_service.py`:

```python
from ocr_service import DocumentOCRService

# Initialize
ocr = DocumentOCRService()

# Process a file
result = ocr.process_file("form.pdf")

# Get extracted text
text = result["full_text"]
structured = result["structured_content"]
```

**Features:**
- ✅ Supports PDF, JPG, PNG
- ✅ Extracts text with layout preservation
- ✅ Handles Hebrew and English
- ✅ Provides structured content (pages, paragraphs, tables)
- ✅ Bounding box information for each element

### 2. **Structured Content**

The OCR service extracts:

```python
{
    "full_text": "Complete text...",
    "structured_content": {
        "pages": [
            {
                "page_number": 1,
                "lines": [
                    {"content": "Line text", "bounding_box": [...]}
                ]
            }
        ],
        "paragraphs": [...],
        "tables": [...],
        "key_value_pairs": [...]
    }
}
```

---

## 🧪 Testing Your OCR

### Test with Sample Files

1. **Place your test PDFs** in the `phase1_data` folder:
   ```
   phase1_data/
   ├── sample1.pdf
   ├── sample2.pdf
   └── sample3.pdf
   ```

2. **Run the test:**
   ```bash
   python test_ocr.py
   ```

3. **Check the output** - you should see extracted text from your forms

### Manual Testing

```python
from ocr_service import DocumentOCRService

# Initialize service
ocr = DocumentOCRService()

# Process your file
result = ocr.process_file("path/to/your/form.pdf")

# Check results
if result["success"]:
    print(result["full_text"])
else:
    print(f"Error: {result['error']}")
```

---

## 🔧 Troubleshooting

### Issue: "Missing Azure Document Intelligence credentials"

**Solution:** Make sure your `.env` file has:
```env
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...
```

### Issue: "Authentication failed"

**Solutions:**
1. Check your API key is correct
2. Verify endpoint URL ends with `/`
3. Ensure you have access permissions in Azure

### Issue: "File type not supported"

**Solution:** Only these formats are supported:
- `.pdf` (PDF documents)
- `.jpg`, `.jpeg` (JPEG images)
- `.png` (PNG images)

### Issue: Hebrew text not extracted correctly

**Solution:** Azure Document Intelligence supports Hebrew out of the box. If text looks garbled:
1. Check the file quality
2. Verify the PDF is not password-protected
3. Try with a different file

---

## 📊 What's Next?

After OCR is working, we'll build:

1. ✅ **OCR Service** - DONE!
2. ⏳ **Extraction Service** - Use GPT-4o to extract fields
3. ⏳ **Validation Service** - Validate extracted data
4. ⏳ **Streamlit UI** - Upload files and display results

---

## 💡 Pro Tips

1. **Start with good quality PDFs** - Clear, high-resolution scans work best
2. **Test with the provided samples** - Use the 3 filled forms in phase1_data
3. **Check the full_text first** - Make sure OCR is extracting text correctly before moving to extraction
4. **Hebrew support is built-in** - No special configuration needed

---

## 📞 Need Help?

If OCR is not working:
1. Run `python test_ocr.py` to diagnose
2. Check your Azure credentials
3. Verify you have internet connection
4. Ensure Azure resources are not paused/disabled

---

**Status:** ✅ OCR Implementation Complete!

**Next Step:** Build the GPT-4o extraction service