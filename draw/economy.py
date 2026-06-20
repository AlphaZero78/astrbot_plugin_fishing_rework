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


def _smooth_curve(
    points: list[tuple[int, int]],
    tension: float = 0.4,
    samples_per_segment: int = 16,
) -> list[tuple[float, float]]:
    """Approximate Chart.js-style tension with a cubic Hermite spline."""
    if len(points) < 3:
        return [(float(x), float(y)) for x, y in points]
    curve: list[tuple[float, float]] = []
    for index in range(len(points) - 1):
        p0 = points[max(index - 1, 0)]
        p1 = points[index]
        p2 = points[index + 1]
        p3 = points[min(index + 2, len(points) - 1)]
        tangent1 = (
            (p2[0] - p0[0]) * tension,
            (p2[1] - p0[1]) * tension,
        )
        tangent2 = (
            (p3[0] - p1[0]) * tension,
            (p3[1] - p1[1]) * tension,
        )
        for sample in range(samples_per_segment):
            t = sample / samples_per_segment
            t2 = t * t
            t3 = t2 * t
            h00 = 2 * t3 - 3 * t2 + 1
            h10 = t3 - 2 * t2 + t
            h01 = -2 * t3 + 3 * t2
            h11 = t3 - t2
            curve.append(
                (
                    h00 * p1[0]
                    + h10 * tangent1[0]
                    + h01 * p2[0]
                    + h11 * tangent2[0],
                    h00 * p1[1]
                    + h10 * tangent1[1]
                    + h01 * p2[1]
                    + h11 * tangent2[1],
                )
            )
    curve.append((float(points[-1][0]), float(points[-1][1])))
    return curve


