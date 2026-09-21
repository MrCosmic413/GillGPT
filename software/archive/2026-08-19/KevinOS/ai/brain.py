import json
import re
import requests

from ai.personality import KevinPersonality
from ai.long_term_memory import LongTermMemory


class KevinBrain:
    def __init__(self):
        self.personality = KevinPersonality()

        self.ollama_url = (
            "http://10.0.0.3:11434/api/generate"
        )

        self.model = "qwen3:4b-instruct"

        # Short-term conversation memory
        self.history = []
        self.max_turns = 8

        # Selective persistent memory
        self.long_term_memory = LongTermMemory()

    # ====================================
    # SHORT-TERM MEMORY
    # ====================================

    def _add_to_history(
        self,
        user_text,
        assistant_text
    ):
        self.history.append({
            "user": user_text,
            "assistant": assistant_text
        })

        if len(self.history) > self.max_turns:
            self.history = self.history[
                -self.max_turns:
            ]

    def get_last_turn(self):
        if not self.history:
            return None

        return self.history[-1]

    def _history_text(self):
        if not self.history:
            return (
                "There is no previous "
                "conversation context."
            )

        lines = []

        for turn in self.history:
            lines.append(
                f"User: {turn['user']}"
            )

            lines.append(
                f"Kevin: {turn['assistant']}"
            )

        return "\n".join(lines)

    def clear_short_term_memory(self):
        self.history.clear()

    # ====================================
    # LONG-TERM MEMORY
    # ====================================

    def save_last_turn(self):
        turn = self.get_last_turn()

        if not turn:
            return False

        self.long_term_memory.add_memory(
            turn["user"],
            turn["assistant"]
        )

        return True

    def forget_last_memory(self):
        return (
            self.long_term_memory
            .forget_last()
        )

    def search_memory(self, query):
        return (
            self.long_term_memory
            .search(query)
        )

    # ====================================
    # STREAMING BRAIN
    # ====================================

    def handle_text_stream(
        self,
        text,
        sentence_callback=None
    ):
        text = text.strip()

        if not text:
            return {
                "response": "",
                "animation": "listen"
            }

        conversation_history = (
            self._history_text()
        )

        permanent_memory = (
            self.long_term_memory
            .context_text()
        )

        prompt = f"""
{self.personality.system_prompt()}

RECENT CONVERSATION:
{conversation_history}

SELECTIVE LONG-TERM MEMORY:
{permanent_memory}

Use recent conversation context for follow-up
references such as "it", "that", "one", "them",
"he", "she", or "the project".

Use long-term memory only when relevant.

Do not mention memory systems unless the user
asks about them.

CURRENT USER MESSAGE:
User: {text}

Kevin:
"""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": "30m"
        }

        response = requests.post(
            self.ollama_url,
            json=payload,
            stream=True,
            timeout=120
        )

        response.raise_for_status()

        full_response = ""
        sentence_buffer = ""

        print(
            "\nKevin: ",
            end="",
            flush=True
        )

        for line in response.iter_lines():
            if not line:
                continue

            data = json.loads(
                line.decode("utf-8")
            )

            token = data.get(
                "response",
                ""
            )

            if not token:
                continue

            print(
                token,
                end="",
                flush=True
            )

            full_response += token
            sentence_buffer += token

            chunks = re.split(
                r"(?<=[.!?,;:])\s+",
                sentence_buffer
            )

            while len(chunks) > 1:
                complete = (
                    chunks.pop(0).strip()
                )

                if (
                    complete
                    and sentence_callback
                ):
                    sentence_callback(
                        complete
                    )

            sentence_buffer = " ".join(
                chunks
            )

        print()

        leftover = sentence_buffer.strip()

        if leftover and sentence_callback:
            sentence_callback(
                leftover
            )

        final_response = (
            full_response.strip()
        )

        if final_response:
            self._add_to_history(
                text,
                final_response
            )

        return {
            "response": final_response,
            "animation": "think"
        }
