# import httpx
# import json
# import os

# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# def generate_handler_code(action_type, details):
#     prompt = f"""
#     You are a Python code generator for an AI system.
#     The AI returned a new action type that isn't yet implemented.
#     Action type: {action_type}
#     Example details: {json.dumps(details, indent=2)}

#     Write a Python function stub that can handle this action.
#     The function should follow this format:

#     def {action_type}(details):
#         # Describe what this action should do
#         pass
#     """

#     try:
#         response = httpx.post(
#             "https://openrouter.ai/api/v1/chat/completions",
#             headers={
#                 "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#                 "Content-Type": "application/json",
#             },
#             json={
#                 "model": "mistralai/mistral-7b-instruct:free",
#                 "messages": [
#                     {"role": "system", "content": "You are a helpful Python code generator."},
#                     {"role": "user", "content": prompt}
#                 ]
#             },
#             timeout=30
#         )

#         data = response.json()
#         code = data["choices"][0]["message"]["content"]

#         print("🧩 AI-suggested handler:")
#         print(code)

#         # Optional: write to a file like handlers/new_actions.py
#         with open("new_action_handlers.py", "a") as f:
#             f.write(f"\n\n{code}\n")
#     except Exception as e:
#         print(f"❌ Could not auto-generate handler: {e}")
