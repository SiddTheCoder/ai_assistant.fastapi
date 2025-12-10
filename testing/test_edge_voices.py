import edge_tts
import asyncio

async def speak(text):
    voice = "en-US-AriaNeural"  # working voice name
    tts = edge_tts.Communicate(text, voice)
    await tts.save("output.mp3")

asyncio.run(speak("Hey Sidd, Spark is speaking right now"))
