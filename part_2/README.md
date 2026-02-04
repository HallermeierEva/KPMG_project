# Medical Chatbot - Israeli Health Funds Service Assistant

## Overview
A microservice-based chatbot system that answers questions about medical services for Israeli health funds (Maccabi, Meuhedet, and Clalit) based on user-specific information.

## Architecture

### Backend (FastAPI Microservice)
- **File**: `main_improved.py`
- **Port**: 8000
- **Type**: Stateless RESTful API
- **Features**:
  - Concurrent user handling
  - Client-side session management
  - Comprehensive error handling
  - Health check endpoints

### Frontend (Streamlit)
- **File**: `app.py`
- **Features**:
  - Two-phase interaction (Collection → Q&A)
  - Bilingual support (Hebrew/English)
  - Session state management

## Setup Instructions

### Prerequisites
```bash
# Python 3.8+
python --version

# Required packages
pip install fastapi uvicorn streamlit requests python-dotenv openai beautifulsoup4
```

### Environment Configuration

Create a `.env` file in the project root:

```env
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
```

### Directory Structure

```
project/
├── .env                          # Environment variables
├── main_improved.py              # FastAPI backend
├── app.py                        # Streamlit frontend
├── processor_improved.py         # Data processing & validation
├── prompts_improved.py           # LLM prompts
├── logger.py                     # Logging configuration
├── test_bot.py                   # Testing suite
├── phase2_data/                  # Knowledge base (HTML files)
│   ├── dentel_services.html
│   ├── optometry_services.html
│   ├── pragrency_services.html
│   ├── workshops_services.html
│   ├── alternative_services.html
│   └── communication_clinic_services.html
└── logs/                         # Application logs
    └── chatbot.log
```

## Running the Application

### Step 1: Start the Backend
```bash
python main_improved.py
```

Expected output:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Verify backend is running:
```bash
curl http://localhost:8000/health
```

### Step 2: Start the Frontend
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage Flow

### Phase 1: Information Collection
The chatbot collects 7 required fields:
1. **Full Name** (שם מלא)
2. **ID Number** (ת.ז) - 9 digits
3. **Gender** (מין) - Male/Female or זכר/נקבה
4. **Age** (גיל) - 0-120
5. **HMO** (קופת חולים) - מכבי/מאוחדת/כללית
6. **HMO Card Number** (מספר כרטיס) - 9 digits
7. **Insurance Tier** (מסלול) - זהב/כסף/ארד

Example conversation:
```
User: Hi, I'm Sarah, 32 years old
Bot: Nice to meet you, Sarah! I need a few more details...
User: ID 123456789, female
Bot: Great! Which health fund are you with?
User: Maccabi Gold, card 987654321
Bot: Perfect! Let me confirm: [shows summary]
User: I confirm
Bot: ✅ Registration complete! How can I help you?
```

### Phase 2: Q&A
Once registered, users can ask about medical services:

```
User: How much discount do I get for glasses?
Bot: Hi Sarah, as a Maccabi Gold member, you get 70% discount 
     up to 1000 ₪ for eyeglasses, with replacement every 2 years.

User: מה ההנחה על טיפול שורש?
Bot: היי שרה, כחברת מכבי זהב, את מקבלת 70% הנחה על טיפולי שורש,
     כולל צילומי רנטגן.
```

## API Endpoints

### POST /chat
Main chat endpoint for both phases.

**Request:**
```json
{
  "message": "user message here",
  "history": [
    {"role": "user", "content": "previous message"},
    {"role": "assistant", "content": "previous response"}
  ],
  "user_profile": {
    "Full Name": "שרה כהן",
    "ID": "123456789",
    ...
  },
  "phase": "collection" | "qa"
}
```

**Response:**
```json
{
  "response": "chatbot response",
  "extracted_profile": {...} | null,
  "phase": "collection" | "qa",
  "error": null | "error message"
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "azure_openai": "connected",
  "knowledge_base": "ok",
  "deployment": "gpt-4"
}
```

## Validation Rules

### ID Number
- Exactly 9 digits
- Numeric only
- Example: `123456789`

### HMO Card Number
- Exactly 9 digits
- Numeric only
- Example: `987654321`

### Age
- Integer between 0 and 120
- Example: `32`

### HMO Name
Valid values (case-insensitive):
- Hebrew: `מכבי`, `מאוחדת`, `כללית`
- English: `Maccabi`, `Meuhedet`, `Clalit`

Auto-normalized to Hebrew internally.

### Insurance Tier
Valid values (case-insensitive):
- Hebrew: `זהב`, `כסף`, `ארד`
- English: `Gold`, `Silver`, `Bronze`

Auto-normalized to Hebrew internally.

## Error Handling

### Backend Errors
- **400 Bad Request**: Invalid input, missing required fields
- **503 Service Unavailable**: Azure OpenAI API unavailable
- **500 Internal Server Error**: Unexpected errors

All errors are logged to `logs/chatbot.log`

### Frontend Errors
- Connection errors displayed to user
- Automatic retry suggestions
- Session recovery on page refresh

## Testing

### Manual Testing
1. Start both backend and frontend
2. Go through registration flow
3. Ask questions about different services
4. Test both Hebrew and English
5. Test error cases (invalid ID, unknown tier, etc.)

### Automated Testing
```bash
# Ensure backend is running first
python test_bot.py
```

Expected output:
```
🚀 Running: Maccabi Gold - Dental Root Canal
  AI Answer: Hi Noa, for Maccabi Gold members, root canals...
  Result: ✅ PASSED (Avg Latency: 1.23s)
...
========================================
SUMMARY: 5/5 Passed
========================================
```

## Logging

Logs are written to `logs/chatbot.log`:

```
2025-02-04 10:15:23 - INFO - Azure OpenAI client initialized successfully
2025-02-04 10:15:45 - INFO - Received request - Phase: collection, Message length: 25
2025-02-04 10:15:47 - INFO - LLM response received - Length: 150
2025-02-04 10:16:02 - INFO - Profile extraction successful for: Sarah Cohen
```

## Troubleshooting

### Backend won't start
1. Check `.env` file exists and has all variables
2. Verify Azure OpenAI credentials
3. Check port 8000 isn't in use: `lsof -i :8000`

### Frontend won't connect
1. Verify backend is running at `http://localhost:8000`
2. Check browser console for errors
3. Try clearing browser cache

### Knowledge base not loading
1. Verify `phase2_data/` folder exists
2. Check HTML files are present
3. Look for errors in `logs/chatbot.log`

### LLM not responding correctly
1. Check prompt in `prompts_improved.py`
2. Verify context is being loaded (check health endpoint)
3. Increase `max_tokens` in `main_improved.py` if responses are cut off

## Performance Optimization

### For High Traffic
1. Use `gunicorn` instead of `uvicorn`:
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main_improved:app
```

2. Enable caching for knowledge base:
```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_all_medical_context():
    # existing implementation
```

3. Add rate limiting with `slowapi`

## Security Considerations

1. **API Keys**: Never commit `.env` to version control
2. **Input Validation**: All inputs are validated before processing
3. **CORS**: Configured for development, restrict in production
4. **Logging**: Sensitive data is not logged

## Future Enhancements

1. **Database Integration**: Store user profiles (with consent)
2. **Analytics**: Track popular questions
3. **Multi-session Support**: Handle appointment booking
4. **Voice Input**: Add speech-to-text
5. **Mobile App**: Native iOS/Android versions

## License
[Your License Here]

## Support
For issues, please check the logs first, then contact support.