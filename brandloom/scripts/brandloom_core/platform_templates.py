"""JSON layout templates for platform-specific cover canvases."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping


def _px(value: float) -> int:
    return max(1, round(value))


def _workflow_steps(
    steps: object,
    *,
    language: str,
    maximum: int,
) -> list[dict[str, str]]:
    if steps is None:
        return []
    if not isinstance(steps, list) or not 2 <= len(steps) <= maximum:
        raise ValueError(f"confirmed workflow must contain between 2 and {maximum} steps for this canvas")
    language_key = "zh" if language.lower().startswith("zh") else "en"
    detail_key = f"detail_{language_key}"
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(steps):
        if isinstance(item, str) and item.strip():
            title = item.strip()
            detail = ""
        elif isinstance(item, Mapping):
            title = item.get(language_key, item.get("title", ""))
            detail = item.get(detail_key, item.get("detail", ""))
            if not isinstance(title, str) or not title.strip():
                raise ValueError(f"workflow step {index + 1} is missing its confirmed {language_key} title")
            if detail is not None and not isinstance(detail, str):
                raise ValueError(f"workflow step {index + 1} detail must be text")
            title = title.strip()
            detail = detail.strip() if isinstance(detail, str) else ""
        else:
            raise ValueError(f"workflow step {index + 1} must be confirmed text or a localized mapping")
        normalized.append({language_key: title, detail_key: detail})
    return normalized


def _make_template(
    target: Mapping[str, object],
    *,
    language: str,
    workflow_steps: object,
    style_profile: str | None = None,
) -> dict[str, object]:
    dimensions = target.get("dimensions")
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 2:
        raise ValueError("target dimensions are missing")
    width, height = dimensions
    if type(width) is not int or type(height) is not int or min(width, height) <= 0:
        raise ValueError("target dimensions must be positive integers")
    ratio = width / height
    margin = _px(min(width, height) * 0.04)
    title_line_spacing = _px(min(width, height) * 0.018)
    body_line_spacing = _px(min(width, height) * 0.012)
    wide = ratio >= 1.2
    max_steps = 4 if wide else 3
    workflow_mode = target.get("workflow_mode", "steps")
    if workflow_mode not in {"steps", "benefits", "none"}:
        raise ValueError("workflow_mode must be steps, benefits, or none")
    if workflow_mode == "none" and workflow_steps:
        raise ValueError("workflow_steps cannot be provided when workflow_mode is none")
    steps = _workflow_steps(workflow_steps, language=language, maximum=max_steps)
    workflow: dict[str, object] | None = None
    if steps:
        if wide:
            workflow = {
                "x": _px(width * 0.52), "y": _px(height * 0.06),
                "w": width - _px(width * 0.56), "h": _px(height * 0.88),
            }
        else:
            workflow = {
                "x": _px(width * 0.06), "y": _px(height * 0.57),
                "w": width - _px(width * 0.12), "h": _px(height * 0.39),
            }
        workflow.update({
            "accent": [56, 193, 255, 255],
            "secondary": [126, 112, 239, 255],
            "card_fill": [7, 24, 52, 255],
            "card_fill_opacity": 0.4,
            "card_blur_radius_ratio": 0.008,
            "heading_subtitle_gap": _px(min(width, height) * 0.022),
            "workflow_mode": workflow_mode,
            "steps": steps,
        })
        for key in ("workflow_heading_zh", "workflow_heading_en", "workflow_subtitle_zh", "workflow_subtitle_en"):
            value = target.get(key)
            if isinstance(value, str) and value.strip():
                workflow[key.removeprefix("workflow_")] = value.strip()

    if wide:
        slots = {
            "company_logo": {"x": _px(width * 0.05), "y": _px(height * 0.045), "w": _px(width * 0.22), "h": _px(height * 0.09), "fit": "contain"},
            "project_mark": {"x": _px(width * 0.37), "y": _px(height * 0.04), "w": _px(width * 0.08), "h": _px(height * 0.10), "fit": "contain"},
            "title": {"x": _px(width * 0.05), "y": _px(height * 0.18), "w": _px(width * 0.43), "h": _px(height * 0.20), "min_font_size": _px(min(width, height) * 0.035), "max_font_size": _px(min(width, height) * 0.10), "line_spacing": title_line_spacing},
            "subtitle": {"x": _px(width * 0.05), "y": _px(height * 0.40), "w": _px(width * 0.43), "h": _px(height * 0.10), "min_font_size": _px(min(width, height) * 0.023), "max_font_size": _px(min(width, height) * 0.055), "line_spacing": body_line_spacing},
            "value_line": {"x": _px(width * 0.05), "y": _px(height * 0.52), "w": _px(width * 0.43), "h": _px(height * 0.08), "min_font_size": _px(min(width, height) * 0.021), "max_font_size": _px(min(width, height) * 0.045), "line_spacing": body_line_spacing},
            "features": {"x": _px(width * 0.05), "y": _px(height * 0.62), "w": _px(width * 0.44), "h": _px(height * 0.32), "min_font_size": _px(min(width, height) * 0.018), "max_font_size": _px(min(width, height) * 0.036), "line_spacing": body_line_spacing},
        }
    else:
        slots = {
            "company_logo": {"x": _px(width * 0.06), "y": _px(height * 0.035), "w": _px(width * 0.31), "h": _px(height * 0.07), "fit": "contain"},
            "project_mark": {"x": _px(width * 0.82), "y": _px(height * 0.025), "w": _px(width * 0.12), "h": _px(height * 0.09), "fit": "contain"},
            "title": {"x": _px(width * 0.06), "y": _px(height * 0.13), "w": _px(width * 0.88), "h": _px(height * 0.12), "min_font_size": _px(min(width, height) * 0.04), "max_font_size": _px(min(width, height) * 0.095), "line_spacing": title_line_spacing},
            "subtitle": {"x": _px(width * 0.06), "y": _px(height * 0.265), "w": _px(width * 0.88), "h": _px(height * 0.075), "min_font_size": _px(min(width, height) * 0.025), "max_font_size": _px(min(width, height) * 0.058), "line_spacing": body_line_spacing},
            "value_line": {"x": _px(width * 0.06), "y": _px(height * 0.35), "w": _px(width * 0.88), "h": _px(height * 0.065), "min_font_size": _px(min(width, height) * 0.023), "max_font_size": _px(min(width, height) * 0.05), "line_spacing": body_line_spacing},
            "features": {"x": _px(width * 0.06), "y": _px(height * 0.425), "w": _px(width * 0.88), "h": _px(height * 0.125), "min_font_size": _px(min(width, height) * 0.018), "max_font_size": _px(min(width, height) * 0.037), "line_spacing": body_line_spacing},
        }

    if target.get("id") == "youtube-channel-banner":
        # Keep all key copy and marks inside a conservative centered banner zone.
        safe_x = _px(width * 0.198)
        safe_y = _px(height * 0.353)
        safe_width = _px(width * 0.604)
        text_width = _px(safe_width * 0.48)
        slots["company_logo"].update({"x": safe_x, "y": safe_y, "w": _px(text_width * 0.62), "h": _px(height * 0.055)})
        slots["project_mark"].update({"x": safe_x + _px(text_width * 0.70), "y": safe_y, "w": _px(text_width * 0.20), "h": _px(height * 0.055)})
        slots["title"].update({"x": safe_x, "y": _px(height * 0.405), "w": text_width, "h": _px(height * 0.08)})
        slots["subtitle"].update({"x": safe_x, "y": _px(height * 0.49), "w": text_width, "h": _px(height * 0.05)})
        slots["value_line"].update({"x": safe_x, "y": _px(height * 0.545), "w": text_width, "h": _px(height * 0.05)})
        slots["features"].update({"x": safe_x, "y": _px(height * 0.60), "w": text_width, "h": _px(height * 0.045)})
        if workflow is not None:
            workflow.update({"x": _px(width * 0.50), "y": _px(height * 0.355), "w": _px(width * 0.29), "h": _px(height * 0.285)})

    if style_profile == "stage-screen-poster":
        if target.get("id") == "youtube-channel-banner":
            # Keep both the title and display text inside the platform's centered safe zone.
            title_width = _px(safe_width * 0.46)
            screen_x = safe_x + title_width + _px(safe_width * 0.035)
            screen_width = max(1, safe_x + safe_width - screen_x)
            slots["title"].update({"x": safe_x, "y": _px(height * 0.405), "w": title_width, "h": _px(height * 0.13)})
            slots["subtitle"].update({"x": screen_x, "y": _px(height * 0.405), "w": screen_width, "h": _px(height * 0.045)})
            slots["value_line"].update({"x": screen_x, "y": _px(height * 0.455), "w": screen_width, "h": _px(height * 0.045)})
            slots["features"].update({"x": screen_x, "y": _px(height * 0.505), "w": screen_width, "h": _px(height * 0.085)})
            if workflow is not None:
                workflow.update({"x": screen_x, "y": _px(height * 0.60), "w": screen_width, "h": _px(height * 0.16)})
        elif wide:
            slots["company_logo"].update({"x": _px(width * 0.05), "y": _px(height * 0.04), "w": _px(width * 0.22), "h": _px(height * 0.08)})
            slots["project_mark"].update({"x": _px(width * 0.40), "y": _px(height * 0.035), "w": _px(width * 0.07), "h": _px(height * 0.09)})
            slots["title"].update({"x": _px(width * 0.05), "y": _px(height * 0.20), "w": _px(width * 0.41), "h": _px(height * 0.34)})
            slots["subtitle"].update({"x": _px(width * 0.55), "y": _px(height * 0.12), "w": _px(width * 0.39), "h": _px(height * 0.11)})
            slots["value_line"].update({"x": _px(width * 0.55), "y": _px(height * 0.245), "w": _px(width * 0.39), "h": _px(height * 0.09)})
            slots["features"].update({"x": _px(width * 0.55), "y": _px(height * 0.35), "w": _px(width * 0.39), "h": _px(height * (0.12 if workflow is not None else 0.55))})
            if workflow is not None:
                workflow.update({"x": _px(width * 0.52), "y": _px(height * 0.50), "w": _px(width * 0.44), "h": _px(height * 0.44)})
        else:
            slots["company_logo"].update({"x": _px(width * 0.05), "y": _px(height * 0.02), "w": _px(width * 0.35), "h": _px(height * 0.06)})
            slots["project_mark"].update({"x": _px(width * 0.41), "y": _px(height * 0.02), "w": _px(width * 0.07), "h": _px(height * 0.07)})
            slots["title"].update({"x": _px(width * 0.05), "y": _px(height * 0.11), "w": _px(width * 0.40), "h": _px(height * 0.23)})
            slots["subtitle"].update({"x": _px(width * 0.52), "y": _px(height * 0.12), "w": _px(width * 0.43), "h": _px(height * 0.09)})
            slots["value_line"].update({"x": _px(width * 0.52), "y": _px(height * 0.22), "w": _px(width * 0.43), "h": _px(height * 0.08)})
            slots["features"].update({"x": _px(width * 0.52), "y": _px(height * 0.32), "w": _px(width * 0.43), "h": _px(height * (0.12 if workflow is not None else 0.56))})
            if workflow is not None:
                workflow.update({"x": _px(width * 0.50), "y": _px(height * 0.48), "w": _px(width * 0.46), "h": _px(height * 0.49)})

    overlays: dict[str, object] = {}
    if workflow is not None:
        overlays["workflow_diagram"] = workflow
    return {
        "schema_version": "1.0",
        "output_stem": f"cover-{target['id']}",
        "target_id": str(target["id"]),
        "canvas": {"width": width, "height": height, "safe_margin": margin},
        "overlays": overlays,
        "slots": slots,
    }


def write_cover_template(
    output_dir: Path,
    target: Mapping[str, object],
    *,
    language: str,
    workflow_steps: object = None,
    style_profile: str | None = None,
) -> Path:
    """Persist a fresh, immutable JSON template for one confirmed target."""
    template = build_cover_template(
        target,
        language=language,
        workflow_steps=workflow_steps,
        style_profile=style_profile,
    )
    output_dir = Path(output_dir).resolve() / "layouts"
    output_dir.mkdir(parents=True, exist_ok=True)
    target_id = re.sub(r"[^A-Za-z0-9_-]+", "-", str(target["id"])).strip("-") or "custom"
    width, height = template["canvas"]["width"], template["canvas"]["height"]  # type: ignore[index]
    version = 1
    while True:
        path = output_dir / f"cover-{target_id}-{width}x{height}-layout-v{version:02d}.json"
        if not path.exists():
            break
        version += 1
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def build_cover_template(
    target: Mapping[str, object],
    *,
    language: str,
    workflow_steps: object = None,
    style_profile: str | None = None,
) -> dict[str, object]:
    """Build and validate a platform layout without writing a workspace file."""
    return _make_template(target, language=language, workflow_steps=workflow_steps, style_profile=style_profile)
