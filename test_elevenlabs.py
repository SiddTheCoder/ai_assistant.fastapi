from app.config import settings
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

elevenlabs = ElevenLabs(
  api_key=settings.ELEVEN_LABS_API_KEY,
)

audio = elevenlabs.text_to_speech.convert(
    text="The first move is what sets everything in motion.",
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)

play(audio)
