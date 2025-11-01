import json
import re
from typing import Dict, Optional

def clean_ai_response(raw_text: str) -> Optional[Dict[str, str]]:
    """
    Parse AI response JSON string and clean formatting:
    - Convert \n to actual newlines
    - Convert numbered lists into proper format
    """
    try:
        # Step 1: parse JSON string
        data = json.loads(raw_text)
        answer = data.get("answer", "")

        # Step 2: replace escaped newlines with real newlines
        answer = answer.replace("\\n", "\n")

        # Step 3: fix numbered lists formatting (optional)
        # Converts "1.something 2.something" => "1. something\n2. something"
        answer = re.sub(r"(\d+)\.(\S)", r"\1. \2", answer)
        # Add newline after each number if not already
        answer = re.sub(r"(\d+\..+?)(?=\d+\.)", r"\1\n", answer)

        # Step 4: strip leading/trailing whitespace
        return {"answer": answer.strip(), "action": data.get("action")}
    except (json.JSONDecodeError, AttributeError):
        # fallback: just return raw text
        return {"answer": raw_text.strip(), "action": "None"}
