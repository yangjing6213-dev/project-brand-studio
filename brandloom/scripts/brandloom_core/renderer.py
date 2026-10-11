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
from .platform_outputs import same_aspect_ratio
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


def required_font_texts(
    brief: BrandBrief | Mapping[str, object],
    template: Mapping[str, object],
) -> dict[str, str]:
    """Return every displayed text string grouped by the font role that draws it."""
    rendered = rendered_copy_values(brief)
    heading: list[str] = []
    body: list[str] = []
    if rendered.get("title"):
        heading.append(str(rendered["title"]))
    for key in ("subtitle", "value_line"):
        if rendered.get(key):
            body.append(str(rendered[key]))
    features = rendered.get("features", ())
    if isinstance(features, (list, tuple)):
        body.extend(f"• {item}" for item in features)

    overlays = template.get("overlays", {})
    workflow = overlays.get("workflow_diagram") if isinstance(overlays, Mapping) else None
    if isinstance(workflow, Mapping):
        language = str(_copy(brief).get("language", "en"))
        key = "zh" if language.startswith("zh") else "en"
        detail_key = "detail_zh" if key == "zh" else "detail_en"
        steps = workflow.get("steps", ())
        labels: list[str] = []
        details: list[str] = []
        if isinstance(steps, list):
            for step in steps[:4]:
                if not isinstance(step, Mapping):
                    continue
                label = step.get(key, step.get("en", step.get("zh", "")))
                if isinstance(label, str) and label.strip():
                    labels.append(label.strip())
                    detail = step.get(detail_key, "")
                    details.append(detail.strip() if isinstance(detail, str) else "")
        if len(labels) >= 2:
            title = workflow.get("heading_zh" if key == "zh" else "heading_en")
            if not isinstance(title, str) or not title.strip():
                benefits_mode = workflow.get("workflow_mode") == "benefits"
                title = ("核心收益" if benefits_mode else "关键步骤") if key == "zh" else (
                    "KEY BENEFITS" if benefits_mode else "KEY STEPS"
                )
            heading.extend((title.strip(), *labels, *(str(index + 1) for index in range(len(labels)))))
            subtitle = workflow.get("subtitle_zh" if key == "zh" else "subtitle_en", "")
            if isinstance(subtitle, str) and subtitle.strip():
                body.append(subtitle.strip())
            body.extend(detail for detail in details if detail)
    result: dict[str, str] = {}
    if heading:
        result["heading"] = "\n".join(heading)
    if body:
        result["body"] = "\n".join(body)
    return result


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


def _draw_emphasized_title(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    lines: tuple[str, ...],
    font: ImageFont.FreeTypeFont,
    base_color,
    emphasis_color,
    emphasis_text: str,
    spacing: int = 8,
) -> None:
    full_text = "\n".join(lines)
    start = full_text.find(emphasis_text)
    if start < 0:
        raise BrandIntegrityError("confirmed title emphasis text is missing from the rendered title")
    end = start + len(emphasis_text)
    bounds = font.getbbox("Ag")
    line_height = max(1, bounds[3] - bounds[1])
    cursor = 0
    for index, line in enumerate(lines):
        line_start, line_end = cursor, cursor + len(line)
        overlap_start, overlap_end = max(start, line_start), min(end, line_end)
        line_y = y + index * (line_height + spacing)
        if overlap_start >= overlap_end:
            draw.text((x, line_y), line, font=font, fill=base_color)
        else:
            before = line[:overlap_start - line_start]
            highlighted = line[overlap_start - line_start:overlap_end - line_start]
            after = line[overlap_end - line_start:]
            draw.text((x, line_y), before, font=font, fill=base_color)
            highlighted_x = x + font.getlength(before)
            draw.text((highlighted_x, line_y), highlighted, font=font, fill=emphasis_color)
            draw.text((highlighted_x + font.getlength(highlighted), line_y), after, font=font, fill=base_color)
        cursor = line_end + 1

