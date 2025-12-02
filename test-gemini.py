from openai import OpenAI

client = OpenAI(
    api_key="AIzaSyDf4WUMRpf9J_2oGc-i681pDMdj4z3Ahoo",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

response = client.chat.completions.create(
    model="gemini-2.0-flash",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "what is the sum of infinte and undefined",
        }
    ]
)

print(response.choices[0].message)