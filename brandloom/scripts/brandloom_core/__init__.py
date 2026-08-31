"""Public runtime models and JSON persistence for BrandLoom."""

from .json_io import read_json_dataclass, write_json_dataclass
from .asset_library import (
    AssetManifestError,
    ResolvedAsset,
    list_assets,
    register_asset,
    resolve_asset,
    resolve_default,
    set_default,
    sha256_file,
)
from .paths import project_root, resolve_personal_root
from .models import (
    AssetCategory,
    AssetRecord,
    AssetScope,
    BrandBrief,
    QAState,
    QASession,
    RightsStatus,
    TaskMode,
)

__all__ = [
    "AssetCategory",
    "AssetManifestError",
    "AssetRecord",
    "AssetScope",
    "BrandBrief",
    "QAState",
    "QASession",
    "RightsStatus",
    "ResolvedAsset",
    "TaskMode",
    "read_json_dataclass",
    "write_json_dataclass",
    "list_assets",
    "register_asset",
    "resolve_asset",
    "resolve_default",
    "set_default",
    "sha256_file",
    "project_root",
    "resolve_personal_root",
]
