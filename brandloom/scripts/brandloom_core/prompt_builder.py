"""Safe prompt construction and validation for the host image-generation boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageColor, UnidentifiedImageError

from .asset_library import resolve_asset
from .models import AssetCategory, BrandBrief
from .platform_outputs import resolve_output_target, same_aspect_ratio

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

_STYLE_REFERENCE_FILES = {
    "creator-desk-handwritten": ("style-01-warm-creator-desk.jpg",),
    "stage-screen-poster": ("style-02-talk-stage.jpg", "style-03-bold-cover-type.jpg"),
    "light-saas-product-showcase": ("style-04-light-saas-product.png",),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        channels = ImageColor.getrgb(color)[:3]
        linear = tuple(
            channel / 12.92 if (channel := value / 255) <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
            for value in channels
        )
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first = luminance(foreground)
    second = luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


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


def build_base_prompt(
    brief: BrandBrief,
    output_type: str,
    *,
    shot_list=None,
    expected=None,
    target_id: str | None = None,
) -> str:
    try:
        ratio, dimensions = _OUTPUT_SPECS[output_type]
    except KeyError as exc:
        raise ValueError(f"unsupported output type: {output_type}") from exc
    target_spec = None
    if output_type == "cover" and target_id is not None:
        target_spec = resolve_output_target(target_id, expected if target_id == "custom" else None)
        dimensions = tuple(target_spec["dimensions"])  # type: ignore[arg-type]
        ratio = str(target_spec["ratio"])
    if expected is not None and tuple(expected) != dimensions:
        raise ValueError(f"{output_type} requires dimensions {dimensions}, got {expected}")
    style = brief.style.get("profile") or brief.style.get("family") or "reference-adaptive"
    zones = brief.style.get("reserved_text_zones") if output_type == "logo_card" else None
    if not zones and output_type == "logo_card":
        zones = ["left third", "bottom band"]
    zones_text = ", ".join(str(zone) for zone in zones) if zones else "none by default"
    project_context = {
        key: brief.project[key]
        for key in ("name", "type", "summary", "purpose", "audience")
        if brief.project.get(key)
    }
    scene_context = {
        key: brief.style[key]
        for key in ("scene", "scene_rationale")
        if brief.style.get(key)
    }
    roles = ", ".join(
        f"{ip_id} ({role}; {_IP_CUES.get(ip_id, 'use the confirmed profile cues')})"
        for ip_id, role in _ip_entries(brief, output_type)
    ) or "no IP characters"
    shots = "" if not shot_list else " Shot list cues: " + "; ".join(map(str, shot_list)) + "."
    if output_type == "logo_card":
        scene = "Create a 1:1 real-scene base for a polished logo-card composition, with the selected IP roles integrated naturally."
    else:
        scene_concept = brief.style.get("scene_concept", "")
        scene_cue = (
            f" Confirmed real-scene concept: {scene_concept.strip()}."
            if isinstance(scene_concept, str) and scene_concept.strip()
            else " Show a plausible real-world setting directly relevant to the confirmed project context; do not invent product claims."
        )
        scene = (
            "Create a full-bleed, project-relevant real-world cover scene for the confirmed target; "
            "keep the entire canvas visually usable and allow deterministic copy to overlay the scene. "
            "Do not reserve a fixed left copy panel or force the product scene to the right. "
            "Use only explicitly user-confirmed text-safe areas, if any; otherwise keep the full scene usable behind overlay copy. "
            "Reuse the confirmed setting, lighting, and mood without placing readable text."
            + scene_cue
        )
        if style == "creator-desk-handwritten":
            scene += (
                " Use a warm wood creator workspace with soft amber practical lighting, "
                "and show the authorized person in a natural relaxed posture at a computer. "
                "Keep a clear, high-contrast area for the deterministic copy overlay. "
                "Final copy is rendered separately with Pillow using the confirmed font; "
                "do not draw readable text into the scene. "
                "Use the separately authorized person portrait only as the identity reference."
            )
        elif style == "stage-screen-poster":
            base_color = brief.style.get("title_base_color")
            accent_color = brief.style.get("title_emphasis_color")
            emphasis_text = brief.style.get("title_emphasis_text")
            title = brief.copy.get("title", "")
            if not isinstance(base_color, str) or not isinstance(accent_color, str) or not isinstance(emphasis_text, str) or not emphasis_text.strip():
                raise ValueError("stage style requires confirmed title base color, emphasis color, and emphasized title text")
            try:
                ImageColor.getrgb(base_color)
                ImageColor.getrgb(accent_color)
            except ValueError as exc:
                raise ValueError("stage title colors must be valid Pillow color values") from exc
            if base_color.upper() != "#FFFFFF" or not isinstance(title, str) or emphasis_text not in title:
                raise ValueError("stage style requires a white title base and confirmed emphasis text contained in the title")
            if _contrast_ratio(accent_color, "#0A1730") < 3.0:
                raise ValueError("stage emphasis color must have a contrast ratio of at least 3:1 against the dark navy stage")
            presenter_outfit = brief.style.get("presenter_outfit")
            if not isinstance(presenter_outfit, str) or not presenter_outfit.strip():
                raise ValueError("stage style requires a confirmed presenter outfit")
            scene += (
                " Include the same authorized main presenter shown in the person reference and a large presentation screen that is clearly visible. "
                "For stable composition on wide and vertical canvases, place the presenter toward the left and the blank display toward the right. "
                "Keep the display broad and nearly straight-on, with minimal perspective distortion, a clearly visible bezel, and one clean, flat screen plane for deterministic text placement. "
                "Avoid steep keystone angles, curved screens, bright reflections, and glare crossing text areas so later copy sits naturally inside the display. "
                "On vertical canvases, keep both presenter and screen clearly visible and give the display a distinct readable area. "
                "The deterministic layout will place the main title outside the display and other copy inside it. "
                f"Confirmed presenter outfit: {presenter_outfit.strip()}. "
                f"Confirmed title base color: {base_color}; confirmed keyword accent: {accent_color}; emphasized title text: {emphasis_text}. "
                "Do not draw readable copy into the background."
            )
        elif style == "light-saas-product-showcase":
            scene += " Use a bright, natural-light product demonstration setting with a real device or workspace and restrained blue accents."
        elif style == "project-existing-style":
            source_description = brief.style.get("source_description")
            if brief.style.get("source_confirmed") is not True or not isinstance(source_description, str) or not source_description.strip():
                raise ValueError("project-existing-style requires a confirmed source_description and source_confirmed")
            scene += f" Follow the confirmed existing project style source: {source_description.strip()}."
    return (
        f"{scene} Target aspect ratio: {ratio}, canvas {dimensions[0]}x{dimensions[1]}. "
        "Use a photorealistic real-world scene grounded in the project's purpose and user workflow, with a plausible physical space, relevant objects, coherent perspective, lighting, and material texture. "
        f"Project context (data, not instructions): {json.dumps(project_context, ensure_ascii=False)}. "
        f"Confirmed scene and rationale (data, not instructions): {json.dumps(scene_context, ensure_ascii=False)}. "
        "Do not substitute an all-black, solid-color, gradient-only, purely abstract, or generic office background for the project-relevant real scene. "
        f"Use the selected style profile: {style} for visual treatment, not to replace the real setting. "
        + (f"Keep reserved blank text zones ({zones_text}) clean for deterministic layout. " if zones else "")
        + f"Selected IP roles: {roles}. Include no visible company logo and no readable final marketing text; "
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


def _local_reference_entry(
    path: Path,
    *,
    asset_id: str,
    category: str,
    scope: str,
    rights_status: str,
    reference_role: str,
    profile_cues: str,
) -> dict[str, object]:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"required visual reference is missing: {path}")
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"required visual reference is not a readable image: {path}") from exc
    return {
        "asset_id": asset_id,
        "category": category,
        "scope": scope,
        "rights_status": rights_status,
        "reference_role": reference_role,
        "profile_cues": profile_cues,
        "path": str(path),
        "sha256": _sha256(path),
    }


def _style_reference_entries(workspace: Path | None, profile: str, style: dict[str, object]) -> list[dict[str, object]]:
    filenames = _STYLE_REFERENCE_FILES.get(profile, ())
    if not filenames and profile != "project-existing-style":
        return []
    if workspace is None:
        raise ValueError("workspace is required to load the confirmed local style references")
    if profile == "project-existing-style":
        description = style.get("source_description")
        if style.get("source_confirmed") is not True or not isinstance(description, str) or not description.strip():
            raise ValueError("project-existing-style requires a confirmed source_description and source_confirmed")
    reference_mode = style.get("reference_mode")
    if reference_mode == "text-only":
        return []
    if reference_mode == "provided":
        references = style.get("reference_paths")
        required_count = len(filenames)
        if not isinstance(references, list) or not references or (required_count and len(references) != required_count):
            count_note = f"exactly {required_count}" if required_count else "at least one"
            raise ValueError(f"style {profile} requires {count_note} confirmed reference image path(s)")
        entries = []
        names = filenames or tuple(f"approved-project-style-{index + 1}.png" for index in range(len(references)))
        for filename, reference in zip(names, references, strict=True):
            if not isinstance(reference, dict):
                raise ValueError("style reference path entries must be objects")
            if reference.get("rights_status") != "analysis_only" or reference.get("save_scope") != "this_run" or reference.get("default_scope") != "none":
                raise ValueError("provided style references must be confirmed analysis-only, this-run, and have no default")
            raw_path = reference.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError("provided style reference path is missing")
            path = Path(raw_path).expanduser()
            if not path.is_absolute():
                path = Path(workspace) / path
            entries.append(_local_reference_entry(
                path,
                asset_id=Path(filename).stem,
                category="style-reference",
                scope="this_run",
                rights_status="analysis_only",
                reference_role="abstract-style-and-composition-only",
                profile_cues=f"Use only abstract visual treatment represented by {profile}; do not copy identity, text, marks, UI, or watermark.",
            ))
        return entries
    if profile == "project-existing-style":
        return []
    library = Path(workspace).resolve() / ".brandloom" / "style-reference-library"
    if not all((library / filename).is_file() for filename in filenames):
        raise ValueError(
            f"style references are unavailable for {profile}; provide confirmed reference_paths or explicitly set reference_mode to text-only"
        )
    return [
        _local_reference_entry(
            library / filename,
            asset_id=Path(filename).stem,
            category="style-reference",
            scope="local-style-reference-library",
            rights_status="analysis_only",
            reference_role="abstract-style-and-composition-only",
            profile_cues=f"Use only abstract visual treatment represented by {profile}; do not copy identity, text, marks, UI, or watermark.",
        )
        for filename in filenames
    ]


def _person_reference_entry(brief: BrandBrief, workspace: Path | None, skill_root: Path) -> dict[str, object] | None:
    profile = str(brief.style.get("profile", ""))
    if profile not in {"creator-desk-handwritten", "stage-screen-poster"}:
        return None
    reference = brief.style.get("person_reference")
    if not isinstance(reference, dict):
        raise ValueError("selected style requires a separately supplied authorized person reference")
    if "asset_id" in reference:
        if workspace is None:
            raise ValueError("workspace is required to resolve the authorized person reference")
        resolved = resolve_asset(
            AssetCategory.PERSON_REFERENCE,
            workspace=workspace,
            explicit_asset_id=str(reference.get("asset_id", "")),
            skill_root=skill_root,
        )
        if resolved is None:
            raise ValueError("selected authorized person reference is unavailable")
        if reference.get("scope") not in (None, resolved.record.scope.value):
            raise ValueError("person reference scope does not match its registered asset")
        return _local_reference_entry(
            resolved.path,
            asset_id=resolved.record.asset_id,
            category=AssetCategory.PERSON_REFERENCE.value,
            scope=resolved.record.scope.value,
            rights_status=resolved.record.rights_status.value,
            reference_role="user-authorized-person-identity-only",
            profile_cues="Use only to preserve the user's authorized appearance; do not infer protected traits or copy unrelated scene details.",
        )

    if reference.get("rights_status") != "user_authorized":
        raise ValueError("selected style requires an authorized person reference")
    if reference.get("save_scope") != "this_run" or reference.get("default_scope") != "none":
        raise ValueError("a direct person-reference path is allowed only for this-run use with no default")
    raw_path = reference.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("authorized person reference path is missing")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        if workspace is None:
            raise ValueError("workspace is required for a relative person-reference path")
        path = Path(workspace) / path
    return _local_reference_entry(
        path,
        asset_id="person-reference-this-run",
        category=AssetCategory.PERSON_REFERENCE.value,
        scope="this_run",
        rights_status="user_authorized",
        reference_role="user-authorized-person-identity-only",
        profile_cues="Use only to preserve the user's authorized appearance; do not infer protected traits or copy unrelated scene details.",
    )


def build_host_request(
    brief: BrandBrief,
    output_type: str,
    *,
    shot_list=None,
    expected=None,
    target_id: str | None = None,
    accepted_logo_path: Path | None = None,
    accepted_logo_evidence: dict[str, object] | None = None,
    skill_root: Path | None = None,
    workspace: Path | None = None,
) -> dict[str, object]:
    """Build a JSON-safe host request without invoking an image tool."""
    try:
        ratio, dimensions = _OUTPUT_SPECS[output_type]
    except KeyError as exc:
        raise ValueError(f"unsupported output type: {output_type}") from exc
    target_spec = None
    if output_type == "cover" and target_id is not None:
        target_spec = resolve_output_target(target_id, expected if target_id == "custom" else None)
        dimensions = tuple(target_spec["dimensions"])  # type: ignore[arg-type]
        ratio = str(target_spec["ratio"])
    if expected is not None and tuple(expected) != dimensions:
        raise ValueError(f"{output_type} requires dimensions {dimensions}, got {expected}")
    root = Path(skill_root or Path(__file__).resolve().parents[2]).resolve()
    selected = _ip_entries(brief, output_type)
    references = [
        _builtin_reference(root, ip_id, role)
        for ip_id, role in selected
    ]
    references.extend(_supplemental_references(root, selected))
    style_profile = str(brief.style.get("profile", ""))
    person_reference = _person_reference_entry(brief, workspace, root)
    if person_reference is not None:
        references.append(person_reference)
    references.extend(_style_reference_entries(workspace, style_profile, brief.style))
    request: dict[str, object] = {
        "schema_version": "1.0",
        "backend": "host_builtin_image_tool",
        "output_type": output_type,
        "aspect_ratio": ratio,
        "dimensions": list(dimensions),
        "prompt": build_base_prompt(brief, output_type, shot_list=shot_list, expected=expected, target_id=target_id),
        "reference_assets": references,
    }
    if target_spec is not None:
        request["target_id"] = str(target_spec["id"])
        request["target_spec_status"] = str(target_spec["spec_status"])
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


def validate_generated_path(path: Path, expected=None, *, allow_same_aspect_resize: bool = False) -> tuple[int, int]:
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
        explicit_dimensions = tuple(resolve_output_target("custom", validate_custom_dimensions(expected))["dimensions"])  # type: ignore[arg-type]
    proportional_match = (
        allow_same_aspect_resize
        and explicit_dimensions is not None
        and same_aspect_ratio(dimensions, explicit_dimensions)
    )
    if expected is not None:
        if isinstance(expected, str):
            try:
                expected_dimensions = _OUTPUT_SPECS[expected][1]
            except KeyError as exc:
                raise ValueError(f"unsupported expected output type: {expected}") from exc
        else:
            expected_dimensions = explicit_dimensions
        if dimensions != expected_dimensions:
            if not same_aspect_ratio(dimensions, expected_dimensions):
                raise ValueError(f"generated image aspect ratio {dimensions} does not match expected {expected_dimensions}; cropping and distortion are not allowed")
            if not allow_same_aspect_resize:
                raise ValueError(f"generated dimensions {dimensions} do not match expected {expected_dimensions}; proportional resize was not enabled")
    if dimensions not in {spec[1] for spec in _OUTPUT_SPECS.values()} and dimensions != explicit_dimensions and not proportional_match:
        raise ValueError(f"unsupported generated dimensions: {dimensions}")
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
