import os
import re
import requests


class SpotifyCommands:
    def __init__(self):
        self.base_url = "http://10.0.0.3:5010"

        self.headers = {
            "X-Kevin-Key": os.environ["KEVIN_BRIDGE_KEY"]
        }

        # Remember recent Spotify context
        self.last_song = None
        self.last_artist = None

    def handle(self, text):
        text = text.strip()
        lowered = text.lower()

        # =================================
        # CURRENT SONG
        # =================================

        if any(
            phrase in lowered
            for phrase in [
                "what's playing",
                "whats playing",
                "what is playing",
                "what song is playing",
                "current song",
                "what are we listening to"
            ]
        ):
            return self._current()

        # =================================
        # PAUSE
        # =================================

        if any(
            phrase in lowered
            for phrase in [
                "pause",
                "pause it",
                "pause the music",
                "pause music",
                "pause spotify",
                "pause the song",
                "stop the music",
                "hold the music"
            ]
        ):
            return self._post(
                "/spotify/pause",
                "Music paused."
            )

        # =================================
        # RESUME
        # =================================

        if any(
            phrase in lowered
            for phrase in [
                "resume",
                "resume it",
                "resume the music",
                "resume music",
                "continue",
                "continue the music",
                "keep playing",
                "turn the music back on"
            ]
        ):
            return self._post(
                "/spotify/resume",
                "Music resumed."
            )

        # =================================
        # NEXT
        # =================================

        if any(
            phrase in lowered
            for phrase in [
                "next song",
                "next track",
                "skip",
                "skip it",
                "skip this",
                "skip this one",
                "play the next one"
            ]
        ):
            return self._post(
                "/spotify/next",
                "Skipping it."
            )

        # =================================
        # PREVIOUS
        # =================================

        if any(
            phrase in lowered
            for phrase in [
                "previous song",
                "previous track",
                "go back",
                "go back a song",
                "last song",
                "play the previous one"
            ]
        ):
            return self._post(
                "/spotify/previous",
                "Going back."
            )

        # =================================
        # ANOTHER SONG BY SAME ARTIST
        # =================================

        same_artist_phrases = [
            "another song by them",
            "another one by them",
            "play another by them",
            "play another song by that artist",
            "another song by that artist",
            "play more by them",
            "play more from them"
        ]

        if any(
            phrase in lowered
            for phrase in same_artist_phrases
        ):
            if self.last_artist:
                return self._play(
                    self.last_artist
                )

            return {
                "handled": True,
                "message":
                    "I don't know which artist you mean yet."
            }

        # =================================
        # PLAY MORE BY NAMED ARTIST
        # =================================

        more_artist_match = re.search(
            r"(?:play|put on)\s+"
            r"(?:some\s+|more\s+)?"
            r"(?:music\s+)?"
            r"(?:by\s+)?(.+)",
            text,
            re.IGNORECASE
        )

        if more_artist_match:
            query = (
                more_artist_match
                .group(1)
                .strip()
            )

            query = re.sub(
                r"\s+(?:please|on spotify)$",
                "",
                query,
                flags=re.IGNORECASE
            ).strip()

            return self._play(query)

        # =================================
        # STANDARD PLAY COMMAND
        # =================================

        play_match = re.search(
            r"(?:kevin[,\s]*)?"
            r"(?:can you\s+|could you\s+|please\s+)?"
            r"play\s+(.+)",
            text,
            re.IGNORECASE
        )

        if play_match:
            query = (
                play_match
                .group(1)
                .strip()
            )

            query = re.sub(
                r"\s+(?:please|on spotify)$",
                "",
                query,
                flags=re.IGNORECASE
            ).strip()

            return self._play(query)

        return None

    # =================================
    # PLAY
    # =================================

    def _play(self, query):
        try:
            response = requests.post(
                self.base_url + "/spotify/play",
                headers={
                    **self.headers,
                    "Content-Type": "application/json"
                },
                json={
                    "query": query
                },
                timeout=15
            )

            response.raise_for_status()

            data = response.json()

            song = data.get(
                "song",
                query
            )

            artist = data.get(
                "artist",
                ""
            )

            # Save context for follow-up commands
            self.last_song = song

            if artist:
                self.last_artist = artist

            if artist:
                message = (
                    f"Playing {song} by {artist}."
                )

            else:
                message = (
                    f"Playing {song}."
                )

            return {
                "handled": True,
                "message": message
            }

        except Exception as error:
            print(
                f"[SPOTIFY PLAY ERROR] {error}"
            )

            return {
                "handled": True,
                "message":
                    "I couldn't start that song."
            }

    # =================================
    # SIMPLE POST COMMAND
    # =================================

    def _post(
        self,
        endpoint,
        success_message
    ):
        try:
            response = requests.post(
                self.base_url + endpoint,
                headers=self.headers,
                timeout=15
            )

            response.raise_for_status()

            return {
                "handled": True,
                "message": success_message
            }

        except Exception as error:
            print(
                f"[SPOTIFY ERROR] {error}"
            )

            return {
                "handled": True,
                "message":
                    "Spotify isn't cooperating right now."
            }

    # =================================
    # CURRENT SONG
    # =================================

    def _current(self):
        try:
            response = requests.get(
                self.base_url + "/spotify/current",
                headers=self.headers,
                timeout=15
            )

            response.raise_for_status()

            data = response.json()

            song = data.get("song")
            artist = data.get("artist")

            if not song:
                return {
                    "handled": True,
                    "message":
                        "Nothing is playing right now."
                }

            # Update context
            self.last_song = song

            if artist:
                self.last_artist = artist

            if artist:
                message = (
                    f"That's {song} by {artist}."
                )

            else:
                message = (
                    f"That's {song}."
                )

            return {
                "handled": True,
                "message": message
            }

        except Exception as error:
            print(
                f"[SPOTIFY CURRENT ERROR] {error}"
            )

            return {
                "handled": True,
                "message":
                    "I couldn't check what's playing."
            }
