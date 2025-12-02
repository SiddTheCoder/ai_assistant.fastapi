"""
AI Provider Manager - Handles smart fallback between Gemini and OpenRouter
"""
import logging
from typing import Dict, Tuple, Optional
from enum import Enum

from app.ai.providers.gemini_client import GeminiClient
from app.ai.providers.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Available AI providers"""
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


class QuotaError(Exception):
    """Raised when API quota is exhausted"""
    pass


class ProviderManager:
    """
    Manages AI provider selection and fallback logic.
    
    Priority: Gemini → OpenRouter
    """
    
    def __init__(self, user_details: Dict):
        """
        Initialize with user-specific details.
        
        Args:
            user_details: User data from Redis/MongoDB containing API keys and quota flags
        """
        self.user_details = user_details
        self.user_id = str(user_details.get('_id', 'unknown'))
        
        # Initialize clients with user-specific API keys
        self.gemini_client = GeminiClient(
            api_key=user_details.get('gemini_api_key'),
            quota_reached=user_details.get('is_gemini_api_quota_reached', False)
        )
        
        self.openrouter_client = OpenRouterClient(
            api_key=user_details.get('openrouter_api_key'),
            quota_reached=user_details.get('is_openrouter_api_quota_reached', False)
        )
    
    def _is_quota_error(self, error: Exception) -> bool:
        """
        Detect if error is quota-related.
        
        Checks for:
        - 429 status codes
        - "quota", "rate limit", "exhausted" in error messages
        """
        error_str = str(error).lower()
        quota_keywords = [
            'quota', 'rate limit', 'resource has been exhausted',
            'too many requests', '429', 'rate_limit_exceeded'
        ]
        
        if getattr(error, 'status_code', None) == 429:
            return True
        
        return any(keyword in error_str for keyword in quota_keywords)
    
    def call_with_fallback(
        self,
        prompt: str,
        model_name: Optional[str] = None
    ) -> Tuple[str, ModelProvider]:
        """
        Call AI provider with automatic fallback.
        
        Flow:
        1. Check Gemini quota → Try Gemini
        2. On failure → Fallback to OpenRouter
        3. Update quota flags if quota errors detected
        
        Args:
            prompt: The prompt to send
            model_name: Optional OpenRouter model name (for fallback)
        
        Returns:
            Tuple of (response_text, provider_used)
        
        Raises:
            Exception: If all providers fail
        """
        
        # --- Try Gemini First ---
        if not self.gemini_client.quota_reached:
            try:
                logger.info(f"🔹 Attempting Gemini for user {self.user_id}")
                response = self.gemini_client.send_message(prompt)
                logger.info(f"✅ Gemini success for user {self.user_id}")
                return response, ModelProvider.GEMINI
            
            except QuotaError as e:
                logger.warning(f"🚨 Gemini quota exhausted for user {self.user_id}: {e}")
                self._update_quota_status(ModelProvider.GEMINI, quota_reached=True)
                # Fall through to OpenRouter
            
            except Exception as e:
                logger.error(f"❌ Gemini failed (non-quota): {e}", exc_info=True)
                # Check if it's actually a quota error disguised as generic error
                if self._is_quota_error(e):
                    self._update_quota_status(ModelProvider.GEMINI, quota_reached=True)
                # Fall through to OpenRouter
        
        else:
            logger.info(f"⏭️  Skipping Gemini (quota reached for user {self.user_id})")
        
        # --- Fallback to OpenRouter ---
        if not self.openrouter_client.quota_reached:
            try:
                logger.info(f"🔸 Attempting OpenRouter for user {self.user_id}")
                response = self.openrouter_client.send_message(prompt, model_name)
                logger.info(f"✅ OpenRouter success for user {self.user_id}")
                return response, ModelProvider.OPENROUTER
            
            except QuotaError as e:
                logger.error(f"🚨 OpenRouter quota exhausted for user {self.user_id}: {e}")
                self._update_quota_status(ModelProvider.OPENROUTER, quota_reached=True)
                raise Exception(
                    "All API quotas exhausted. Please add your own API keys in settings or try again later."
                )
            
            except Exception as e:
                logger.error(f"❌ OpenRouter failed: {e}", exc_info=True)
                if self._is_quota_error(e):
                    self._update_quota_status(ModelProvider.OPENROUTER, quota_reached=True)
                raise Exception(f"OpenRouter API error: {str(e)}")
        
        else:
            logger.error(f"❌ All quotas exhausted for user {self.user_id}")
            raise Exception(
                "All API quotas exhausted. Please add your own API keys in settings or contact support."
            )
    
    def _update_quota_status(self, provider: ModelProvider, quota_reached: bool):
        """
        Update quota status in Redis.
        
        Args:
            provider: Which provider to update
            quota_reached: New quota status
        """
        try:
            from app.cache.redis.config import set_user_details
            
            # Update in-memory flag
            if provider == ModelProvider.GEMINI:
                self.gemini_client.quota_reached = quota_reached
                self.user_details['is_gemini_api_quota_reached'] = quota_reached
            else:
                self.openrouter_client.quota_reached = quota_reached
                self.user_details['is_openrouter_api_quota_reached'] = quota_reached
            
            # Persist to Redis
            set_user_details(self.user_id, self.user_details)
            logger.info(f"✅ Updated {provider.value} quota status: {quota_reached}")
        
        except Exception as e:
            logger.error(f"Failed to update quota status in Redis: {e}", exc_info=True)