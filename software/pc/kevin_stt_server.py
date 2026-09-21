from flask import Flask, request, jsonify
from faster_whisper import WhisperModel
import tempfile
import os


app = Flask(__name__)

print("Loading Kevin speech recognition model...")

model = WhisperModel(
    "base.en",
    device="cpu",
    compute_type="int8"
)

print("Kevin speech recognition ready.")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model": "base.en"
    })


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({
            "error": "No audio file provided"
        }), 400

    audio_file = request.files["audio"]

    fd, path = tempfile.mkstemp(
        suffix=".wav"
    )

    os.close(fd)

    try:
        audio_file.save(path)

        segments, info = model.transcribe(
            path,
            beam_size=1,
            vad_filter=True
        )

        text_parts = []

        for segment in segments:
            text_parts.append(
                segment.text.strip()
            )

        text = " ".join(text_parts).strip()

        return jsonify({
            "text": text
        })

    finally:
        if os.path.exists(path):
            os.remove(path)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5006,
        threaded=True
    )