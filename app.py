"""Potential Radar — local Flask dashboard. Runs on 127.0.0.1:8799.

Shows mock sample data until a real scan populates the DB. Add a free Spotify
developer key (.env) to go live.
"""

import os

from flask import Flask, jsonify, render_template


def _load_dotenv():
    """Minimal .env loader: KEY=VALUE per line. Real environment vars always win."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()

import db        # noqa: E402  (import after .env load is intentional)
import mock      # noqa: E402
import scan      # noqa: E402
import spotify   # noqa: E402

app = Flask(__name__)
db.init()


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/artists")
def api_artists():
    rows = db.latest(limit=100)
    if not rows:
        return jsonify(
            {
                "artists": mock.SAMPLE,
                "demo": True,
                "connected": spotify.enabled(),
            }
        )
    return jsonify(
        {
            "artists": rows,
            "demo": False,
            "connected": spotify.enabled(),
            "scanned_at": db.last_scan(),
        }
    )


@app.route("/api/scan", methods=["POST"])
def api_scan():
    return jsonify(scan.run())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8799, debug=False)
