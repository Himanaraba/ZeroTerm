from __future__ import annotations

from .base import BaseDisplay


class NullDisplay(BaseDisplay):
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def init(self) -> None:
        return None

    def show(self, image) -> None:
        return None

    def sleep(self) -> None:
        return None