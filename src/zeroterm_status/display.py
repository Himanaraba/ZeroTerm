from __future__ import annotations

import logging

from .config import StatusConfig
from .drivers.base import BaseDisplay
from .drivers.file import FileDisplay
from .drivers.null import NullDisplay
from .drivers.waveshare import WaveshareDisplay

logger = logging.getLogger(__name__)


def create_display(config: StatusConfig) -> BaseDisplay:
    driver = (config.epaper_driver or "").lower()
    if driver == "file":
        output = config.epaper_output or "/var/lib/zeroterm/epaper.png"
        return FileDisplay(config.epaper_width, config.epaper_height, output)
    if driver == "waveshare":
        return WaveshareDisplay(config.epaper_model, config.epaper_lib)
    if driver == "null":
        return NullDisplay(config.epaper_width, config.epaper_height)

    logger.warning("Unknown e-paper driver '%s', falling back to null", driver)
    return NullDisplay(config.epaper_width, config.epaper_height)