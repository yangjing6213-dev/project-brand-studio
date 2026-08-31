"""Deterministic Pillow renderer for BrandLoom templates."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping

from PIL import Image, ImageColor, ImageDraw, ImageFont

from .layout import TextLayout, TextOverflowError, fit_text_box
from .models import BrandBrief


class BrandIntegrityError(ValueError):
    """Raised when a render input violates the BrandLoom contract."""


@dataclass(frozen=True)
class RenderResult:
    output_path: Path
    width: int
    height: int
    source_hashes: dict[str, str]
    logo_size: tuple[int, int] = (0, 0)
    template_id: str = ""


def load_template(path: Path) -> dict[str, object]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BrandIntegrityError(f"invalid template: {source}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
        raise BrandIntegrityError("template schema_version must be 1.0")
    canvas = payload.get("canvas")
    slots = payload.get("slots")
    if not isinstance(canvas, dict) or not isinstance(slots, dict):
        raise BrandIntegrityError("template requires canvas and slots")
    if not all(isinstance(canvas.get(k), int) and canvas[k] > 0 for k in ("width", "height")):
        raise BrandIntegrityError("canvas width and height must be positive integers")
    return payload


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image(value: Path | Image.Image) -> tuple[Image.Image, str | None]:
    if isinstance(value, Image.Image):
        return value.convert("RGBA"), None
    path = Path(value)
    if not path.is_file():
        raise BrandIntegrityError(f"image does not exist: {path}")
    with Image.open(path) as source:
        return source.convert("RGBA"), _sha(path)


def _fit(image: Image.Image, width: int, height: int) -> tuple[Image.Image, tuple[int, int]]:
    scale = min(width / image.width, height / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS), size


def _slot(payload: Mapping[str, object], name: str) -> dict[str, int]:
    slot = payload.get(name)
    if not isinstance(slot, dict):
        raise BrandIntegrityError(f"template slot missing: {name}")
    return slot  # type: ignore[return-value]


def _copy(brief: BrandBrief | Mapping[str, object]) -> Mapping[str, object]:
    if isinstance(brief, BrandBrief):
        return brief.copy
    value = brief.get("copy", {})
    return value if isinstance(value, Mapping) else {}


def render_brand_asset(
    template_path: Path,
    brief: BrandBrief | Mapping[str, object],
    *,
    base_image: Path | Image.Image,
    asset_paths: Mapping[str, Path | Image.Image],
    font_paths: Mapping[str, Path | str],
    output_dir: Path,
) -> RenderResult:
    template = load_template(template_path)
    canvas = template["canvas"]
    assert isinstance(canvas, dict)
    width, height = int(canvas["width"]), int(canvas["height"])
    background, base_hash = _image(base_image)
    if background.size != (width, height):
        background = background.resize((width, height), Image.Resampling.LANCZOS)
    output = background.convert("RGBA")
    hashes: dict[str, str] = {}
    template_file = Path(template_path)
    if template_file.is_file():
        hashes["template"] = _sha(template_file)
    if base_hash:
        hashes["base_image"] = base_hash
    logo_size = (0, 0)
    if "company_logo" in asset_paths:
        logo, digest = _image(asset_paths["company_logo"])
        if digest:
            hashes["company_logo"] = digest
        slot = _slot(template["slots"], "company_logo")  # type: ignore[arg-type]
        fitted, logo_size = _fit(logo, int(slot["w"]), int(slot["h"]))
        x = int(slot["x"]) + (int(slot["w"]) - fitted.width) // 2
        y = int(slot["y"]) + (int(slot["h"]) - fitted.height) // 2
        output.alpha_composite(fitted, (x, y))
    marks = asset_paths.get("project_mark")
    if marks is not None:
        mark, digest = _image(marks)
        if digest:
            hashes["project_mark"] = digest
        slot = _slot(template["slots"], "project_mark")  # type: ignore[arg-type]
        fitted, _ = _fit(mark, int(slot["w"]), int(slot["h"]))
        x = int(slot["x"]) + (int(slot["w"]) - fitted.width) // 2
        y = int(slot["y"]) + (int(slot["h"]) - fitted.height) // 2
        output.alpha_composite(fitted, (x, y))
    copy = _copy(brief)
    draw = ImageDraw.Draw(output)
    foreground = "#111111"
    if isinstance(brief, BrandBrief):
        foreground = str(brief.style.get("foreground", foreground))
    elif isinstance(brief, Mapping) and isinstance(brief.get("style"), Mapping):
        foreground = str(brief["style"].get("foreground", foreground))
    try:
        fill = ImageColor.getrgb(foreground)
    except ValueError as exc:
        raise BrandIntegrityError(f"invalid foreground color: {foreground}") from exc
    for key, role in (("title", "heading"), ("subtitle", "body")):
        value = copy.get(key)
        if not value:
            continue
        slot = _slot(template["slots"], key)  # type: ignore[arg-type]
        font_path = font_paths.get(role) or font_paths.get("heading")
        if font_path is None:
            raise BrandIntegrityError(f"font path missing for {role}")
        if isinstance(font_path, (str, Path)) and Path(font_path).is_file():
            hashes.setdefault(f"font_{role}", _sha(Path(font_path)))
        layout = fit_text_box(
            str(value),
            (int(slot["w"]), int(slot["h"])),
            font_path,
            max_font_size=int(slot.get("max_font_size", 176)),
            min_font_size=int(slot.get("min_font_size", 24)),
        )
        font = ImageFont.truetype(str(font_path), layout.font_size)
        draw.multiline_text((int(slot["x"]), int(slot["y"])), "\n".join(layout.lines), font=font, fill=fill, spacing=8)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(template_path).stem
    destination = output_dir / f"{stem}.png"
    version = 2
    while destination.exists():
        destination = output_dir / f"{stem}-v{version:02d}.png"
        version += 1
    output = output.convert("RGBA")
    output.save(destination, format="PNG")
    return RenderResult(destination, width, height, hashes, logo_size, stem)
