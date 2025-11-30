import socketio
import logging
from typing import Dict
import edge_tts
import asyncio
from app.services.stt_service import transcribe_audio
from app.socket.socket_utils import socket_emit,emit_server_status
from app.services.chat_service import chat
logger = logging.getLogger(__name__)

# Create Socket.IO server with increased timeouts
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    namespaces=["/"],
    ping_timeout=60,  # Wait 60s for ping response (default: 20s)
    ping_interval=25,  # Send ping every 25s (default: 25s)
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
    return True

@sio.event
async def disconnect(sid):
    """Called when client disconnects"""
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

async def serialize_response(chatRes) -> dict:
    """Helper to safely serialize chat response to dict"""
    if chatRes is None:
        return {"error": "No response from chat service"}
    
    if hasattr(chatRes, "model_dump") and callable(getattr(chatRes, "model_dump")):
        return chatRes.model_dump()
    elif hasattr(chatRes, "dict") and callable(getattr(chatRes, "dict")):
        return chatRes.dict()
    else:
        try:
            return dict(chatRes)
        except Exception:
            return {"response": str(chatRes)}

# ==================== MESSAGING EVENTS ====================

@sio.on("request-tts") #type: ignore
async def request_tts(sid, data):
    logger.info(f"⚡ request-tts from {sid}")

    try:
        # Validate payload
        if not data or "text" not in data:
            await sio.emit(
                "response-tts",
                {"success": False, "error": "Missing text"},
                to=sid
            )
            return

        text = data.get("text")
        voice = data.get("voice", "hi-IN-MadhurNeural")

        # Notify frontend: starting
        await sio.emit("tts-start", {"text": text, "voice": voice}, to=sid)

        communicator = edge_tts.Communicate(
            text,
            voice,
            rate="+20%",
            pitch="-5Hz"
        )

        async for chunk in communicator.stream():

            # SAFEST POSSIBLE FILTER:
            if chunk.get("type") != "audio":
                continue

            audio_bytes = chunk.get("data")

            # Additional safety: skip empty chunks
            if not audio_bytes:
                continue

            # python-socketio auto-handles binary if bytes
            await sio.emit(
                "tts-chunk",
                audio_bytes,   # <-- NO binary=True needed
                to=sid
            )
            # await asyncio.sleep(0.01)  # Small delay to prevent flooding

        # End event
        await sio.emit("tts-end", {"success": True}, to=sid)

    except Exception as e:
        logger.exception("TTS ERROR:")
        await sio.emit(
            "response-tts",
            {"success": False, "error": str(e)},
            to=sid
        )


@sio.on("send-user-text-query") #type: ignore
async def send_user_text_query(sid, query):
    """Handle text query from client"""
    logger.info(f"🔥 send_user_text_query triggered for sid: {sid}")
    
    try:
        from app.services.chat_service import chat
        
        chatRes = await chat(query)
        dict_data = await serialize_response(chatRes)
        
        await sio.emit(
            "query-result",
            {"result": dict_data, "success": True},
            to=sid
        )
        logger.info(f"✅ Sent query-result to {sid}")
        
    except Exception as e:
        logger.error(f"❌ Error in send_user_text_query: {e}", exc_info=True)
        await sio.emit(
            "query-result",
            {"error": str(e), "success": False},
            to=sid
        )


@sio.on("send-user-voice-query") #type: ignore
async def send_user_voice_query(sid, data): 
    """Handle voice query from client - now fully async and non-blocking"""
    logger.info(f"🔥 send_user_voice_query triggered for sid: {sid}")
    # Emit server status
    await emit_server_status("Backend Fired Up","Success", sid)
    await emit_server_status("Analyzing your data","Success", sid)
    
    if not data:
        logger.error(f"❌ No data received for sid: {sid}")
        await sio.emit("query-error", {"error": "No data received", "success": False}, to=sid)
        await emit_server_status("Error: No data received","Error", sid)
        return
    
    try:
        # Extract audio data
        audio_data = data.get("audio")
        mime_type = data.get("mimeType", "audio/webm")
        
        if not audio_data:
            logger.error(f"❌ No audio data in payload for sid: {sid}")
            await sio.emit("query-error", {"error": "No audio data", "success": False}, to=sid)
            await emit_server_status("Audio Data not revcieved","Errpr", sid)
            return
        
        # Log data info
        if isinstance(audio_data, str):
            logger.info(f"📊 Received base64 audio: {len(audio_data)} chars, type: {mime_type}")
        elif isinstance(audio_data, bytes):
            logger.info(f"📊 Received binary audio: {len(audio_data)} bytes, type: {mime_type}")
        else:
            logger.error(f"❌ Unexpected audio data type: {type(audio_data)}")
            await sio.emit("query-result", {"error": "Invalid audio format", "success": False}, to=sid)
            return
        
        # ✅ Send immediate acknowledgment to keep connection alive
        await sio.emit("processing", {"status": "Transcribing audio..."}, to=sid)
        
        # Transcribe audio
        text = await transcribe_audio(audio_data, mime_type)
        
        logger.info(f"✅ Transcription result: '{text}'")
        
        # ✅ Fixed logic bug (was: if(text != "" or text != "[No speech detected]"))
        if text and text not in ["", "[No speech detected]", "[Transcription failed], [Empty audio file]"]:
            # Send status update
            await sio.emit("processing", {"status": "Getting response..."}, to=sid)
            
            # Get chat response
            chatRes = await chat(text)
            dict_data = await serialize_response(chatRes)
            
            # Send final result
            await sio.emit(
                "query-result",
                {
                    "result": text,
                    "success": True,
                    "data": dict_data
                },
                to=sid
            )
            logger.info(f"✅ Sent complete query-result to {sid}")
        else:
            # No valid speech detected
            await sio.emit(
                "query-error",
                {
                    "result": text,
                    "success": False,
                    "message": "No speech detected or transcription failed"
                },
                to=sid
            )
            logger.info(f"⚠️ No valid speech for {sid}")
        
    except Exception as e:
        logger.error(f"❌ Error in send_user_voice_query: {e}", exc_info=True)
        await sio.emit(
            "query-error",
            {"error": str(e), "success": False},
            to=sid
        )