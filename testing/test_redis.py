from app.cache.redis.config import RedisManager 
import asyncio
import json
from app.cache.load_user import load_user
from app.utils.format_context import format_context

async def main():
    config = RedisManager()
    await config.initialize()
    # await config.add_message("user123", "user", "Hello, World!")
    # await config.add_message("user123", "ai", "Hi there!")
    # await config.add_message("user123", "user", "Hey what is up?")
    # await config.add_message("user123", "ai", "Not much!")
    from app.db.mongo import connect_to_mongo
    await connect_to_mongo()
    doc = await config.get_last_n_messages("guest",5)
    print(json.dumps(doc, indent=4))
    plain, a = format_context(doc, [])
    print(plain)

    from app.services.chat_service import chat
    response = await chat("what did you just said?", user_id="guest")
    print("Chat Response:", response)


if __name__ == "__main__":
    asyncio.run(main())      