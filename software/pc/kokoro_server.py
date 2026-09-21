from flask import Flask, request, Response, jsonify
from kokoro import KPipeline
import numpy as np

app = Flask(__name__)

pipeline = KPipeline(lang_code="a")

VOICE = "am_adam"
SPEED = 1.08
SAMPLE_RATE = 24000


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "voice": VOICE,
        "speed": SPEED,
        "sample_rate": SAMPLE_RATE
    })


@app.route("/speak_raw", methods=["POST"])
def speak_raw():
    data = request.get_json(silent=True) or {}

    text = data.get("text", "").strip()

    if not text:
        return jsonify({
            "error": "No text provided"
        }), 400

    audio_parts = []

    generator = pipeline(
        text,
        voice=VOICE,
        speed=SPEED
    )

    for _, _, audio in generator:
        audio = audio.detach().cpu().numpy()
        audio = np.asarray(audio).squeeze()

        pcm = np.clip(audio, -1.0, 1.0)
        pcm = (pcm * 32767).astype(np.int16)

        audio_parts.append(pcm.tobytes())

    raw_audio = b"".join(audio_parts)

    return Response(
        raw_audio,
        mimetype="application/octet-stream"
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5005,
        threaded=True
    )