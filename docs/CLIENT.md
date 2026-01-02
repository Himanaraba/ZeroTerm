# Web Client Behavior

The ZeroTerm client is intentionally minimal and framework-free. It renders a
small VT100-style subset to keep the transport thin and predictable.

## Supported Controls

- Carriage return, line feed, backspace, tab
- Cursor movement: CSI A/B/C/D/E/F/G/H/f
- Erase: CSI J and CSI K
- Cursor save/restore: ESC 7/ESC 8 and CSI s/u
- Private modes: ?25h/?25l (cursor) and ?1049h/?1049l (alt screen)
- SGR colors: 30-37/90-97 (foreground), 40-47/100-107 (background)
- SGR extended colors: 38/48;5;n (256-color) and 38/48;2;r;g;b (truecolor)
- SGR attributes: 1 (bold), 7 (inverse), 22/27/39/49 (reset)

## Not Implemented

- Other SGR attributes (underline, italic, blink, strike)
- Advanced DEC modes beyond the subset above

## Behavior Notes

- The client always forwards raw input bytes to the PTY.
- Full-screen TUI apps work for basic navigation; complex rendering may be limited.
- Touch devices show a small key bar (ESC/TAB/CTRL+C/CTRL+D/arrows).
