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


def _text_height(font) -> int:
    bbox = font.getbbox("Ag")
    return bbox[3] - bbox[1]


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


def render_status(
    status: str,
    ip: str,
    wifi: str,
    battery: str,
    updated: str | None,
    config: RenderConfig,
):
    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError("Pillow is required for e-paper rendering.")

    image = Image.new("1", (config.width, config.height), 255)
    draw = ImageDraw.Draw(image)
    font_body = _load_font(config.font_path, config.font_size)
    font_header = _load_font(config.font_path, max(10, config.font_size + 2))
    if font_body is None or font_header is None:
        raise RuntimeError("Pillow font unavailable.")

    header_height = _text_height(font_header) + 6
    if header_height > config.height:
        header_height = config.height

    draw.rectangle((0, 0, config.width, header_height), fill=0)
    draw.rectangle((0, 0, config.width - 1, config.height - 1), outline=0)

    margin = config.margin
    header_y = max(0, (header_height - _text_height(font_header)) // 2)
    draw.text((margin, header_y), "ZEROTERM", font=font_header, fill=255)

    status_text = status.strip().upper() or "READY"
    status_width = _text_width(draw, status_text, font_header)
    draw.text(
        (config.width - margin - status_width, header_y),
        status_text,
        font=font_header,
        fill=255,
    )

    body_lines = [f"IP {ip}", f"WIFI {wifi}", f"BAT {battery}"]
    if updated:
        body_lines.append(f"UPD {updated}")

    line_height = _text_height(font_body)
    y = header_height + max(2, config.line_gap)
    max_width = config.width - margin * 2

    for line in body_lines:
        if y + line_height > config.height - margin:
            break
        fitted = _fit_text(draw, line, font_body, max_width)
        draw.text((margin, y), fitted, font=font_body, fill=0)
        y += line_height + config.line_gap

    if config.rotate % 360:
        image = image.rotate(config.rotate, expand=False)
    return image
