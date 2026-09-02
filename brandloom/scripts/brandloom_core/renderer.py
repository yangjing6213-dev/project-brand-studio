"""Deterministic Pillow renderer for BrandLoom templates."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Mapping

from PIL import Image, ImageCms, ImageColor, ImageDraw, ImageFilter, ImageFont

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


def _text_spacing(slot: Mapping[str, object]) -> int:
    """Return deterministic multiline spacing for a text slot."""
    value = slot.get("line_spacing", 8)
    try:
        spacing = int(value)
    except (TypeError, ValueError):
        spacing = 8
    return max(0, spacing)


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


def _rgba(value: object, default: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Parse a template RGBA list while keeping overlay rendering fail-closed."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return default
    try:
        channels = tuple(max(0, min(255, int(channel))) for channel in value)
    except (TypeError, ValueError):
        return default
    return channels  # type: ignore[return-value]


def _overlay_box(config: Mapping[str, object]) -> tuple[int, int, int, int] | None:
    try:
        x, y = int(config["x"]), int(config["y"])
        width, height = int(config["w"]), int(config["h"])
    except (KeyError, TypeError, ValueError):
        return None
    if width <= 0 or height <= 0 or x < 0 or y < 0:
        return None
    return x, y, width, height


def _draw_text_backdrop(output: Image.Image, config: Mapping[str, object]) -> None:
    box = _overlay_box(config)
    if box is None:
        return
    x, y, width, height = box
    if x + width > output.width or y + height > output.height:
        return
    radius = max(0, int(config.get("radius", 0)))
    blur_radius = max(0, int(config.get("blur_radius", 0)))
    tint = _rgba(config.get("tint"), (3, 10, 25, 178))
    if "opacity" in config:
        try:
            opacity = max(0.0, min(1.0, float(config["opacity"])))
            tint = (tint[0], tint[1], tint[2], round(opacity * 255))
        except (TypeError, ValueError):
            pass

    region = output.crop((x, y, x + width, y + height)).convert("RGBA")
    if blur_radius:
        region = region.filter(ImageFilter.GaussianBlur(blur_radius))
    region = Image.alpha_composite(region, Image.new("RGBA", region.size, tint))
    mask = Image.new("L", region.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    output.paste(region, (x, y), mask)
    if "border" in config:
        border = _rgba(config.get("border"), (55, 145, 255, 105))
        ImageDraw.Draw(output).rounded_rectangle(
            (x, y, x + width - 1, y + height - 1), radius=radius, outline=border, width=2
        )


def _centered_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    bounds = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    draw.text(
        (left + (right - left - text_width) / 2, top + (bottom - top - text_height) / 2 - bounds[1]),
        text,
        font=font,
        fill=fill,
    )


def _draw_step_icon(draw: ImageDraw.ImageDraw, center: tuple[int, int], index: int, color: tuple[int, int, int, int], scale: float = 1.0) -> None:
    """Draw a small geometric stage icon without relying on an external icon font."""
    cx, cy = center
    def s(value: float) -> int:
        return max(1, round(value * scale))
    if index == 0:  # inspect / analyze
        draw.ellipse((cx - s(10), cy - s(10), cx + s(6), cy + s(6)), outline=color, width=s(3))
        draw.line((cx + s(4), cy + s(4), cx + s(13), cy + s(13)), fill=color, width=s(3))
    elif index == 1:  # confirm
        draw.ellipse((cx - s(12), cy - s(12), cx + s(12), cy + s(12)), outline=color, width=s(3))
        draw.line((cx - s(6), cy, cx - s(1), cy + s(6)), fill=color, width=s(3))
        draw.line((cx - s(1), cy + s(6), cx + s(8), cy - s(6)), fill=color, width=s(3))
    elif index == 2:  # generate / spark
        draw.polygon(((cx, cy - s(14)), (cx + s(5), cy - s(5)), (cx + s(14), cy), (cx + s(5), cy + s(5)), (cx, cy + s(14)), (cx - s(5), cy + s(5)), (cx - s(14), cy), (cx - s(5), cy - s(5))), outline=color)
        draw.line((cx, cy - s(9), cx, cy + s(9)), fill=color, width=s(2))
        draw.line((cx - s(9), cy, cx + s(9), cy), fill=color, width=s(2))
    else:  # deliver / package
        draw.rectangle((cx - s(12), cy - s(8), cx + s(12), cy + s(11)), outline=color, width=s(3))
        draw.line([(cx - s(12), cy - s(2)), (cx, cy + s(5)), (cx + s(12), cy - s(2))], fill=color, width=s(2))
        draw.line((cx, cy - s(8), cx, cy + s(5)), fill=color, width=s(2))


def _fit_overlay_font(font_path: Path | str, text: str, *, max_size: int, min_size: int, max_width: int) -> ImageFont.FreeTypeFont:
    """Choose the largest font that remains inside an inset workflow text box."""
    for size in range(max_size, min_size - 1, -1):
        try:
            font = ImageFont.truetype(str(font_path), size=size)
        except OSError:
            break
        bounds = font.getbbox(text)
        if bounds[2] - bounds[0] <= max_width:
            return font
    return ImageFont.truetype(str(font_path), size=min_size)


def _draw_workflow_diagram(
    output: Image.Image,
    config: Mapping[str, object],
    *,
    font_paths: Mapping[str, Path | str],
    language: str,
) -> None:
    """Draw a crisp, transparent workflow occupying the right side of a cover."""
    box = _overlay_box(config)
    steps = config.get("steps")
    if box is None or not isinstance(steps, list) or len(steps) < 2:
        return
    x, y, width, height = box
    if x + width > output.width or y + height > output.height:
        return
    try:
        blur_radius = max(0, int(config.get("blur_radius", 0)))
    except (TypeError, ValueError):
        blur_radius = 0
    if blur_radius:
        return
    heading_path = font_paths.get("heading") or font_paths.get("body")
    body_path = font_paths.get("body") or heading_path
    if heading_path is None or body_path is None:
        return
    try:
        render_scale = max(0.25, float(config.get("render_scale", 1.0)))
    except (TypeError, ValueError, OverflowError):
        render_scale = 1.0
    def s(value: float) -> int:
        return max(1, round(value * render_scale))
    try:
        node_gap = max(12, int(config.get("node_gap", 20)))
        node_height = max(96, int(config.get("node_height", 142)))
        inner_padding = max(16, int(config.get("inner_padding", 24)))
    except (TypeError, ValueError):
        node_gap, node_height, inner_padding = 20, 142, 24
    try:
        node_blur_radius = max(0, min(64, int(config.get("node_blur_radius", 0))))
        node_transparency = float(config.get("node_blur_transparency", 1.0))
        node_alpha = round(255 - 255 * node_transparency) if 0 <= node_transparency <= 1 else 0
    except (TypeError, ValueError, OverflowError):
        node_blur_radius, node_alpha = 0, 0

    normalized_steps: list[str] = []
    step_details: list[str] = []
    for step in steps[:4]:
        if not isinstance(step, Mapping):
            continue
        key = "zh" if language.startswith("zh") else "en"
        value = step.get(key, step.get("en", step.get("zh", "")))
        if isinstance(value, str) and value.strip():
            normalized_steps.append(value.strip())
            detail_key = "detail_zh" if language.startswith("zh") else "detail_en"
            detail = step.get(detail_key, "")
            step_details.append(str(detail).strip() if isinstance(detail, str) else "")
    if len(normalized_steps) < 2:
        return

    total_nodes_height = node_height * len(normalized_steps) + node_gap * (len(normalized_steps) - 1)
    heading_height = s(98)
    if total_nodes_height + heading_height > height:
        node_height = max(84, (height - heading_height - node_gap * (len(normalized_steps) - 1)) // len(normalized_steps))
        total_nodes_height = node_height * len(normalized_steps) + node_gap * (len(normalized_steps) - 1)
    if total_nodes_height + heading_height > height:
        return

    accent = _rgba(config.get("accent"), (56, 193, 255, 255))
    secondary = _rgba(config.get("secondary"), (126, 112, 239, 255))
    node_colors = (accent, (43, 130, 235, 255), secondary, (236, 178, 63, 255))
    # Draw on a transparent layer so there is no opaque workflow background.
    layer = Image.new("RGBA", output.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    title = "工作流程" if language.startswith("zh") else "HOW IT WORKS"
    detail_title = "从想法到可用素材" if language.startswith("zh") else "From idea to usable visuals"
    title_font = _fit_overlay_font(heading_path, title, max_size=s(36), min_size=s(26), max_width=width - inner_padding * 2)
    subtitle_font = _fit_overlay_font(body_path, detail_title, max_size=s(20), min_size=s(14), max_width=width - inner_padding * 2)
    draw.text((x + inner_padding, y + s(4)), title, font=title_font, fill=(245, 250, 255, 255))
    draw.text((x + inner_padding, y + s(47)), detail_title, font=subtitle_font, fill=(163, 201, 235, 255))
    draw.line((x + inner_padding, y + s(77), x + width - inner_padding, y + s(77)), fill=(95, 164, 231, 210), width=s(2))

    try:
        corner_radius = max(0, s(float(config.get("node_corner_radius", 16))))
        border_width = max(1, s(float(config.get("node_border_width", 2))))
    except (TypeError, ValueError, OverflowError):
        corner_radius, border_width = s(16), s(2)

    node_x = x + inner_padding
    node_w = width - inner_padding * 2
    node_y = y + heading_height
    for index, label in enumerate(normalized_steps):
        top = node_y + index * (node_height + node_gap)
        bottom = top + node_height
        if node_blur_radius and node_alpha:
            # Only soften the underlying scene; foreground is composited last.
            interior = (node_x + border_width, top + border_width, node_x + node_w - border_width, bottom - border_width)
            region = output.crop(interior).filter(ImageFilter.GaussianBlur(node_blur_radius))
            mask = Image.new("L", region.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, region.width - 1, region.height - 1), radius=max(0, corner_radius - border_width), fill=node_alpha,
            )
            output.paste(region, interior[:2], mask)
        color = node_colors[index % len(node_colors)]
        if index:
            connector_x = node_x + s(34)
            previous_bottom = top - node_gap
            draw.line((connector_x, previous_bottom + s(2), connector_x, top - s(10)), fill=color, width=s(4))
            draw.polygon(((connector_x, top - s(2)), (connector_x - s(9), top - s(15)), (connector_x + s(9), top - s(15))), fill=color)
        # Draw the crisp inset stroke above the optional local backdrop.
        draw.rounded_rectangle((node_x, top, node_x + node_w, bottom), radius=corner_radius, outline=color, width=border_width)
        draw.line((node_x + s(16), top + s(20), node_x + s(16), bottom - s(20)), fill=color, width=s(5))
        number_box = (node_x + s(28), top + s(24), node_x + s(70), top + s(66))
        draw.ellipse(number_box, fill=color)
        number_font = _fit_overlay_font(heading_path, str(index + 1), max_size=s(24), min_size=s(18), max_width=s(28))
        _centered_text(draw, number_box, str(index + 1), number_font, (5, 18, 42, 255))
        _draw_step_icon(draw, (node_x + s(104), top + node_height // 2), index, color, render_scale)
        content_left = node_x + s(142)
        content_right = node_x + node_w - inner_padding
        label_font = _fit_overlay_font(heading_path, label, max_size=s(30), min_size=s(19), max_width=content_right - content_left)
        detail = step_details[index] if index < len(step_details) else ""
        detail_font = _fit_overlay_font(body_path, detail, max_size=s(19), min_size=s(13), max_width=content_right - content_left)
        label_top = top + s(28)
        draw.text((content_left, label_top), label, font=label_font, fill=(245, 250, 255, 255))
        divider_y = top + node_height // 2 + s(8)
        draw.line((content_left, divider_y, content_right, divider_y), fill=(95, 164, 231, 165), width=s(1))
        if detail:
            draw.text((content_left, divider_y + s(14)), detail, font=detail_font, fill=(164, 201, 235, 255))
    output.alpha_composite(layer)


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
    overlays = template.get("overlays")
    if isinstance(overlays, Mapping):
        backdrop = overlays.get("text_backdrop")
        if isinstance(backdrop, Mapping):
            _draw_text_backdrop(output, backdrop)
        workflow = overlays.get("workflow_diagram")
        if isinstance(workflow, Mapping):
            language = str(_copy(brief).get("language", "en"))
            _draw_workflow_diagram(output, workflow, font_paths=font_paths, language=language)
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
        spacing = _text_spacing(slot)
        layout = fit_text_box(
            text,
            (int(slot["w"]), int(slot["h"])),
            font_path,
            max_font_size=int(slot.get("max_font_size", 176)),
            min_font_size=int(slot.get("min_font_size", 24)),
            spacing=spacing,
        )
        font = ImageFont.truetype(str(font_path), layout.font_size)
        draw.multiline_text((int(slot["x"]), int(slot["y"])), "\n".join(layout.lines), font=font, fill=fill, spacing=spacing)
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
