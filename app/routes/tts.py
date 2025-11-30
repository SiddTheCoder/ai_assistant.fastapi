import edge_tts
from fastapi.responses import StreamingResponse
from fastapi import APIRouter
import logging
logger = logging.getLogger(__name__)
from pydantic import BaseModel

class TTSRequest(BaseModel):
    text: str
    # voice: str = "en-US-BrianNeural"
    voice: str = "hi-IN-MadhurNeural"

router = APIRouter(prefix="/api")

async def stream_tts(text: str, voice: str):
    communicate = edge_tts.Communicate(text, voice, rate="+20%", pitch="-5Hz")
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            data = chunk.get("data")
            if data is not None:
                yield data

@router.post("/tts")
@router.get("/tts")
async def tts(payload: TTSRequest):
    return StreamingResponse(
        stream_tts(payload.text, payload.voice),
        media_type="audio/mpeg"
    )
