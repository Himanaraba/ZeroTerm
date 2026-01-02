from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - optional dependency
    Image = None
    ImageDraw = None
    ImageFont = None


@dataclass(frozen=True)
class RenderConfig:
    width: int
    height: int
    rotate: int
    font_path: str | None
    font_size: int
    margin: int = 6
    line_gap: int = 2


def _load_font(font_path: str | None, font_size: int):
    if ImageFont is None:
        return None
    if font_path:
        try:
            return ImageFont.truetype(font_path, font_size)
        except OSError:
            return ImageFont.load_default()
    return ImageFont.load_default()


def _text_width(draw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _fit_text(draw, text: str, font, max_width: int) -> str:
    if _text_width(draw, text, font) <= max_width:
        return text
    if max_width <= 0:
        return ""
    ellipsis = "..."
    trimmed = text
    while trimmed:
        candidate = trimmed + ellipsis
        if _text_width(draw, candidate, font) <= max_width:
            return candidate
        trimmed = trimmed[:-1]
    return ""


def render_lines(lines: Iterable[str], config: RenderConfig):
    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError("Pillow is required for e-paper rendering.")

    image = Image.new("1", (config.width, config.height), 255)
    draw = ImageDraw.Draw(image)
    font = _load_font(config.font_path, config.font_size)
    if font is None:
        raise RuntimeError("Pillow font unavailable.")

    line_height = font.getbbox("A")[3] - font.getbbox("A")[1]
    y = config.margin
    max_width = config.width - config.margin * 2

    for line in lines:
        line = line.strip()
        if not line:
            y += line_height + config.line_gap
            continue
        fitted = _fit_text(draw, line, font, max_width)
        draw.text((config.margin, y), fitted, font=font, fill=0)
        y += line_height + config.line_gap
        if y > config.height:
            break

    if config.rotate % 360:
        image = image.rotate(config.rotate, expand=False)
    return image