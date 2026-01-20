
import asyncio
import sys
import os
from typing import Dict

# Add app root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.providers.manager import ProviderManager, ModelProvider
from app.cache import redis_manager

async def test_client_caching():
    print("\n--- Testing Client Caching ---")
    user_details = {
        "_id": "test_user_1",
        "gemini_api_key": "dummy_gemini_key",
        "openrouter_api_key": "dummy_or_key",
        "is_gemini_api_quota_reached": False,
        "is_openrouter_api_quota_reached": False
    }
    
    manager1 = ProviderManager(user_details)
    manager2 = ProviderManager(user_details)
    
    print(f"Manager 1 Gemini Client ID: {id(manager1.gemini_client)}")
    print(f"Manager 2 Gemini Client ID: {id(manager2.gemini_client)}")
    
    if id(manager1.gemini_client) == id(manager2.gemini_client):
        print("✅ SUCCESS: Gemini clients are cached and reused.")
    else:
        print("❌ FAILURE: Gemini clients are NOT cached.")
        
    if id(manager1.openrouter_client) == id(manager2.openrouter_client):
        print("✅ SUCCESS: OpenRouter clients are cached and reused.")
    else:
        print("❌ FAILURE: OpenRouter clients are NOT cached.")

    # Test cache isolation
    user_details_2 = user_details.copy()
    user_details_2["_id"] = "test_user_2"
    manager3 = ProviderManager(user_details_2)
    
    if id(manager1.gemini_client) != id(manager3.gemini_client):
        print("✅ SUCCESS: Client cache is isolated per user.")
    else:
        print("❌ FAILURE: Client cache is shared between users.")

async def test_quota_auto_reset():
    print("\n--- Testing Quota Auto-Reset ---")
    user_id = "test_user_quota"
    user_details = {
        "_id": user_id,
        "gemini_api_key": "dummy_gemini_key",
        "is_gemini_api_quota_reached": True 
    }
    
    # Initialize manager while quota is reached
    manager = ProviderManager(user_details)
    print(f"Initial gemini quota_reached: {manager.gemini_client.quota_reached}")
    
    # Manually remove the block key in Redis to simulate TTL expiry
    block_key = f"user:{user_id}:quota_blocked:gemini"
    await redis_manager.delete(block_key)
    print(f"Deleted block key {block_key}")
    
    # Mock calling with fallback
    # In a real call, it should detect the block is gone and reset status
    try:
        # We need to mock send_message to not fail
        from unittest.mock import MagicMock
        manager.gemini_client.send_message = MagicMock(return_value="test response")
        
        await manager.call_with_fallback("test prompt")
        print(f"After call, gemini quota_reached: {manager.gemini_client.quota_reached}")
        
        if not manager.gemini_client.quota_reached:
            print("✅ SUCCESS: Quota auto-reset detected and applied.")
        else:
            print("❌ FAILURE: Quota still marked as reached.")
            
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    async def run_tests():
        await test_client_caching()
        await test_quota_auto_reset()
        # Clean up
        await redis_manager.delete("user:test_user_quota:quota_blocked:gemini")
        print("\nTests completed.")

    asyncio.run(run_tests())
