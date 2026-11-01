"""Interactive CLI Chatbot with LiteLLM and Gemini.

Features:
- Multi-turn conversational memory in terminal.
- Automatic retry with exponential backoff for 429 (rate limit) and 503 (high demand).
- Seamless fallback to alternate Gemini models if daily quotas or retries are exhausted.
- Response cost calculation per interaction.
"""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from dotenv import load_dotenv
from litellm import completion
from litellm.exceptions import RateLimitError, ServiceUnavailableError

# Load environment variables (e.g. GEMINI_API_KEY) from lab/.env
load_dotenv(Path(__file__).resolve().parent / ".env")


@dataclass
class ChatMessage:
    """Typed representation of an individual chat turn."""
    role: Literal["system", "user", "assistant"]
    content: str

    def to_dict(self) -> dict[str, str]:
        """Converts the message to a dictionary expected by LiteLLM."""
        return {"role": self.role, "content": self.content}


@dataclass
class Conversation:
    """Typed container representing conversation history."""
    system_prompt: str = "You are a helpful assistant."
    messages: list[ChatMessage] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.messages and self.system_prompt:
            self.add_system(self.system_prompt)

    def add_message(self, role: Literal["system", "user", "assistant"], content: str) -> ChatMessage:
        """Appends a new typed message to the conversation."""
        msg = ChatMessage(role=role, content=content)
        self.messages.append(msg)
        return msg

    def add_user(self, content: str) -> ChatMessage:
        """Appends a user message to the conversation."""
        return self.add_message("user", content)

    def add_assistant(self, content: str) -> ChatMessage:
        """Appends an assistant message to the conversation."""
        return self.add_message("assistant", content)

    def add_system(self, content: str) -> ChatMessage:
        """Appends a system message to the conversation."""
        return self.add_message("system", content)

    def to_payload(self) -> list[dict[str, str]]:
        """Exports messages as a list of dictionaries for LiteLLM completion calls."""
        return [msg.to_dict() for msg in self.messages]

    def __len__(self) -> int:
        return len(self.messages)

    def __iter__(self):
        return iter(self.messages)


def call_llm(
    conversation: Conversation | list[ChatMessage] | list[dict[str, Any]],
    primary_model: str = "gemini/gemini-3.5-flash-lite",
    max_retries: int = 3,
):
    """Calls the model with exponential backoff for 503/429 and fallback to alternate models.

    Args:
        conversation: Typed Conversation, list of ChatMessage, or list of dicts representing chat history.
        primary_model (str): Primary model identifier to attempt first.
        max_retries (int): Maximum number of retry attempts per model.

    Returns:
        ModelResponse: LiteLLM response object containing the generated message and metadata.

    Raises:
        Exception: The last encountered error if all candidate models and retries fail.
    """
    # Normalize input to list of dicts required by LiteLLM
    if isinstance(conversation, Conversation):
        payload = conversation.to_payload()
    elif isinstance(conversation, list):
        payload = [
            m.to_dict() if isinstance(m, ChatMessage) else m for m in conversation
        ]
    else:
        payload = conversation

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
                response = completion(model=model, messages=payload)
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

def main() -> None:
    """Runs the interactive command-line chat loop."""
    # Initialize typed conversation object with a baseline system prompt
    conversation = Conversation(system_prompt="You are a helpful assistant.")

    print("Chat initialized (type 'exit' or 'quit' to stop).\n")

    # Main conversational REPL loop
    while True:
        user_input = input("You: ")
        # Check for exit command
        if user_input.strip().lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        # Add user message to typed conversation object
        conversation.add_user(user_input)

        # Send conversation history to the LLM
        response = call_llm(conversation)
        reply = response.choices[0].message.content or ""
        print("Bot:", reply)

        # Display token usage cost if available in LiteLLM metadata
        cost = response._hidden_params.get("response_cost")
        if cost is not None:
            print(f"Cost: ${cost:.6f}")

        # Add assistant reply to typed conversation object for context in next turn
        conversation.add_assistant(reply)


if __name__ == "__main__":
    main()

