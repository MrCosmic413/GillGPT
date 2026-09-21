# Kevin PC services

Recovered Windows-side source:

| Script | Purpose | Port |
| --- | --- | --- |
| `kokoro_server.py` | Kokoro `am_adam` speech, 24 kHz signed 16-bit PCM | 5005 |
| `kevin_stt_server.py` | faster-whisper `base.en`, CPU/int8 transcription | 5006 |
| `kevin_pc_bridge.py` | Spotify control and approved-folder file search/open | 5010 |

Run each service in its own configured Python environment with `python <script>.py`. Dependencies visible in source are Flask, kokoro, NumPy, faster-whisper, python-dotenv, and spotipy; exact working versions have not yet been recovered. Ollama runs separately.

For the optional bridge, copy `.env.example` to `.env`, supply your own Spotify application settings, and set a private `KEVIN_BRIDGE_KEY`. Configure the same key in the Pi client's environment. The archive reads this key from the environment; it does not automatically load this PC `.env`.

The bridge uses `Documents/School`, `Documents/Projects`, and `Downloads` under the current user's home as its approved folders. Adjust that allowlist for your installation. Spotify OAuth may need interactive authorization.

These development services bind to all interfaces. Use them on a trusted local network; the speech endpoints have no authentication. Do not expose them directly to the internet.

The publishing copy fixes a syntax error and duplicate file-search functions in the recovered bridge, and removes machine-specific paths and the embedded shared key. End-to-end audio, Spotify, and Pi compatibility have not been tested here.
