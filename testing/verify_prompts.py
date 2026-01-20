import sys
import os
import json
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.prompts.pqh_prompt import build_prompt_en, build_prompt_hi, build_prompt_ne

def verify_prompt(lang, prompt):
    print(f"\n--- Verifying {lang.upper()} Prompt ---")
    
    # Check for emojis (rough check)
    emojis = [c for c in prompt if ord(c) > 0x1F600 and ord(c) < 0x1F64F] or [c for c in prompt if ord(c) > 0x1F300 and ord(c) < 0x1F5FF]
    if emojis:
        print(f"FAILED: Found emojis: {''.join(emojis)}")
    else:
        print("SUCCESS: No emojis found.")

    # Check for GenZ words instruction
    if "GENZ MODE:" in prompt:
        print("SUCCESS: GenZ mode instruction present.")
    else:
        print("FAILED: GenZ mode instruction missing.")

    # Check for available words
    if "Available words:" in prompt:
        print("SUCCESS: Available words list present.")
    else:
        print("FAILED: Available words list missing.")

def main():
    query = "test query"
    emotion = "happy"
    recent = []
    query_context = []
    tools = [{"name": "open_app"}]
    
    prompts = {
        "english": build_prompt_en(emotion, query, recent, query_context, tools),
        "hindi": build_prompt_hi(emotion, query, recent, query_context, tools),
        "nepali": build_prompt_ne(emotion, query, recent, query_context, tools)
    }

    for lang, prompt in prompts.items():
        verify_prompt(lang, prompt)
        # print(prompt) # Uncomment to see full prompt for manual review

if __name__ == "__main__":
    main()
