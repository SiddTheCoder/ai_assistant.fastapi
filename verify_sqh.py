
# import sys
# import os
# import json

# # Add project root to path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# from app.models.pqh_response_model import PQHResponse, CognitiveState
# from app.prompts.sqh_prompt import build_sqh_prompt


# def test_sqh_prompt():
#     # Registry should auto-load now

#     # 1. Mock Data using Pydantic Models
#     c_state = CognitiveState(
#         userQuery="Open Chrome and find me a recipe for Momos",
#         emotion="neutral",
#         thought_process="User wants to browse. Need to open chrome and search. Two steps.",
#         answer="Sure! Opening Chrome and searching for Momo recipes.",
#         answerEnglish="Sure! Opening Chrome and searching for Momo recipes."
#     )
    
#     pqh_response = PQHResponse(
#         request_id="test_123",
#         cognitive_state=c_state,
#         requested_tool=["open_app", "web_search"]
#     )
    
#     user_details = {
#         "name": "Siddhant",
#         "ai_gender": "male",
#         "user_gender": "male",
#         "timezone": 5.75,
#         "language": "en" # Testing English
#     }
    
#     try:
#         prompt = build_sqh_prompt(
#             pqh_response=pqh_response, # Passing object, not dict
#             user_details=user_details
#         )
        
#         # Write to file to avoid console encoding issues
#         print("prompt --------------------------------------------------------------------------------------------------:", prompt)
            
#         print("✅ Prompt built and saved to sqh_prompt_output.txt")
        
#         # Check for key elements
#         if "User:** Siddhant" in prompt or "User:** Siddhant" in prompt.replace("*", ""):
#              print("✅ User details present")
#         elif "Siddhant" in prompt:
#              print(f"⚠️ User name found but strict format match might have failed. Check file.")
#         else:
#              print("❌ User details missing")
            
#         if "English" in prompt:
#             print("✅ Language detected correctly")
            
#         if "Sir / Boss" in prompt:
#             print("✅ Honorifics correct")
            
#     except Exception as e:
#         print(f"❌ Error building prompt: {e}")
#         import traceback
#         traceback.print_exc()

# if __name__ == "__main__":
#     test_sqh_prompt()

from app.services.sqh_service import process_sqh

async def main():
  await process_sqh()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())