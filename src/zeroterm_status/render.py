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


def _wrap_text(draw, text: str, font, max_width: int, max_lines: int = 2) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if _text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines - 1:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if len(lines) == max_lines and len(words) > 0:
        lines[-1] = _fit_text(draw, lines[-1], font, max_width)
    return lines


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


def _battery_short(percent: int | None, battery_text: str) -> str:
    if percent is None:
        return "--"
    suffix = ""
    text = (battery_text or "").upper()
    if "CHARG" in text:
        suffix = "C"
    elif "FULL" in text:
        suffix = "F"
    return f"{percent}%{suffix}"


def _status_message(status_text: str) -> str:
    status = status_text.strip().upper()
    if status == "RUNNING":
        return "SESSION LIVE"
    if status in {"DOWN", "FAILED"}:
        return "SERVICE DOWN"
    if status == "READY":
        return "WAITING FOR INPUT"
    return "STATUS UNKNOWN"


def _draw_eye_open(draw, center: tuple[int, int], radius: int) -> None:
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=0)
    pupil = max(1, radius // 2)
    draw.ellipse((x - pupil, y - pupil, x + pupil, y + pupil), fill=0)


def _draw_eye_line(draw, center: tuple[int, int], radius: int) -> None:
    x, y = center
    draw.line((x - radius, y, x + radius, y), fill=0)


def _draw_eye_cross(draw, center: tuple[int, int], radius: int) -> None:
    x, y = center
    draw.line((x - radius, y - radius, x + radius, y + radius), fill=0)
    draw.line((x - radius, y + radius, x + radius, y - radius), fill=0)


def _draw_mouth(draw, box, mood: str) -> None:
    x0, y0, x1, y1 = box
    if mood == "happy" or mood == "wink":
        draw.arc((x0, y0, x1, y1), 200, 340, fill=0)
    elif mood == "sad":
        draw.arc((x0, y0, x1, y1), 20, 160, fill=0)
    else:
        y = (y0 + y1) // 2
        draw.line((x0, y, x1, y), fill=0)


def _draw_face(draw, box, mood: str) -> None:
    x0, y0, x1, y1 = box
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)
    pad = max(2, int(min(width, height) * 0.06))
    head = (x0 + pad, y0 + pad, x1 - pad, y1 - pad)
    draw.ellipse(head, outline=0)

    center_x = (x0 + x1) // 2
    eye_y = y0 + int(height * 0.38)
    eye_dx = int(width * 0.22)
    eye_radius = max(2, int(min(width, height) * 0.11))

    left_eye = (center_x - eye_dx, eye_y)
    right_eye = (center_x + eye_dx, eye_y)

    if mood == "dead":
        _draw_eye_cross(draw, left_eye, eye_radius)
        _draw_eye_cross(draw, right_eye, eye_radius)
    elif mood == "sad":
        draw.arc(
            (
                left_eye[0] - eye_radius,
                left_eye[1] - eye_radius,
                left_eye[0] + eye_radius,
                left_eye[1] + eye_radius,
            ),
            20,
            160,
            fill=0,
        )
        draw.arc(
            (
                right_eye[0] - eye_radius,
                right_eye[1] - eye_radius,
                right_eye[0] + eye_radius,
                right_eye[1] + eye_radius,
            ),
            20,
            160,
            fill=0,
        )
    elif mood == "wink":
        _draw_eye_open(draw, left_eye, eye_radius)
        _draw_eye_line(draw, right_eye, eye_radius)
    else:
        _draw_eye_open(draw, left_eye, eye_radius)
        _draw_eye_open(draw, right_eye, eye_radius)

    mouth_width = int(width * 0.26)
    mouth_height = int(height * 0.12)
    mouth_x0 = center_x - mouth_width // 2
    mouth_y0 = y0 + int(height * 0.62)
    _draw_mouth(
        draw,
        (mouth_x0, mouth_y0, mouth_x0 + mouth_width, mouth_y0 + mouth_height),
        mood,
    )

    # keep the face clean for low-resolution e-ink


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
    mem: str,
    cpu: str,
    battery_percent: int | None,
    updated: str | None,
    config: RenderConfig,
):
    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError("Pillow is required for e-paper rendering.")

    image = Image.new("1", (config.width, config.height), 255)
    draw = ImageDraw.Draw(image)
    font_header = _load_font(config.font_path, max(9, config.font_size - 4))
    font_body = _load_font(config.font_path, max(10, config.font_size - 2))
    font_small = _load_font(config.font_path, max(8, config.font_size - 6))
    font_face = _load_font(config.font_path, max(18, config.font_size + 10))
    if font_body is None or font_header is None or font_small is None or font_face is None:
        raise RuntimeError("Pillow font unavailable.")

    margin = config.margin
    header_height = min(config.height, max(12, _text_height(font_header) + 2))
    footer_height = min(config.height, max(12, _text_height(font_header) + 2))

    draw.rectangle((0, 0, config.width - 1, config.height - 1), outline=0)
    draw.line((0, header_height, config.width - 1, header_height), fill=0)

    status_text = status.strip().upper() or "READY"
    wifi_state, wifi_ssid = _split_wifi_text(wifi)
    wifi_short = _short_wifi_state(wifi_state)
    uptime_text = uptime or "--"
    battery_short = _battery_short(battery_percent, battery)

    segments = [
        f"IP {ip}",
        f"WIFI {wifi_short}",
        f"BAT {battery_short}",
        f"UP {uptime_text}",
    ]
    weights = [1.6, 1.1, 0.9, 1.2]
    header_width = max(1, config.width - margin * 2)
    total_weight = sum(weights)
    col_widths = [int(header_width * w / total_weight) for w in weights]
    col_widths[-1] = header_width - sum(col_widths[:-1])
    header_text_y = max(0, (header_height - _text_height(font_header)) // 2)
    x = margin
    for segment, col_width in zip(segments, col_widths):
        text = _fit_text(draw, segment, font_header, col_width - 2)
        draw.text((x, header_text_y), text, font=font_header, fill=0)
        x += col_width

    footer_top = config.height - footer_height
    draw.line((0, footer_top, config.width - 1, footer_top), fill=0)

    footer_left = f"WIFI {wifi_ssid or _short_wifi_state(wifi_state)}"
    footer_right = f"LOAD {load or '--'}"
    footer_left_text = _fit_text(draw, footer_left, font_header, config.width - margin * 2)
    draw.text((margin, footer_top + 2), footer_left_text, font=font_header, fill=0)
    footer_right_text = _fit_text(draw, footer_right, font_header, config.width - margin * 2)
    right_width = _text_width(draw, footer_right_text, font_header)
    draw.text(
        (config.width - margin - right_width, footer_top + 2),
        footer_right_text,
        font=font_header,
        fill=0,
    )

    body_top = header_height + 2
    body_bottom = footer_top - 2
    content_width = config.width - margin * 2
    gap = 6
    right_width = max(90, int(content_width * 0.38))
    left_width = content_width - right_width - gap
    if left_width < 80:
        left_width = 80
        right_width = max(60, content_width - left_width - gap)

    left_x0 = margin
    left_x1 = left_x0 + left_width
    right_x0 = left_x1 + gap
    right_x1 = right_x0 + right_width

    row1_y = body_top
    name_text = _fit_text(draw, "zeroterm>", font_body, left_width - 4)
    draw.text((left_x0, row1_y), name_text, font=font_body, fill=0)

    status_line = _fit_text(draw, _status_message(status_text), font_body, right_width - 4)
    draw.text((right_x0, row1_y), status_line, font=font_body, fill=0)

    row1_height = _text_height(font_body) + 2

    label_height = _text_height(font_small)
    bar_height = max(6, label_height // 2 + 2)
    battery_block = label_height + bar_height + 6
    face_top = row1_y + row1_height + 2

    face_box = (
        left_x0 + 2,
        face_top,
        left_x1 - 2,
        body_bottom - battery_block - 4,
    )
    face_text = _pick_face(status_text, battery_percent)
    if face_box[2] > face_box[0] and face_box[3] > face_box[1]:
        face_text = _fit_text(draw, face_text, font_face, face_box[2] - face_box[0] - 4)
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

    message_x = right_x0
    message_y = face_top
    state_line = _fit_text(draw, f"STATE {status_text}", font_small, right_width - 4)
    draw.text((message_x, message_y), state_line, font=font_small, fill=0)
    message_y += _text_height(font_small) + 2
    ssid_line = _fit_text(draw, f"SSID {wifi_ssid or '--'}", font_small, right_width - 4)
    draw.text((message_x, message_y), ssid_line, font=font_small, fill=0)
    message_y += _text_height(font_small) + 4

    metrics_top = body_bottom - (_text_height(font_body) + _text_height(font_small) + 6)
    if metrics_top < message_y:
        metrics_top = message_y
    metric_labels = [("MEM", mem), ("CPU", cpu), ("TMP", temp)]
    columns = 3
    inner_width = right_width - 8
    col_width = max(1, inner_width // columns)
    for index, (label, value) in enumerate(metric_labels):
        x0 = right_x0 + 4 + index * col_width
        x1 = x0 + col_width
        _center_text(draw, label, font_small, (x0, metrics_top, x1, metrics_top + _text_height(font_small)), fill=0)
        _center_text(
            draw,
            value or "--",
            font_body,
            (
                x0,
                metrics_top + _text_height(font_small) + 2,
                x1,
                metrics_top + _text_height(font_small) + 2 + _text_height(font_body),
            ),
            fill=0,
        )

    if updated:
        updated_text = _fit_text(draw, updated, font_small, config.width - margin * 2)
        updated_width = _text_width(draw, updated_text, font_small)
        updated_y = footer_top - 2 - _text_height(font_small)
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
        return "(T_T)"
    if status == "RUNNING":
        return "(^_^)"
    if status == "READY":
        return "(^_~)"
    return "(^_^)"
