import os
import time
from pathlib import Path
from dotenv import load_dotenv
from litellm import completion
from litellm.exceptions import RateLimitError, ServiceUnavailableError

# Load environment variables from lab/.env
load_dotenv(Path(__file__).resolve().parent / ".env")


def call_llm(messages, primary_model="gemini/gemini-3.5-flash-lite", max_retries=3):
    """Calls the model with exponential backoff for 503/429 and fallback to alternate models."""
    models_to_try = [
        primary_model,
        "gemini/gemini-3.5-flash-lite",
        "gemini/gemini-flash-latest",
        "gemini/gemini-3.8-flash",
    ]
    # Deduplicate while preserving order
    models_to_try = list(dict.fromkeys(models_to_try))

    last_error = None
    for model in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                response = completion(model=model, messages=messages)
                return response
            except ServiceUnavailableError as e:
                wait_time = 2 ** attempt
                print(f"⚠️ [{model}] High demand (503). Retrying in {wait_time}s (attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
                last_error = e
            except RateLimitError as e:
                err_str = str(e)
                # If daily quota limit exceeded, switch immediately to next fallback model
                if "per day limit exceeded" in err_str or "daily" in err_str.lower():
                    print(f"⚠️ [{model}] Daily quota exceeded. Switching to fallback model...")
                    last_error = e
                    break
                wait_time = 3 * attempt
                print(f"⚠️ [{model}] Rate limit reached (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                last_error = e
            except Exception as e:
                print(f"⚠️ [{model}] Unexpected error: {e}. Retrying in 2s...")
                time.sleep(2)
                last_error = e

    raise last_error or RuntimeError("All models and retries exhausted.")


messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant."
    }
]

print("Chat initialized (type 'exit' or 'quit' to stop).\n")

while True:
    user_input = input("You: ")
    if user_input.strip().lower() in ("exit", "quit"):
        print("Goodbye!")
        break

    messages.append({
        "role": "user",
        "content": user_input
    })

    response = call_llm(messages)
    reply = response.choices[0].message.content
    print("Bot:", reply)

    cost = response._hidden_params.get("response_cost")
    if cost is not None:
        print(f"Cost: ${cost:.6f}")

    messages.append({
        "role": "assistant",
        "content": reply
    })

