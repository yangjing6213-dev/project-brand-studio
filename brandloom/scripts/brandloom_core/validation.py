"""Deterministic localization helpers and internal output QA."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Iterable, Mapping

from PIL import Image

from .models import BrandBrief


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
    if language:
        project["language"] = language
    return BrandBrief(
        schema_version=brief.schema_version,
        project=project,
        copy=deepcopy(dict(replacement)),
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
    return True, values["copy"]  # type: ignore[return-value]


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
                asset_id = str(entry.get("asset_id", "")).lower()
                if asset_id in {"company_logo", "company-logo", "logo"} or asset_id.startswith("logo-"):
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
) -> QAReport:
    """Run offline automated checks and report manual visual review separately."""
    output = Path(output_path)
    payload = manifest or {}
    hashes = asset_hashes or {}
    if expected_dimensions is None:
        expected_dimensions = (1280, 640) if output_type in {"social-preview", "social_preview"} else ((2048, 1024) if output_type == "cover" else (2048, 2048))
    checks: dict[str, bool] = {}
    failures: list[str] = []
    checks["output_exists"] = output.is_file()
    if not checks["output_exists"]:
        failures.append("output_missing")
    checks["dimensions"] = False
    if output.is_file():
        try:
            with Image.open(output) as image:
                checks["dimensions"] = image.size == expected_dimensions
        except (OSError, ValueError):
            checks["dimensions"] = False
    if not checks["dimensions"]:
        failures.append("dimensions")
    logo_hash = _company_logo_hash(payload, hashes)
    checks["company_logo_hash"] = bool(logo_hash)
    if not checks["company_logo_hash"]:
        failures.append("company_logo_hash")
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
    versioned = bool(re.search(r"-v\d+(?=\.[^.]+$)", output.name))
    checks["versioned_output"] = not collision or versioned
    if not checks["versioned_output"]:
        failures.append("output_collision")
    rights_fail = False
    for status in custom_ip_rights or ():
        value = status.get("rights_status", status.get("status", "")) if isinstance(status, Mapping) else status
        if str(value).lower() == "analysis_only":
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
