from app.db.mongo import get_db
import logging

async def create_indexes():
    db = get_db()

    # CHATS COLLECTION
    await db.chats.create_index([("user_id",1), ("created_at",-1)])

    # # SOCKET LOGS
    # await db.socket_logs.create_index("socket_id")
    # await db.socket_logs.create_index("timestamp")

    # MEMORY
    await db.memory.create_index("user_id")
    await db.memory.create_index("importance")

    logging.info("✅ MongoDB indexes created")