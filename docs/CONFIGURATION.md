# Configuration

ZeroTerm is configured entirely through environment variables. The systemd unit
loads /etc/zeroterm/zeroterm.env so you can change defaults without editing code.

## Variables

- ZEROTERM_BIND (default: 0.0.0.0)
  Address to bind the HTTP/WebSocket server.

- ZEROTERM_PORT (default: 8080)
  Port for the HTTP/WebSocket server.

- ZEROTERM_SHELL (default: /bin/bash)
  Shell to launch inside the PTY.

- ZEROTERM_TERM (default: linux)
  TERM value exported to the shell session.

- ZEROTERM_CWD (default: empty)
  Optional working directory for the shell. Empty means the user home.

- ZEROTERM_LOG_LEVEL (default: info)
  Logging verbosity (debug, info, warning, error).

- ZEROTERM_STATIC_DIR (default: /opt/zeroterm/web)
  Directory that serves static assets for the web client.
