import os
import re
import requests


class FileCommands:
    def __init__(self):
        self.base_url = (
            "http://10.0.0.3:5010"
        )

        self.headers = {
            "X-Kevin-Key":
                os.environ["KEVIN_BRIDGE_KEY"]
        }

        self.last_matches = []

    def handle(self, text):
        text = text.strip()
        lowered = text.lower()

        # =================================
        # OPEN PREVIOUS RESULT
        # =================================

        open_patterns = {
            0: [
                "open the first one",
                "open first one",
                "open the first file",
                "open first file",
                "open number one"
            ],

            1: [
                "open the second one",
                "open second one",
                "open the second file",
                "open second file",
                "open number two"
            ],

            2: [
                "open the third one",
                "open third one",
                "open the third file",
                "open third file",
                "open number three"
            ]
        }

        for index, phrases in (
            open_patterns.items()
        ):
            if any(
                phrase in lowered
                for phrase in phrases
            ):
                return self._open_match(
                    index
                )

        # =================================
        # SEARCH COMMANDS
        # =================================

        patterns = [
            r"(?:kevin[,\s]*)?"
            r"(?:can you\s+|could you\s+)?"
            r"find\s+(?:my\s+)?(.+)",

            r"(?:kevin[,\s]*)?"
            r"(?:can you\s+|could you\s+)?"
            r"search\s+(?:for\s+)?(.+)",

            r"(?:kevin[,\s]*)?"
            r"(?:can you\s+|could you\s+)?"
            r"look\s+for\s+(.+)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if not match:
                continue

            query = (
                match.group(1)
                .strip()
            )

            query = re.sub(
                r"[?.!]+$",
                "",
                query
            ).strip()

            folder = None

            # -------------------------
            # FOLDER ALIASES
            # -------------------------

            folder_patterns = [
                (
                    r"\s+in\s+(?:my\s+)?"
                    r"school(?:\s+folder)?$",
                    "school"
                ),
                (
                    r"\s+in\s+(?:my\s+)?"
                    r"downloads(?:\s+folder)?$",
                    "downloads"
                ),
                (
                    r"\s+in\s+(?:my\s+)?"
                    r"(?:cpu\s+project|"
                    r"projects?)(?:\s+folder)?$",
                    "projects"
                )
            ]

            for (
                folder_pattern,
                folder_name
            ) in folder_patterns:

                if re.search(
                    folder_pattern,
                    query,
                    re.IGNORECASE
                ):
                    folder = folder_name

                    query = re.sub(
                        folder_pattern,
                        "",
                        query,
                        flags=re.IGNORECASE
                    ).strip()

                    break

            query = re.sub(
                r"\s+(?:file|files|"
                r"document|documents)$",
                "",
                query,
                flags=re.IGNORECASE
            ).strip()

            return self._search(
                query,
                folder
            )

        return None

    def _search(
        self,
        query,
        folder=None
    ):
        try:
            response = requests.post(
                self.base_url
                + "/files/search",
                headers={
                    **self.headers,
                    "Content-Type":
                        "application/json"
                },
                json={
                    "query": query,
                    "folder": folder
                },
                timeout=20
            )

            response.raise_for_status()

            data = response.json()

            matches = data.get(
                "matches",
                []
            )

            self.last_matches = (
                matches
            )

            if not matches:
                return {
                    "handled": True,
                    "message":
                        f"I couldn't find anything matching {query}."
                }

            names = [
                item["name"]
                for item
                in matches[:3]
            ]

            if len(names) == 1:
                message = (
                    f"I found {names[0]}."
                )

            elif len(names) == 2:
                message = (
                    f"I found {names[0]} "
                    f"and {names[1]}."
                )

            else:
                message = (
                    f"I found {names[0]}, "
                    f"{names[1]}, and "
                    f"{names[2]}."
                )

            return {
                "handled": True,
                "message": message
            }

        except Exception as error:
            print(
                "[FILE SEARCH ERROR] "
                f"{error}"
            )

            return {
                "handled": True,
                "message":
                    "I couldn't reach your files right now."
            }

    def _open_match(
        self,
        index
    ):
        if not self.last_matches:
            return {
                "handled": True,
                "message":
                    "I don't have a recent file search."
            }

        if (
            index
            >= len(self.last_matches)
        ):
            return {
                "handled": True,
                "message":
                    "I didn't find that many files."
            }

        match = (
            self.last_matches[index]
        )

        try:
            response = requests.post(
                self.base_url
                + "/files/open",
                headers={
                    **self.headers,
                    "Content-Type":
                        "application/json"
                },
                json={
                    "path":
                        match["path"]
                },
                timeout=20
            )

            response.raise_for_status()

            return {
                "handled": True,
                "message":
                    f"Opening {match['name']}."
            }

        except Exception as error:
            print(
                "[FILE OPEN ERROR] "
                f"{error}"
            )

            return {
                "handled": True,
                "message":
                    "I couldn't open that file."
            }