def _draw_step_icon(draw: ImageDraw.ImageDraw, center: tuple[int, int], index: int, color: tuple[int, int, int, int]) -> None:
    """Draw a small geometric stage icon without relying on an external icon font."""
    cx, cy = center
    if index == 0:  # inspect / analyze
        draw.ellipse((cx - 10, cy - 10, cx + 6, cy + 6), outline=color, width=3)
        draw.line((cx + 4, cy + 4, cx + 13, cy + 13), fill=color, width=3)
    elif index == 1:  # confirm
        draw.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), outline=color, width=3)
        draw.line((cx - 6, cy, cx - 1, cy + 6), fill=color, width=3)
        draw.line((cx - 1, cy + 6, cx + 8, cy - 6), fill=color, width=3)
    elif index == 2:  # generate / spark
        draw.polygon(((cx, cy - 14), (cx + 5, cy - 5), (cx + 14, cy), (cx + 5, cy + 5), (cx, cy + 14), (cx - 5, cy + 5), (cx - 14, cy), (cx - 5, cy - 5)), outline=color)
        draw.line((cx, cy - 9, cx, cy + 9), fill=color, width=2)
        draw.line((cx - 9, cy, cx + 9, cy), fill=color, width=2)
    else:  # deliver / package
        draw.rectangle((cx - 12, cy - 8, cx + 12, cy + 11), outline=color, width=3)
        draw.line([(cx - 12, cy - 2), (cx, cy + 5), (cx + 12, cy - 2)], fill=color, width=2)
        draw.line((cx, cy - 8, cx, cy + 5), fill=color, width=2)


def _fit_overlay_font(font_path: Path | str, text: str, *, max_size: int, min_size: int, max_width: int) -> ImageFont.FreeTypeFont:
    """Choose the largest font that remains inside an inset workflow text box."""
    for size in range(max_size, min_size - 1, -1):
        try:
            font = ImageFont.truetype(str(font_path), size=size)
        except OSError as exc:
            raise BrandIntegrityError(f"cannot read workflow font: {font_path}") from exc
        bounds = font.getbbox(text)
        if bounds[2] - bounds[0] <= max_width:
            return font
    raise BrandIntegrityError(f"workflow text does not fit available width {max_width}")


def _workflow_geometry(
    config: Mapping[str, object], *, width: int, height: int, step_count: int,
) -> tuple[int, int, int, int]:
    """Use confirmed geometry when it fits; otherwise adapt cards to the target canvas."""
    heading_height = max(44, round(height * 0.13))
    try:
        heading_height = max(44, int(config.get("heading_height", heading_height)))
        node_gap = max(8, int(config.get("node_gap", round(height * 0.018))))
        inner_padding = max(12, int(config.get("inner_padding", round(min(width, height) * 0.025))))
    except (TypeError, ValueError):
        node_gap = max(8, round(height * 0.018))
        inner_padding = max(12, round(min(width, height) * 0.025))

    available_height = height - heading_height - node_gap * (step_count - 1)
    requested_height = config.get("node_height")
    if type(requested_height) is int and requested_height >= 70 and requested_height * step_count <= available_height:
        node_height = requested_height
    else:
        node_height = available_height // step_count if step_count > 0 else 0
    if step_count < 2 or node_height < 70:
        raise BrandIntegrityError("workflow diagram area is too small for readable text")
    return heading_height, node_gap, node_height, inner_padding


