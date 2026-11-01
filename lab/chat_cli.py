"""Interactive CLI Chatbot with LiteLLM and Gemini.

Features:
- Multi-turn conversational memory in terminal.
- Automatic retry with exponential backoff for 429 (rate limit) and 503 (high demand).
- Seamless fallback to alternate Gemini models if daily quotas or retries are exhausted.
- Response cost calculation per interaction.
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from litellm import completion
from litellm.exceptions import RateLimitError, ServiceUnavailableError

# Load environment variables (e.g. GEMINI_API_KEY) from lab/.env
load_dotenv(Path(__file__).resolve().parent / ".env")


def call_llm(messages, primary_model="gemini/gemini-3.5-flash-lite", max_retries=3):
    """Calls the model with exponential backoff for 503/429 and fallback to alternate models.

    Args:
        messages (list[dict]): List of message objects representing conversation history.
        primary_model (str): Primary model identifier to attempt first.
        max_retries (int): Maximum number of retry attempts per model.

    Returns:
        ModelResponse: LiteLLM response object containing the generated message and metadata.

    Raises:
        Exception: The last encountered error if all candidate models and retries fail.
    """
    # Candidate models to fall back through if the current one fails
    models_to_try = [
        primary_model,
        "gemini/gemini-3.5-flash-lite",
        "gemini/gemini-flash-latest",
        "gemini/gemini-3.8-flash",
    ]
    # Deduplicate while preserving order
    models_to_try = list(dict.fromkeys(models_to_try))

    last_error = None
    # Iterate through fallback models
    for model in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                # Attempt to get a completion from the model
                response = completion(model=model, messages=messages)
                return response
            except ServiceUnavailableError as e:
                # 503 Service Unavailable: Back off exponentially and retry
                wait_time = 2 ** attempt
                print(f"⚠️ [{model}] High demand (503). Retrying in {wait_time}s (attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
                last_error = e
            except RateLimitError as e:
                # 429 Rate Limit: Check if it's a daily limit or per-minute rate limit
                err_str = str(e)
                # If daily quota limit exceeded, switch immediately to next fallback model
                if "per day limit exceeded" in err_str or "daily" in err_str.lower():
                    print(f"⚠️ [{model}] Daily quota exceeded. Switching to fallback model...")
                    last_error = e
                    break
                # Temporary rate limit: back off linearly/exponentially
                wait_time = 3 * attempt
                print(f"⚠️ [{model}] Rate limit reached (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                last_error = e
            except Exception as e:
                # Catch-all for other transient errors
                print(f"⚠️ [{model}] Unexpected error: {e}. Retrying in 2s...")
                time.sleep(2)
                last_error = e

    raise last_error or RuntimeError("All models and retries exhausted.")


# ---------------------------------------------------------------------------
# Interactive Chat Session (REPL)
# ---------------------------------------------------------------------------

# Initialize conversation history with a baseline system prompt
messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant."
    }
]

print("Chat initialized (type 'exit' or 'quit' to stop).\n")

# Main conversational REPL loop
while True:
    user_input = input("You: ")
    # Check for exit command
    if user_input.strip().lower() in ("exit", "quit"):
        print("Goodbye!")
        break

    # Append user turn to conversation history
    messages.append({
        "role": "user",
        "content": user_input
    })

    # Send multi-turn history to the LLM
    response = call_llm(messages)
    reply = response.choices[0].message.content
    print("Bot:", reply)

    # Display token usage cost if available in LiteLLM metadata
    cost = response._hidden_params.get("response_cost")
    if cost is not None:
        print(f"Cost: ${cost:.6f}")

    # Append assistant reply to conversation history for context in next turn
    messages.append({
        "role": "assistant",
        "content": reply
    })

