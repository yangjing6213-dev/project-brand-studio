"""Deterministic Pillow renderer for BrandLoom templates."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Mapping

from PIL import Image, ImageCms, ImageColor, ImageDraw, ImageFont

from .fonts import missing_glyphs
from .layout import TextLayout, TextOverflowError, fit_text_box
from .models import BrandBrief
from .treatments import canonicalize_logo_treatment, operation_for_treatment


def _asset_operation_forbidden(path: Path, operation: str) -> bool:
    """Read adjacent machine-readable operation policy for packaged assets."""
    candidates = (path.with_name(f"{path.stem}.provenance.json"), path.with_name("provenance.json"))
    for metadata in candidates:
        if not metadata.is_file():
            continue
        try:
            payload = json.loads(metadata.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        forbidden = payload.get("forbidden_operations", ())
        return isinstance(forbidden, (list, tuple)) and operation in forbidden
    return False


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
    rendered_copy: dict[str, object] = field(default_factory=dict)
    logo_treatment: str = "default"


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


def _apply_logo_treatment(image: Image.Image, treatment: str) -> Image.Image:
    if treatment == "default":
        return image
    if treatment != "monochrome-black":
        raise BrandIntegrityError(f"unsupported company logo treatment: {treatment}")
    # Keep the source alpha channel (and therefore its geometry) byte-for-byte;
    # only replace visible RGB channels at composition time.
    alpha = image.getchannel("A")
    black = Image.new("RGBA", image.size, (0, 0, 0, 0))
    black.putalpha(alpha)
    return black


def _selected_logo_treatment(brief: BrandBrief | Mapping[str, object], explicit: str | None) -> str:
    if explicit is not None:
        selected = explicit
    elif isinstance(brief, BrandBrief):
        selected = brief.assets.get("company_logo_treatment", brief.assets.get("logo_treatment", "default"))
    else:
        assets = brief.get("assets", {})
        selected = assets.get("company_logo_treatment", assets.get("logo_treatment", "default")) if isinstance(assets, Mapping) else "default"
    try:
        return canonicalize_logo_treatment(selected)
    except ValueError as exc:
        raise BrandIntegrityError(str(exc)) from exc


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


_RENDERED_COPY_FIELDS = ("title", "subtitle", "value_line", "features")
_COPY_METADATA_FIELDS = {"language", "direction"}


def rendered_copy_values(brief: BrandBrief | Mapping[str, object]) -> dict[str, object]:
    copy = _copy(brief)
    for key, value in copy.items():
        if key in _RENDERED_COPY_FIELDS or key in _COPY_METADATA_FIELDS:
            continue
        if value not in (None, "", (), [], {}):
            raise BrandIntegrityError(f"unsupported non-empty copy field: {key}")
    rendered: dict[str, object] = {}
    for key in _RENDERED_COPY_FIELDS:
        value = copy.get(key)
        if value in (None, "", (), []):
            continue
        if key == "features":
            if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
                raise BrandIntegrityError("copy.features must be a list of strings")
            rendered[key] = list(value)
        elif not isinstance(value, str):
            raise BrandIntegrityError(f"copy.{key} must be a string")
        else:
            rendered[key] = value
    return rendered


def render_brand_asset(
    template_path: Path,
    brief: BrandBrief | Mapping[str, object],
    *,
    base_image: Path | Image.Image,
    asset_paths: Mapping[str, Path | Image.Image],
    font_paths: Mapping[str, Path | str],
    output_dir: Path,
    logo_treatment: str | None = None,
    confirmed_treatment: str | None = None,
) -> RenderResult:
    template = load_template(template_path)
    canvas = template["canvas"]
    assert isinstance(canvas, dict)
    width, height = int(canvas["width"]), int(canvas["height"])
    background, base_hash = _image(base_image)
    if background.size != (width, height):
        raise BrandIntegrityError(
            f"base image dimensions {background.size} do not match template canvas {(width, height)}"
        )
    output = background.convert("RGBA")
    selected_treatment = _selected_logo_treatment(brief, logo_treatment)
    if selected_treatment != "default":
        if confirmed_treatment is None:
            raise BrandIntegrityError("company logo treatment requires exact affirmative confirmation")
        try:
            confirmed = canonicalize_logo_treatment(confirmed_treatment)
        except ValueError as exc:
            raise BrandIntegrityError(str(exc)) from exc
        if confirmed != selected_treatment:
            raise BrandIntegrityError("company logo treatment is not affirmatively confirmed")
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
        if selected_treatment == "monochrome-black" and isinstance(asset_paths["company_logo"], (str, Path)) and _asset_operation_forbidden(Path(asset_paths["company_logo"]), operation_for_treatment(selected_treatment)):
            raise BrandIntegrityError("company logo asset forbids recolor_monochrome")
        logo = _apply_logo_treatment(logo, selected_treatment)
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
    rendered_copy = rendered_copy_values(brief)
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
    for key, role in (("title", "heading"), ("subtitle", "body"), ("value_line", "body"), ("features", "body")):
        value = rendered_copy.get(key)
        if not value:
            continue
        slot = _slot(template["slots"], key)  # type: ignore[arg-type]
        font_path = font_paths.get(role)
        if font_path is None:
            raise BrandIntegrityError(f"font path missing for {role}")
        if isinstance(font_path, (str, Path)) and Path(font_path).is_file():
            hashes.setdefault(f"font_{role}", _sha(Path(font_path)))
        text = "\n".join(f"• {item}" for item in value) if key == "features" else str(value)
        missing = missing_glyphs(font_path, text)
        if missing:
            chars = " ".join(repr(char) for char in missing)
            raise BrandIntegrityError(f"confirmed {role} font cannot render copy characters: {chars}; select a font that supports these characters")
        layout = fit_text_box(
            text,
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
    version = 1
    destination = output_dir / f"{stem}-v{version:02d}.png"
    while destination.exists():
        version += 1
        destination = output_dir / f"{stem}-v{version:02d}.png"
    output = output.convert("RGBA")
    srgb_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    output.save(destination, format="PNG", icc_profile=srgb_profile)
    return RenderResult(destination, width, height, hashes, logo_size, stem, rendered_copy, selected_treatment)
