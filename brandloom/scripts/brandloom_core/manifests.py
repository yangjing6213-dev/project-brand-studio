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
        elif isinstance(value, Mapping):
            asset_id = value.get("asset_id", key or "")
            digest = value.get("sha256", "")
            relative = value.get("relative_path", value.get("path", ""))
        else:
            asset_id, digest, relative = key or str(value), "", ""
        output.append({"asset_id": str(asset_id), "sha256": str(digest), "path": str(relative)})
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
) -> dict[str, object]:
    """Build a JSON-safe manifest without retaining prompts or conversation text."""
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
    }
    if output_type:
        manifest["output_type"] = output_type
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

