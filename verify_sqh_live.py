
import sys
import os
import asyncio
from unittest.mock import MagicMock
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Mock heavy libraries BEFORE importing app modules
sys.modules['faster_whisper'] = MagicMock()
sys.modules['deepface'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
# Also mock services that use them if needed to avoid granular errors
# But assuming imports are the bottleneck, this should be enough.
# Let's mock the service modules directly to be safe and fast.
sys.modules['app.services.stt_services'] = MagicMock()
sys.modules['app.services.emotion_services'] = MagicMock()
sys.modules['app.services.embedding_services'] = MagicMock()
# sys.modules['app.services.translate_service'] = MagicMock() # Often uses googletrans which is light
# sys.modules['app.services.tts_services'] = MagicMock()

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.cache.redis.config import RedisManager 
from app.db.mongo import connect_to_mongo
from app.services.chat_service import chat

async def main():
    print("🚀 Starting Live SQH Verification (Mocked)...")
    
    # Init DBs
    await connect_to_mongo()
    config = RedisManager()
    await config.initialize()
    
    query = "Lets do some code open vscode and also write something related to AI in notepad"
    print(f"📝 Sending Query: {query}")
    
    # Call Chat
    response = await chat(query, user_id="guest")
    print("✅ PQH Response received!")
    print(f"   Tools requested: {response.requested_tool}")
    
    print("⏳ Waiting 5 seconds for background SQH to finish...")
    await asyncio.sleep(5)
    print("🏁 Done.")

if __name__ == "__main__":
    asyncio.run(main())
