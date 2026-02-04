"""
Improved Medical Chatbot Backend with FastAPI
Refactored with service-oriented architecture & Turn Chaining

"""
import uvicorn
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import models
from models import ChatRequest, ChatResponse

# Import services
from services import get_llm_service, get_rag_service, get_validation_service, get_language_service
from services.llm_service import LLMService

# Import prompts
from prompts import COLLECTION_PROMPT, format_qa_prompt
from logger import logger

load_dotenv()

app = FastAPI(
    title="Medical Chatbot API",
    description="Israeli Health Fund Medical Services Chatbot",
    version="2.0"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services (STATELESS - see services/__init__.py documentation)
# These are singleton service instances that don't store user state
llm_service = get_llm_service()
rag_service = get_rag_service()
validation_service = get_validation_service()
language_service = get_language_service()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Medical Chatbot API",
        "version": "2.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        context = rag_service.get_all_medical_context()
        kb_status = "ok" if rag_service.is_context_valid(context) else "error"
        llm_status = "connected" if llm_service.is_healthy() else "unavailable"

        return {
            "status": "healthy" if kb_status == "ok" and llm_status == "connected" else "degraded",
            "azure_openai": llm_status,
            "knowledge_base": kb_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # 1. Setup
        user_lang = request.preferred_language or language_service.detect_language(request.message)
        lang_inst = language_service.get_language_instruction(user_lang)

        # 2. Logic for current phase
        context = rag_service.get_all_medical_context() if request.phase == "qa" else ""
        system_content = (format_qa_prompt(request.user_profile, context) if request.phase == "qa"
                          else COLLECTION_PROMPT) + lang_inst

        # 3. Call LLM
        ai_content = llm_service.get_completion(
            system_prompt=system_content,
            history=request.history,
            user_message=request.message,
            temperature=0.7
        )

        extracted_data = None
        current_phase = request.phase

        # 4. TURN CHAINING (The fix for the silence)
        if "[COMPLETE]" in ai_content:
            logger.info("Detected [COMPLETE] tag. Attempting turn chaining...")
            json_match = re.search(r"\{.*\}", ai_content, re.DOTALL)

            if json_match:
                try:
                    profile = json.loads(json_match.group())
                    # Log for debugging - check your terminal!
                    logger.info(f"Extracted Profile: {profile}")

                    # 1. Force state change
                    extracted_data = profile
                    current_phase = "qa"

                    # 2. Get Knowledge Base
                    med_context = rag_service.get_all_medical_context()

                    # 3. Format Prompt
                    qa_sys = format_qa_prompt(extracted_data, med_context) + lang_inst

                    # 4. Build history and find the ORIGINAL question
                    # We search the history for the first message longer than 5 chars
                    # that isn't a 'confirm' or a 'yes'
                    original_question = request.message  # Default
                    for msg in request.history:
                        content = msg["content"].lower()
                        if msg["role"] == "user" and not any(x in content for x in ["מאשר", "confirm", "כן", "ok"]):
                            original_question = msg["content"]
                            break

                    logger.info(f"Chaining to answer original question: {original_question}")

                    # 5. CALL LLM IMMEDIATELY
                    medical_answer = llm_service.get_completion(
                        system_prompt=qa_sys,
                        history=request.history + [{"role": "assistant", "content": ai_content}],
                        user_message=f"הרישום אושר. כעת ענה בפירוט על השאלה: {original_question}",
                        temperature=0.2
                    )

                    # 6. Merge for the final response
                    name = extracted_data.get('Full Name', '').split()[0]
                    prefix = "✅ " + (
                        f"שלום {name}, הפרטים אומתו.\n\n" if user_lang == "he" else f"Hello {name}\n\n")
                    ai_content = f"{prefix}{medical_answer}"

                except Exception as e:
                    logger.error(f"Turn chaining failed internally: {str(e)}")
                    # If it fails, we still want to show the user we finished registration
                    ai_content = "✅ הרישום הושלם. אנא שאל שוב את שאלתך כעת."

        return ChatResponse(response=ai_content, extracted_profile=extracted_data, phase=current_phase)
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    missing_vars = LLMService.validate_environment()
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        exit(1)

    logger.info("Starting Medical Chatbot API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)