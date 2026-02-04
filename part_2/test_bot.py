import requests
import json
import time
import os
import subprocess
import signal
import sys
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = "http://localhost:8000/chat"
HEALTH_URL = "http://localhost:8000/health"

# Initialize Judge Client
judge_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")


def start_backend():
    """Starts the FastAPI backend in a separate process with robust health polling."""
    print(f"⏳ Starting backend server (main.py)...")

    # Using 'python' or 'python3' - sys.executable ensures the same venv is used
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid if os.name != 'nt' else None
    )

    # Wait a moment for the process to actually spawn
    time.sleep(2)

    max_retries = 15
    for i in range(max_retries):
        try:
            # Increased timeout to 5s to allow for slow startup/logic loading
            # Switched to 127.0.0.1 to avoid local DNS resolution delays
            HEALTH_CHECK_URL = "http://127.0.0.1:8000/health"
            response = requests.get(HEALTH_CHECK_URL, timeout=5)

            if response.status_code == 200:
                print("✅ Backend is healthy and ready!")
                return process
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            # This is expected while the server is still booting
            pass
        except Exception as e:
            print(f"  (Note: Unexpected poll error: {type(e).__name__})")

        print(f"  ...waiting for backend to respond ({i + 1}/{max_retries})")
        time.sleep(3)

    # If we reach here, it failed. Print any errors from the backend itself.
    print("❌ Error: Backend failed to start.")
    stdout, stderr = process.communicate(timeout=1)
    if stderr:
        print(f"Backend Error Log:\n{stderr}")

    process.kill()
    sys.exit(1)


def stop_backend(process):
    """Safely terminates the backend server and its process group."""
    print(f"\n🛑 Shutting down backend server (PID: {process.pid})...")
    try:
        if os.name == 'nt':
            process.terminate()
        else:
            # Get the process group ID
            pgid = os.getpgid(process.pid)
            # Send the termination signal to the whole group
            os.killpg(pgid, signal.SIGTERM)

        # Give it a moment to exit cleanly
        process.wait(timeout=5)
        print("✅ Backend stopped successfully.")
    except ProcessLookupError:
        # The process already exited, we can ignore this
        print("ℹ️ Backend was already closed.")
    except Exception as e:
        print(f"⚠️ Note during shutdown: {e}")
        # Final fallback: force kill the individual process
        try:
            process.kill()
        except:
            pass

# --- LLM Judge and Chat logic remain similar ---

def llm_judge(received_answer, expected_truth):
    prompt = f"""
    Judge the medical chatbot's accuracy.
    EXPECTED TRUTH: {expected_truth}
    BOT ANSWER: {received_answer}
    Respond only with 'CORRECT' or 'INCORRECT'.
    """
    try:
        response = judge_client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[{"role": "system", "content": "You are a QA judge."},
                      {"role": "user", "content": prompt}]
        )
        return "CORRECT" in response.choices[0].message.content.upper()
    except Exception as e:
        print(f"Judge Error: {e}")
        return False


def send_chat(message, history, profile=None, phase="collection", lang=None):
    payload = {
        "message": message,
        "history": history,
        "user_profile": profile,
        "phase": phase,
        "preferred_language": lang
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=40)
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}")
        return None


def run_scenario(name, initial_question, collection_inputs, ground_truth, lang="he"):
    print(f"\n🚀 Scenario: {name}")
    history, profile, phase = [], {}, "collection"
    messages = [initial_question] + collection_inputs + (["I confirm"] if lang == "en" else ["אני מאשר"])

    final_resp = ""
    for msg in messages:
        res = send_chat(msg, history, profile, phase, lang)
        if not res: return False
        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": res['response']})
        if res.get("extracted_profile"):
            profile, phase = res["extracted_profile"], res["phase"]
        final_resp = res['response']

    passed = llm_judge(final_resp, ground_truth)
    print(f"  Result: {'✅ PASSED' if passed else '❌ FAILED'}")
    return passed


def main():
    backend_process = start_backend()

    try:
        scenarios = [
            {
                "name": "Maccabi Gold Chaining",
                "initial_question": "What is my coverage for root canals?",
                "lang": "en",
                "inputs": ["Eva, 45, ID 123456789, Female, Maccabi, Card 111222333, Gold"],
                "truth": "70% discount for root canals"
            },
            {
                "name": "Maccabi Gold Workshops (Hebrew)",
                "initial_question": "אני רוצה לדעת כיסוי על סדנאות",
                "lang": "he",
                "inputs": ["שילת מזור בת 45, נקבה, תז 473839888, כרטיס 37462928, מכבי זהב"],
                "truth": "סדנאות גמילה מעישון ותזונה בחינם"
            }
        ]

        passed_count = sum(
            1 for s in scenarios if run_scenario(s["name"], s["initial_question"], s["inputs"], s["truth"], s["lang"]))
        print(f"\n{'=' * 30}\nOVERALL: {passed_count}/{len(scenarios)} PASSED\n{'=' * 30}")

    finally:
        stop_backend(backend_process)


if __name__ == "__main__":
    main()