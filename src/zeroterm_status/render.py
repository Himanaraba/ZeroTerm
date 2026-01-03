from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


DEFAULT_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
]


def _load_font(font_path: str | None, font_size: int):
    if ImageFont is None:
        return None
    candidates = []
    if font_path:
        candidates.append(font_path)
    else:
        candidates.extend(DEFAULT_FONT_CANDIDATES)
    for candidate in candidates:
        try:
            if candidate and Path(candidate).exists():
                return ImageFont.truetype(candidate, font_size)
        except OSError:
            continue
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
    temp: str,
    load: str,
    uptime: str,
    battery_percent: int | None,
    updated: str | None,
    config: RenderConfig,
):
    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError("Pillow is required for e-paper rendering.")

    image = Image.new("1", (config.width, config.height), 255)
    draw = ImageDraw.Draw(image)
    font_body = _load_font(config.font_path, max(10, config.font_size))
    font_header = _load_font(config.font_path, max(12, config.font_size + 2))
    font_face = _load_font(config.font_path, max(16, config.font_size + 8))
    font_small = _load_font(config.font_path, max(9, config.font_size - 2))
    if font_body is None or font_header is None or font_face is None or font_small is None:
        raise RuntimeError("Pillow font unavailable.")

    margin = config.margin
    header_height = min(config.height, max(18, _text_height(font_header) + 6))

    draw.rectangle((0, 0, config.width, header_height), fill=0)
    draw.rectangle((0, 0, config.width - 1, config.height - 1), outline=0)

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

    face_text = _pick_face(status_text, battery_percent)
    face_width = _text_width(draw, face_text, font_face)
    face_x = max(margin, (config.width - face_width) // 2)
    face_y = header_height + 4
    draw.text((face_x, face_y), face_text, font=font_face, fill=0)

    line_height = _text_height(font_body)
    stats_top = face_y + _text_height(font_face) + 4
    col_gap = 8
    col_width = max(1, (config.width - margin * 2 - col_gap) // 2)
    left_x = margin
    right_x = margin + col_width + col_gap

    rows = [
        (f"IP {ip}", f"BAT {battery}"),
        (f"WIFI {wifi}", f"TMP {temp}"),
        (f"UP {uptime}", f"LOAD {load}"),
    ]

    y = stats_top
    for left, right in rows:
        if y + line_height > config.height - margin:
            break
        left_text = _fit_text(draw, left, font_body, col_width)
        right_text = _fit_text(draw, right, font_body, col_width)
        draw.text((left_x, y), left_text, font=font_body, fill=0)
        draw.text((right_x, y), right_text, font=font_body, fill=0)
        y += line_height + config.line_gap

    if updated:
        updated_text = _fit_text(draw, updated, font_small, config.width - margin * 2)
        updated_width = _text_width(draw, updated_text, font_small)
        updated_y = config.height - margin - _text_height(font_small)
        if updated_y > y:
            draw.text(
                (config.width - margin - updated_width, updated_y),
                updated_text,
                font=font_small,
                fill=0,
            )

    if config.rotate % 360:
        image = image.rotate(config.rotate, expand=False)
    return image


def _pick_face(status_text: str, battery_percent: int | None) -> str:
    status = status_text.strip().upper()
    if status in {"DOWN", "FAILED"}:
        return "(x_x)"
    if battery_percent is not None and battery_percent <= 15:
        return "(;_;)"
    if status == "RUNNING":
        return "(o_o)"
    if status == "READY":
        return "(-_-)"
    return "(o_o)"
