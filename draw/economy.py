from __future__ import annotations

import os
import time
from typing import Iterable

from PIL import Image, ImageDraw

from .gradient_utils import create_vertical_gradient
from .styles import (
    COLOR_ACCENT,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_TEXT_DARK,
    COLOR_TEXT_GRAY,
    COLOR_TEXT_WHITE,
    load_font,
)
from .text_utils import wrap_text_by_width_optimized


def _line_count(text: str, font, width: int) -> int:
    return max(1, len(wrap_text_by_width_optimized(str(text), font, width)))


def draw_economy_panel(
    title: str,
    subtitle: str,
    sections: Iterable[dict],
    footer: str = "",
) -> Image.Image:
    """Draw a reusable shop, market, or exchange information panel."""
    width = 1000
    margin = 34
    card_width = width - margin * 2
    title_font = load_font(34)
    subtitle_font = load_font(18)
    section_font = load_font(24)
    primary_font = load_font(20)
    secondary_font = load_font(16)
    meta_font = load_font(15)
    content_width = card_width - 36

    normalized_sections = []
    height = 120
    for section in sections:
        rows = list(section.get("rows") or [])
        if not rows:
            continue
        section_height = 54
        for row in rows:
            section_height += 26 * _line_count(
                row.get("primary", ""), primary_font, content_width
            )
            if row.get("secondary"):
                section_height += 22 * _line_count(
                    row["secondary"], secondary_font, content_width
                )
            if row.get("meta"):
                section_height += 21 * _line_count(
                    row["meta"], meta_font, content_width
                )
            section_height += 18
        section_height += 12
        normalized_sections.append((section, rows, section_height))
        height += section_height + 18
    if footer:
        height += 54
    height = max(height, 280)

    image = create_vertical_gradient(
        width, height, (232, 244, 255), (248, 250, 255)
    )
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (0, 0, width, 92),
        radius=0,
        fill=COLOR_ACCENT,
    )
    draw.text((margin, 18), title, font=title_font, fill=COLOR_TEXT_WHITE)
    draw.text((margin, 65), subtitle, font=subtitle_font, fill=(225, 240, 255))

    y = 112
    for section, rows, section_height in normalized_sections:
        draw.rounded_rectangle(
            (margin, y, width - margin, y + section_height),
            radius=16,
            fill=COLOR_CARD_BG,
            outline=COLOR_CARD_BORDER,
            width=2,
        )
        draw.text(
            (margin + 18, y + 14),
            str(section.get("title", "")),
            font=section_font,
            fill=section.get("color", COLOR_ACCENT),
        )
        row_y = y + 52
        for row in rows:
            accent = row.get("accent", COLOR_ACCENT)
            draw.rounded_rectangle(
                (margin + 16, row_y + 3, margin + 22, row_y + 24),
                radius=3,
                fill=accent,
            )
            text_x = margin + 34
            for line in wrap_text_by_width_optimized(
                str(row.get("primary", "")), primary_font, content_width
            ):
                draw.text(
                    (text_x, row_y),
                    line,
                    font=primary_font,
                    fill=COLOR_TEXT_DARK,
                )
                row_y += 26
            if row.get("secondary"):
                for line in wrap_text_by_width_optimized(
                    str(row["secondary"]), secondary_font, content_width
                ):
                    draw.text(
                        (text_x, row_y),
                        line,
                        font=secondary_font,
                        fill=COLOR_TEXT_GRAY,
                    )
                    row_y += 22
            if row.get("meta"):
                for line in wrap_text_by_width_optimized(
                    str(row["meta"]), meta_font, content_width
                ):
                    draw.text(
                        (text_x, row_y),
                        line,
                        font=meta_font,
                        fill=accent,
                    )
                    row_y += 21
            row_y += 18
        y += section_height + 18

    if footer:
        draw.text(
            (margin, height - 36),
            footer,
            font=meta_font,
            fill=COLOR_TEXT_GRAY,
        )
    return image


def save_economy_image(
    image: Image.Image,
    prefix: str,
    data_dir: str,
) -> str:
    temp_dir = os.path.join(data_dir, "temp_images")
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, f"{prefix}_{int(time.time() * 1000)}.png")
    image.save(path, "PNG")
    return path
