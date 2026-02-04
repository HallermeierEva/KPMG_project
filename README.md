# KPMG GenAI Developer Assessment

A comprehensive two-part AI system demonstrating enterprise-grade document processing and conversational AI capabilities for Israeli healthcare applications.

## 🎯 Project Overview

This assessment showcases:
- **Part 1:** OCR + Field Extraction from Hebrew/English National Insurance forms
- **Part 2:** Stateless microservice chatbot for Israeli HMO information

**Technologies:** Azure Document Intelligence, Azure OpenAI (GPT-4o), FastAPI, Streamlit, Python 3.9+

---

## 📁 Project Structure

```
KPMG_project-main/
├── README.md                  # This file
├── .gitignore                 # Git ignore rules
├── .env.example               # Environment variables template
├── requirements.txt           # Global dependencies
├── test_azure_setup.py        # Azure credentials test
│
├── part_1/                    # Part 1: Field Extraction
│   ├── README.md              # Detailed Part 1 documentation
│   ├── run_part1.sh           # One-command startup script
│   ├── requirements.txt       # Part 1 dependencies
│   ├── ocr-service/           # Azure Document Intelligence OCR
│   ├── extraction-service/    # GPT-4o field extraction
│   ├── validation-service/    # Data validation & scoring
│   ├── ui-service/            # Streamlit interface
│   ├── shared/                # Common models & config
│   ├── prompts/               # LLM prompts
│   └── data/                  # Sample PDF forms
│
├── part_2/                    # Part 2: Medical Chatbot
│   ├── README.md              # Detailed Part 2 documentation
│   ├── main.py                # FastAPI backend server
│   ├── app.py                 # Streamlit frontend
│   ├── models.py              # Pydantic request/response models
│   ├── prompts.py             # LLM conversation prompts
│   ├── services/              # Business logic services
│   │   ├── llm_service.py     # Azure OpenAI integration
│   │   ├── rag_service.py     # Knowledge base RAG
│   │   ├── validation_service.py
│   │   └── language_service.py
│   ├── knowledge_base/        # Processed medical data
│   ├── phase2_data/           # Raw HTML knowledge files
│   └── test_bot.py            # Automated tests
│
└── instructions.md            # Original assignment brief
```

---

## Architecture Diagrams

### Part 1: Document Processing Pipeline

\`\`\`mermaid
graph LR
    A[User Upload PDF] --> B[OCR Service]
    B --> C[Azure Document Intelligence]
    C --> B
    B --> D[Extraction Service]
    D --> E[GPT-4o]
    E --> D
    D --> F[Validation Service]
    F --> G[UI Display]
    
    style A fill:#e3f2fd
    style G fill:#c8e6c9
    style B fill:#fff9c4
    style D fill:#fff9c4
    style F fill:#fff9c4
\`\`\`

### Part 2: Chatbot Flow

\`\`\`mermaid
sequenceDiagram
    participant U as User (Browser)
    participant F as Frontend (Streamlit)
    participant B as Backend (FastAPI)
    participant AI as Azure OpenAI
    participant KB as Knowledge Base
    
    U->>F: Send message
    F->>F: Store in session_state
    F->>B: POST /chat (message + history + profile)
    B->>AI: Generate response
    
    alt Collection Phase
        AI-->>B: Conversational response
        B-->>F: Response + extracted profile
        F->>F: Update session_state
    else Q&A Phase
        B->>KB: Get relevant context
        KB-->>B: Filtered data (HMO + tier)
        B->>AI: Answer with context
        AI-->>B: Grounded answer
        B-->>F: Response
    end
    
    F-->>U: Display message
\`\`\`

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.9 or higher
python --version

# Verify you have the Azure credentials from the email
```

### 1. Clone and Setup

```bash
# Clone repository
git clone <your-repo-url>
cd KPMG_project-main

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Azure credentials from the email
nano .env  # or use your preferred editor
```

Required variables:
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`
- `AZURE_DOCUMENT_INTELLIGENCE_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_KEY`
- `AZURE_OPENAI_GPT4O_DEPLOYMENT`

### 3. Test Azure Connection

```bash
python test_azure_setup.py
```

Expected output: ✅ All connections successful

---

## 📄 Part 1: Field Extraction

### What It Does
Extracts structured data from Israeli National Insurance Institute (ביטוח לאומי) work injury forms using OCR and AI.

### Run Part 1

**Option A: One-command startup (Recommended)**
```bash
cd part_1
chmod +x run_part1.sh
./run_part1.sh
```

This starts:
- OCR service (port 8001)
- Extraction service (port 8002)
- Validation service (port 8003)
- Streamlit UI (opens in browser)

**Option B: Manual startup**
```bash
cd part_1

# Terminal 1: OCR service
uvicorn ocr-service.app:app --port 8001

# Terminal 2: Extraction service
uvicorn extraction-service.app:app --port 8002

