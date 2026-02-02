# server side backedn of the app - need to run first - python main.py
from http.client import HTTPException


import uvicorn

import os
import json
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from openai import AzureOpenAI
from prompts import COLLECTION_PROMPT, QA_PROMPT
from processor import get_all_medical_context

load_dotenv()

app = FastAPI()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")


class ChatRequest(BaseModel):
    message: str
    history: List[dict]
    user_profile: Optional[dict] = None
    phase: str


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # 1. Determine Context
        context = ""
        if request.phase == "qa":
            context = get_all_medical_context()

        # 2. Select and Format Prompt
        # Use .replace instead of .format if your prompts have extra { }
        if request.phase == "qa":
            system_content = QA_PROMPT.replace("{context}", context).replace("{user_profile}",
                                                                             json.dumps(request.user_profile,
                                                                                        ensure_ascii=False))
        else:
            system_content = COLLECTION_PROMPT

        messages = [{"role": "system", "content": system_content}]
        messages.extend(request.history)
        messages.append({"role": "user", "content": request.message})

        # 3. Call OpenAI
        response = client.chat.completions.create(
            model=deployment_name,
            messages=messages
        )

        ai_content = response.choices[0].message.content

        # 4. Check for completion
        extracted_data = None
        if "[COMPLETE]" in ai_content:
            json_match = re.search(r"\{.*\}", ai_content, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())

        return {"response": ai_content, "extracted_profile": extracted_data}

    except Exception as e:
        # THIS PRINT IS CRUCIAL: It shows the error in the FastAPI terminal
        print(f"BACKEND ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)