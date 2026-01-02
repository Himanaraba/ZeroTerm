from __future__ import annotations

import importlib
import sys

from .base import BaseDisplay, DisplayError


class WaveshareDisplay(BaseDisplay):
    def __init__(self, model: str, lib_path: str | None = None) -> None:
        self._model = model
        self._lib_path = lib_path
        self._epd = None
        self.width = 0
        self.height = 0

    def init(self) -> None:
        try:
            if self._lib_path and self._lib_path not in sys.path:
                sys.path.insert(0, self._lib_path)
            module = importlib.import_module(f"waveshare_epd.{self._model}")
            self._epd = module.EPD()
            self._epd.init()
            self.width = int(getattr(self._epd, "width", 0))
            self.height = int(getattr(self._epd, "height", 0))
        except Exception as exc:
            raise DisplayError(f"Failed to initialize waveshare driver {self._model}: {exc}")

    def show(self, image) -> None:
        if self._epd is None:
            raise DisplayError("waveshare display not initialized")
        self._epd.display(self._epd.getbuffer(image))

    def sleep(self) -> None:
        if self._epd is None:
            return
        try:
            self._epd.sleep()
        except Exception:
            return