# Terminal 3: Validation service
uvicorn validation-service.app:app --port 8003

# Terminal 4: UI
streamlit run ui-service/app.py
```

### Test Part 1

```bash
cd part_1

# Run test suite
pytest

# Run end-to-end evaluation
python evaluate_ground_truth_accuracy.py
```

📖 **Full documentation:** [part_1/README.md](part_1/README.md)

---

## 🤖 Part 2: Medical Chatbot

### What It Does
A stateless chatbot that:
1. Collects user information through natural conversation (LLM-driven, no forms)
2. Answers questions about Israeli HMO services based on user's health fund and tier
3. Supports Hebrew and English

### Run Part 2

**Terminal 1: Start Backend**
```bash
cd part_2
python main.py
```

Expected: `Uvicorn running on http://0.0.0.0:8000`

**Terminal 2: Start Frontend**
```bash
cd part_2
streamlit run app.py
```

Your browser opens at: `http://localhost:8501`

### Test Part 2

```bash
cd part_2
python test_bot.py
```

📖 **Full documentation:** [part_2/README.md](part_2/README.md)

---

## 🏗️ Architecture Highlights

### Part 1: Microservice Pipeline
```
PDF Upload → OCR Service → Extraction Service → Validation Service → UI
              (Azure DI)     (GPT-4o)           (Rules + Scores)
```

### Part 2: Stateless Chatbot
```
Frontend (Streamlit) → Backend API (FastAPI) → Azure OpenAI
    ↓                        ↓                      ↑
Session State         RAG Service              Knowledge Base
(Client-side)      (HTML → Context)           (phase2_data/)
```

**Key Features:**
- ✅ Stateless backend (no server-side sessions)
- ✅ Client-side state management
- ✅ Concurrent user support
- ✅ LLM-driven information collection
- ✅ Bilingual (Hebrew/English)

---

## 🧪 Testing

### Part 1 Tests
```bash
cd part_1
pytest                              # Unit tests
python evaluate_ground_truth_accuracy.py  # E2E evaluation
```

### Part 2 Tests
```bash
cd part_2
python test_bot.py                  # Automated conversation tests
```

### Manual Testing
1. Upload test PDFs in Part 1 UI
2. Complete registration flow in Part 2
3. Ask questions about medical services
4. Test both Hebrew and English

---

## 📊 Validation & Metrics

### Part 1
- **Field Extraction Accuracy:** Measured against ground truth
- **Completeness Score:** Percentage of filled fields
- **Validation Errors:** ID validation, date ranges, phone numbers
- **OCR Quality:** Text extraction confidence

### Part 2
- **Profile Extraction:** 7 required fields validated
- **Response Accuracy:** Based on HMO + tier filtering
- **Latency:** <2s average response time
- **Bilingual Support:** Auto-detects Hebrew/English

---

## 🔐 Security Notes

⚠️ **IMPORTANT:**
- Never commit `.env` file
- `.gitignore` protects sensitive files
- API keys in environment variables only
- No credentials in code

---

## 🐛 Troubleshooting

### Azure Connection Issues
```bash
# Test connection
python test_azure_setup.py

# Check environment variables
cat .env | grep AZURE

# Verify no trailing slashes in endpoints
```

### Part 1 Issues
- **OCR fails:** Check Document Intelligence credentials
- **Extraction poor:** Verify GPT-4o deployment name
- **Services won't start:** Check ports 8001-8003 are free

### Part 2 Issues
- **Backend won't start:** Verify port 8000 is free
- **Frontend connection error:** Ensure backend is running
- **No responses:** Check Azure OpenAI quota

📖 **Detailed troubleshooting:** See individual part READMEs

---

## 📚 Additional Resources

- **Part 1 Documentation:** [part_1/README.md](part_1/README.md)
- **Part 2 Documentation:** [part_2/README.md](part_2/README.md)
- **Assignment Instructions:** [instructions.md](instructions.md)
- **Azure OpenAI Docs:** https://learn.microsoft.com/en-us/azure/ai-services/openai/
- **Document Intelligence Docs:** https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/

---

## 👨‍💻 Development Notes

### Tech Stack
- **Python:** 3.9+
- **OCR:** Azure Document Intelligence
- **LLM:** Azure OpenAI GPT-4o
- **Backend:** FastAPI
- **Frontend:** Streamlit
- **Validation:** Pydantic
- **Testing:** pytest
- **Logging:** Python logging module

### Code Quality
- Type hints throughout
- Pydantic models for data validation
- Comprehensive error handling
- Structured logging
- Clean separation of concerns

---

## 📝 License

This is an assessment project for KPMG.

---

## 📧 Contact

For questions about this assessment:
**Dor Getter** - Assessment Coordinator

---

**Last Updated:** February 4, 2026
**Version:** 2.0
**Status:** ✅ Ready for Review