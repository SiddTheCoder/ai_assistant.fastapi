import socketio
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    # ⭐ FIX: Add namespace support
    namespaces=["/"]  # Default namespace
)

# Create ASGI wrapper
socket_app = socketio.ASGIApp(sio)

# Store users
connected_users: Dict[str, str] = {}

# ================= CONNECTION EVENTS ================= #

@sio.event
async def connect(sid, environ):
    """Called when client connects"""
    logger.info(f"🔌 Client connected: {sid}")
    return True  # ⭐ FIX: Explicitly accept connection

@sio.event
async def disconnect(sid):
    """Called when client disconnects"""
    # Remove if in connected_users
    for uid, socket_id in list(connected_users.items()):
        if socket_id == sid:
            del connected_users[uid]
            logger.info(f"👋 User {uid} disconnected")
            break
    
    logger.info(f"🔌 Client {sid} disconnected")

@sio.event
async def register_user(sid, user_id):
    """User registers after connecting"""
    try:
        connected_users[user_id] = sid
        logger.info(f"✅ User {user_id} registered with sid {sid}")
        
        # ⭐ FIX: Emit to the specific socket
        await sio.emit("registered", {"userId": user_id}, to=sid)
        
    except Exception as e:
        logger.error(f"❌ Error registering user: {e}")

# ================= HELPER FUNCTIONS ================= #

async def send_to_user(user_id: str, event: str, data: dict):
    """Send event to a specific user"""
    if user_id in connected_users:
        sid = connected_users[user_id]
        await sio.emit(event, data, to=sid)
        logger.info(f"📤 Sent {event} to user {user_id}")
        return True
    else:
        logger.warning(f"⚠️ User {user_id} not connected")
        return False

def get_connected_users():
    """Get list of connected user IDs"""
    return list(connected_users.keys())

# ==================== MESSAGING EVENTS ====================

@sio.on('get-new-message')
async def get_new_message(sid):
    """Handle request for new message"""
    logger.info(f"🔥 get_new_message triggered for sid: {sid}")
    
    try:
        await sio.emit(
            "new-message",
            {"text": "Hey there its me from server"},
            to=sid
        )
        logger.info(f"✅ Sent new-message to {sid}")
    except Exception as e:
        logger.error(f"❌ Error sending message: {e}")

@sio.on('send-query')
async def send_query(sid, data):
    """Handle query from client"""
    logger.info(f"🔥 send_query triggered for sid: {sid}")
    from app.services.chat_service import chat
    chatRes = await chat(data)
    dict_data = chatRes.model_dump()
    
    try:
        await sio.emit(
            "query-result",
            {"result": dict_data},
            to=sid
        )
        logger.info(f"✅ Sent query-result to {sid}")
    except Exception as e:
        logger.error(f"❌ Error sending query result: {e}")