import os
from dotenv import load_dotenv
from litellm import completion

load_dotenv()
MODEL = os.getenv("LLM_MODEL", "groq/openai/gpt-oss-20b")

questions = [
    "I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left?",
    "I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left?",
    "I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left?",
    "What is the capital of the Bono East Region of Ghana?",
    "Who founded Makola Market in Accra?",
]

for q in questions:
    resp = completion(
        model=MODEL,
        temperature=0,
        messages=[{"role": "user", "content": q}],
    )
    print("Q:", q)
    print("A:", resp.choices[0].message.content)
    print("-" * 60)