import os
from pathlib import Path
import subprocess
import re

from flask import Flask, jsonify, request
from dotenv import load_dotenv
from difflib import SequenceMatcher

import spotipy
from spotipy.oauth2 import SpotifyOAuth


app = Flask(__name__)

load_dotenv(Path(__file__).with_name(".env"))
BRIDGE_KEY = os.environ["KEVIN_BRIDGE_KEY"]
APPROVED_FOLDERS = {
    "school": Path(Path.home() / "Documents" / "School"),
    "projects": Path(Path.home() / "Documents" / "Projects"),
    "downloads": Path(Path.home() / "Downloads"),
}

FOLDER_ALIASES = {
    "school": "school",
    "class": "school",
    "classes": "school",
    "homework": "school",

    "project": "projects",
    "projects": "projects",
    "cpu project": "projects",
    "cpu": "projects",
    "kevin project": "projects",
    "drone project": "projects",

    "download": "downloads",
    "downloads": "downloads",
}


def normalize_text(text):
    text = text.lower()

    text = re.sub(
        r"[_\-.]+",
        " ",
        text
    )

    text = re.sub(
        r"[^a-z0-9\s]",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def resolve_folder_alias(folder_name):
    if not folder_name:
        return None

    normalized = normalize_text(
        folder_name
    )

    alias = FOLDER_ALIASES.get(
        normalized
    )

    if not alias:
        return None

    return APPROVED_FOLDERS.get(
        alias
    )


def is_allowed_path(path):
    try:
        resolved = Path(path).resolve()

        for folder in APPROVED_FOLDERS.values():
            folder_resolved = (
                folder.resolve()
            )

            if resolved == folder_resolved:
                return True

            if (
                folder_resolved
                in resolved.parents
            ):
                return True

        return False

    except Exception:
        return False


def similarity_score(query, filename):
    query = normalize_text(query)

    filename = normalize_text(
        filename
    )

    query_words = query.split()

    # Exact phrase match gets a big boost
    phrase_score = (
        1.0
        if query in filename
        else 0.0
    )

    # Count how many requested words appear
    word_matches = sum(
        1
        for word in query_words
        if word in filename
    )

    if query_words:
        word_score = (
            word_matches
            / len(query_words)
        )
    else:
        word_score = 0.0

    # Fuzzy similarity helps with typos
    fuzzy_score = SequenceMatcher(
        None,
        query,
        filename
    ).ratio()

    return (
        phrase_score * 3.0
        + word_score * 2.0
        + fuzzy_score
    )


def search_files(
    query,
    limit=10,
    folder_alias=None
):
    matches = []

    selected_folder = (
        resolve_folder_alias(
            folder_alias
        )
    )

    if selected_folder:
        folders = [
            selected_folder
        ]
    else:
        folders = list(
            APPROVED_FOLDERS.values()
        )

    for folder in folders:
        if not folder.exists():
            continue

        for path in folder.rglob("*"):
            if not path.is_file():
                continue

            score = similarity_score(
                query,
                path.stem
            )

            # Ignore very weak matches
            if score < 1.0:
                continue

            matches.append({
                "name": path.name,
                "path": str(path),
                "score": round(
                    score,
                    3
                )
            })

    matches.sort(
        key=lambda item:
            item["score"],
        reverse=True
    )

    return matches[:limit]

load_dotenv(
    Path(__file__).with_name(".env")
)


spotify = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=(
            "user-read-playback-state "
            "user-modify-playback-state"
        ),
        cache_path=str(Path.home() / ".kevin_spotify_cache")
    )
)


def authorized():
    return (
        request.headers.get("X-Kevin-Key")
        == BRIDGE_KEY
    )


def get_computer_device():
    devices = spotify.devices()

    for device in devices["devices"]:
        if device["type"].lower() == "computer":
            return device

    return None


def activate_computer():
    device = get_computer_device()

    if not device:
        raise RuntimeError(
            "No Spotify computer device found."
        )

    if not device["is_active"]:
        spotify.transfer_playback(
            device_id=device["id"],
            force_play=False
        )

    return device


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "computer": "Kevin PC Bridge",
        "spotify": "enabled"
    })


@app.route("/test", methods=["POST"])
def test():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    return jsonify({
        "success": True,
        "message": "Kevin can access the PC."
    })


@app.route("/spotify/devices", methods=["GET"])
def spotify_devices():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    devices = spotify.devices()["devices"]

    return jsonify({
        "devices": devices
    })


@app.route("/spotify/play", methods=["POST"])
def spotify_play():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}

    query = data.get(
        "query",
        ""
    ).strip()

    if not query:
        return jsonify({
            "error": "No song query provided."
        }), 400

    try:
        device = activate_computer()

        results = spotify.search(
            q=query,
            type="track",
            limit=1
        )

        tracks = (
            results
            .get("tracks", {})
            .get("items", [])
        )

        if not tracks:
            return jsonify({
                "error": "No matching song found."
            }), 404

        track = tracks[0]

        spotify.start_playback(
            device_id=device["id"],
            uris=[track["uri"]]
        )

        artists = ", ".join(
            artist["name"]
            for artist in track["artists"]
        )

        return jsonify({
            "success": True,
            "song": track["name"],
            "artist": artists,
            "device": device["name"]
        })

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


@app.route("/spotify/pause", methods=["POST"])
def spotify_pause():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    try:
        spotify.pause_playback()

        return jsonify({
            "success": True,
            "message": "Spotify paused."
        })

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


@app.route("/spotify/resume", methods=["POST"])
def spotify_resume():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    try:
        device = activate_computer()

        spotify.start_playback(
            device_id=device["id"]
        )

        return jsonify({
            "success": True,
            "message": "Spotify resumed."
        })

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


@app.route("/spotify/next", methods=["POST"])
def spotify_next():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    try:
        spotify.next_track()

        return jsonify({
            "success": True,
            "message": "Skipped to next track."
        })

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


@app.route("/spotify/previous", methods=["POST"])
def spotify_previous():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    try:
        spotify.previous_track()

        return jsonify({
            "success": True,
            "message": "Returned to previous track."
        })

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


@app.route("/spotify/current", methods=["GET"])
def spotify_current():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    try:
        playback = spotify.current_playback()

        if not playback or not playback.get("item"):
            return jsonify({
                "playing": False
            })

        track = playback["item"]

        artists = ", ".join(
            artist["name"]
            for artist in track["artists"]
        )

        return jsonify({
            "playing": playback["is_playing"],
            "song": track["name"],
            "artist": artists
        })

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500

@app.route(
    "/files/search",
    methods=["POST"]
)
def files_search():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    query = data.get(
        "query",
        ""
    ).strip()

    folder = data.get(
        "folder",
        ""
    ).strip()

    if not query:
        return jsonify({
            "error":
                "No search query provided."
        }), 400

    matches = search_files(
        query=query,
        folder_alias=folder
    )

    return jsonify({
        "success": True,
        "matches": matches
    })

@app.route("/files/open", methods=["POST"])
def files_open():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}

    path = data.get("path", "").strip()

    if not path:
        return jsonify({
            "error": "No path provided."
        }), 400

    if not is_allowed_path(path):
        return jsonify({
            "error": "Path is outside approved folders."
        }), 403

    file_path = Path(path)

    if not file_path.exists():
        return jsonify({
            "error": "File does not exist."
        }), 404

    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", str(file_path)],
            shell=False
        )

        return jsonify({
            "success": True,
            "opened": str(file_path)
        })

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5010,
        threaded=True
    )