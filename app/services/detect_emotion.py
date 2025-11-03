from transformers import pipeline
import logging

logger = logging.getLogger(__name__)

# Load model once at startup
emotion_analyzer = pipeline(
    "text-classification",
    model="SamLowe/roberta-base-go_emotions",
    return_all_scores=False  # only top emotion
)

async def detect_emotion(text: str) -> str:
    """
    Detects the dominant emotion from user input text.
    Returns emotion labels like: 'joy', 'amusement', 'curiosity', 'anger', etc.
    """
    try:
        result = emotion_analyzer(text)
        if result and len(result) > 0:
            emotion = result[0]['label'].lower()
            logger.info(f"Detected emotion: {emotion}")
            return emotion
    except Exception as e:
        logger.error(f"Emotion detection failed: {e}")
    return "neutral"
