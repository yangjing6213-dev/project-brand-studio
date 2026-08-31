"""Safe prompt construction and validation for the host image-generation boundary."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .models import BrandBrief

_OUTPUT_SPECS = {"logo_card": ("1:1", (2048, 2048)), "cover": ("2:1", (2048, 1024))}


def _ip_entries(brief: BrandBrief) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for entry in brief.assets.get("ip_profiles", []):
        if isinstance(entry, dict):
            ip_id = str(entry.get("id", "")).strip()
            role = str(entry.get("role", "")).strip() or "selected IP"
        else:
            ip_id, role = str(entry).strip(), "selected IP"
        if ip_id:
            result.append((ip_id, role))
    return result


def build_base_prompt(brief: BrandBrief, output_type: str, *, shot_list=None, expected=None) -> str:
    try:
        ratio, dimensions = _OUTPUT_SPECS[output_type]
    except KeyError as exc:
        raise ValueError(f"unsupported output type: {output_type}") from exc
    if expected is not None and tuple(expected) != dimensions:
        raise ValueError(f"{output_type} requires dimensions {dimensions}, got {expected}")
    style = brief.style.get("profile") or brief.style.get("family") or "reference-adaptive"
    zones = brief.style.get("reserved_text_zones") or ["left third", "bottom band"]
    zones_text = ", ".join(str(zone) for zone in zones)
    roles = ", ".join(f"{ip_id} ({role})" for ip_id, role in _ip_entries(brief)) or "no IP characters"
    shots = "" if not shot_list else " Shot list cues: " + "; ".join(map(str, shot_list)) + "."
    if output_type == "logo_card":
        scene = "Create a 1:1 real-scene base for a polished logo-card composition, with the selected IP roles integrated naturally."
    else:
        scene = "Create a 2:1 cover scene; reuse the accepted LOGO visual DNA and the selected IP roles without drawing a logo."
    return (
        f"{scene} Target aspect ratio: {ratio}, canvas {dimensions[0]}x{dimensions[1]}. "
        f"Use the selected style profile: {style}. Keep reserved blank text zones ({zones_text}) clean for deterministic layout. "
        f"Selected IP roles: {roles}. Include no visible company logo and no readable final marketing text; "
        "use only abstract non-readable UI marks if needed. Do not bake copy, labels, buttons, watermarks, or signatures into the image."
        + shots
    )


def validate_generated_path(path: Path) -> tuple[int, int]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            dimensions = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"returned path is not a readable image: {path}") from exc
    if dimensions not in {spec[1] for spec in _OUTPUT_SPECS.values()}:
        raise ValueError(f"unsupported generated dimensions: {dimensions}")
    return dimensions
