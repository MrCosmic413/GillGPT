import json
from datetime import datetime
from pathlib import Path


class LongTermMemory:
    def __init__(self):
        self.memory_file = (
            Path.home()
            / "KevinOS"
            / "memory"
            / "long_term_memory.json"
        )

        self.memory_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.memories = []

        self._load()

    def _load(self):
        if not self.memory_file.exists():
            self._save()
            return

        try:
            with open(
                self.memory_file,
                "r",
                encoding="utf-8"
            ) as file:
                self.memories = json.load(file)

        except Exception:
            self.memories = []

    def _save(self):
        with open(
            self.memory_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.memories,
                file,
                indent=2
            )

    def add_memory(
        self,
        user_text,
        assistant_text=""
    ):
        memory = {
            "timestamp": datetime.now().isoformat(),
            "user": user_text.strip(),
            "assistant": assistant_text.strip()
        }

        self.memories.append(memory)

        self._save()

        return memory

    def forget_last(self):
        if not self.memories:
            return False

        self.memories.pop()

        self._save()

        return True

    def search(self, query):
        query_words = (
            query.lower()
            .strip()
            .split()
        )

        matches = []

        for memory in self.memories:
            combined = (
                memory.get("user", "")
                + " "
                + memory.get("assistant", "")
            ).lower()

            score = sum(
                1
                for word in query_words
                if word in combined
            )

            if score > 0:
                matches.append(
                    (
                        score,
                        memory
                    )
                )

        matches.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return [
            memory
            for _, memory in matches[:5]
        ]

    def context_text(self):
        if not self.memories:
            return (
                "Kevin currently has no "
                "saved long-term memories."
            )

        recent = self.memories[-10:]

        lines = []

        for memory in recent:
            user_text = memory.get(
                "user",
                ""
            )

            lines.append(
                f"- {user_text}"
            )

        return "\n".join(lines)
