from app.prompts.app_prompt import build_prompt_hi, build_prompt_en, build_prompt_ne

def test_prompt_hi():
    prompt_hi  = build_prompt_hi("neutral", "What is the capital of India?", [], [])
    print(prompt_hi)

def test_prompt_en():
    prompt_en = build_prompt_en("neutral", "What is the capital of India?", [], [])
    print(prompt_en)

def test_prompt_ne():
    prompt_ne = build_prompt_ne("neutral", "What is the capital of India?", [], [])
    print(prompt_ne)

if __name__ == "__main__":
    test_prompt_hi()
    test_prompt_en()
    test_prompt_ne()