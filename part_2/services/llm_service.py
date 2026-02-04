"""
LLM Service - Handles all Azure OpenAI interactions
"""
import os
from typing import List, Dict, Optional
from openai import AzureOpenAI
from dotenv import load_dotenv
from logger import logger

load_dotenv()


class LLMService:
    """Service for interacting with Azure OpenAI"""
    
    def __init__(self):
        self.client: Optional[AzureOpenAI] = None
        self.deployment_name: Optional[str] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the Azure OpenAI client"""
        try:
            self.client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION")
            )
            self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            logger.info("Azure OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            raise
    
    def get_completion(
        self,
        system_prompt: str,
        history: List[Dict],
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Get a completion from the LLM.
        
        Args:
            system_prompt: The system prompt to use
            history: Conversation history
            user_message: The current user message
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            
        Returns:
            The LLM's response content
            
        Raises:
            Exception: If the API call fails
        """
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            logger.info(f"LLM response received - Length: {len(content)}")
            return content
            
        except Exception as e:
            logger.error(f"Azure OpenAI API error: {str(e)}")
            raise
    
    def is_healthy(self) -> bool:
        """Check if the LLM service is properly configured"""
        return self.client is not None and self.deployment_name is not None
    
    @staticmethod
    def validate_environment() -> List[str]:
        """
        Validate that all required environment variables are set.
        
        Returns:
            List of missing environment variable names
        """
        required_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_KEY",
            "AZURE_OPENAI_API_VERSION",
            "AZURE_OPENAI_DEPLOYMENT_NAME"
        ]
        return [var for var in required_vars if not os.getenv(var)]


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
