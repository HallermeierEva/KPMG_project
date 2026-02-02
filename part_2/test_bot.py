import requests
import json
import time
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = "http://localhost:8000/chat"

# Initialize Judge Client
judge_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")


def llm_judge(received_answer, expected_truth):
    """Uses an LLM to determine if the bot's answer matches the medical truth."""
    prompt = f"""
    You are an impartial judge evaluating a medical chatbot's accuracy.

    EXPECTED TRUTH: {expected_truth}
    BOT ANSWER: {received_answer}

    Rules:
    1. If the bot provides the correct numerical value or benefit mentioned in the truth, it is CORRECT.
    2. Language differences (Hebrew vs English) do not matter.
    3. Phrasing differences (e.g., 'no cost' vs 'free') do not matter.
    4. If the bot says 'I don't know' but the truth has data, it is INCORRECT.

    Respond only with 'CORRECT' or 'INCORRECT'.
    """
    try:
        response = judge_client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[{"role": "system", "content": "You are a quality assurance judge."},
                      {"role": "user", "content": prompt}]
        )
        return "CORRECT" in response.choices[0].message.content.upper()
    except Exception as e:
        print(f"Judge Error: {e}")
        return False


def send_chat(message, history, profile=None, phase="collection"):
    payload = {"message": message, "history": history, "user_profile": profile, "phase": phase}
    start_time = time.time()
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        return response.json(), time.time() - start_time
    except:
        return None, 0


def run_scenario(name, inputs, ground_truth):
    print(f"\n🚀 Running: {name}")
    history, profile, phase = [], {}, "collection"
    total_latency = 0

    for i, msg in enumerate(inputs):
        res, latency = send_chat(msg, history, profile, phase)
        total_latency += latency
        if not res: return False, 0
        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": res['response']})
        if res.get("extracted_profile"):
            profile, phase = res["extracted_profile"], "qa"

    # Final Validation using LLM Judge
    final_resp = history[-1]["content"]
    passed = llm_judge(final_resp, ground_truth)

    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"  AI Answer: {final_resp[:100]}...")
    print(f"  Result: {status} (Avg Latency: {total_latency / len(inputs):.2f}s)")
    return passed, total_latency / len(inputs)


def main():
    scenarios = [
        {"name": "Maccabi Gold - Dental Root Canal",
         "inputs": ["Hi, I'm Noa, 28", "ID 123456789, Female, Maccabi, Card 111222333, Gold", "I confirm",
                    "How much for a root canal?"],
         "truth": "70% discount for root canals, includes X-rays"},
        {"name": "Clalit Gold - Genetic Screening (Hebrew)",
         "inputs": ["שלום, אני מאיה, בת 32", "ת.ז 987654321, נקבה, כללית, כרטיס 777888999, זהב", "אני מאשרת",
                    "מה הכיסוי לבדיקות סקר גנטיות?"],
         "truth": "95% discount for genetic screening"},
        {"name": "Maccabi Silver - Optometry Glasses",
         "inputs": ["Hi, Ben, 50", "ID 333444555, Male, Maccabi, Card 999000111, Silver", "I confirm",
                    "Coverage for glasses?"],
         "truth": "50% discount up to 700 NIS"},
        {"name": "Meuhedet Gold - Nutrition Workshop",
         "inputs": ["Lea, 35", "ID 444555666, Female, Meuhedet, Card 222333444, Gold", "I confirm",
                    "Nutrition workshops?"],
         "truth": "Free, includes a personal nutrition plan"},
        {"name": "Maccabi Gold - Smoking Cessation",
         "inputs": ["Eli, 55", "ID 000111222, Male, Maccabi, Card 456456456, Gold", "I confirm", "Quit smoking?"],
         "truth": "Free, includes medication"}
    ]

    total_passed = 0
    for s in scenarios:
        passed, _ = run_scenario(s["name"], s["inputs"], s["truth"])
        if passed: total_passed += 1

    print(f"\n{'=' * 40}\nSUMMARY: {total_passed}/{len(scenarios)} Passed\n{'=' * 40}")


if __name__ == "__main__":
    main()