def _validate_workflow_text(
    config: Mapping[str, object],
    *,
    canvas_size: tuple[int, int],
    font_paths: Mapping[str, Path | str],
    language: str,
) -> None:
    """Reject workflow copy that cannot render or fit before an image is requested."""
    box = _overlay_box(config)
    steps = config.get("steps")
    if box is None or not isinstance(steps, list) or len(steps) < 2:
        return
    x, y, width, height = box
    if x + width > canvas_size[0] or y + height > canvas_size[1]:
        return
    heading_path = font_paths.get("heading") or font_paths.get("body")
    body_path = font_paths.get("body") or heading_path
    if heading_path is None or body_path is None:
        raise BrandIntegrityError("workflow diagram requires confirmed heading and body fonts")

    key = "zh" if language.startswith("zh") else "en"
    detail_key = "detail_zh" if key == "zh" else "detail_en"
    labels: list[str] = []
    details: list[str] = []
    for step in steps[:4]:
        if not isinstance(step, Mapping):
            continue
        label = step.get(key, step.get("en", step.get("zh", "")))
        if isinstance(label, str) and label.strip():
            labels.append(label.strip())
            detail = step.get(detail_key, "")
            details.append(detail.strip() if isinstance(detail, str) else "")
    if len(labels) < 2:
        return

    _, _, node_height, inner_padding = _workflow_geometry(
        config, width=width, height=height, step_count=len(labels),
    )
    title = config.get("heading_zh" if key == "zh" else "heading_en")
    if not isinstance(title, str) or not title.strip():
        benefits_mode = config.get("workflow_mode") == "benefits"
        title = ("核心收益" if benefits_mode else "关键步骤") if key == "zh" else ("KEY BENEFITS" if benefits_mode else "KEY STEPS")
    title = title.strip()
    subtitle = config.get("subtitle_zh" if key == "zh" else "subtitle_en", "")
    subtitle = subtitle.strip() if isinstance(subtitle, str) else ""

    heading_font_size = max(16, min(54, round(min(width, height) * 0.045)))
    _fit_overlay_font(
        heading_path, title, max_size=heading_font_size,
        min_size=max(14, heading_font_size // 2), max_width=width - inner_padding * 2,
    )
    if subtitle:
        _fit_overlay_font(
            body_path, subtitle, max_size=max(12, heading_font_size // 2),
            min_size=12, max_width=width - inner_padding * 2,
        )

    node_width = width - inner_padding * 2
    content_width = node_width - round(node_width * 0.25) - inner_padding
    max_label_size = max(16, min(64, round(min(node_height * 0.31, node_width * 0.055))))
    for label, detail in zip(labels, details):
        _fit_overlay_font(
            heading_path, label, max_size=max_label_size,
            min_size=max(13, max_label_size // 2), max_width=content_width,
        )
        if detail:
            _fit_overlay_font(
                body_path, detail, max_size=max(12, round(max_label_size * 0.62)),
                min_size=11, max_width=content_width,
            )

    for role, path, text in (
        ("heading", heading_path, "\n".join((title, *labels))),
        ("body", body_path, "\n".join((subtitle, *details))),
    ):
        missing = missing_glyphs(path, text)
        if missing:
            chars = " ".join(repr(char) for char in missing)
            raise BrandIntegrityError(
                f"confirmed {role} font cannot render workflow characters: {chars}; select a font that supports these characters"
            )


def validate_composition_layout(
    brief: BrandBrief | Mapping[str, object],
    template: Mapping[str, object],
    font_paths: Mapping[str, Path | str],
) -> None:
    """Validate copy fonts and geometry without loading a generated base image."""
    rendered = rendered_copy_values(brief)
    slots = template.get("slots")
    if not isinstance(slots, Mapping):
        raise BrandIntegrityError("template slots are missing")
    for key, role in (("title", "heading"), ("subtitle", "body"), ("value_line", "body"), ("features", "body")):
        value = rendered.get(key)
        if not value:
            continue
        slot = _slot(slots, key)
        font_path = font_paths.get(role)
        if font_path is None:
            raise BrandIntegrityError(f"font path missing for {role}")
        text = "\n".join(f"• {item}" for item in value) if key == "features" else str(value)
        missing = missing_glyphs(font_path, text)
        if missing:
            chars = " ".join(repr(char) for char in missing)
            raise BrandIntegrityError(
                f"confirmed {role} font cannot render copy characters: {chars}; select a font that supports these characters"
            )
        fit_text_box(
            text,
            (int(slot["w"]), int(slot["h"])),
            font_path,
            max_font_size=int(slot.get("max_font_size", 176)),
            min_font_size=int(slot.get("min_font_size", 24)),
        )

    canvas = template.get("canvas")
    overlays = template.get("overlays", {})
    if not isinstance(canvas, Mapping) or not isinstance(overlays, Mapping):
        raise BrandIntegrityError("template canvas and overlays must be objects")
    workflow = overlays.get("workflow_diagram")
    if isinstance(workflow, Mapping):
        _validate_workflow_text(
            workflow,
            canvas_size=(int(canvas["width"]), int(canvas["height"])),
            font_paths=font_paths,
            language=str(_copy(brief).get("language", "en")),
        )
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

    heading_height, node_gap, node_height, inner_padding = _workflow_geometry(
        config, width=width, height=height, step_count=len(normalized_steps),
    )

    accent = _rgba(config.get("accent"), (56, 193, 255, 255))
    secondary = _rgba(config.get("secondary"), (126, 112, 239, 255))
    node_colors = (accent, (43, 130, 235, 255), secondary, (236, 178, 63, 255))
    # Draw on a transparent layer so there is no opaque workflow background.
    layer = Image.new("RGBA", output.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    title = config.get("heading_zh" if language.startswith("zh") else "heading_en")
    if not isinstance(title, str) or not title.strip():
        benefits_mode = config.get("workflow_mode") == "benefits"
        title = ("核心收益" if benefits_mode else "关键步骤") if language.startswith("zh") else ("KEY BENEFITS" if benefits_mode else "KEY STEPS")
    detail_title = config.get("subtitle_zh" if language.startswith("zh") else "subtitle_en", "")
    detail_title = detail_title.strip() if isinstance(detail_title, str) else ""
    heading_font_size = max(16, min(54, round(min(width, height) * 0.045)))
    title_font = _fit_overlay_font(heading_path, title, max_size=heading_font_size, min_size=max(14, heading_font_size // 2), max_width=width - inner_padding * 2)
    draw.text((x + inner_padding, y + 2), title, font=title_font, fill=(245, 250, 255, 255))
    heading_line_y = y + heading_height - max(4, round(heading_height * 0.12))
    if detail_title:
        subtitle_font = _fit_overlay_font(body_path, detail_title, max_size=max(12, heading_font_size // 2), min_size=12, max_width=width - inner_padding * 2)
        draw.text((x + inner_padding, y + title_font.size + 8), detail_title, font=subtitle_font, fill=(163, 201, 235, 255))
    draw.line((x + inner_padding, heading_line_y, x + width - inner_padding, heading_line_y), fill=(95, 164, 231, 210), width=max(1, round(min(output.size) * 0.001)))

    node_x = x + inner_padding
    node_w = width - inner_padding * 2
    node_y = y + heading_height
    for index, label in enumerate(normalized_steps):
        top = node_y + index * (node_height + node_gap)
        bottom = top + node_height
        color = node_colors[index % len(node_colors)]
        if index:
            connector_x = node_x + 34
            previous_bottom = top - node_gap
            draw.line((connector_x, previous_bottom + 2, connector_x, top - 10), fill=color, width=4)
            draw.polygon(((connector_x, top - 2), (connector_x - 9, top - 15), (connector_x + 9, top - 15)), fill=color)
        radius = max(8, min(node_height, node_w) // 16)
        fill_opacity = config.get("card_fill_opacity", 0.6)
        blur_ratio = config.get("card_blur_radius_ratio", 0.008)
        try:
            fill_alpha = max(0, min(255, round(float(fill_opacity) * 255)))
            blur_radius = max(0.0, float(blur_ratio) * min(output.size))
        except (TypeError, ValueError) as exc:
            raise BrandIntegrityError("workflow card frosted style values must be numeric") from exc
        if not 0.0 <= float(fill_opacity) <= 1.0 or blur_radius > min(output.size) * 0.05:
            raise BrandIntegrityError("workflow card frosted style is outside safe visual bounds")
        card_box = (node_x, top, node_x + node_w, bottom)
        local_scene = output.crop(card_box)
        frosted = local_scene.filter(ImageFilter.GaussianBlur(blur_radius))
        tint_rgb = _rgba(config.get("card_fill"), (7, 24, 52, 255))
        tint = Image.new("RGBA", frosted.size, (tint_rgb[0], tint_rgb[1], tint_rgb[2], fill_alpha))
        frosted = Image.alpha_composite(frosted, tint)
        card_mask = Image.new("L", frosted.size, 0)
        ImageDraw.Draw(card_mask).rounded_rectangle((0, 0, node_w - 1, node_height - 1), radius=radius, fill=255)
        layer.paste(frosted, (node_x, top), card_mask)
        outline_width = max(1, round(min(output.size) * 0.0014))
        draw.rounded_rectangle(card_box, radius=radius, outline=color, width=outline_width)
        rail_x = node_x + max(8, round(node_w * 0.018))
        draw.line((rail_x, top + max(12, round(node_height * 0.14)), rail_x, bottom - max(12, round(node_height * 0.14))), fill=color, width=outline_width)
        number_diameter = max(28, min(round(node_height * 0.34), round(node_w * 0.12)))
        number_left = node_x + max(18, round(node_w * 0.04))
        number_top = top + (node_height - number_diameter) // 2
        number_box = (number_left, number_top, number_left + number_diameter, number_top + number_diameter)
        draw.ellipse(number_box, fill=color)
        number_font = _fit_overlay_font(heading_path, str(index + 1), max_size=max(18, round(number_diameter * 0.62)), min_size=14, max_width=number_diameter - 6)
        _centered_text(draw, number_box, str(index + 1), number_font, (5, 18, 42, 255))
        icon_center_x = node_x + round(node_w * 0.18)
        _draw_step_icon(draw, (icon_center_x, top + node_height // 2), index, color)
        content_left = node_x + round(node_w * 0.25)
        content_right = node_x + node_w - inner_padding
        max_label_size = max(16, min(64, round(min(node_height * 0.31, node_w * 0.055))))
        label_font = _fit_overlay_font(heading_path, label, max_size=max_label_size, min_size=max(13, max_label_size // 2), max_width=content_right - content_left)
        detail = step_details[index] if index < len(step_details) else ""
        detail_font = _fit_overlay_font(body_path, detail, max_size=max(12, round(max_label_size * 0.62)), min_size=11, max_width=content_right - content_left)
        label_top = top + max(8, round(node_height * 0.16))
        draw.text((content_left, label_top), label, font=label_font, fill=(245, 250, 255, 255))
        divider_y = top + round(node_height * 0.55)
        draw.line((content_left, divider_y, content_right, divider_y), fill=(95, 164, 231, 165), width=max(1, round(min(output.size) * 0.0006)))
        if detail:
            draw.text((content_left, divider_y + max(5, round(node_height * 0.07))), detail, font=detail_font, fill=(164, 201, 235, 255))
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
    validate_composition_layout(brief, template, font_paths)
    background, base_hash = _image(base_image)
    if background.size != (width, height):
        if not same_aspect_ratio(background.size, (width, height)):
            raise BrandIntegrityError(
                f"base image aspect ratio {background.size} does not match template canvas {(width, height)}; cropping and distortion are not allowed"
            )
        background = background.resize((width, height), Image.Resampling.LANCZOS)
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
    style_data: Mapping[str, object] = {}
    if isinstance(brief, BrandBrief):
        style_data = brief.style
        foreground = str(brief.style.get("foreground", foreground))
    elif isinstance(brief, Mapping) and isinstance(brief.get("style"), Mapping):
        style_data = brief["style"]
        foreground = str(style_data.get("foreground", foreground))
    stage_style = style_data.get("profile") == "stage-screen-poster"
    if stage_style:
        foreground = "#FFFFFF"
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
        if key == "title" and stage_style:
            base_color = style_data.get("title_base_color")
            accent_color = style_data.get("title_emphasis_color")
            emphasis_text = style_data.get("title_emphasis_text")
            if not isinstance(base_color, str) or base_color.upper() != "#FFFFFF":
                raise BrandIntegrityError("stage poster title base color must be confirmed white")
            if not isinstance(accent_color, str) or not isinstance(emphasis_text, str) or not emphasis_text:
                raise BrandIntegrityError("stage poster title emphasis color and text must be confirmed")
            try:
                base_fill = (*ImageColor.getrgb(base_color)[:3], 255)
                accent_fill = (*ImageColor.getrgb(accent_color)[:3], 255)
            except ValueError as exc:
                raise BrandIntegrityError("stage poster title colors are invalid") from exc
            _draw_emphasized_title(
                draw,
                x=int(slot["x"]),
                y=int(slot["y"]),
                lines=layout.lines,
                font=font,
                base_color=base_fill,
                emphasis_color=accent_fill,
                emphasis_text=emphasis_text,
            )
        else:
            draw.multiline_text((int(slot["x"]), int(slot["y"])), "\n".join(layout.lines), font=font, fill=fill, spacing=8)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = str(template.get("output_stem") or Path(template_path).stem)
    version = 1
    destination = output_dir / f"{stem}-v{version:02d}.png"
    while destination.exists():
        version += 1
        destination = output_dir / f"{stem}-v{version:02d}.png"
    output = output.convert("RGBA")
    srgb_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    output.save(destination, format="PNG", icc_profile=srgb_profile)
    return RenderResult(destination, width, height, hashes, logo_size, stem, rendered_copy, selected_treatment)
