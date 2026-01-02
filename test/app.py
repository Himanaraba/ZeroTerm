from __future__ import annotations

from pathlib import Path
import os

from flask import Flask, Response, send_from_directory

ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "web"
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = Flask(__name__, static_folder=None)


@app.get("/")
def index() -> Response:
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("/zeroterm.js", "/zeroterm.test.js")
    return Response(html, mimetype="text/html")


@app.get("/zeroterm.css")
def css() -> Response:
    return send_from_directory(WEB_DIR, "zeroterm.css")


@app.get("/zeroterm.test.js")
def js() -> Response:
    return send_from_directory(STATIC_DIR, "zeroterm.test.js")


if __name__ == "__main__":
    host = os.environ.get("ZEROTERM_TEST_HOST", "127.0.0.1")
    port = int(os.environ.get("ZEROTERM_TEST_PORT", "8081"))
    app.run(host=host, port=port, debug=False)