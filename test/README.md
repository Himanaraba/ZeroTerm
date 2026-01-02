# ZeroTerm Mock UI (Windows + Flask)

This is a local-only mock UI for visual checks. It does not execute commands
or connect to a PTY. The layout and styling are identical to the real web UI.

## Setup

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

From the repo root:

```
python test\app.py
```

Open:

```
http://127.0.0.1:8081/
```

## Notes

- This is for UI preview only; no commands are executed.
- Uses Flask only for local preview and is not part of the Pi runtime.
- Change host/port with ZEROTERM_TEST_HOST / ZEROTERM_TEST_PORT.