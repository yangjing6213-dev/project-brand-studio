"""Deterministic text measurement and fitting for BrandLoom."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import ImageFont


class TextOverflowError(ValueError):
    """Raised when text cannot fit a template slot at its minimum size."""


@dataclass(frozen=True)
class TextLayout:
    lines: tuple[str, ...]
    font_size: int
    bbox: tuple[int, int, int, int]
    line_height: int


def _font(font_path: Path | str | ImageFont.FreeTypeFont, size: int):
    if isinstance(font_path, (str, Path)):
        return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.truetype(font_path.path, size=size) if hasattr(font_path, "path") else font_path.font_variant(size=size)


def _wrap(text: str, font, width: int) -> tuple[str, ...]:
    lines: list[str] = []
    for explicit in str(text).split("\n"):
        words = explicit.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if current and font.getlength(candidate) > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return tuple(lines)


def fit_text_box(
    text: str,
    box: tuple[int, int] | tuple[int, int, int, int],
    font_path: Path | str | ImageFont.FreeTypeFont,
    *,
    max_font_size: int = 176,
    min_font_size: int = 24,
    spacing: int = 8,
) -> TextLayout:
    """Fit text from max to min size while preserving explicit line breaks."""
    width, height = (box[-2], box[-1]) if len(box) == 4 else box
    if width <= 0 or height <= 0:
        raise ValueError("text box dimensions must be positive")
    for size in range(int(max_font_size), int(min_font_size) - 1, -1):
        font = _font(font_path, size)
        lines = _wrap(text, font, width)
        bbox = font.getbbox("Ag")
        line_height = max(1, bbox[3] - bbox[1])
        multiline_bbox = font.getbbox("\n".join(lines))
        measured = (0, 0, 0, line_height * len(lines) + spacing * (len(lines) - 1))
        max_line = max((font.getlength(line) for line in lines), default=0)
        if max_line <= width and measured[3] <= height:
            return TextLayout(lines, size, (0, 0, int(round(max_line)), int(measured[3])), line_height)
    raise TextOverflowError(f"text does not fit box {width}x{height} at minimum font size {min_font_size}")
