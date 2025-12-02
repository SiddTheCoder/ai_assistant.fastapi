"""
Gemini API Client - Handles Gemini-specific API calls
"""
import logging
from typing import Optional
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Handles all Gemini API interactions.
    
    Supports both:
    - System-wide default API key (from settings)
    - User-specific API keys (from user profile)
    """
    
    DEFAULT_MODEL = "gemini-2.0-flash-exp:free"
    DEFAULT_MODEL_FLASH = "gemini-2.0-flash"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    
    def __init__(self, api_key: Optional[str] = None, quota_reached: bool = False):
        """
        Initialize Gemini client.
        
        Args:
            api_key: User-specific API key (optional, falls back to system default)
            quota_reached: Whether quota is already exhausted
        """
        self.quota_reached = quota_reached
        
        # Use user key if provided, otherwise fall back to system default
        self.api_key = api_key or settings.gemini_api_key
        
        if not self.api_key:
            logger.warning("No Gemini API key configured (user or system)")
            self.quota_reached = True  # Mark as unavailable
            self.client = None
        else:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL
            )
            logger.info(f"✅ Gemini client initialized (using {'user' if api_key else 'system'} key)")
    
    def send_message(
        self,
        prompt: str,
        # model: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Send a message to Gemini API.
        
        Args:
            prompt: The user prompt
            model: Model name (defaults to gemini-2.0-flash-exp)
            temperature: Sampling temperature
        
        Returns:
            AI response text
        
        Raises:
            QuotaError: If quota is exhausted
            Exception: For other API errors
        """
        from app.ai.providers.manager import QuotaError
        
        if not self.client:
            raise QuotaError("Gemini client not initialized (no API key)")
        
        if self.quota_reached:
            raise QuotaError("Gemini quota already exhausted")
        
        try:
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://siddhantyadav.com.np",
                    "X-Title": "Siddy Coddy",
                },
                model=self.DEFAULT_MODEL_FLASH,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            
            response = completion.choices[0].message.content
            
            if not response:
                raise ValueError("Empty response from Gemini")
            
            logger.debug(f"Gemini response: {response[:100]}...")
            return response
        
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for quota-specific errors
            if any(kw in error_str for kw in ['quota', 'rate limit', '429', 'exhausted']):
                raise QuotaError(f"Gemini quota error: {e}")
            
            # Re-raise other errors
            logger.error(f"Gemini API error: {e}", exc_info=True)
            raise