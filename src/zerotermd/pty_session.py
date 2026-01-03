from __future__ import annotations

import fcntl
import os
import pty
import signal
import struct
import termios


def spawn_pty(
    shell: str,
    term: str,
    cwd: str | None,
    shell_cmd: list[str] | None = None,
) -> tuple[int, int]:
    pid, master_fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = term
        if cwd:
            os.chdir(cwd)
        if shell_cmd:
            os.execvp(shell_cmd[0], shell_cmd)
        os.execv(shell, [shell, "-l"])
    return pid, master_fd


def resize_pty(master_fd: int, pid: int, rows: int, cols: int) -> None:
    if rows <= 0 or cols <= 0:
        return
    size = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, size)
    if pid > 0:
        try:
            os.kill(pid, signal.SIGWINCH)
        except ProcessLookupError:
            pass
