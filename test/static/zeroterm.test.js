(() => {
  const statusEl = document.getElementById("status");
  const hintEl = document.getElementById("hint");
  const termEl = document.getElementById("terminal");
  const termTextEl = document.getElementById("terminal-text");
  const cursorEl = document.getElementById("cursor");
  const inputEl = document.getElementById("terminal-input");
  const keysEl = document.getElementById("terminal-keys");
  const batteryEl = document.getElementById("battery-value");
  const powerEl = document.getElementById("power-value");
  const profileEl = document.getElementById("power-profile");
  const powerActionsEl = document.getElementById("power-actions");

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
      this.scrollTop = 0;
      this.scrollBottom = rows - 1;
      this.dirtyRows = new Set();
      this.dirtyAll = true;
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
      this.scrollTop = 0;
      this.scrollBottom = rows - 1;
      this._markAllDirty();
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

    renderRow(row) {
      const screen = this._activeScreen();
      if (row < 0 || row >= screen.length) {
        return "";
      }
      return this._renderLine(screen[row]);
    }

    consumeDirtyRows() {
      if (this.dirtyAll) {
        this.dirtyAll = false;
        this.dirtyRows.clear();
        return { all: true, rows: [] };
      }
      if (this.dirtyRows.size === 0) {
        return null;
      }
      const rows = Array.from(this.dirtyRows);
      this.dirtyRows.clear();
      return { all: false, rows };
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
        if (ch === "D") {
          this._lineFeed();
          this.state = "normal";
          return;
        }
        if (ch === "M") {
          this._reverseIndex();
          this.state = "normal";
          return;
        }
        if (ch === "c") {
          this._reset();
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
        case "d": {
          const row = toInt(parts[0], 1) - 1;
          this.cursorRow = Math.max(0, Math.min(this.rows - 1, row));
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
        case "r": {
          const top = toIntAllowZero(parts[0], 1);
          const bottom = toIntAllowZero(parts[1], this.rows);
          this._setScrollRegion(top, bottom);
          break;
        }
        case "L": {
          const count = toInt(parts[0], 1);
          this._insertLines(count);
          break;
        }
        case "M": {
          const count = toInt(parts[0], 1);
          this._deleteLines(count);
          break;
        }
        case "S": {
          const count = toInt(parts[0], 1);
          this._scrollRegionUp(count);
          break;
        }
        case "T": {
          const count = toInt(parts[0], 1);
          this._scrollRegionDown(count);
          break;
        }
        case "@": {
          const count = toInt(parts[0], 1);
          this._insertChars(count);
          break;
        }
        case "P": {
          const count = toInt(parts[0], 1);
          this._deleteChars(count);
          break;
        }
        case "X": {
          const count = toInt(parts[0], 1);
          this._eraseChars(count);
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
      const wasAlt = this.useAlt;
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
      if (this.useAlt !== wasAlt) {
        this.scrollTop = 0;
        this.scrollBottom = this.rows - 1;
        this._markAllDirty();
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
      this._markDirty(this.cursorRow);
      this.cursorCol += 1;
      if (this.cursorCol >= this.cols) {
        this.cursorCol = 0;
        this._lineFeed();
      }
    }

    _lineFeed() {
      if (this.cursorRow >= this.scrollBottom) {
        this.cursorRow = this.scrollBottom;
        this._scrollRegionUp(1);
        return;
      }
      this.cursorRow = Math.min(this.rows - 1, this.cursorRow + 1);
    }

    _tab() {
      const next = Math.floor(this.cursorCol / 8 + 1) * 8;
      const target = Math.min(next, this.cols - 1);
      while (this.cursorCol < target) {
        this._writeChar(" ");
      }
    }

    _scrollUp() {
      this._scrollRegionUp(1);
    }

    _reverseIndex() {
      if (this.cursorRow <= this.scrollTop) {
        this.cursorRow = this.scrollTop;
        this._scrollRegionDown(1);
        return;
      }
      this.cursorRow = Math.max(0, this.cursorRow - 1);
    }

    _reset() {
      this.useAlt = false;
      this.screen = this._createScreen(this.rows, this.cols);
      this.altScreen = this._createScreen(this.rows, this.cols);
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
      this.scrollTop = 0;
      this.scrollBottom = this.rows - 1;
      this._markAllDirty();
    }

    _setScrollRegion(top, bottom) {
      const resolvedTop = Math.max(0, top - 1);
      const resolvedBottom = Math.min(this.rows - 1, bottom - 1);
      if (resolvedTop >= resolvedBottom) {
        this.scrollTop = 0;
        this.scrollBottom = this.rows - 1;
      } else {
        this.scrollTop = resolvedTop;
        this.scrollBottom = resolvedBottom;
      }
      this.cursorRow = this.scrollTop;
      this.cursorCol = 0;
    }

    _insertLines(count) {
      if (this.cursorRow < this.scrollTop || this.cursorRow > this.scrollBottom) {
        return;
      }
      const screen = this._activeScreen();
      const max = this.scrollBottom - this.cursorRow + 1;
      const total = Math.min(count, max);
      if (total <= 0) {
        return;
      }
      for (let i = 0; i < total; i += 1) {
        screen.splice(this.cursorRow, 0, this._blankLine(this.cols, this._currentAttrs()));
        screen.splice(this.scrollBottom + 1, 1);
      }
      this._markDirtyRange(this.cursorRow, this.scrollBottom);
    }

    _deleteLines(count) {
      if (this.cursorRow < this.scrollTop || this.cursorRow > this.scrollBottom) {
        return;
      }
      const screen = this._activeScreen();
      const max = this.scrollBottom - this.cursorRow + 1;
      const total = Math.min(count, max);
      if (total <= 0) {
        return;
      }
      for (let i = 0; i < total; i += 1) {
        screen.splice(this.cursorRow, 1);
        screen.splice(this.scrollBottom, 0, this._blankLine(this.cols, this._currentAttrs()));
      }
      this._markDirtyRange(this.cursorRow, this.scrollBottom);
    }

    _scrollRegionUp(count) {
      const screen = this._activeScreen();
      const height = this.scrollBottom - this.scrollTop + 1;
      const total = Math.min(count, height);
      if (total <= 0) {
        return;
      }
      for (let i = 0; i < total; i += 1) {
        screen.splice(this.scrollTop, 1);
        screen.splice(this.scrollBottom, 0, this._blankLine(this.cols, this._currentAttrs()));
      }
      this._markDirtyRange(this.scrollTop, this.scrollBottom);
    }

    _scrollRegionDown(count) {
      const screen = this._activeScreen();
      const height = this.scrollBottom - this.scrollTop + 1;
      const total = Math.min(count, height);
      if (total <= 0) {
        return;
      }
      for (let i = 0; i < total; i += 1) {
        screen.splice(this.scrollBottom, 1);
        screen.splice(this.scrollTop, 0, this._blankLine(this.cols, this._currentAttrs()));
      }
      this._markDirtyRange(this.scrollTop, this.scrollBottom);
    }

    _insertChars(count) {
      if (this.cursorRow < 0 || this.cursorRow >= this.rows) {
        return;
      }
      if (this.cursorCol < 0 || this.cursorCol >= this.cols) {
        return;
      }
      const line = this._activeScreen()[this.cursorRow];
      const total = Math.min(count, this.cols - this.cursorCol);
      if (total <= 0) {
        return;
      }
      for (let col = this.cols - 1; col >= this.cursorCol + total; col -= 1) {
        line[col] = line[col - total];
      }
      const attrs = this._currentAttrs();
      for (let col = 0; col < total; col += 1) {
        line[this.cursorCol + col] = this._blankCell(attrs);
      }
      this._markDirty(this.cursorRow);
    }

    _deleteChars(count) {
      if (this.cursorRow < 0 || this.cursorRow >= this.rows) {
        return;
      }
      if (this.cursorCol < 0 || this.cursorCol >= this.cols) {
        return;
      }
      const line = this._activeScreen()[this.cursorRow];
      const total = Math.min(count, this.cols - this.cursorCol);
      if (total <= 0) {
        return;
      }
      for (let col = this.cursorCol; col < this.cols - total; col += 1) {
        line[col] = line[col + total];
      }
      const attrs = this._currentAttrs();
      for (let col = this.cols - total; col < this.cols; col += 1) {
        line[col] = this._blankCell(attrs);
      }
      this._markDirty(this.cursorRow);
    }

    _eraseChars(count) {
      if (this.cursorRow < 0 || this.cursorRow >= this.rows) {
        return;
      }
      if (this.cursorCol < 0 || this.cursorCol >= this.cols) {
        return;
      }
      const line = this._activeScreen()[this.cursorRow];
      const total = Math.min(count, this.cols - this.cursorCol);
      if (total <= 0) {
        return;
      }
      const attrs = this._currentAttrs();
      for (let col = this.cursorCol; col < this.cursorCol + total; col += 1) {
        line[col] = this._blankCell(attrs);
      }
      this._markDirty(this.cursorRow);
    }

    _eraseDisplay(mode) {
      const screen = this._activeScreen();
      const attrs = this._currentAttrs();
      if (mode === 2) {
        for (let row = 0; row < this.rows; row += 1) {
          screen[row] = this._blankLine(this.cols, attrs);
        }
        this._markAllDirty();
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
        this._markDirtyRange(0, this.cursorRow);
        return;
      }
      const row = this.cursorRow;
      for (let col = this.cursorCol; col < this.cols; col += 1) {
        screen[row][col] = this._blankCell(attrs);
      }
      for (let r = row + 1; r < this.rows; r += 1) {
        screen[r] = this._blankLine(this.cols, attrs);
      }
      this._markDirtyRange(row, this.rows - 1);
    }

    _eraseLine(mode) {
      const screen = this._activeScreen();
      const attrs = this._currentAttrs();
      if (mode === 2) {
        screen[this.cursorRow] = this._blankLine(this.cols, attrs);
        this._markDirty(this.cursorRow);
        return;
      }
      if (mode === 1) {
        for (let col = 0; col <= this.cursorCol; col += 1) {
          screen[this.cursorRow][col] = this._blankCell(attrs);
        }
        this._markDirty(this.cursorRow);
        return;
      }
      for (let col = this.cursorCol; col < this.cols; col += 1) {
        screen[this.cursorRow][col] = this._blankCell(attrs);
      }
      this._markDirty(this.cursorRow);
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

    _markDirty(row) {
      if (this.dirtyAll) {
        return;
      }
      if (row < 0 || row >= this.rows) {
        return;
      }
      this.dirtyRows.add(row);
    }

    _markDirtyRange(start, end) {
      if (this.dirtyAll) {
        return;
      }
      const from = Math.max(0, start);
      const to = Math.min(this.rows - 1, end);
      for (let row = from; row <= to; row += 1) {
        this.dirtyRows.add(row);
      }
    }

    _markAllDirty() {
      this.dirtyAll = true;
      this.dirtyRows.clear();
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
      this.rowEls = [];
    }

    resizeToFit() {
      this._measure();
      const cols = Math.max(10, Math.floor(this.textEl.clientWidth / this.cell.width));
      const rows = Math.max(5, Math.floor(this.textEl.clientHeight / this.cell.height));
      this.emulator.resize(rows, cols);
      this._ensureRows(rows);
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
      const dirty = this.emulator.consumeDirtyRows();
      if (!dirty) {
        this._updateCursor();
        return;
      }
      this._ensureRows(this.emulator.rows);
      if (dirty.all) {
        for (let row = 0; row < this.emulator.rows; row += 1) {
          this.rowEls[row].innerHTML = this.emulator.renderRow(row);
        }
      } else {
        const rows = dirty.rows;
        for (const row of rows) {
          if (row < 0 || row >= this.emulator.rows) {
            continue;
          }
          this.rowEls[row].innerHTML = this.emulator.renderRow(row);
        }
      }
      this._updateCursor();
    }

    _ensureRows(rows) {
      const current = this.rowEls.length;
      if (current > rows) {
        for (let i = rows; i < current; i += 1) {
          this.rowEls[i].remove();
        }
        this.rowEls.length = rows;
      }
      if (current < rows) {
        const fragment = document.createDocumentFragment();
        for (let i = current; i < rows; i += 1) {
          const rowEl = document.createElement("div");
          rowEl.className = "terminal-row";
          fragment.appendChild(rowEl);
          this.rowEls.push(rowEl);
        }
        this.textEl.appendChild(fragment);
      }
    }

    _measure() {
      const probe = document.createElement("span");
      probe.className = "probe";
      const sampleSize = 10;
      probe.textContent = "M".repeat(sampleSize);
      this.textEl.appendChild(probe);
      const rect = probe.getBoundingClientRect();
      probe.remove();

      const styles = window.getComputedStyle(this.textEl);
      const lineHeight = parseFloat(styles.lineHeight);
      const fontSize = parseFloat(styles.fontSize);

      this.cell = {
        width: rect.width > 0 ? rect.width / sampleSize : 8,
        height: Number.isFinite(lineHeight)
          ? lineHeight
          : rect.height || (Number.isFinite(fontSize) ? fontSize * 1.3 : 16),
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
      const x = this.origin.x + col * this.cell.width;
      const y = this.origin.y + row * this.cell.height;
      this.cursorEl.style.transform = `translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`;
      this.cursorEl.style.opacity = this.emulator.cursorVisible ? "1" : "0";
    }
  }

  const view = new TerminalView(termTextEl, cursorEl);
  const hostName = "pi";
  const userName = "kali";
  const homeDir = "/home/kali";
  let currentDir = homeDir;
  let previousDir = homeDir;
  let currentLine = "";
  let lastInputAt = Date.now();
  let forcedState = null;
  let progressTimer = null;

  const telemetryState = {
    battery_percent: null,
    battery_status: null,
    power_state: null,
    profile: null,
  };

  const mockBootAt = Date.now() - Math.floor(Math.random() * 6 * 60 * 60 * 1000);
  const mockNetwork = {
    ip: `192.168.0.${Math.floor(20 + Math.random() * 180)}`,
    wifiState: "UP",
    ssid: "KALI-NET",
    extIface: "wlan1",
  };
  const mockFs = {
    "/": ["home", "opt", "etc", "var", "boot", "dev", "proc", "sys"],
    "/home": ["kali"],
    "/home/kali": ["zeroterm", "notes.txt", ".bashrc", ".ssh"],
    "/home/kali/zeroterm": ["README.md", "docs", "src", "web", "systemd", "scripts"],
    "/opt": ["zeroterm"],
    "/opt/zeroterm": ["config", "docs", "scripts", "src", "systemd", "web"],
    "/etc": ["zeroterm", "os-release", "hostname"],
    "/etc/zeroterm": ["zeroterm.env"],
    "/var": ["log", "lib"],
    "/var/log": ["syslog", "zeroterm"],
    "/var/log/zeroterm": ["power-events.log", "battery.csv"],
    "/var/lib": ["zeroterm"],
    "/var/lib/zeroterm": ["epaper.png", "rtl8821au.status"],
  };
  const mockFiles = {
    "/etc/hostname": `${hostName}\n`,
    "/etc/os-release": [
      "PRETTY_NAME=\"Kali GNU/Linux\"",
      "NAME=\"Kali GNU/Linux\"",
      "VERSION=\"2025.1\"",
      "ID=kali",
      "HOME_URL=\"https://www.kali.org/\"",
    ].join("\n"),
    "/etc/zeroterm/zeroterm.env": [
      "ZEROTERM_BIND=0.0.0.0",
      "ZEROTERM_PORT=8080",
      "ZEROTERM_STATUS_PROFILE=balanced",
    ].join("\n"),
    "/var/log/zeroterm/power-events.log": "2025-01-03T01:12:03Z STATE DIS 76\n",
    "/var/log/zeroterm/battery.csv": "timestamp,percent,status\n2025-01-03T01:00:00Z,82,Discharging\n",
    "/var/lib/zeroterm/rtl8821au.status": "RTL8821AU: OK (monitor mode enabled)\n",
  };

  const setStatus = (text, tone) => {
    statusEl.textContent = text;
    statusEl.dataset.tone = tone || "idle";
  };

  let statusTimer = null;

  const setActiveProfile = (profile) => {
    if (!powerActionsEl) {
      return;
    }
    const normalized = profile ? profile.toLowerCase() : "";
    const buttons = powerActionsEl.querySelectorAll("button[data-profile]");
    for (const button of buttons) {
      const isActive = button.dataset.profile === normalized;
      button.dataset.active = isActive ? "true" : "false";
    }
  };

  const updateTelemetry = (payload) => {
    if (!payload) {
      return;
    }
    if ("battery_percent" in payload) {
      telemetryState.battery_percent = payload.battery_percent;
      const batteryPercent =
        typeof payload.battery_percent === "number" ? `${payload.battery_percent}%` : "--";
      if (batteryEl) {
        batteryEl.textContent = batteryPercent;
      }
    }
    if ("battery_status" in payload) {
      telemetryState.battery_status = payload.battery_status;
    }
    if ("power_state" in payload) {
      telemetryState.power_state = payload.power_state;
      const powerState = payload.power_state || "--";
      if (powerEl) {
        powerEl.textContent = powerState;
      }
    }
    if ("profile" in payload) {
      telemetryState.profile = payload.profile;
      const profile = payload.profile ? payload.profile.toUpperCase() : "--";
      if (profileEl) {
        profileEl.textContent = profile;
      }
      setActiveProfile(payload.profile || "");
    }
  };

  const fetchStatus = async () => {
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      updateTelemetry(payload);
    } catch (error) {
      // Ignore status fetch failures to keep the test UI responsive.
    }
  };

  const startStatusPoll = () => {
    if (statusTimer) {
      clearInterval(statusTimer);
    }
    fetchStatus();
    statusTimer = setInterval(fetchStatus, 15000);
  };

  const postPowerProfile = async (profile) => {
    if (!profile) {
      return;
    }
    try {
      const response = await fetch("/api/power", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile }),
      });
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      updateTelemetry(payload);
      setTimeout(fetchStatus, 800);
    } catch (error) {
      // Ignore control failures to avoid blocking the test UI.
    }
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

  const writeLine = (text = "") => {
    writeText(`\r\n${text}`);
  };

  const toCrlf = (text) => text.replace(/\r?\n/g, "\r\n");

  const writeBlock = (text) => {
    writeText(`\r\n${toCrlf(text)}`);
  };

  const formatPrompt = () => {
    let shortDir = currentDir;
    if (currentDir === homeDir) {
      shortDir = "~";
    } else if (currentDir.startsWith(`${homeDir}/`)) {
      shortDir = `~${currentDir.slice(homeDir.length)}`;
    }
    return `${userName}@${hostName}:${shortDir}$ `;
  };

  const normalizePath = (path) => {
    if (!path) {
      return "/";
    }
    const isAbs = path.startsWith("/");
    const parts = [];
    for (const piece of path.split("/")) {
      if (!piece || piece === ".") {
        continue;
      }
      if (piece === "..") {
        parts.pop();
        continue;
      }
      parts.push(piece);
    }
    const normalized = `${isAbs ? "/" : ""}${parts.join("/")}`;
    return normalized || "/";
  };

  const resolvePath = (input) => {
    if (!input || input === "~") {
      return homeDir;
    }
    let target = input;
    if (input.startsWith("~/")) {
      target = `${homeDir}${input.slice(1)}`;
    } else if (!input.startsWith("/")) {
      target = `${currentDir}/${input}`;
    }
    return normalizePath(target);
  };

  const isDir = (path) => Object.prototype.hasOwnProperty.call(mockFs, path);

  const getDirEntries = (path, showAll) => {
    const entries = mockFs[path] || [];
    if (showAll) {
      return entries.slice();
    }
    return entries.filter((name) => !name.startsWith("."));
  };

  const formatLs = (path, showAll, longFormat) => {
    if (!isDir(path)) {
      return `ls: cannot access '${path}': No such file or directory`;
    }
    const entries = getDirEntries(path, showAll);
    if (!longFormat) {
      return entries.join("  ");
    }
    const now = new Date();
    const stamp = `${now.toLocaleString("en-US", { month: "short" })} ${String(now.getDate()).padStart(2, " ")} ${String(
      now.getHours()
    ).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    return entries
      .map((name) => {
        const fullPath = path === "/" ? `/${name}` : `${path}/${name}`;
        const isDirectory = isDir(fullPath);
        const mode = isDirectory ? "drwxr-xr-x" : "-rw-r--r--";
        const size = isDirectory ? 4096 : 512;
        return `${mode} 1 ${userName} ${userName} ${String(size).padStart(5, " ")} ${stamp} ${name}`;
      })
      .join("\r\n");
  };

  const formatUptime = () => {
    const elapsed = Math.max(0, Date.now() - mockBootAt);
    const totalMinutes = Math.floor(elapsed / 60000);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    if (hours > 0) {
      return `${hours}h${minutes}m`;
    }
    return `${minutes}m`;
  };

  const formatDate = () => new Date().toString();

  const statusMessage = (status) => {
    const upper = status.toUpperCase();
    if (upper === "RUNNING") {
      return "SESSION LIVE";
    }
    if (upper === "DOWN" || upper === "FAILED") {
      return "SERVICE DOWN";
    }
    if (upper === "READY") {
      return "WAITING FOR INPUT";
    }
    return "STATUS UNKNOWN";
  };

  const shortWifiState = (state) => {
    if (!state) {
      return "UNK";
    }
    const upper = state.toUpperCase();
    const mapping = {
      UP: "UP",
      DOWN: "DN",
      UNKNOWN: "UNK",
      MISSING: "MISS",
      DORMANT: "DORM",
      LOWERLAYERDOWN: "LLDN",
    };
    return mapping[upper] || upper.slice(0, 4);
  };

  const batteryShort = (percent, batteryStatus, powerState) => {
    if (typeof percent !== "number") {
      return "--";
    }
    const status = (batteryStatus || powerState || "").toString().toUpperCase();
    let suffix = "";
    if (status.includes("CHARG")) {
      suffix = "C";
    } else if (status.includes("FULL")) {
      suffix = "F";
    }
    return `${percent}%${suffix}`;
  };

  const pickFace = (status, batteryPercent) => {
    const upper = status.toUpperCase();
    if (upper === "DOWN" || upper === "FAILED") {
      return "(x_x)";
    }
    if (typeof batteryPercent === "number" && batteryPercent <= 15) {
      return "(T_T)";
    }
    if (upper === "RUNNING") {
      return "(^_^)";
    }
    if (upper === "READY") {
      return "(^_~)";
    }
    return "(^_^)";
  };

  const printPrompt = (lineBreak) => {
    if (lineBreak) {
      writeText("\r\n");
    }
    writeText(formatPrompt());
    currentLine = "";
  };

  const runProgressDemo = () => {
    if (progressTimer) {
      clearInterval(progressTimer);
    }
    let percent = 0;
    const renderBar = (value) => {
      const total = 20;
      const filled = Math.round((value / 100) * total);
      return `${"#".repeat(filled)}${"-".repeat(total - filled)}`;
    };
    writeLine(`Progress: ${percent}% [${renderBar(percent)}]`);
    progressTimer = setInterval(() => {
      percent += 5;
      if (percent > 100) {
        percent = 100;
      }
      writeText(`\r\x1b[KProgress: ${percent}% [${renderBar(percent)}]`);
      if (percent >= 100) {
        clearInterval(progressTimer);
        progressTimer = null;
        writeLine("Done.");
        printPrompt(true);
      }
    }, 120);
  };

  const handleCommand = (line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      printPrompt(true);
      return;
    }
    const tokens = trimmed.match(/\S+/g) || [];
    const command = tokens[0].toLowerCase();
    const args = tokens.slice(1);

    if (command === "clear") {
      writeText("\x1b[2J\x1b[H");
      writeText("ZeroTerm TEST MODE\r\nType 'help' for mock commands.");
      printPrompt(true);
      return;
    }
    if (command === "help") {
      writeBlock(
        [
          "Mock commands:",
          "  help, clear, exit",
          "  pwd, cd, ls, cat, echo",
          "  date, uptime, whoami, uname",
          "  ip, ifconfig, iwconfig, wifi",
          "  status, battery, power",
          "  demo colors|progress",
          "  state auto|running|ready|down|failed",
        ].join("\n")
      );
      printPrompt(true);
      return;
    }
    if (command === "exit") {
      writeLine("Session closed (test mode). Restart the page to continue.");
      printPrompt(true);
      return;
    }
    if (command === "pwd") {
      writeLine(currentDir);
      printPrompt(true);
      return;
    }
    if (command === "cd") {
      const targetArg = args[0] || "~";
      if (targetArg === "-") {
        const swap = currentDir;
        currentDir = previousDir;
        previousDir = swap;
        writeLine(currentDir);
        printPrompt(true);
        return;
      }
      const resolved = resolvePath(targetArg);
      if (!isDir(resolved)) {
        writeLine(`cd: no such file or directory: ${targetArg}`);
        printPrompt(true);
        return;
      }
      previousDir = currentDir;
      currentDir = resolved;
      printPrompt(true);
      return;
    }
    if (command === "ls") {
      let showAll = false;
      let longFormat = false;
      const paths = [];
      for (const arg of args) {
        if (arg.startsWith("-")) {
          showAll = showAll || arg.includes("a");
          longFormat = longFormat || arg.includes("l");
        } else {
          paths.push(arg);
        }
      }
      if (paths.length === 0) {
        writeBlock(formatLs(currentDir, showAll, longFormat));
        printPrompt(true);
        return;
      }
      const outputs = [];
      for (const path of paths) {
        const resolved = resolvePath(path);
        const header = paths.length > 1 ? `${path}:` : "";
        if (header) {
          outputs.push(header);
        }
        outputs.push(formatLs(resolved, showAll, longFormat));
        if (paths.length > 1) {
          outputs.push("");
        }
      }
      writeBlock(outputs.join("\n"));
      printPrompt(true);
      return;
    }
    if (command === "cat") {
      if (args.length === 0) {
        writeLine("cat: missing file operand");
        printPrompt(true);
        return;
      }
      const outputs = [];
      for (const path of args) {
        const resolved = resolvePath(path);
        if (isDir(resolved)) {
          outputs.push(`cat: ${path}: Is a directory`);
          continue;
        }
        const content = mockFiles[resolved];
        if (typeof content === "string") {
          outputs.push(content);
        } else {
          outputs.push(`cat: ${path}: No such file or directory`);
        }
      }
      writeBlock(outputs.join("\n"));
      printPrompt(true);
      return;
    }
    if (command === "echo") {
      writeLine(args.join(" "));
      printPrompt(true);
      return;
    }
    if (command === "date") {
      writeLine(formatDate());
      printPrompt(true);
      return;
    }
    if (command === "uptime") {
      writeLine(`up ${formatUptime()}, load average: 0.18, 0.22, 0.25`);
      printPrompt(true);
      return;
    }
    if (command === "whoami") {
      writeLine(userName);
      printPrompt(true);
      return;
    }
    if (command === "uname") {
      if (args.includes("-a")) {
        writeLine("Linux pi 6.1.0-kali-armv7l #1 SMP PREEMPT armv7l GNU/Linux");
      } else if (args.includes("-r")) {
        writeLine("6.1.0-kali-armv7l");
      } else {
        writeLine("Linux");
      }
      printPrompt(true);
      return;
    }
    if (command === "ip") {
      writeBlock(
        [
          "2: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500",
          `    inet ${mockNetwork.ip}/24 brd 192.168.0.255 scope global wlan0`,
          "       valid_lft forever preferred_lft forever",
        ].join("\n")
      );
      printPrompt(true);
      return;
    }
    if (command === "ifconfig") {
      writeBlock(
        [
          "wlan0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500",
          `        inet ${mockNetwork.ip}  netmask 255.255.255.0  broadcast 192.168.0.255`,
          "        RX packets 120  TX packets 95",
        ].join("\n")
      );
      printPrompt(true);
      return;
    }
    if (command === "iwconfig") {
      writeBlock(
        [
          `wlan0  IEEE 802.11  ESSID:\"${mockNetwork.ssid}\"`,
          "      Mode:Managed  Frequency:2.437 GHz  Access Point: 00:11:22:33:44:55",
          "      Link Quality=70/70  Signal level=-39 dBm",
        ].join("\n")
      );
      printPrompt(true);
      return;
    }
    if (command === "wifi") {
      writeLine(`WIFI ${mockNetwork.wifiState} ${mockNetwork.ssid}`);
      printPrompt(true);
      return;
    }
    if (command === "battery") {
      const percent =
        typeof telemetryState.battery_percent === "number" ? `${telemetryState.battery_percent}%` : "--";
      const powerState = telemetryState.power_state || "--";
      const batteryStatus = telemetryState.battery_status || "--";
      writeLine(`BAT ${percent} ${batteryStatus} PWR ${powerState}`);
      printPrompt(true);
      return;
    }
    if (command === "power") {
      if (args.length === 0) {
        writeLine(`Power profile: ${telemetryState.profile || "default"}`);
        printPrompt(true);
        return;
      }
      const profile = args[0].toLowerCase();
      if (!["eco", "balanced", "performance", "default"].includes(profile)) {
        writeLine("Usage: power <eco|balanced|performance|default>");
        printPrompt(true);
        return;
      }
      writeLine(`Applying power profile: ${profile}`);
      const payloadProfile = profile === "default" ? "default" : profile;
      postPowerProfile(payloadProfile).then(() => {
        writeLine(`Power profile: ${telemetryState.profile || payloadProfile}`);
        printPrompt(true);
      });
      return;
    }
    if (command === "status") {
      writeLine("Fetching /api/status...");
      fetch("/api/status", { cache: "no-store" })
        .then((response) => {
          if (!response.ok) {
            throw new Error("status fetch failed");
          }
          return response.json();
        })
        .then((payload) => {
          updateTelemetry(payload);
          writeBlock(JSON.stringify(payload, null, 2));
          printPrompt(true);
        })
        .catch(() => {
          writeLine("status: unable to fetch /api/status");
          printPrompt(true);
        });
      return;
    }
    if (command === "demo") {
      const mode = (args[0] || "").toLowerCase();
      if (mode === "colors") {
        writeBlock(
          [
            "\u001b[31m[!] red warning\u001b[0m",
            "\u001b[32m[+] green ok\u001b[0m",
            "\u001b[33m[*] yellow info\u001b[0m",
            "\u001b[34m[i] blue note\u001b[0m",
            "\u001b[35m[@] magenta\u001b[0m",
            "\u001b[36m[#] cyan\u001b[0m",
            "\u001b[1mBold text\u001b[22m normal",
            "\u001b[7mInverse sample\u001b[27m",
          ].join("\n")
        );
        printPrompt(true);
        return;
      }
      if (mode === "progress") {
        runProgressDemo();
        return;
      }
      writeLine("Usage: demo colors|progress");
      printPrompt(true);
      return;
    }
    if (command === "state") {
      const mode = (args[0] || "").toLowerCase();
      if (!mode || mode === "auto") {
        forcedState = null;
        writeLine("State: auto");
        printPrompt(true);
        return;
      }
      const normalized = mode.toUpperCase();
      if (["RUNNING", "READY", "DOWN", "FAILED"].includes(normalized)) {
        forcedState = normalized;
        writeLine(`State: ${normalized}`);
        printPrompt(true);
        return;
      }
      writeLine("Usage: state auto|running|ready|down|failed");
      printPrompt(true);
      return;
    }

    writeLine(`[TEST MODE] Command not executed: ${line}`);
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
      case "Up":
      case "ArrowUp":
        return "\x1b[A";
      case "Down":
      case "ArrowDown":
        return "\x1b[B";
      case "Right":
      case "ArrowRight":
        return "\x1b[C";
      case "Left":
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

    if (event.keyCode) {
      switch (event.keyCode) {
        case 38:
          return "\x1b[A";
        case 40:
          return "\x1b[B";
        case 39:
          return "\x1b[C";
        case 37:
          return "\x1b[D";
        default:
          break;
      }
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

  if (keysEl && navigator.maxTouchPoints > 0) {
    keysEl.style.display = "flex";
  }

  if (powerActionsEl) {
    powerActionsEl.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-profile]");
      if (!button) {
        return;
      }
      const profile = button.dataset.profile;
      if (profile) {
        postPowerProfile(profile);
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
      const ip = /\d+\.\d+\.\d+\.\d+/.test(host) ? host : mockNetwork.ip;
      const autoState = Date.now() - lastInputAt < 20000 ? "RUNNING" : "READY";
      const status = forcedState || autoState;
      const wifiState = navigator.onLine ? mockNetwork.wifiState : "DOWN";
      if (Math.random() > 0.85) {
        mockNetwork.ssid = ssids[Math.floor(Math.random() * ssids.length)];
      }
      const ssid = mockNetwork.ssid;
      const extIface = mockNetwork.extIface;
      const battery =
        typeof telemetryState.battery_percent === "number"
          ? telemetryState.battery_percent
          : Math.floor(40 + Math.random() * 55);
      const powerState =
        telemetryState.power_state || (battery < 20 ? "DIS" : Math.random() > 0.5 ? "CHG" : "DIS");
      const batteryStatus = telemetryState.battery_status;
      const alertFlags = [];
      if (Math.random() > 0.9) {
        alertFlags.push("TIME");
      }
      if (Math.random() > 0.92) {
        alertFlags.push("UPD");
      }
      if (typeof battery === "number" && battery <= 20) {
        alertFlags.push("LOW");
      }
      const load = (Math.random() * 0.9 + 0.1).toFixed(2);
      const temp = Math.floor(36 + Math.random() * 10);
      const mem = Math.floor(30 + Math.random() * 50);
      const cpu = Math.floor(5 + Math.random() * 60);
      const uptimeMinutes = Math.max(0, Math.floor((Date.now() - mockBootAt) / 60000));
      const upHours = Math.floor(uptimeMinutes / 60);
      const upMinutes = uptimeMinutes % 60;
      const faceText = pickFace(status, battery);
      const wifiShort = shortWifiState(wifiState);
      const batteryShortText = batteryShort(battery, batteryStatus, powerState);
      const upText = `${upHours}:${String(upMinutes).padStart(2, "0")}`;

      topIpEl.textContent = `IP ${ip}`;
      topWifiEl.textContent = `WIFI ${wifiShort}`;
      topBatEl.textContent = `BAT ${batteryShortText}`;
      topUpEl.textContent = `UP ${upText}`;
      faceTextEl.textContent = faceText;
      statusLineEl.textContent = statusMessage(status);
      msgMainEl.textContent = `STATE ${status}`;
      msgSubEl.textContent = `SSID ${ssid}`;
      msgExtEl.textContent = extIface ? `EXT ${extIface.toUpperCase()}` : "";
      msgPowerEl.textContent = `PWR ${powerState || "--"}`;
      msgAlertEl.textContent = alertFlags.length ? `ALRT ${alertFlags.join(" ")}` : "";
      batPercentEl.textContent = `${battery}%`;
      batFillEl.style.width = `${battery}%`;
      memEl.textContent = `${mem}%`;
      cpuEl.textContent = `${cpu}%`;
      tempEl.textContent = `${temp}C`;
      footerLeftEl.textContent = `WIFI ${ssid || wifiShort}`;
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
  startStatusPoll();
})();
