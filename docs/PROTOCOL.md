# Protocol

ZeroTerm uses a single HTTP/WebSocket endpoint. The WebSocket link is a direct
byte pipe to the PTY with only minimal control messages.

## WebSocket Endpoint

- URL: ws://<host>:<port>/ws
- Binary frames: Raw PTY bytes (both directions)
- Text frames: Control messages in JSON

## Control Messages (Client -> Server)

Resize the PTY when the browser window changes size:

```
{"type":"resize","cols":80,"rows":24}
```

## Server Messages

- Binary frames only (raw PTY output)
- No JSON or REST command wrapping

## Notes

- Commands are never filtered or translated.
- The browser is a transport cable for the TTY.
