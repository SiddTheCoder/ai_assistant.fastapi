from openai import OpenAI
from app.config import settings

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=settings.openrouter_api_key,
)
