from fastapi import APIRouter, File, UploadFile, HTTPException
from faster_whisper import WhisperModel
import tempfile
import os

router = APIRouter(prefix="/api")

model = WhisperModel("medium", device="cpu", compute_type="int8")

# try:
#     model = whisper.load_model("medium")
# except Exception as e:
#     print("❌ Whisper model failed to load:", e)
#     model = None

# Supported audio file extensions
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".mpga", ".webm", ".mp4"}

@router.post("/stt")
async def transcribe_audio(file: UploadFile = File(...)):
    filename = file.filename or "tempfile.tmp"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    tmp_path = None
    try:
        # Save uploaded file to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Transcribe using Faster-Whisper
        segments, info = model.transcribe(
            tmp_path,
            language="en",      # force Hindi
            task="transcribe"
        )
        text = " ".join([segment.text for segment in segments])

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {"text": text}
