"""Filesystem locations used by the local BrandLoom asset library."""

import os
from pathlib import Path


def resolve_personal_root() -> Path:
    """Return the personal BrandLoom data root without creating it."""
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return base / "brandloom"


def project_root(workspace: Path) -> Path:
    """Return a workspace's BrandLoom root without creating it."""
    return Path(workspace).resolve() / ".brandloom"
