(() => {
  const statusEl = document.getElementById("status");
  const hintEl = document.getElementById("hint");
  const termEl = document.getElementById("terminal");
  const termTextEl = document.getElementById("terminal-text");
  const cursorEl = document.getElementById("cursor");
  const inputEl = document.getElementById("terminal-input");
  const keysEl = document.getElementById("terminal-keys");

  const encoder = new TextEncoder();
  const decoder = new TextDecoder("utf-8");

  const ANSI_COLORS = [
    "#1d2127",
    "#e06c75",
    "#98c379",
    "#e5c07b",
    "#61afef",
    "#c678dd",
    "#56b6c2",
    "#d7dae0",
  ];
  const ANSI_BRIGHT = [
    "#5c6370",
    "#ff7a85",
    "#a8e59f",
    "#f7d794",
    "#82aaff",
    "#d8a6ff",
    "#7ee0d6",
    "#ffffff",
  ];
  const DEFAULT_FG = "var(--term-fg)";
  const DEFAULT_BG = "var(--term-bg)";

  const escapeHtml = (text) =>
    text.replace(/[&<>]/g, (char) => {
      if (char === "&") {
        return "&amp;";
      }
      if (char === "<") {
        return "&lt;";
      }
      return "&gt;";
    });

  const colorFrom256 = (value) => {
    if (value < 0 || value > 255 || Number.isNaN(value)) {
      return null;
    }
    if (value < 16) {
      return (ANSI_COLORS.concat(ANSI_BRIGHT))[value];
    }
    if (value >= 232) {
      const shade = 8 + (value - 232) * 10;
      return `rgb(${shade}, ${shade}, ${shade})`;
    }
    const index = value - 16;
    const r = Math.floor(index / 36);
    const g = Math.floor((index % 36) / 6);
    const b = index % 6;
    const map = [0, 95, 135, 175, 215, 255];
    return `rgb(${map[r]}, ${map[g]}, ${map[b]})`;
  };

  class TerminalEmulator {
    constructor(rows, cols) {
      this.rows = rows;
      this.cols = cols;
      this.screen = this._createScreen(rows, cols);
      this.altScreen = this._createScreen(rows, cols);
      this.useAlt = false;
      this.cursorRow = 0;
      this.cursorCol = 0;
      this.cursorVisible = true;
      this.savedCursor = { row: 0, col: 0 };
      this.mainCursor = { row: 0, col: 0 };
      this.altCursor = { row: 0, col: 0 };
      this.fg = null;
      this.bg = null;
      this.bold = false;
      this.inverse = false;
      this.state = "normal";
      this.csiBuffer = "";
      this.oscBuffer = "";
      this.decoder = decoder;
    }

    resize(rows, cols) {
      if (rows <= 0 || cols <= 0) {
        return;
      }
      if (rows === this.rows && cols === this.cols) {
        return;
      }
      this.screen = this._resizeScreen(this.screen, rows, cols);
      this.altScreen = this._resizeScreen(this.altScreen, rows, cols);
      this.rows = rows;
      this.cols = cols;
      this.cursorRow = Math.min(this.cursorRow, rows - 1);
      this.cursorCol = Math.min(this.cursorCol, cols - 1);
    }

    write(bytes) {
      const text = this.decoder.decode(bytes, { stream: true });
      for (const ch of text) {
        this._processChar(ch);
      }
    }

    renderText() {
      const screen = this._activeScreen();
      return screen.map((line) => this._renderLine(line)).join("\n");
    }

    _processChar(ch) {
      if (this.state === "normal") {
        if (ch === "\x1b") {
          this.state = "esc";
          return;
        }
        if (ch === "\n") {
          this._lineFeed();
          return;
        }
        if (ch === "\r") {
          this.cursorCol = 0;
          return;
        }
        if (ch === "\b") {
          if (this.cursorCol > 0) {
            this.cursorCol -= 1;
          }
          return;
        }
        if (ch === "\t") {
          this._tab();
          return;
        }
        if (ch === "\x07") {
          return;
        }
        this._writeChar(ch);
        return;
      }

      if (this.state === "esc") {
        if (ch === "[") {
          this.state = "csi";
          this.csiBuffer = "";
          return;
        }
        if (ch === "]") {
          this.state = "osc";
          this.oscBuffer = "";
          return;
        }
        if (ch === "7") {
          this.savedCursor = { row: this.cursorRow, col: this.cursorCol };
          this.state = "normal";
          return;
        }
        if (ch === "8") {
          this.cursorRow = this.savedCursor.row;
          this.cursorCol = this.savedCursor.col;
          this.state = "normal";
          return;
        }
        this.state = "normal";
        return;
      }

      if (this.state === "csi") {
        if (ch >= "@" && ch <= "~") {
          this._handleCsi(ch, this.csiBuffer);
          this.state = "normal";
          return;
        }
        this.csiBuffer += ch;
        return;
      }

      if (this.state === "osc") {
        if (ch === "\x07") {
          this.state = "normal";
          return;
        }
        if (ch === "\x1b") {
          this.state = "osc_esc";
          return;
        }
        this.oscBuffer += ch;
        return;
      }

      if (this.state === "osc_esc") {
        if (ch === "\\") {
          this.state = "normal";
          return;
        }
        this.state = "osc";
      }
    }

    _handleCsi(finalChar, buffer) {
      let prefix = "";
      let params = buffer;
      if (params.startsWith("?")) {
        prefix = "?";
        params = params.slice(1);
      }
      const parts = params.length ? params.split(";") : [];
      const toInt = (value, fallback) => {
        const num = parseInt(value, 10);
        if (Number.isNaN(num) || num === 0) {
          return fallback;
        }
        return num;
      };
      const toIntAllowZero = (value, fallback) => {
        const num = parseInt(value, 10);
        if (Number.isNaN(num)) {
          return fallback;
        }
        return num;
      };

      switch (finalChar) {
        case "A": {
          const count = toInt(parts[0], 1);
          this.cursorRow = Math.max(0, this.cursorRow - count);
          break;
        }
        case "B": {
          const count = toInt(parts[0], 1);
          this.cursorRow = Math.min(this.rows - 1, this.cursorRow + count);
          break;
        }
        case "C": {
          const count = toInt(parts[0], 1);
          this.cursorCol = Math.min(this.cols - 1, this.cursorCol + count);
          break;
        }
        case "D": {
          const count = toInt(parts[0], 1);
          this.cursorCol = Math.max(0, this.cursorCol - count);
          break;
        }
        case "E": {
          const count = toInt(parts[0], 1);
          this.cursorRow = Math.min(this.rows - 1, this.cursorRow + count);
          this.cursorCol = 0;
          break;
        }
        case "F": {
          const count = toInt(parts[0], 1);
          this.cursorRow = Math.max(0, this.cursorRow - count);
          this.cursorCol = 0;
          break;
        }
        case "G": {
          const col = toInt(parts[0], 1) - 1;
          this.cursorCol = Math.max(0, Math.min(this.cols - 1, col));
          break;
        }
        case "H":
        case "f": {
          const row = toInt(parts[0], 1) - 1;
          const col = toInt(parts[1], 1) - 1;
          this.cursorRow = Math.max(0, Math.min(this.rows - 1, row));
          this.cursorCol = Math.max(0, Math.min(this.cols - 1, col));
          break;
        }
        case "J": {
          const mode = toIntAllowZero(parts[0], 0);
          this._eraseDisplay(mode);
          break;
        }
        case "K": {
          const mode = toIntAllowZero(parts[0], 0);
          this._eraseLine(mode);
          break;
        }
        case "m": {
          this._handleSgr(parts);
          break;
        }
        case "s": {
          this.savedCursor = { row: this.cursorRow, col: this.cursorCol };
          break;
        }
        case "u": {
          this.cursorRow = this.savedCursor.row;
          this.cursorCol = this.savedCursor.col;
          break;
        }
        case "h":
        case "l": {
          if (prefix === "?") {
            const values = parts.map((value) => parseInt(value, 10));
            const enable = finalChar === "h";
            if (values.includes(25)) {
              this.cursorVisible = enable;
            }
            if (values.some((value) => value === 1049 || value === 1047 || value === 47)) {
              this._useAltScreen(enable);
            }
          }
          break;
        }
        default:
          break;
      }
    }

    _useAltScreen(enable) {
      if (enable && !this.useAlt) {
        this.mainCursor = { row: this.cursorRow, col: this.cursorCol };
        this.useAlt = true;
        this.altScreen = this._createScreen(this.rows, this.cols);
        this.cursorRow = 0;
        this.cursorCol = 0;
      } else if (!enable && this.useAlt) {
        this.altCursor = { row: this.cursorRow, col: this.cursorCol };
        this.useAlt = false;
        this.cursorRow = this.mainCursor.row;
        this.cursorCol = this.mainCursor.col;
      }
    }

    _writeChar(ch) {
      if (this.cursorRow < 0 || this.cursorRow >= this.rows) {
        return;
      }
      if (this.cursorCol < 0 || this.cursorCol >= this.cols) {
        return;
      }
      const screen = this._activeScreen();
      screen[this.cursorRow][this.cursorCol] = this._makeCell(ch);
      this.cursorCol += 1;
      if (this.cursorCol >= this.cols) {
        this.cursorCol = 0;
        this._lineFeed();
      }
    }

    _lineFeed() {
      this.cursorRow += 1;
      if (this.cursorRow >= this.rows) {
        this.cursorRow = this.rows - 1;
        this._scrollUp();
      }
    }

    _tab() {
      const next = Math.floor(this.cursorCol / 8 + 1) * 8;
      const target = Math.min(next, this.cols - 1);
      while (this.cursorCol < target) {
        this._writeChar(" ");
      }
    }

    _scrollUp() {
      const screen = this._activeScreen();
      screen.shift();
      screen.push(this._blankLine(this.cols, this._currentAttrs()));
    }

    _eraseDisplay(mode) {
      const screen = this._activeScreen();
      const attrs = this._currentAttrs();
      if (mode === 2) {
        for (let row = 0; row < this.rows; row += 1) {
          screen[row] = this._blankLine(this.cols, attrs);
        }
        return;
      }
      if (mode === 1) {
        for (let row = 0; row <= this.cursorRow; row += 1) {
          const start = row === this.cursorRow ? 0 : 0;
          const end = row === this.cursorRow ? this.cursorCol + 1 : this.cols;
          for (let col = start; col < end; col += 1) {
            screen[row][col] = this._blankCell(attrs);
          }
        }
        return;
      }
      const row = this.cursorRow;
      for (let col = this.cursorCol; col < this.cols; col += 1) {
        screen[row][col] = this._blankCell(attrs);
      }
      for (let r = row + 1; r < this.rows; r += 1) {
        screen[r] = this._blankLine(this.cols, attrs);
      }
    }

    _eraseLine(mode) {
      const screen = this._activeScreen();
      const attrs = this._currentAttrs();
      if (mode === 2) {
        screen[this.cursorRow] = this._blankLine(this.cols, attrs);
        return;
      }
      if (mode === 1) {
        for (let col = 0; col <= this.cursorCol; col += 1) {
          screen[this.cursorRow][col] = this._blankCell(attrs);
        }
        return;
      }
      for (let col = this.cursorCol; col < this.cols; col += 1) {
        screen[this.cursorRow][col] = this._blankCell(attrs);
      }
    }

    _createScreen(rows, cols) {
      const screen = [];
      for (let row = 0; row < rows; row += 1) {
        screen.push(this._blankLine(cols));
      }
      return screen;
    }

    _resizeScreen(screen, rows, cols) {
      const resized = [];
      for (let row = 0; row < rows; row += 1) {
        if (row < screen.length) {
          const line = screen[row].slice(0, cols);
          while (line.length < cols) {
            line.push(this._blankCell());
          }
          resized.push(line);
        } else {
          resized.push(this._blankLine(cols));
        }
      }
      return resized;
    }

    _blankLine(cols, attrs = null) {
      return Array.from({ length: cols }, () => this._blankCell(attrs));
    }

    _blankCell(attrs = null) {
      const fill = attrs || {
        fg: null,
        bg: null,
        bold: false,
        inverse: false,
      };
      return {
        ch: " ",
        fg: fill.fg,
        bg: fill.bg,
        bold: fill.bold,
        inverse: fill.inverse,
      };
    }

    _makeCell(ch) {
      return {
        ch,
        fg: this.fg,
        bg: this.bg,
        bold: this.bold,
        inverse: this.inverse,
      };
    }

    _currentAttrs() {
      return {
        fg: this.fg,
        bg: this.bg,
        bold: this.bold,
        inverse: this.inverse,
      };
    }

    _activeScreen() {
      return this.useAlt ? this.altScreen : this.screen;
    }

    _handleSgr(parts) {
      const codes = parts.length ? parts.map((value) => parseInt(value, 10)) : [0];
      let i = 0;
      while (i < codes.length) {
        const code = Number.isNaN(codes[i]) ? 0 : codes[i];
        if (code === 0) {
          this.fg = null;
          this.bg = null;
          this.bold = false;
          this.inverse = false;
          i += 1;
          continue;
        }
        if (code === 1) {
          this.bold = true;
          i += 1;
          continue;
        }
        if (code === 22) {
          this.bold = false;
          i += 1;
          continue;
        }
        if (code === 7) {
          this.inverse = true;
          i += 1;
          continue;
        }
        if (code === 27) {
          this.inverse = false;
          i += 1;
          continue;
        }
        if (code === 39) {
          this.fg = null;
          i += 1;
          continue;
        }
        if (code === 49) {
          this.bg = null;
          i += 1;
          continue;
        }
        if (code >= 30 && code <= 37) {
          this.fg = ANSI_COLORS[code - 30];
          i += 1;
          continue;
        }
        if (code >= 90 && code <= 97) {
          this.fg = ANSI_BRIGHT[code - 90];
          i += 1;
          continue;
        }
        if (code >= 40 && code <= 47) {
          this.bg = ANSI_COLORS[code - 40];
          i += 1;
          continue;
        }
        if (code >= 100 && code <= 107) {
          this.bg = ANSI_BRIGHT[code - 100];
          i += 1;
          continue;
        }
        if (code === 38 || code === 48) {
          const isBg = code === 48;
          const mode = codes[i + 1];
          if (mode === 5 && typeof codes[i + 2] !== "undefined") {
            const color = colorFrom256(codes[i + 2]);
            if (color) {
              if (isBg) {
                this.bg = color;
              } else {
                this.fg = color;
              }
            }
            i += 3;
            continue;
          }
          if (
            mode === 2 &&
            typeof codes[i + 2] !== "undefined" &&
            typeof codes[i + 3] !== "undefined" &&
            typeof codes[i + 4] !== "undefined"
          ) {
            const r = Math.max(0, Math.min(255, codes[i + 2]));
            const g = Math.max(0, Math.min(255, codes[i + 3]));
            const b = Math.max(0, Math.min(255, codes[i + 4]));
            const color = `rgb(${r}, ${g}, ${b})`;
            if (isBg) {
              this.bg = color;
            } else {
              this.fg = color;
            }
            i += 5;
            continue;
          }
        }
        i += 1;
      }
    }

    _renderLine(line) {
      let html = "";
      let buffer = "";
      let styleKey = null;
      let styleCss = null;

      const flush = () => {
        if (!buffer) {
          return;
        }
        const escaped = escapeHtml(buffer);
        if (styleCss) {
          html += `<span style="${styleCss}">${escaped}</span>`;
        } else {
          html += escaped;
        }
        buffer = "";
      };

      for (const cell of line) {
        const style = this._styleForCell(cell);
        if (style.key !== styleKey) {
          flush();
          styleKey = style.key;
          styleCss = style.css;
        }
        buffer += cell.ch;
      }

      flush();
      return html;
    }

    _styleForCell(cell) {
      let fg = cell.fg || DEFAULT_FG;
      let bg = cell.bg || DEFAULT_BG;
      if (cell.inverse) {
        const temp = fg;
        fg = bg;
        bg = temp;
      }
      const bold = cell.bold;
      const isDefault = fg === DEFAULT_FG && bg === DEFAULT_BG && !bold;
      if (isDefault) {
        return { key: "default", css: null };
      }
      const css = `color:${fg};background-color:${bg};${bold ? "font-weight:600;" : ""}`;
      return { key: `${fg}|${bg}|${bold ? 1 : 0}`, css };
    }
  }

  class TerminalView {
    constructor(textEl, cursorEl) {
      this.textEl = textEl;
      this.cursorEl = cursorEl;
      this.cell = { width: 8, height: 16 };
      this.origin = { x: 0, y: 0 };
      this.emulator = new TerminalEmulator(24, 80);
      this.renderPending = false;
    }

    resizeToFit() {
      this._measure();
      const cols = Math.max(10, Math.floor(this.textEl.clientWidth / this.cell.width));
      const rows = Math.max(5, Math.floor(this.textEl.clientHeight / this.cell.height));
      this.emulator.resize(rows, cols);
      this._updateCursor();
      this._render();
      return { cols, rows };
    }

    write(bytes) {
      this.emulator.write(bytes);
      this._scheduleRender();
    }

    _scheduleRender() {
      if (this.renderPending) {
        return;
      }
      this.renderPending = true;
      requestAnimationFrame(() => {
        this.renderPending = false;
        this._render();
      });
    }

    _render() {
      this.textEl.innerHTML = this.emulator.renderText();
      this._updateCursor();
    }

    _measure() {
      const probe = document.createElement("span");
      probe.className = "probe";
      probe.textContent = "M";
      this.textEl.appendChild(probe);
      const rect = probe.getBoundingClientRect();
      probe.remove();

      this.cell = {
        width: rect.width || 8,
        height: rect.height || 16,
      };

      const textRect = this.textEl.getBoundingClientRect();
      const hostRect = termEl.getBoundingClientRect();
      this.origin = {
        x: textRect.left - hostRect.left,
        y: textRect.top - hostRect.top,
      };
      this.cursorEl.style.width = `${this.cell.width}px`;
      this.cursorEl.style.height = `${this.cell.height}px`;
    }

    _updateCursor() {
      const row = this.emulator.cursorRow;
      const col = this.emulator.cursorCol;
      const x = Math.floor(this.origin.x + col * this.cell.width);
      const y = Math.floor(this.origin.y + row * this.cell.height);
      this.cursorEl.style.transform = `translate(${x}px, ${y}px)`;
      this.cursorEl.style.opacity = this.emulator.cursorVisible ? "1" : "0";
    }
  }

  const view = new TerminalView(termTextEl, cursorEl);
  const promptText = "zeroterm@pi:~$ ";
  let currentLine = "";
  let lastInputAt = Date.now();

  const setStatus = (text, tone) => {
    statusEl.textContent = text;
    statusEl.dataset.tone = tone || "idle";
  };

  const writeText = (text) => {
    view.write(encoder.encode(text));
  };

  const keyMap = {
    esc: "\x1b",
    tab: "\t",
    "ctrl-c": "\x03",
    "ctrl-d": "\x04",
    up: "\x1b[A",
    down: "\x1b[B",
    left: "\x1b[D",
    right: "\x1b[C",
  };

  const printPrompt = (lineBreak) => {
    if (lineBreak) {
      writeText("\r\n");
    }
    writeText(promptText);
    currentLine = "";
  };

  const handleCommand = (line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      printPrompt(true);
      return;
    }
    if (trimmed === "clear") {
      writeText("\x1b[2J\x1b[H");
      writeText("ZeroTerm TEST MODE\r\nType 'help' for mock commands.");
      printPrompt(true);
      return;
    }
    if (trimmed === "help") {
      writeText("\r\nMock commands: help, clear, exit");
      printPrompt(true);
      return;
    }
    if (trimmed === "exit") {
      writeText("\r\nSession closed (test mode). Restart the page to continue.");
      printPrompt(true);
      return;
    }
    writeText(`\r\n[TEST MODE] Command not executed: ${line}`);
    printPrompt(true);
  };

  const skipEscapeSequence = (text, index) => {
    if (text[index] !== "\x1b") {
      return index;
    }
    if (text[index + 1] !== "[") {
      return index + 1;
    }
    let i = index + 2;
    while (i < text.length) {
      const ch = text[i];
      if ((ch >= "@" && ch <= "~") || ch === "~") {
        return i + 1;
      }
      i += 1;
    }
    return text.length;
  };

  const handleInput = (text) => {
    if (text && text.length) {
      lastInputAt = Date.now();
    }
    let i = 0;
    while (i < text.length) {
      const ch = text[i];
      if (ch === "\x1b") {
        i = skipEscapeSequence(text, i);
        continue;
      }
      if (ch === "\r" || ch === "\n") {
        handleCommand(currentLine);
        i += 1;
        continue;
      }
      if (ch === "\x7f") {
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1);
          writeText("\b \b");
        }
        i += 1;
        continue;
      }
      if (ch < " ") {
        i += 1;
        continue;
      }
      currentLine += ch;
      writeText(ch);
      i += 1;
    }
  };

  const mapKey = (event) => {
    if (event.ctrlKey && !event.altKey && !event.metaKey) {
      if (event.key === " ") {
        return "\x00";
      }
      if (event.key.length === 1) {
        const upper = event.key.toUpperCase();
        const code = upper.charCodeAt(0);
        if (code >= 64 && code <= 95) {
          return String.fromCharCode(code - 64);
        }
      }
      return null;
    }

    switch (event.key) {
      case "Enter":
        return "\r";
      case "Backspace":
        return "\x7f";
      case "Tab":
        return "\t";
      case "Escape":
        return "\x1b";
      case "ArrowUp":
        return "\x1b[A";
      case "ArrowDown":
        return "\x1b[B";
      case "ArrowRight":
        return "\x1b[C";
      case "ArrowLeft":
        return "\x1b[D";
      case "Home":
        return "\x1b[H";
      case "End":
        return "\x1b[F";
      case "PageUp":
        return "\x1b[5~";
      case "PageDown":
        return "\x1b[6~";
      case "Delete":
        return "\x1b[3~";
      default:
        break;
    }

    return null;
  };

  inputEl.addEventListener("keydown", (event) => {
    const mapped = mapKey(event);
    if (mapped) {
      event.preventDefault();
      handleInput(mapped);
    }
  });

  inputEl.addEventListener("input", () => {
    if (inputEl.value.length) {
      handleInput(inputEl.value.replace(/\r\n/g, "\n"));
      inputEl.value = "";
    }
  });

  inputEl.addEventListener("compositionend", () => {
    if (inputEl.value.length) {
      handleInput(inputEl.value.replace(/\r\n/g, "\n"));
      inputEl.value = "";
    }
  });

  inputEl.addEventListener("paste", (event) => {
    const text = event.clipboardData.getData("text");
    if (text) {
      event.preventDefault();
      handleInput(text.replace(/\r\n/g, "\n"));
    }
  });

  termEl.addEventListener("click", () => {
    inputEl.focus();
  });

  termEl.addEventListener("touchstart", () => {
    inputEl.focus();
  });

  if (keysEl) {
    keysEl.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-key]");
      if (!button) {
        return;
      }
      const seq = keyMap[button.dataset.key];
      if (seq) {
        handleInput(seq);
        inputEl.focus();
      }
    });
  }

  const createEpaperDebug = () => {
    const style = document.createElement("style");
    style.textContent = `
      .epaper-debug {
        position: fixed;
        right: 16px;
        bottom: 16px;
        width: 250px;
        height: 122px;
        background: #f4f3e8;
        color: #111;
        border: 2px solid #111;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
        font-family: "IBM Plex Mono", "Iosevka Term", monospace;
        display: flex;
        flex-direction: column;
        z-index: 999;
      }
      .epaper-debug__top {
        color: #111;
        display: grid;
        grid-template-columns: 1.6fr 1.1fr 0.9fr 1.2fr;
        font-size: 9px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        border-bottom: 1px solid #111;
      }
      .epaper-debug__top span {
        padding: 2px 3px;
        text-align: left;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .epaper-debug__body {
        flex: 1;
        padding: 4px 6px;
        display: grid;
        grid-template-columns: 1.5fr 1fr;
        gap: 6px;
      }
      .epaper-debug__left,
      .epaper-debug__right {
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .epaper-debug__name {
        font-size: 9px;
        letter-spacing: 0.08em;
      }
      .epaper-debug__face-wrap {
        flex: 1;
        display: grid;
        place-items: center;
        padding: 4px;
      }
      .epaper-debug__face {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        letter-spacing: 0.08em;
      }
      .epaper-debug__face-text {
        line-height: 1;
      }
      .epaper-debug__battery {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 8px;
      }
      .epaper-debug__battery-row {
        display: flex;
        justify-content: space-between;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .epaper-debug__battery-bar {
        position: relative;
        height: 6px;
        border: 1px solid #111;
        background: #f4f3e8;
      }
      .epaper-debug__battery-fill {
        position: absolute;
        inset: 0;
        width: 0%;
        background: #111;
      }
      .epaper-debug__status-line {
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 2px;
      }
      .epaper-debug__message {
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .epaper-debug__message-sub {
        font-size: 8px;
        letter-spacing: 0.1em;
        margin-top: 2px;
      }
      .epaper-debug__metrics {
        margin-top: auto;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 4px;
        text-align: center;
      }
      .epaper-debug__metric-label {
        font-size: 8px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }
      .epaper-debug__metric-value {
        font-size: 10px;
      }
      .epaper-debug__bottom {
        border-top: 1px solid #111;
        padding: 2px 6px;
        display: flex;
        justify-content: space-between;
        font-size: 9px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      @media (max-width: 720px) {
        .epaper-debug {
          right: 10px;
          bottom: 10px;
          transform: scale(0.9);
          transform-origin: bottom right;
        }
      }
    `;
    document.head.appendChild(style);

    const panel = document.createElement("div");
    panel.className = "epaper-debug";
    panel.innerHTML = `
      <div class="epaper-debug__top">
        <span data-top="ip"></span>
        <span data-top="wifi"></span>
        <span data-top="bat"></span>
        <span data-top="up"></span>
      </div>
      <div class="epaper-debug__body">
        <div class="epaper-debug__left">
          <div class="epaper-debug__name">zeroterm&gt;</div>
          <div class="epaper-debug__face-wrap">
            <div class="epaper-debug__face">
              <div class="epaper-debug__face-text"></div>
            </div>
          </div>
          <div class="epaper-debug__battery">
            <div class="epaper-debug__battery-row">
              <span>BAT</span>
              <span data-line="bat-percent"></span>
            </div>
            <div class="epaper-debug__battery-bar">
              <div class="epaper-debug__battery-fill"></div>
            </div>
          </div>
        </div>
        <div class="epaper-debug__right">
          <div class="epaper-debug__status-line" data-line="status-line"></div>
          <div class="epaper-debug__message">
            <div data-line="msg-main"></div>
            <div class="epaper-debug__message-sub" data-line="msg-sub"></div>
            <div class="epaper-debug__message-sub" data-line="msg-ext"></div>
            <div class="epaper-debug__message-sub" data-line="msg-power"></div>
            <div class="epaper-debug__message-sub" data-line="msg-alert"></div>
          </div>
          <div class="epaper-debug__metrics">
            <div>
              <div class="epaper-debug__metric-label">MEM</div>
              <div class="epaper-debug__metric-value" data-line="mem"></div>
            </div>
            <div>
              <div class="epaper-debug__metric-label">CPU</div>
              <div class="epaper-debug__metric-value" data-line="cpu"></div>
            </div>
            <div>
              <div class="epaper-debug__metric-label">TMP</div>
              <div class="epaper-debug__metric-value" data-line="temp"></div>
            </div>
          </div>
        </div>
      </div>
      <div class="epaper-debug__bottom">
        <span data-line="footer-left"></span>
        <span data-line="footer-right"></span>
      </div>
    `;
    document.body.appendChild(panel);

    const topIpEl = panel.querySelector('[data-top="ip"]');
    const topWifiEl = panel.querySelector('[data-top="wifi"]');
    const topBatEl = panel.querySelector('[data-top="bat"]');
    const topUpEl = panel.querySelector('[data-top="up"]');
    const faceTextEl = panel.querySelector(".epaper-debug__face-text");
    const statusLineEl = panel.querySelector('[data-line="status-line"]');
    const msgMainEl = panel.querySelector('[data-line="msg-main"]');
    const msgSubEl = panel.querySelector('[data-line="msg-sub"]');
    const msgExtEl = panel.querySelector('[data-line="msg-ext"]');
    const msgPowerEl = panel.querySelector('[data-line="msg-power"]');
    const msgAlertEl = panel.querySelector('[data-line="msg-alert"]');
    const batPercentEl = panel.querySelector('[data-line="bat-percent"]');
    const batFillEl = panel.querySelector(".epaper-debug__battery-fill");
    const memEl = panel.querySelector('[data-line="mem"]');
    const cpuEl = panel.querySelector('[data-line="cpu"]');
    const tempEl = panel.querySelector('[data-line="temp"]');
    const footerLeftEl = panel.querySelector('[data-line="footer-left"]');
    const footerRightEl = panel.querySelector('[data-line="footer-right"]');
    const ssids = ["ZEROTERM-LAB", "FIELD-NODE", "KALI-NET"];

    const render = () => {
      const host = location.hostname;
      const ip = /\d+\.\d+\.\d+\.\d+/.test(host)
        ? host
        : `192.168.0.${Math.floor(20 + Math.random() * 180)}`;
      const status = Date.now() - lastInputAt < 20000 ? "RUNNING" : "READY";
      const wifiState = navigator.onLine ? "UP" : "DOWN";
      const ssid = ssids[Math.floor(Math.random() * ssids.length)];
      const extIface = Math.random() > 0.6 ? "wlan1" : null;
      const battery = Math.floor(40 + Math.random() * 55);
      const powerState = battery < 20 ? "LOW" : Math.random() > 0.5 ? "CHG" : "DIS";
      const alertFlags = [];
      if (Math.random() > 0.9) {
        alertFlags.push("TIME");
      }
      if (Math.random() > 0.92) {
        alertFlags.push("UPD");
      }
      const load = (Math.random() * 0.9 + 0.1).toFixed(2);
      const temp = Math.floor(36 + Math.random() * 10);
      const mem = Math.floor(30 + Math.random() * 50);
      const cpu = Math.floor(5 + Math.random() * 60);
      const upHours = Math.floor(1 + Math.random() * 9);
      const upMinutes = Math.floor(Math.random() * 59);
      const faceText =
        status === "DOWN"
          ? "(x_x)"
          : battery <= 20
            ? "(T_T)"
            : status === "RUNNING"
              ? "(^_^)"
              : "(^_~)";
      const wifiShort = wifiState === "DOWN" ? "DN" : wifiState;
      const upText = `${upHours}:${String(upMinutes).padStart(2, "0")}`;

      topIpEl.textContent = `IP ${ip}`;
      topWifiEl.textContent = `WIFI ${wifiShort}`;
      topBatEl.textContent = `BAT ${battery}%`;
      topUpEl.textContent = `UP ${upText}`;
      faceTextEl.textContent = faceText;
      statusLineEl.textContent = status === "RUNNING" ? "SESSION LIVE" : "WAITING FOR INPUT";
      msgMainEl.textContent = `STATE ${status}`;
      msgSubEl.textContent = `SSID ${ssid}`;
      msgExtEl.textContent = extIface ? `EXT ${extIface.toUpperCase()}` : "";
      msgPowerEl.textContent = `PWR ${powerState}`;
      msgAlertEl.textContent = alertFlags.length ? `ALRT ${alertFlags.join(" ")}` : "";
      batPercentEl.textContent = `${battery}%`;
      batFillEl.style.width = `${battery}%`;
      memEl.textContent = `${mem}%`;
      cpuEl.textContent = `${cpu}%`;
      tempEl.textContent = `${temp}C`;
      footerLeftEl.textContent = `WIFI ${ssid}`;
      footerRightEl.textContent = `LOAD ${load}`;
    };

    render();
    setInterval(render, 30000);
  };

  window.addEventListener("resize", () => {
    clearTimeout(window.__zerotermResize);
    window.__zerotermResize = setTimeout(() => {
      view.resizeToFit();
    }, 120);
  });

  view.resizeToFit();
  setStatus("TEST MODE", "warn");
  hintEl.textContent = "Mock shell - commands are not executed";
  writeText("ZeroTerm TEST MODE\r\nType 'help' for mock commands.");
  printPrompt(true);
  inputEl.value = "";
  inputEl.focus();
  createEpaperDebug();
})();
