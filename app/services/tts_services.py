# app/services/tts_service.py
import asyncio
import edge_tts
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TTSConfig(BaseModel):
    """Configuration for TTS generation"""
    text: str
    voice: str
    rate: str = "+15%"
    pitch: str = "-5Hz"


class TTSService:
    """
    Unified TTS service for both WebSocket and REST API usage.
    Handles audio generation with proper error handling and streaming.
    """
    
    def __init__(self, default_rate: str = "+15%", default_pitch: str = "-0Hz"):
        self.default_rate = default_rate
        self.default_pitch = default_pitch
        
        # Voice-specific overrides (some voices don't support pitch/rate well)
        self.voice_overrides: Dict[str, Dict[str, str]] = {
            "hi-IN-SwaraNeural": {"rate": "+15%", "pitch": "+10Hz"},
            "hi-IN-MadhurNeural": {"rate": "+15%", "pitch": "+10Hz"},
        }

    def _get_voice_settings(self, voice: str) -> Dict[str, str]:
        """Get rate and pitch settings for a specific voice"""
        return self.voice_overrides.get(voice, {
            "rate": self.default_rate,
            "pitch": self.default_pitch
        })

    async def generate_audio_stream(
        self, 
        text: str, 
        voice: str,
        rate: Optional[str] = None,
        pitch: Optional[str] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Generate audio stream from text.
        
        Args:
            text: Text to convert to speech
            voice: Voice ID to use
            rate: Speech rate (optional, uses default if not provided)
            pitch: Speech pitch (optional, uses default if not provided)
            
        Yields:
            Audio bytes chunks
            
        Raises:
            Exception: If TTS generation fails
        """
        try:
            # Get voice-specific settings if not provided
            settings = self._get_voice_settings(voice)
            final_rate = rate or settings["rate"]
            final_pitch = pitch or settings["pitch"]
            
            logger.info(f"[TTSService] Generating audio: voice={voice}, rate={final_rate}, pitch={final_pitch}")

            communicator = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=final_rate,
                pitch=final_pitch
            )

            chunk_count = 0
            async for chunk in communicator.stream():
                if chunk.get("type") != "audio":
                    continue

                audio_bytes = chunk.get("data")
                if not audio_bytes:
                    continue

                chunk_count += 1
                yield audio_bytes

            if chunk_count == 0:
                raise Exception("No audio chunks generated. Voice may not be available or parameters invalid.")
                
            logger.info(f"[TTSService] Successfully generated {chunk_count} audio chunks")

        except Exception as e:
            logger.error(f"[TTSService] Error generating audio: {e}")
            raise

    async def stream_to_socket(
        self,
        sio: Any,
        sid: str,
        text: str,
        voice: str,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        chunk_delay: float = 0.005
    ) -> bool:
        """
        Stream TTS audio to a WebSocket client.
        
        Args:
            sio: SocketIO instance
            sid: Socket ID
            text: Text to convert
            voice: Voice ID
            rate: Optional speech rate
            pitch: Optional speech pitch
            chunk_delay: Delay between chunks (prevents flooding)
            
        Returns:
            bool: True if successful, False if failed
        """
        logger.info(f"[TTSService] Streaming to socket {sid}")
        
        # Send start event
        await sio.emit("tts-start", {"text": text, "voice": voice}, to=sid)

        try:
            audio_stream = self.generate_audio_stream(text, voice, rate, pitch)
            chunk_count = 0

            async for audio_bytes in audio_stream:
                await sio.emit("tts-chunk", audio_bytes, to=sid)
                chunk_count += 1
                
                if chunk_delay > 0:
                    await asyncio.sleep(chunk_delay)

            # Success
            logger.info(f"[TTSService] Streamed {chunk_count} chunks to {sid}")
            await sio.emit("tts-end", {"success": True}, to=sid)
            return True

        except Exception as e:
            logger.exception(f"[TTSService] Socket stream error: {e}")
            await sio.emit("tts-end", {"success": False, "error": str(e)}, to=sid)
            return False

    async def generate_complete_audio(
        self,
        text: str,
        voice: str,
        rate: Optional[str] = None,
        pitch: Optional[str] = None
    ) -> bytes:
        """
        Generate complete audio file (non-streaming).
        Useful for scenarios where you need the full audio at once.
        
        Args:
            text: Text to convert
            voice: Voice ID
            rate: Optional speech rate
            pitch: Optional speech pitch
            
        Returns:
            Complete audio as bytes
        """
        audio_chunks = []
        
        async for chunk in self.generate_audio_stream(text, voice, rate, pitch):
            audio_chunks.append(chunk)
        
        return b"".join(audio_chunks)


# Singleton instance
tts_service = TTSService()