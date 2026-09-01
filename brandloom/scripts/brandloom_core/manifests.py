"""Versioned, provenance-rich generation manifests for local BrandLoom runs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Mapping


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(path: Path | str | None, **extra: object) -> dict[str, object]:
    result: dict[str, object] = dict(extra)
    if path is not None:
        source = Path(path)
        result.update({"path": source.as_posix(), "sha256": _sha256(source) if source.is_file() else ""})
    return result


def _asset_entries(assets: Iterable[object] | Mapping[str, object] | None) -> list[dict[str, object]]:
    if assets is None:
        return []
    values = assets.items() if isinstance(assets, Mapping) else ((None, item) for item in assets)
    output: list[dict[str, object]] = []
    for key, value in values:
        if hasattr(value, "asset_id"):
            asset_id, digest, relative = value.asset_id, value.sha256, value.relative_path
            category = getattr(value.category, "value", value.category)
            scope = getattr(value.scope, "value", value.scope)
            rights = getattr(value.rights_status, "value", value.rights_status)
        elif isinstance(value, Mapping):
            asset_id = value.get("asset_id", key or "")
            digest = value.get("expected_sha256", value.get("sha256", ""))
            relative = value.get("relative_path", value.get("path", ""))
            category = value.get("category", "")
            scope = value.get("scope", "")
            rights = value.get("rights_status", "")
        else:
            asset_id, digest, relative = key or str(value), "", ""
            category = scope = rights = ""
        path = Path(relative) if relative else None
        observed = _sha256(path) if path is not None and path.is_file() else ""
        output.append({
            "asset_id": str(asset_id),
            "category": str(category),
            "scope": str(scope),
            "rights_status": str(rights),
            "path": str(relative),
            "expected_sha256": str(digest),
            "observed_sha256": observed,
            "sha256": observed or str(digest),
        })
    return output


def build_generation_manifest(
    *,
    brief_path: Path,
    assets: Iterable[object] | Mapping[str, object] | None = None,
    template_path: Path,
    font_paths: Mapping[str, Path | str] | None = None,
    base_image_path: Path,
    output_path: Path,
    qa_state: str,
    rendered_copy: Mapping[str, object] | None = None,
    output_type: str | None = None,
    base_prompt: str | None = None,
    image_tool_returned_path: Path | str | None = None,
    host_request: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build a JSON-safe manifest without retaining secrets or conversation text."""
    fonts = {
        str(role): _entry(path)
        for role, path in (font_paths or {}).items()
        if path is not None
    }
    manifest: dict[str, object] = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "qa_state": str(qa_state),
        "brief": _entry(brief_path),
        "assets": _asset_entries(assets),
        "template": _entry(template_path),
        "fonts": fonts,
        "base_image": _entry(base_image_path),
        "output": _entry(output_path),
        "rendered_copy": dict(rendered_copy or {}),
        "output_type": str(output_type or ""),
        "host_request": dict(host_request or {"schema_version": "1.0", "backend": "host_builtin_image_tool", "reference_assets": []}),
    }
    if base_prompt is not None:
        manifest["base_prompt"] = base_prompt
    if image_tool_returned_path is not None:
        # Preserve the host tool's returned string verbatim for auditability.
        manifest["image_tool_returned_path"] = str(image_tool_returned_path)
    return manifest


def write_manifest(path: Path, manifest: Mapping[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(dict(manifest), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)
