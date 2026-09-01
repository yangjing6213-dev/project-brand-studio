"""Rights-aware, local-first persistence for BrandLoom image assets."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from PIL import Image

from .json_io import _construct, _to_json
from .models import AssetCategory, AssetRecord, AssetScope, RightsStatus
from .paths import project_root, resolve_personal_root


_GENERATION_CATEGORIES = {
    AssetCategory.COMPANY_LOGO,
    AssetCategory.PROJECT_MARK,
    AssetCategory.IP_CHARACTER,
}
_COMPANY_LOGO_FORBIDDEN = (
    "redraw", "distort", "change_letterforms", "change_geometry", "use_as_training_reference"
)
_COMPANY_LOGO_ALLOWED = ("scale", "position", "recolor_monochrome")


class AssetManifestError(ValueError):
    """Raised when an existing asset manifest cannot be trusted."""


@dataclass(frozen=True)
class ResolvedAsset:
    record: AssetRecord
    path: Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scope_root(scope: AssetScope, workspace: Path | None) -> Path:
    if scope is AssetScope.PROJECT:
        if workspace is None:
            raise ValueError("workspace is required for project-scoped assets")
        return project_root(workspace)
    if scope is AssetScope.PERSONAL:
        return resolve_personal_root()
    # Skill defaults are read-only and should not be registered by this library.
    raise ValueError("skill-defaults assets are read-only")


def _manifest_path(root: Path) -> Path:
    return root / "asset-manifest.json"


def _load_records(root: Path) -> list[AssetRecord]:
    path = _manifest_path(root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        values = data.get("assets", data) if isinstance(data, dict) else data
        if not isinstance(values, list):
            raise AssetManifestError(f"asset manifest assets must be a list: {path}")
        if any(not isinstance(item, dict) for item in values):
            raise AssetManifestError(f"asset manifest contains a non-record entry: {path}")
        return [_construct(item, AssetRecord) for item in values]
    except AssetManifestError:
        raise
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise AssetManifestError(f"invalid existing asset manifest: {path}") from exc


def _write_records(root: Path, records: Iterable[AssetRecord]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    destination = _manifest_path(root)
    temporary = destination.with_name(destination.name + ".tmp")
    payload = {"assets": [_to_json(record) for record in records]}
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._")
    return value or "asset"


def _as_category(value: AssetCategory | str) -> AssetCategory:
    return value if isinstance(value, AssetCategory) else AssetCategory(value)


def _as_scope(value: AssetScope | str) -> AssetScope:
    return value if isinstance(value, AssetScope) else AssetScope(value)


def _as_rights(value: RightsStatus | str) -> RightsStatus:
    return value if isinstance(value, RightsStatus) else RightsStatus(value)


def register_asset(
    source: Path,
    *,
    category: AssetCategory,
    scope: AssetScope,
    workspace: Path | None = None,
    rights_status: RightsStatus = RightsStatus.UNKNOWN,
    save_scope_confirmed: bool = False,
    make_default: bool = False,
    asset_id: str | None = None,
    allowed_operations: tuple[str, ...] | None = None,
    forbidden_operations: tuple[str, ...] | None = None,
    default_scope: AssetScope | None = None,
) -> AssetRecord:
    """Validate, copy, and register an image, atomically updating its manifest."""
    if not save_scope_confirmed:
        raise ValueError("save_scope_confirmed must be true before saving an asset")
    source = Path(source)
    if not source.is_file() or not os.access(source, os.R_OK):
        raise ValueError(f"asset source is not a readable regular file: {source}")
    category = _as_category(category)
    scope = _as_scope(scope)
    rights_status = _as_rights(rights_status)
    if scope is AssetScope.SKILL_DEFAULTS:
        raise ValueError("skill-defaults assets are read-only")
    if category in _GENERATION_CATEGORIES and rights_status in (RightsStatus.MISSING, RightsStatus.UNKNOWN):
        raise ValueError(f"{rights_status.value} rights cannot be used for generation-capable assets")
    if make_default and rights_status is not RightsStatus.USER_AUTHORIZED:
        raise ValueError("only user_authorized assets may become defaults")
    try:
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:
            width, height = image.size
            suffix = source.suffix.lower() or ".png"
    except Exception as exc:
        raise ValueError(f"asset source is not a readable image: {source}") from exc
    digest = sha256_file(source)
    root = _scope_root(scope, workspace)
    records = _load_records(root)
    for existing in records:
        if existing.scope is scope and existing.category is category and existing.sha256 == digest:
            if make_default:
                set_default(existing.asset_id, category=category, scope=scope, workspace=workspace)
                return resolve_default(category, scope, workspace) or existing
            return existing

    safe_id = _slug(asset_id or f"{_slug(source.stem)}-{digest[:12]}")
    # An explicit ID is a logical record identity.  Preserve it for the first
    # record, then version collisions so defaults can address one record only.
    existing_ids = {record.asset_id for record in records if record.scope is scope and record.category is category}
    if safe_id in existing_ids:
        identity_version = 2
        candidate = f"{safe_id}-v{identity_version:02d}"
        while candidate in existing_ids:
            identity_version += 1
            candidate = f"{safe_id}-v{identity_version:02d}"
        safe_id = candidate
    library_dir = root / "library" / category.value
    library_dir.mkdir(parents=True, exist_ok=True)
    version = 1
    while True:
        filename = f"{safe_id}-v{version:02d}{suffix}"
        destination = library_dir / filename
        if not destination.exists():
            break
        version += 1
    shutil.copy2(source, destination)
    relative_path = destination.relative_to(root).as_posix()
    forbidden = tuple(forbidden_operations or ())
    if category is AssetCategory.COMPANY_LOGO:
        forbidden = tuple(dict.fromkeys((*forbidden, *_COMPANY_LOGO_FORBIDDEN)))
    allowed = tuple(allowed_operations or (("scale", "position") if category is AssetCategory.COMPANY_LOGO else ()))
    record = AssetRecord(
        asset_id=safe_id,
        category=category,
        scope=scope,
        relative_path=relative_path,
        sha256=digest,
        width=width,
        height=height,
        rights_status=rights_status,
        save_scope_confirmed=True,
        default_scope=scope if make_default else default_scope,
        allowed_operations=allowed,
        forbidden_operations=forbidden,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    if make_default:
        records = [r if not (r.scope is scope and r.category is category) else AssetRecord(**{**r.__dict__, "default_scope": None}) for r in records]
    _write_records(root, [*records, record])
    return record


def list_assets(
    workspace: Path | None = None,
    *,
    scope: AssetScope | None = None,
    category: AssetCategory | None = None,
) -> tuple[AssetRecord, ...]:
    scopes = (scope,) if scope is not None else (AssetScope.PROJECT, AssetScope.PERSONAL)
    records: list[AssetRecord] = []
    for item_scope in scopes:
        try:
            root = _scope_root(_as_scope(item_scope), workspace)
        except ValueError:
            continue
        records.extend(_load_records(root))
    if category is not None:
        category = _as_category(category)
        records = [record for record in records if record.category is category]
    return tuple(records)


def set_default(
    asset: AssetRecord | str,
    *,
    category: AssetCategory | None = None,
    scope: AssetScope | None = None,
    workspace: Path | None = None,
) -> None:
    exact_record = asset if isinstance(asset, AssetRecord) else None
    if exact_record is not None:
        asset_id, category, scope = exact_record.asset_id, exact_record.category, exact_record.scope
    else:
        asset_id = asset
    if category is None or scope is None:
        raise ValueError("category and scope are required")
    category, scope = _as_category(category), _as_scope(scope)
    root = _scope_root(scope, workspace)
    records = _load_records(root)
    candidates = [
        record for record in records
        if record.asset_id == asset_id and record.category is category and record.scope is scope
    ]
    if not candidates:
        raise ValueError(f"asset not found: {asset_id}")
    if exact_record is not None:
        candidates = [
            record for record in candidates
            if record.sha256 == exact_record.sha256 and record.relative_path == exact_record.relative_path
        ]
    if not candidates:
        raise ValueError(f"asset not found: {asset_id}")
    if any(record.rights_status is not RightsStatus.USER_AUTHORIZED for record in candidates):
        raise ValueError("only user_authorized assets may become defaults")
    selected = False
    updated: list[AssetRecord] = []
    for record in records:
        if record.category is not category:
            updated.append(record)
            continue
        matches = record.asset_id == asset_id and (
            exact_record is None
            or (record.sha256 == exact_record.sha256 and record.relative_path == exact_record.relative_path)
        )
        is_selected = matches and not selected
        selected = selected or is_selected
        updated.append(AssetRecord(**{**record.__dict__, "default_scope": scope if is_selected else None}))
    _write_records(root, updated)


def resolve_default(
    category: AssetCategory,
    scope: AssetScope | None = None,
    workspace: Path | None = None,
) -> AssetRecord | None:
    category = _as_category(category)
    scopes = (_as_scope(scope),) if scope is not None else (AssetScope.PROJECT, AssetScope.PERSONAL)
    for item_scope in scopes:
        for record in list_assets(workspace, scope=item_scope, category=category):
            if record.default_scope is item_scope:
                if record.rights_status is not RightsStatus.USER_AUTHORIZED:
                    raise ValueError("non-authorized asset cannot be resolved as a default")
                return record
    return None


def _record_path(record: AssetRecord, workspace: Path | None, skill_root: Path) -> Path:
    if record.scope is AssetScope.PROJECT:
        if workspace is None:
            raise ValueError("workspace is required for project assets")
        root = project_root(workspace)
    elif record.scope is AssetScope.PERSONAL:
        root = resolve_personal_root()
    else:
        root = skill_root
    path = (root / record.relative_path).resolve()
    root = root.resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"asset path escapes its scope root: {record.relative_path}")
    return path


def _skill_default_records(category: AssetCategory, skill_root: Path) -> tuple[AssetRecord, ...]:
    if category is AssetCategory.COMPANY_LOGO:
        parent = skill_root / "assets" / "defaults" / "company-logo"
    elif category is AssetCategory.IP_CHARACTER:
        parent = skill_root / "assets" / "defaults" / "ip"
    else:
        return ()
    records: list[AssetRecord] = []
    if not parent.is_dir():
        return ()
    for directory in sorted((path for path in parent.iterdir() if path.is_dir()), key=lambda path: path.name):
        image_path = directory / "reference.png"
        per_file_provenance = image_path.with_name(f"{image_path.stem}.provenance.json")
        provenance_path = per_file_provenance if per_file_provenance.is_file() else directory / "provenance.json"
        if not image_path.is_file() or not provenance_path.is_file():
            continue
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AssetManifestError(f"invalid Skill-default provenance: {provenance_path}") from exc
        if provenance.get("authorization_status") != RightsStatus.USER_AUTHORIZED.value:
            continue
        if provenance.get("distribution_scope") != "public_skill_package":
            continue
        digest = sha256_file(image_path)
        expected = provenance.get("reference_sha256", provenance.get("sha256"))
        if not isinstance(expected, str) or digest != expected.lower():
            raise AssetManifestError(f"Skill-default hash mismatch: {image_path}")
        try:
            with Image.open(image_path) as image:
                image.load()
                width, height = image.size
        except Exception as exc:
            raise AssetManifestError(f"Skill-default is not a readable image: {image_path}") from exc
        allowed_metadata = provenance.get("allowed_operations")
        forbidden_metadata = provenance.get("forbidden_operations")
        allowed_ops = tuple(str(item) for item in allowed_metadata) if isinstance(allowed_metadata, list) else (("scale", "position") if category is AssetCategory.COMPANY_LOGO else ())
        forbidden_ops = tuple(str(item) for item in forbidden_metadata) if isinstance(forbidden_metadata, list) else ((_COMPANY_LOGO_FORBIDDEN + (("recolor_monochrome",) if directory.name == "enhe-white-v2" else ())) if category is AssetCategory.COMPANY_LOGO else ())
        records.append(
            AssetRecord(
                asset_id=directory.name,
                category=category,
                scope=AssetScope.SKILL_DEFAULTS,
                relative_path=image_path.relative_to(skill_root).as_posix(),
                sha256=digest,
                width=width,
                height=height,
                rights_status=RightsStatus.USER_AUTHORIZED,
                save_scope_confirmed=True,
                default_scope=AssetScope.SKILL_DEFAULTS,
                allowed_operations=allowed_ops,
                forbidden_operations=forbidden_ops,
                created_at=str(provenance.get("confirmed_at", "")),
            )
        )
    return tuple(records)


def _resolved(record: AssetRecord, workspace: Path | None, skill_root: Path) -> ResolvedAsset:
    if record.rights_status is not RightsStatus.USER_AUTHORIZED:
        raise ValueError(f"asset is not authorized for composition: {record.asset_id}")
    path = _record_path(record, workspace, skill_root)
    if not path.is_file():
        raise ValueError(f"resolved asset is missing: {path}")
    observed = sha256_file(path)
    if observed != record.sha256:
        raise ValueError(f"resolved asset hash mismatch: {record.asset_id}")
    return ResolvedAsset(record, path)


def resolve_asset(
    category: AssetCategory,
    *,
    workspace: Path | None,
    explicit_asset_id: str | None = None,
    skill_root: Path | None = None,
) -> ResolvedAsset | None:
    """Resolve explicit -> project -> personal -> authorized Skill default."""
    category = _as_category(category)
    skill_root = Path(skill_root or Path(__file__).resolve().parents[2]).resolve()
    scoped_records = (
        *list_assets(workspace, scope=AssetScope.PROJECT, category=category),
        *list_assets(workspace, scope=AssetScope.PERSONAL, category=category),
        *_skill_default_records(category, skill_root),
    )
    if explicit_asset_id:
        for record in scoped_records:
            if record.asset_id == explicit_asset_id:
                return _resolved(record, workspace, skill_root)
        raise ValueError(f"explicit asset not found: {explicit_asset_id}")
    for scope in (AssetScope.PROJECT, AssetScope.PERSONAL):
        default = resolve_default(category, scope, workspace)
        if default is not None:
            return _resolved(default, workspace, skill_root)
    skill_records = [record for record in scoped_records if record.scope is AssetScope.SKILL_DEFAULTS]
    return _resolved(skill_records[0], workspace, skill_root) if skill_records else None
