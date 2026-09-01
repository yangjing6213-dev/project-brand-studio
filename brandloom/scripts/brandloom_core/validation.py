"""Deterministic localization helpers and internal output QA."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from io import BytesIO
import re
from pathlib import Path
from typing import Iterable, Mapping

from PIL import Image, ImageCms

from .models import BrandBrief
from .treatments import canonicalize_logo_treatment, operation_for_treatment


@dataclass(frozen=True)
class QAReport:
    """Result of automated checks plus explicit manual-review warnings."""

    passed: bool
    checks: dict[str, bool]
    warnings: tuple[str, ...]
    failures: tuple[str, ...]

    @property
    def automated_passed(self) -> bool:
        return self.passed

    @property
    def manual_review_required(self) -> bool:
        return bool(self.warnings)


def localize_brief(
    brief: BrandBrief,
    *,
    language: str = "en",
    copy: Mapping[str, object] | None = None,
    localized_copy: Mapping[str, object] | None = None,
) -> BrandBrief:
    """Return a localized copy of a brief without mutating the source brief.

    ``copy`` is the stable keyword; ``localized_copy`` is accepted as a clear
    alias for callers that keep translations separately.  Assets, style,
    fonts, and output choices are reused byte-for-byte by reference.
    """
    if not isinstance(brief, BrandBrief):
        raise TypeError("brief must be a BrandBrief")
    replacement = localized_copy if localized_copy is not None else copy
    if replacement is None:
        replacement = brief.copy
    if not isinstance(replacement, Mapping):
        raise TypeError("copy must be a mapping")
    project = deepcopy(brief.project)
    translated_copy = deepcopy(dict(replacement))
    if language:
        translated_copy["language"] = language
    return BrandBrief(
        schema_version=brief.schema_version,
        project=project,
        copy=translated_copy,
        style=deepcopy(brief.style),
        fonts=deepcopy(brief.fonts),
        assets=deepcopy(brief.assets),
        outputs=deepcopy(brief.outputs),
    )


def _manifest_copy(manifest: Mapping[str, object]) -> Mapping[str, object] | None:
    value = manifest.get("rendered_copy")
    return value if isinstance(value, Mapping) else None


def _brief_copy(brief: BrandBrief | Mapping[str, object]) -> tuple[bool, Mapping[str, object]]:
    if isinstance(brief, BrandBrief):
        values = {name: getattr(brief, name) for name in ("project", "copy", "style", "fonts", "assets", "outputs")}
    elif isinstance(brief, Mapping):
        values = {name: brief.get(name) for name in ("project", "copy", "style", "fonts", "assets", "outputs")}
    else:
        return False, {}
    valid = all(isinstance(value, Mapping) for value in values.values())
    if not valid:
        return False, {}
    copy = values["copy"]
    assert isinstance(copy, Mapping)
    rendered: dict[str, object] = {}
    for key, value in copy.items():
        if key in {"language", "direction"}:
            if value is not None and not isinstance(value, str):
                return False, {}
            continue
        if key not in {"title", "subtitle", "value_line", "features"}:
            if value not in (None, "", (), [], {}):
                return False, {}
            continue
        if value in (None, "", (), []):
            continue
        if key == "features":
            if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
                return False, {}
            rendered[key] = list(value)
        elif not isinstance(value, str):
            return False, {}
        else:
            rendered[key] = value
    return True, rendered


def _company_logo_hash(manifest: Mapping[str, object], asset_hashes: Mapping[str, object]) -> str:
    direct = asset_hashes.get("company_logo", "")
    if direct:
        return str(direct)
    assets = manifest.get("assets", [])
    if isinstance(assets, Mapping):
        entry = assets.get("company_logo", {})
        if isinstance(entry, Mapping):
            return str(entry.get("sha256", ""))
    if isinstance(assets, Iterable) and not isinstance(assets, (str, bytes)):
        for entry in assets:
            if isinstance(entry, Mapping):
                category = str(entry.get("category", ""))
                rights = str(entry.get("rights_status", ""))
                if category == "company-logo":
                    if rights and rights != "user_authorized":
                        return ""
                    return str(entry.get("observed_sha256", entry.get("sha256", "")))
                asset_id = str(entry.get("asset_id", "")).lower()
                if not category and (asset_id in {"company_logo", "company-logo", "logo"} or asset_id.startswith("logo-")):
                    return str(entry.get("sha256", ""))
    return ""


def _path_collision(output_path: Path, existing: Iterable[object] | None) -> bool:
    if existing is None:
        return False
    target = output_path.resolve()
    for value in existing:
        candidate = Path(value).resolve()
        if candidate == target:
            return True
    return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", value))


def _recorded_path(value: object, base: Path | None) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    return path.resolve()


def _entry_integrity(
    entry: object,
    *,
    base: Path | None,
    expected_path: Path | None = None,
) -> bool:
    if not isinstance(entry, Mapping):
        return False
    path = _recorded_path(entry.get("path"), base)
    digest = entry.get("sha256")
    if path is None or not path.is_file() or not _valid_sha256(digest):
        return False
    if expected_path is not None and path != Path(expected_path).resolve():
        return False
    return _sha256(path) == str(digest).lower()


def validate_accepted_logo_evidence(evidence: object, *, expected_slug: str | None = None) -> bool:
    if not isinstance(evidence, Mapping):
        return False
    required = ("path", "sha256", "manifest_path", "manifest_sha256", "manifest_output_sha256", "output_type", "slug")
    if any(not isinstance(evidence.get(key), str) or not evidence[key] for key in required):
        return False
    output = Path(str(evidence["path"])); manifest_path = Path(str(evidence["manifest_path"]))
    if not output.is_absolute() or not manifest_path.is_absolute() or output != output.resolve() or manifest_path != manifest_path.resolve():
        return False
    if expected_slug is not None and evidence.get("slug") != expected_slug:
        return False
    if str(evidence["output_type"]).replace("-", "_") != "logo_card":
        return False
    if not _valid_sha256(evidence["sha256"]) or not _valid_sha256(evidence["manifest_sha256"]) or not _valid_sha256(evidence["manifest_output_sha256"]):
        return False
    if not output.is_file() or not manifest_path.is_file():
        return False
    if _sha256(output) != str(evidence["sha256"]).lower() or _sha256(manifest_path) != str(evidence["manifest_sha256"]).lower():
        return False
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, Mapping) or str(payload.get("output_type", "")).replace("-", "_") != "logo_card":
        return False
    entry = payload.get("output")
    recorded = _recorded_path(entry.get("path"), manifest_path.parent) if isinstance(entry, Mapping) else None
    digest = entry.get("sha256") if isinstance(entry, Mapping) else None
    return recorded == output and _valid_sha256(digest) and str(digest).lower() == str(evidence["manifest_output_sha256"]).lower() == str(evidence["sha256"]).lower()


def _asset_integrity(entry: object, *, base: Path | None) -> bool:
    if not isinstance(entry, Mapping):
        return False
    if not all(isinstance(entry.get(key), str) and str(entry[key]).strip() for key in (
        "asset_id", "category", "scope", "rights_status", "path",
    )):
        return False
    if entry.get("rights_status") != "user_authorized":
        return False
    expected = entry.get("expected_sha256")
    observed = entry.get("observed_sha256")
    if not _valid_sha256(expected) or not _valid_sha256(observed) or str(expected).lower() != str(observed).lower():
        return False
    path = _recorded_path(entry.get("path"), base)
    if path is None or not path.is_file() or _sha256(path) != str(observed).lower():
        return False
    digest = entry.get("sha256")
    return not digest or (isinstance(digest, str) and digest.lower() == str(observed).lower())


def _host_request_integrity(value: object, *, base: Path | None, require_accepted_logo: bool = False, expected_output_type: str | None = None, expected_dimensions: tuple[int, int] | None = None) -> bool:
    if value is None:
        return False
    if not isinstance(value, Mapping) or value.get("schema_version") != "1.0" or value.get("backend") != "host_builtin_image_tool":
        return False
    if expected_output_type and str(value.get("output_type", "")).replace("-", "_") != expected_output_type:
        return False
    ratio = "1:1" if expected_dimensions == (1254, 1254) else "2:1" if expected_dimensions == (1774, 887) else None
    if not isinstance(value.get("output_type"), str) or not isinstance(value.get("aspect_ratio"), str) or (ratio and value.get("aspect_ratio") != ratio):
        return False
    if not isinstance(value.get("dimensions"), list) or tuple(value["dimensions"]) != expected_dimensions or not isinstance(value.get("prompt"), str) or not value["prompt"]:
        return False
    if "reference_assets" not in value:
        return False
    references = value["reference_assets"]
    if not isinstance(references, list):
        return False
    for entry in references:
        if not isinstance(entry, Mapping):
            return False
        raw_path = entry.get("path")
        path = _recorded_path(raw_path, base)
        digest = entry.get("sha256")
        if (
            path is None or not isinstance(raw_path, str) or not Path(raw_path).is_absolute() or Path(raw_path) != path
            or not path.is_file()
            or not _valid_sha256(digest)
            or _sha256(path) != str(digest).lower()
            or entry.get("rights_status") != "user_authorized"
            or entry.get("category") != "ip-character"
            or not isinstance(entry.get("profile_cues"), str)
            or not entry.get("profile_cues")
        ):
            return False
    accepted = value.get("accepted_logo")
    if require_accepted_logo and accepted is None:
        return False
    if accepted is not None and not validate_accepted_logo_evidence(accepted):
        return False
    return True


def _png_checks(output: Path, expected_dimensions: tuple[int, int]) -> dict[str, bool]:
    result = {"png_decode": False, "dimensions": False, "color_mode": False, "srgb": False}
    if not output.is_file():
        return result
    try:
        with Image.open(output) as image:
            image.load()
            result["png_decode"] = image.format == "PNG"
            result["dimensions"] = image.size == expected_dimensions
            result["color_mode"] = image.mode in {"RGB", "RGBA"}
            profile_bytes = image.info.get("icc_profile")
            if profile_bytes is None:
                result["srgb"] = result["color_mode"]
            elif isinstance(profile_bytes, bytes):
                try:
                    profile = ImageCms.ImageCmsProfile(BytesIO(profile_bytes))
                    result["srgb"] = "srgb" in ImageCms.getProfileDescription(profile).casefold()
                except (ImageCms.PyCMSError, OSError, ValueError):
                    result["srgb"] = False
    except (OSError, SyntaxError, ValueError):
        pass
    return result


def validate_output(
    output_path: Path,
    *,
    expected_dimensions: tuple[int, int] | None = None,
    manifest: Mapping[str, object] | None = None,
    brief: BrandBrief | Mapping[str, object] | None = None,
    asset_hashes: Mapping[str, object] | None = None,
    output_type: str | None = None,
    existing_output_paths: Iterable[object] | None = None,
    existing_outputs: Iterable[object] | None = None,
    custom_ip_rights: Iterable[object] | None = None,
    logo_card_ip: Iterable[object] | None = None,
    confirmed_ip_count: int = 3,
    manual_visual_checks: bool = False,
    brief_path: Path | None = None,
    manifest_path: Path | None = None,
    output_root: Path | None = None,
) -> QAReport:
    """Run offline automated checks and report manual visual review separately."""
    output = Path(output_path)
    payload = manifest or {}
    hashes = asset_hashes or {}
    if expected_dimensions is None:
        expected_dimensions = (1280, 640) if output_type in {"social-preview", "social_preview"} else ((1774, 887) if output_type == "cover" else (1254, 1254))
    checks: dict[str, bool] = {}
    failures: list[str] = []
    checks["output_exists"] = output.is_file()
    if not checks["output_exists"]:
        failures.append("output_missing")
    checks.update(_png_checks(output, expected_dimensions))
    for name in ("png_decode", "dimensions", "color_mode", "srgb"):
        if not checks[name]:
            failures.append(name)

    manifest_base = Path(manifest_path).resolve().parent if manifest_path is not None else None
    checks["manifest_brief"] = _entry_integrity(payload.get("brief"), base=manifest_base, expected_path=brief_path)
    checks["manifest_template"] = _entry_integrity(payload.get("template"), base=manifest_base)
    checks["manifest_base_image"] = _entry_integrity(payload.get("base_image"), base=manifest_base)
    checks["manifest_output"] = _entry_integrity(payload.get("output"), base=manifest_base, expected_path=output)
    fonts = payload.get("fonts")
    checks["manifest_fonts"] = (
        isinstance(fonts, Mapping)
        and bool(fonts)
        and all(_entry_integrity(entry, base=manifest_base) for entry in fonts.values())
    )
    assets = payload.get("assets")
    checks["manifest_assets"] = (
        isinstance(assets, list)
        and bool(assets)
        and all(_asset_integrity(entry, base=manifest_base) for entry in assets)
    )
    requested_type = payload.get("output_type")
    expected_type = str(output_type or "").replace("-", "_")
    checks["manifest_output_type"] = (
        isinstance(requested_type, str)
        and bool(requested_type.strip())
        and (not expected_type or requested_type.replace("-", "_") == expected_type)
    )
    checks["manifest_rendered_copy"] = isinstance(payload.get("rendered_copy"), Mapping)
    checks["manifest_host_request"] = _host_request_integrity(
        payload.get("host_request"), base=manifest_base,
        require_accepted_logo=str(requested_type).replace("-", "_") == "cover",
        expected_output_type=expected_type,
        expected_dimensions=expected_dimensions,
    )
    output_entry = payload.get("output")
    recorded_output = _recorded_path(output_entry.get("path"), manifest_base) if isinstance(output_entry, Mapping) else None
    checks["output_manifest_path"] = recorded_output == output.resolve()
    if output_root is None:
        checks["output_contained"] = True
    else:
        root = Path(output_root).resolve()
        checks["output_contained"] = output.resolve().is_relative_to(root)
    for name in (
        "manifest_brief", "manifest_template", "manifest_base_image", "manifest_output",
        "manifest_fonts", "manifest_assets", "manifest_host_request", "output_manifest_path",
        "manifest_output_type", "manifest_rendered_copy", "output_contained",
    ):
        if not checks[name]:
            failures.append(name)
    logo_hash = _company_logo_hash(payload, hashes)
    checks["company_logo_hash"] = bool(logo_hash)
    if not checks["company_logo_hash"]:
        failures.append("company_logo_hash")
    treatment_raw = payload.get("logo_treatment")
    expected_treatment = None
    if brief is not None:
        brief_assets = brief.assets if isinstance(brief, BrandBrief) else brief.get("assets", {}) if isinstance(brief, Mapping) else {}
        if isinstance(brief_assets, Mapping):
            brief_selected = brief_assets.get("company_logo_treatment", brief_assets.get("logo_treatment"))
            if brief_selected not in (None, ""):
                try:
                    expected_treatment = canonicalize_logo_treatment(brief_selected)
                except ValueError:
                    expected_treatment = "invalid"
                treatment_raw = brief_selected if treatment_raw is None else treatment_raw
    try:
        treatment = canonicalize_logo_treatment(treatment_raw)
        treatment_valid = isinstance(treatment_raw, str) or treatment_raw is None
    except ValueError:
        treatment, treatment_valid = "default", False
    checks["manifest_logo_treatment"] = treatment_valid and (expected_treatment is None or treatment == expected_treatment)
    checks["manifest_logo_operation"] = True
    checks["manifest_logo_confirmation"] = True
    checks["manifest_logo_source_hash"] = True
    if treatment != "default":
        operation = payload.get("logo_operation")
        confirmation = payload.get("logo_confirmation")
        source_hash = payload.get("logo_source_hash")
        checks["manifest_logo_operation"] = operation == operation_for_treatment(treatment)
        checks["manifest_logo_confirmation"] = confirmation == treatment
        checks["manifest_logo_source_hash"] = isinstance(source_hash, str) and bool(source_hash) and source_hash == logo_hash
        company_entries = [entry for entry in (assets if isinstance(assets, list) else ())
                           if isinstance(entry, Mapping) and str(entry.get("category", "")) == "company-logo"]
        checks["manifest_logo_source_hash"] = checks["manifest_logo_source_hash"] and bool(company_entries) and all(
            str(entry.get("sha256", entry.get("observed_sha256", ""))) == str(source_hash) for entry in company_entries
        )
    for name in ("manifest_logo_treatment", "manifest_logo_operation", "manifest_logo_confirmation", "manifest_logo_source_hash"):
        if not checks[name]:
            failures.append(name)
    if brief is not None:
        brief_valid, expected_copy = _brief_copy(brief)
        checks["brief_schema"] = brief_valid
        if not brief_valid:
            failures.append("brief_schema")
        canonical_copy = _manifest_copy(payload)
        checks["manifest_copy"] = brief_valid and canonical_copy is not None and canonical_copy == expected_copy
        if not checks["manifest_copy"]:
            failures.append("manifest_copy")
    else:
        checks["brief_schema"] = True
        checks["manifest_copy"] = True
    collision_values = existing_output_paths if existing_output_paths is not None else existing_outputs
    collision = _path_collision(output, collision_values)
    versioned = bool(re.search(r"-v\d{2,}(?=\.png$)", output.name, flags=re.IGNORECASE))
    checks["versioned_output"] = not collision and versioned
    if not checks["versioned_output"]:
        failures.append("output_collision")
    rights_fail = False
    for status in custom_ip_rights or ():
        value = status.get("rights_status", status.get("status", "")) if isinstance(status, Mapping) else status
        if str(value).lower() != "user_authorized":
            rights_fail = True
    checks["custom_ip_rights"] = not rights_fail
    if rights_fail:
        failures.append("custom_ip_analysis_only")
    selected = list(logo_card_ip or ())
    checks["logo_card_ip_count"] = len(selected) <= max(0, int(confirmed_ip_count))
    if not checks["logo_card_ip_count"]:
        failures.append("logo_card_ip_count")
    warnings = () if manual_visual_checks else ("manual_visual_review_required",)
    checks["manual_visual_review"] = bool(manual_visual_checks)
    return QAReport(not failures, checks, tuple(warnings), tuple(failures))
