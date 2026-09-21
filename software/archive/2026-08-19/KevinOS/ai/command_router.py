import re


class CommandRouter:
    def __init__(
        self,
        brain,
        spotify,
        files
    ):
        self.brain = brain
        self.spotify = spotify
        self.files = files

    def route(self, text):
        lowered = (
            text.lower()
            .strip()
        )

        # =================================
        # MEMORY COMMANDS
        # =================================

        if any(
            phrase in lowered
            for phrase in [
                "add that to your memory",
                "remember that",
                "save that to your memory",
                "remember what i just said"
            ]
        ):
            success = (
                self.brain.save_last_turn()
            )

            if success:
                return {
                    "handled": True,
                    "message":
                        "Got it. I'll remember that."
                }

            return {
                "handled": True,
                "message":
                    "I don't have anything to save yet."
            }

        if any(
            phrase in lowered
            for phrase in [
                "forget that",
                "forget the last memory",
                "remove that from your memory"
            ]
        ):
            success = (
                self.brain
                .forget_last_memory()
            )

            if success:
                return {
                    "handled": True,
                    "message":
                        "Alright. I forgot it."
                }

            return {
                "handled": True,
                "message":
                    "I don't have anything saved to forget."
            }

        memory_match = re.search(
            r"(?:what do you remember about|"
            r"what do you know about)\s+(.+)",
            lowered
        )

        if memory_match:
            query = (
                memory_match
                .group(1)
                .strip(" ?.!")
            )

            matches = (
                self.brain
                .search_memory(query)
            )

            if not matches:
                return {
                    "handled": True,
                    "message":
                        f"I don't have anything saved about {query}."
                }

            saved = matches[0]

            return {
                "handled": True,
                "message":
                    "You asked me to remember that "
                    + saved["user"]
                }

        # =================================
        # SPOTIFY
        # =================================

        spotify_result = (
            self.spotify.handle(text)
        )

        if spotify_result:
            return spotify_result

        # =================================
        # FILE COMMANDS
        # =================================

        file_result = (
            self.files.handle(text)
        )

        if file_result:
            return file_result

        # =================================
        # NORMAL CHAT
        # =================================

        return None
