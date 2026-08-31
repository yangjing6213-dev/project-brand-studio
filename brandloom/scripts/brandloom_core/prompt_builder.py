"""Safe prompt construction and validation for the host image-generation boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .models import BrandBrief

_OUTPUT_SPECS = {"logo_card": ("1:1", (2048, 2048)), "cover": ("2:1", (2048, 1024))}


_IP_ROLES = {
    "author-anime": "presenter",
    "tuotuo": "execution/system",
    "xingbi": "feedback/result",
}

_IP_CUES = {
    "author-anime": "black tousled hair, light gray jacket, white inner shirt, friendly confident expression",
    "tuotuo": "blue rounded form, square black glasses, lightning-shaped head feature",
    "xingbi": "yellow five-point star, white gloves and shoes, friendly smile",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ip_entries(brief: BrandBrief, output_type: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    selected = brief.assets.get(f"{output_type}_ip")
    if selected is None:
        selected = brief.assets.get("ip_profiles", [])
    for entry in selected:
        if isinstance(entry, dict):
            ip_id = str(entry.get("id", "")).strip()
            role = str(entry.get("role", "")).strip() or _IP_ROLES.get(ip_id, "selected IP")
        else:
            ip_id = str(entry).strip()
            role = _IP_ROLES.get(ip_id, "selected IP")
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
    roles = ", ".join(
        f"{ip_id} ({role}; {_IP_CUES.get(ip_id, 'use the confirmed profile cues')})"
        for ip_id, role in _ip_entries(brief, output_type)
    ) or "no IP characters"
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


def _builtin_reference(skill_root: Path, ip_id: str, role: str) -> dict[str, object]:
    if ip_id not in _IP_CUES:
        raise ValueError(f"custom IP reference must be supplied through the confirmed Skill route: {ip_id}")
    directory = skill_root / "assets" / "defaults" / "ip" / ip_id
    image_path = (directory / "reference.png").resolve()
    provenance_path = directory / "provenance.json"
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid built-in IP provenance: {provenance_path}") from exc
    if provenance.get("authorization_status") != "user_authorized":
        raise ValueError(f"built-in IP is not authorized: {ip_id}")
    digest = _sha256(image_path)
    expected = provenance.get("reference_sha256", provenance.get("sha256"))
    if not isinstance(expected, str) or digest != expected.lower():
        raise ValueError(f"built-in IP hash mismatch: {ip_id}")
    try:
        with Image.open(image_path) as image:
            image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"built-in IP is not a readable image: {ip_id}") from exc
    return {
        "asset_id": ip_id,
        "category": "ip-character",
        "scope": "skill-defaults",
        "rights_status": "user_authorized",
        "role": role,
        "profile_cues": _IP_CUES[ip_id],
        "path": str(image_path),
        "sha256": digest,
    }


def build_host_request(
    brief: BrandBrief,
    output_type: str,
    *,
    shot_list=None,
    expected=None,
    accepted_logo_path: Path | None = None,
    skill_root: Path | None = None,
) -> dict[str, object]:
    """Build a JSON-safe host request without invoking an image tool."""
    try:
        ratio, dimensions = _OUTPUT_SPECS[output_type]
    except KeyError as exc:
        raise ValueError(f"unsupported output type: {output_type}") from exc
    root = Path(skill_root or Path(__file__).resolve().parents[2]).resolve()
    references = [
        _builtin_reference(root, ip_id, role)
        for ip_id, role in _ip_entries(brief, output_type)
    ]
    request: dict[str, object] = {
        "schema_version": "1.0",
        "backend": "host_builtin_image_tool",
        "output_type": output_type,
        "aspect_ratio": ratio,
        "dimensions": list(dimensions),
        "prompt": build_base_prompt(brief, output_type, shot_list=shot_list, expected=expected),
        "reference_assets": references,
    }
    if accepted_logo_path is not None:
        accepted = Path(accepted_logo_path).resolve()
        validate_generated_path(accepted, expected="logo_card")
        request["accepted_logo"] = {"path": str(accepted), "sha256": _sha256(accepted)}
    return request


def validate_generated_path(path: Path, expected=None) -> tuple[int, int]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            dimensions = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"returned path is not a readable image: {path}") from exc
    if dimensions not in {spec[1] for spec in _OUTPUT_SPECS.values()}:
        raise ValueError(f"unsupported generated dimensions: {dimensions}")
    if expected is not None:
        if isinstance(expected, str):
            try:
                expected_dimensions = _OUTPUT_SPECS[expected][1]
            except KeyError as exc:
                raise ValueError(f"unsupported expected output type: {expected}") from exc
        else:
            expected_dimensions = tuple(expected)
        if dimensions != expected_dimensions:
            raise ValueError(f"generated dimensions {dimensions} do not match expected {expected_dimensions}")
    return dimensions