def _draw_line_chart(
    image: Image.Image,
    bounds: tuple[int, int, int, int],
    chart: dict,
) -> None:
    x0, y0, x1, y1 = bounds
    scale = 3
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)
    chart_image = Image.new(
        "RGB",
        (width * scale, height * scale),
        COLOR_CARD_BG,
    )
    draw = ImageDraw.Draw(chart_image)
    title_font = load_font(17 * scale)
    label_font = load_font(12 * scale)
    tick_font = load_font(11 * scale)

    def point(x: float, y: float) -> tuple[int, int]:
        return int(x * scale), int(y * scale)

    series = [
        item
        for item in chart.get("series", [])
        if len(item.get("values") or []) >= 2
    ]
    draw.text(
        point(0, 0),
        str(chart.get("title", "价格趋势")),
        font=title_font,
        fill=COLOR_TEXT_DARK,
    )
    if not series:
        draw.text(
            point(0, 42),
            "暂无足够历史数据",
            font=label_font,
            fill=COLOR_TEXT_GRAY,
        )
        image.paste(
            chart_image.resize((width, height), Image.Resampling.LANCZOS),
            (x0, y0),
        )
        return

    legend_x = 0
    legend_y = 29
    for item in series:
        color = tuple(item.get("color", COLOR_ACCENT))
        draw.line(
            (*point(legend_x, legend_y + 7), *point(legend_x + 18, legend_y + 7)),
            fill=color,
            width=3 * scale,
        )
        draw.text(
            point(legend_x + 24, legend_y),
            str(item.get("name", "")),
            font=label_font,
            fill=COLOR_TEXT_GRAY,
        )
        legend_x += 105

    plot_left = 56
    plot_top = 58
    plot_right = width - 8
    plot_bottom = height - 30
    if plot_right <= plot_left or plot_bottom <= plot_top:
        return

    values = [float(value) for item in series for value in item["values"]]
    minimum = min(values)
    maximum = max(values)
    if maximum == minimum:
        padding = max(abs(maximum) * 0.05, 1)
    else:
        padding = (maximum - minimum) * 0.12
    minimum -= padding
    maximum += padding
    value_range = maximum - minimum

    grid_color = (225, 231, 240)
    for index in range(5):
        ratio = index / 4
        y = int(plot_top + (plot_bottom - plot_top) * ratio)
        draw.line(
            (*point(plot_left, y), *point(plot_right, y)),
            fill=grid_color,
            width=scale,
        )
        tick_value = maximum - value_range * ratio
        draw.text(
            point(0, y - 7),
            f"{int(round(tick_value)):,}",
            font=tick_font,
            fill=COLOR_TEXT_GRAY,
        )

    labels = list(chart.get("labels") or [])
    max_points = max(len(item["values"]) for item in series)
    for item in series:
        item_values = [float(value) for value in item["values"]]
        point_count = len(item_values)
        points = []
        for index, value in enumerate(item_values):
            x_ratio = index / max(point_count - 1, 1)
            y_ratio = (maximum - value) / value_range
            points.append(
                (
                    int(plot_left + (plot_right - plot_left) * x_ratio),
                    int(plot_top + (plot_bottom - plot_top) * y_ratio),
                )
            )
        color = tuple(item.get("color", COLOR_ACCENT))
        scaled_curve = [
            point(x, y) for x, y in _smooth_curve(points, tension=0.4)
        ]
        draw.line(
            scaled_curve,
            fill=color,
            width=3 * scale,
            joint="curve",
        )
        for x, y in points:
            draw.ellipse(
                (*point(x - 4, y - 4), *point(x + 4, y + 4)),
                fill=color,
                outline=color,
                width=2 * scale,
            )

    if labels:
        first_label = str(labels[0])
        middle_label = str(labels[(len(labels) - 1) // 2])
        last_label = str(labels[min(len(labels), max_points) - 1])
        draw.text(
            point(plot_left, plot_bottom + 8),
            first_label,
            font=tick_font,
            fill=COLOR_TEXT_GRAY,
        )
        middle_width = draw.textbbox(
            (0, 0), middle_label, font=tick_font
        )[2]
        draw.text(
            (
                int((plot_left + plot_right) * scale / 2 - middle_width / 2),
                int((plot_bottom + 8) * scale),
            ),
            middle_label,
            font=tick_font,
            fill=COLOR_TEXT_GRAY,
        )
        last_width = draw.textbbox((0, 0), last_label, font=tick_font)[2]
        draw.text(
            (int(plot_right * scale - last_width), int((plot_bottom + 8) * scale)),
            last_label,
            font=tick_font,
            fill=COLOR_TEXT_GRAY,
        )
    image.paste(
        chart_image.resize((width, height), Image.Resampling.LANCZOS),
        (x0, y0),
    )


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
        chart = section.get("chart")
        row_content_width = 350 if chart else content_width
        section_height = 54
        for row in rows:
            section_height += 26 * _line_count(
                row.get("primary", ""), primary_font, row_content_width
            )
            if row.get("secondary"):
                section_height += 22 * _line_count(
                    row["secondary"], secondary_font, row_content_width
                )
            if row.get("meta"):
                section_height += 21 * _line_count(
                    row["meta"], meta_font, row_content_width
                )
            section_height += 18
        section_height += 12
        if chart:
            section_height = max(section_height, 326)
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
        chart = section.get("chart")
        row_content_width = 350 if chart else content_width
        for row in rows:
            accent = row.get("accent", COLOR_ACCENT)
            draw.rounded_rectangle(
                (margin + 16, row_y + 3, margin + 22, row_y + 24),
                radius=3,
                fill=accent,
            )
            text_x = margin + 34
            for line in wrap_text_by_width_optimized(
                str(row.get("primary", "")), primary_font, row_content_width
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
                    str(row["secondary"]), secondary_font, row_content_width
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
                    str(row["meta"]), meta_font, row_content_width
                ):
                    draw.text(
                        (text_x, row_y),
                        line,
                        font=meta_font,
                        fill=accent,
                    )
                    row_y += 21
            row_y += 18
        if chart:
            divider_x = margin + 396
            draw.line(
                (divider_x, y + 54, divider_x, y + section_height - 18),
                fill=COLOR_CARD_BORDER,
                width=2,
            )
            _draw_line_chart(
                image,
                (
                    divider_x + 20,
                    y + 58,
                    width - margin - 18,
                    y + section_height - 18,
                ),
                chart,
            )
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
