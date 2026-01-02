from __future__ import annotations

from pathlib import Path

from .base import BaseDisplay


class FileDisplay(BaseDisplay):
    def __init__(self, width: int, height: int, output_path: str) -> None:
        self.width = width
        self.height = height
        self._output = Path(output_path)

    def init(self) -> None:
        self._output.parent.mkdir(parents=True, exist_ok=True)

    def show(self, image) -> None:
        image.save(self._output, format="PNG")

    def sleep(self) -> None:
        return None