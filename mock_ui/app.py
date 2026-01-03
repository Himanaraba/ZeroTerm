from __future__ import annotations

from pathlib import Path
import os

from flask import Flask, Response, jsonify, request, send_from_directory
import random
import time

ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "web"
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = Flask(__name__, static_folder=None)
app.config["TEST_PROFILE"] = "balanced"


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


@app.get("/api/status")
def status() -> Response:
    battery = random.randint(35, 98)
    power_state = random.choice(["CHG", "DIS", "FULL", "IDLE"])
    wifi_mode = random.choice(["managed", "monitor"])
    wifi_channel = random.choice(["1", "6", "11"])
    wifi_packets = random.randint(1200, 85000)
    status_map = {
        "CHG": "Charging",
        "DIS": "Discharging",
        "FULL": "Full",
        "IDLE": "Not charging",
    }
    battery_status = status_map.get(power_state)
    payload = {
        "battery_percent": battery,
        "battery_status": battery_status,
        "power_state": power_state,
        "profile": app.config.get("TEST_PROFILE"),
        "wifi_iface": "wlan0",
        "wifi_state": "up",
        "wifi_ssid": "KALI-NET",
        "wifi_mode": wifi_mode,
        "wifi_channel": wifi_channel,
        "wifi_packets": wifi_packets,
        "wifi_ip": "192.168.0.50",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return jsonify(payload)


@app.post("/api/power")
def power() -> Response:
    payload = request.get_json(silent=True) or {}
    profile = str(payload.get("profile", "")).strip().lower()
    if profile in {"default", "none", "off", ""}:
        app.config["TEST_PROFILE"] = None
        return jsonify({"ok": True, "profile": None, "restarted": False})
    if profile not in {"eco", "balanced", "performance"}:
        return jsonify({"ok": False, "error": "invalid profile"}), 400
    app.config["TEST_PROFILE"] = profile
    return jsonify({"ok": True, "profile": profile, "restarted": False})


if __name__ == "__main__":
    host = os.environ.get("ZEROTERM_TEST_HOST", "127.0.0.1")
    port = int(os.environ.get("ZEROTERM_TEST_PORT", "8081"))
    app.run(host=host, port=port, debug=False)
