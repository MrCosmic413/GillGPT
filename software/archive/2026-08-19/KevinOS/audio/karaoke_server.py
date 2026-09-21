import os
from flask import Flask, jsonify, request

from motors.kevin import Kevin


app = Flask(__name__)

BRIDGE_KEY = os.environ["KEVIN_BRIDGE_KEY"]

kevin = Kevin()

mouth_threshold = 0.035
body_threshold = 0.055


def authorized():
    return (
        request.headers.get("X-Kevin-Key")
        == BRIDGE_KEY
    )


@app.route("/karaoke/update", methods=["POST"])
def karaoke_update():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    rms = float(
        data.get("rms", 0.0)
    )

    peak = float(
        data.get("peak", 0.0)
    )

    if rms >= mouth_threshold:
        kevin.mouth.pulse(
            open_time=0.08,
            close_time=0.06
        )

    if peak >= body_threshold:
        kevin.head.out()

    else:
        kevin.head.home()

    return jsonify({
        "success": True
    })


@app.route("/karaoke/stop", methods=["POST"])
def karaoke_stop():
    if not authorized():
        return jsonify({
            "error": "unauthorized"
        }), 401

    kevin.stop()

    return jsonify({
        "success": True
    })


if __name__ == "__main__":
    try:
        app.run(
            host="0.0.0.0",
            port=5020,
            threaded=True
        )

    finally:
        kevin.shutdown()
