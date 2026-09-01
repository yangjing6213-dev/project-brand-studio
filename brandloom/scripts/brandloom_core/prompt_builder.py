"""Safe prompt construction and validation for the host image-generation boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .models import BrandBrief

_OUTPUT_SPECS = {"logo_card": ("1:1", (1254, 1254)), "cover": ("2:1", (1774, 887))}


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

_SUPPLEMENTAL_REFERENCES = {
    "tuotuo": {
        "asset_id": "tuotuo-geometry-v1",
        "relative_path": "assets/defaults/ip/tuotuo/tuotuo-five-view-v1.png",
        "reference_role": "supplemental_geometry",
        "profile_cues": _IP_CUES["tuotuo"],
    },
    "xingbi": {
        "asset_id": "xingbi-geometry-v1",
        "relative_path": "assets/defaults/ip/xingbi/xingbi-five-view-v1.png",
        "reference_role": "supplemental_geometry",
        "profile_cues": _IP_CUES["xingbi"],
    },
}

_SHARED_APPEARANCE = {
    "asset_id": "tuotuo-xingbi-front-v1",
    "relative_path": "assets/defaults/ip/shared/tuotuo-xingbi-front-v1.png",
    "reference_role": "shared_primary_appearance",
    "profile_cues": f"Tuotuo: {_IP_CUES['tuotuo']}; Xingbi: {_IP_CUES['xingbi']}",
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
        "use only abstract non-readable UI marks if needed. Do not bake copy, labels, buttons, watermarks, or signatures into the image. When the shared pair reference is present, treat it as the primary appearance source; treat five-view references as geometry-only supplements and do not let their rendering style override that appearance."
        + shots
    )


def _reference_provenance_path(image_path: Path) -> Path:
    per_file = image_path.with_name(f"{image_path.stem}.provenance.json")
    if per_file.is_file():
        return per_file
    return image_path.with_name("provenance.json")


def _validated_reference(
    image_path: Path,
    *,
    asset_id: str,
    reference_role: str,
    profile_cues: str,
) -> dict[str, object]:
    provenance_path = _reference_provenance_path(image_path)
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid built-in reference provenance: {provenance_path}") from exc
    if provenance.get("authorization_status") != "user_authorized" or provenance.get("distribution_scope") != "public_skill_package":
        raise ValueError(f"built-in reference is not authorized: {asset_id}")
    digest = _sha256(image_path)
    expected = provenance.get("reference_sha256", provenance.get("sha256"))
    if not isinstance(expected, str) or digest != expected.lower():
        raise ValueError(f"built-in reference hash mismatch: {asset_id}")
    try:
        with Image.open(image_path) as image:
            image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"built-in reference is not a readable image: {asset_id}") from exc
    return {
        "asset_id": asset_id,
        "category": "ip-character",
        "scope": "skill-defaults",
        "rights_status": "user_authorized",
        "role": reference_role,
        "reference_role": reference_role,
        "profile_cues": profile_cues,
        "path": str(image_path.resolve()),
        "sha256": digest,
    }


def _builtin_reference(skill_root: Path, ip_id: str, role: str) -> dict[str, object]:
    if ip_id not in _IP_CUES:
        raise ValueError(f"custom IP reference must be supplied through the confirmed Skill route: {ip_id}")
    entry = _validated_reference(
        (skill_root / "assets" / "defaults" / "ip" / ip_id / "reference.png").resolve(),
        asset_id=ip_id,
        reference_role="canonical_appearance",
        profile_cues=_IP_CUES[ip_id],
    )
    entry["role"] = role
    return entry


def _supplemental_references(skill_root: Path, selected: list[tuple[str, str]]) -> list[dict[str, object]]:
    ids = list(dict.fromkeys(ip_id for ip_id, _role in selected))
    references: list[dict[str, object]] = []
    if {"tuotuo", "xingbi"}.issubset(ids):
        references.append(
            _validated_reference(
                (skill_root / _SHARED_APPEARANCE["relative_path"]).resolve(),
                asset_id=str(_SHARED_APPEARANCE["asset_id"]),
                reference_role=str(_SHARED_APPEARANCE["reference_role"]),
                profile_cues=str(_SHARED_APPEARANCE["profile_cues"]),
            )
        )
    for ip_id in ids:
        supplemental = _SUPPLEMENTAL_REFERENCES.get(ip_id)
        if supplemental is None:
            continue
        references.append(
            _validated_reference(
                (skill_root / str(supplemental["relative_path"])).resolve(),
                asset_id=str(supplemental["asset_id"]),
                reference_role=str(supplemental["reference_role"]),
                profile_cues=str(supplemental["profile_cues"]),
            )
        )
    return references


def build_host_request(
    brief: BrandBrief,
    output_type: str,
    *,
    shot_list=None,
    expected=None,
    accepted_logo_path: Path | None = None,
    accepted_logo_evidence: dict[str, object] | None = None,
    skill_root: Path | None = None,
) -> dict[str, object]:
    """Build a JSON-safe host request without invoking an image tool."""
    try:
        ratio, dimensions = _OUTPUT_SPECS[output_type]
    except KeyError as exc:
        raise ValueError(f"unsupported output type: {output_type}") from exc
    root = Path(skill_root or Path(__file__).resolve().parents[2]).resolve()
    selected = _ip_entries(brief, output_type)
    references = [
        _builtin_reference(root, ip_id, role)
        for ip_id, role in selected
    ]
    references.extend(_supplemental_references(root, selected))
    request: dict[str, object] = {
        "schema_version": "1.0",
        "backend": "host_builtin_image_tool",
        "output_type": output_type,
        "aspect_ratio": ratio,
        "dimensions": list(dimensions),
        "prompt": build_base_prompt(brief, output_type, shot_list=shot_list, expected=expected),
        "reference_assets": references,
    }
    if accepted_logo_evidence is not None:
        accepted = dict(accepted_logo_evidence)
        path = Path(str(accepted.get("path", ""))).resolve()
        validate_generated_path(path, expected="logo_card")
        accepted["path"] = str(path)
        request["accepted_logo"] = accepted
    elif accepted_logo_path is not None:
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
    explicit_dimensions = None
    if expected is not None and not isinstance(expected, str):
        explicit_dimensions = validate_custom_dimensions(expected)
    if dimensions not in {spec[1] for spec in _OUTPUT_SPECS.values()} and dimensions != explicit_dimensions:
        raise ValueError(f"unsupported generated dimensions: {dimensions}")
    if expected is not None:
        if isinstance(expected, str):
            try:
                expected_dimensions = _OUTPUT_SPECS[expected][1]
            except KeyError as exc:
                raise ValueError(f"unsupported expected output type: {expected}") from exc
        else:
            expected_dimensions = explicit_dimensions
        if dimensions != expected_dimensions:
            raise ValueError(f"generated dimensions {dimensions} do not match expected {expected_dimensions}")
    return dimensions


def validate_custom_dimensions(value) -> tuple[int, int]:
    """Validate an explicit local template canvas dimension pair.

    Custom canvases are an offline renderer/template escape hatch.  They are
    never inferred for a host request; callers must pass the exact pair again
    when validating the returned file.
    """
    try:
        dimensions = tuple(value)
    except TypeError as exc:
        raise ValueError("custom dimensions must contain exactly two integers") from exc
    if len(dimensions) != 2 or any(type(item) is not int or item <= 0 for item in dimensions):
        raise ValueError("custom dimensions must contain exactly two positive integers")
    return dimensions  # type: ignore[return-value]
