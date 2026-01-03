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


def _center_text(draw, text: str, font, box, fill: int = 0) -> None:
    x0, y0, x1, y1 = box
    text_width = _text_width(draw, text, font)
    text_height = _text_height(font)
    x = x0 + max(0, (x1 - x0 - text_width) // 2)
    y = y0 + max(0, (y1 - y0 - text_height) // 2)
    draw.text((x, y), text, font=font, fill=fill)


def _draw_battery_bar(draw, box, percent: int | None) -> None:
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        return
    draw.rectangle((x0, y0, x1, y1), outline=0, fill=255)
    if percent is None:
        return
    pct = max(0, min(100, percent))
    inner_x0 = x0 + 1
    inner_y0 = y0 + 1
    inner_x1 = x1 - 1
    inner_y1 = y1 - 1
    if inner_x1 <= inner_x0 or inner_y1 <= inner_y0:
        return
    fill_width = int((inner_x1 - inner_x0) * pct / 100)
    draw.rectangle((inner_x0, inner_y0, inner_x0 + fill_width, inner_y1), fill=0)


def _draw_card(draw, box, label: str, value: str, font_label, font_value) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle((x0, y0, x1, y1), outline=0)
    box_height = max(1, y1 - y0)
    label_height = _text_height(font_label)
    header_height = min(label_height + 4, max(8, box_height - 6))
    header_bottom = y0 + header_height
    draw.rectangle((x0 + 1, y0 + 1, x1 - 1, header_bottom), fill=0)

    label_text = _fit_text(draw, label, font_label, x1 - x0 - 6)
    draw.text((x0 + 3, y0 + 2), label_text, font=font_label, fill=255)

    value_area_top = header_bottom + 2
    value_area_bottom = y1 - 2
    if value_area_bottom <= value_area_top:
        return
    value_text = _fit_text(draw, value, font_value, x1 - x0 - 6)
    value_y = value_area_bottom - _text_height(font_value)
    if value_y < value_area_top:
        value_y = value_area_top
    draw.text((x0 + 3, value_y), value_text, font=font_value, fill=0)


def _split_wifi_text(text: str) -> tuple[str | None, str | None]:
    text = (text or "").strip()
    if not text:
        return None, None
    parts = text.split()
    state = parts[0].upper()
    ssid = " ".join(parts[1:]).strip() if len(parts) > 1 else None
    if ssid == "":
        ssid = None
    return state, ssid


def _short_wifi_state(state: str | None) -> str:
    if not state:
        return "UNK"
    state = state.upper()
    mapping = {
        "UP": "UP",
        "DOWN": "DN",
        "UNKNOWN": "UNK",
        "MISSING": "MISS",
        "DORMANT": "DORM",
        "LOWERLAYERDOWN": "LLDN",
    }
    return mapping.get(state, state[:4])


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

    body_top = header_height + 3
    body_bottom = config.height - margin
    content_width = config.width - margin * 2
    gap = 6
    left_width = min(96, max(72, int(content_width * 0.36)))
    if content_width - left_width - gap < 110:
        left_width = max(60, content_width - gap - 110)
    right_width = max(60, content_width - left_width - gap)

    left_x0 = margin
    left_x1 = left_x0 + left_width
    right_x0 = left_x1 + gap
    right_x1 = right_x0 + right_width

    draw.rectangle((left_x0, body_top, left_x1, body_bottom), outline=0)
    draw.rectangle((right_x0, body_top, right_x1, body_bottom), outline=0)

    face_text = _pick_face(status_text, battery_percent)
    label_height = _text_height(font_small)
    bar_height = max(6, label_height // 2 + 2)
    battery_block = label_height + bar_height + 6

    face_box = (
        left_x0 + 4,
        body_top + 4,
        left_x1 - 4,
        body_bottom - battery_block - 4,
    )
    face_size = min(face_box[2] - face_box[0], face_box[3] - face_box[1])
    face_box = (
        face_box[0] + max(0, (face_box[2] - face_box[0] - face_size) // 2),
        face_box[1] + max(0, (face_box[3] - face_box[1] - face_size) // 2),
        face_box[0] + max(0, (face_box[2] - face_box[0] - face_size) // 2) + face_size,
        face_box[1] + max(0, (face_box[3] - face_box[1] - face_size) // 2) + face_size,
    )
    if face_box[2] > face_box[0] and face_box[3] > face_box[1]:
        draw.ellipse(face_box, outline=0)
        _center_text(draw, face_text, font_face, face_box, fill=0)

    bat_label = "BAT"
    bat_value = f"{battery_percent}%" if battery_percent is not None else "--"
    bat_y = body_bottom - battery_block + 2
    draw.text((left_x0 + 4, bat_y), bat_label, font=font_small, fill=0)
    bat_value_width = _text_width(draw, bat_value, font_small)
    draw.text((left_x1 - 4 - bat_value_width, bat_y), bat_value, font=font_small, fill=0)

    bar_y = bat_y + label_height + 2
    bar_box = (left_x0 + 4, bar_y, left_x1 - 6, bar_y + bar_height)
    _draw_battery_bar(draw, bar_box, battery_percent)

    grid_top = body_top + 2
    grid_bottom = body_bottom - 2
    grid_height = max(1, grid_bottom - grid_top)
    cols = 2
    rows = 3
    gap_x = 6
    gap_y = 4
    cell_width = max(1, (right_width - gap_x) // cols)
    cell_height = max(1, (grid_height - gap_y * (rows - 1)) // rows)

    wifi_state, wifi_ssid = _split_wifi_text(wifi)
    wifi_label = f"WIFI {_short_wifi_state(wifi_state)}"
    wifi_value = wifi_ssid or "--"

    cards = [
        ("IP", ip),
        ("BAT", battery),
        (wifi_label, wifi_value),
        ("TMP", temp),
        ("UP", uptime),
        ("LOAD", load),
    ]

    card_index = 0
    for row in range(rows):
        for col in range(cols):
            if card_index >= len(cards):
                break
            x0 = right_x0 + col * (cell_width + gap_x)
            y0 = grid_top + row * (cell_height + gap_y)
            x1 = x0 + cell_width
            y1 = y0 + cell_height
            label, value = cards[card_index]
            _draw_card(draw, (x0, y0, x1, y1), label, value, font_small, font_body)
            card_index += 1

    if updated:
        updated_text = _fit_text(draw, updated, font_small, config.width - margin * 2)
        updated_width = _text_width(draw, updated_text, font_small)
        updated_y = config.height - margin - _text_height(font_small)
        if updated_y > body_top:
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
