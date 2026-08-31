"""Filesystem locations used by the local BrandLoom asset library."""

import os
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath
import re


def resolve_personal_root() -> Path:
    """Return the personal BrandLoom data root without creating it."""
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return base / "brandloom"


def project_root(workspace: Path) -> Path:
    """Return a workspace's BrandLoom root without creating it."""
    return Path(workspace).resolve() / ".brandloom"


def safe_project_slug(value: object) -> str:
    """Return a single safe output-directory segment or reject it."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("project slug must be a non-empty trimmed string")
    if value in {".", ".."} or PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
        raise ValueError(f"unsafe project slug: {value!r}")
    if PureWindowsPath(value).drive or "/" in value or "\\" in value:
        raise ValueError(f"unsafe project slug: {value!r}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError(f"unsafe project slug: {value!r}")
    return value


def project_output_dir(workspace: Path, slug: object) -> Path:
    outputs = (project_root(workspace) / "outputs").resolve()
    destination = (outputs / safe_project_slug(slug)).resolve()
    if not destination.is_relative_to(outputs):
        raise ValueError("output path escapes .brandloom/outputs")
    return destination
