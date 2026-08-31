"""Rights-aware, local-first persistence for BrandLoom image assets."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
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
            return []
        return [_construct(item, AssetRecord) for item in values]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return []


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
    rights_status: RightsStatus = RightsStatus.USER_AUTHORIZED,
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
            records.extend(_load_records(_scope_root(_as_scope(item_scope), workspace)))
        except ValueError:
            continue
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
    if not any(record.asset_id == asset_id for record in records):
        raise ValueError(f"asset not found: {asset_id}")
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
                return record
    return None
