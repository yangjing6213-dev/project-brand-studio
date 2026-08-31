"""Command-line entry point for the local, offline BrandLoom pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

try:
    from .brandloom_core.asset_library import list_assets, register_asset, resolve_default
    from .brandloom_core.json_io import read_json_dataclass
    from .brandloom_core.manifests import build_generation_manifest, write_manifest
    from .brandloom_core.models import AssetCategory, AssetScope, BrandBrief, QAState, QASession, RightsStatus, TaskMode
    from .brandloom_core.paths import project_root
    from .brandloom_core.renderer import render_brand_asset
    from .brandloom_core.state_machine import assert_generation_ready
except ImportError:  # pragma: no cover - supports direct script execution
    from brandloom.scripts.brandloom_core.asset_library import list_assets, register_asset, resolve_default
    from brandloom.scripts.brandloom_core.json_io import read_json_dataclass
    from brandloom.scripts.brandloom_core.manifests import build_generation_manifest, write_manifest
    from brandloom.scripts.brandloom_core.models import AssetCategory, AssetScope, BrandBrief, QAState, QASession, RightsStatus, TaskMode
    from brandloom.scripts.brandloom_core.paths import project_root
    from brandloom.scripts.brandloom_core.renderer import render_brand_asset
    from brandloom.scripts.brandloom_core.state_machine import assert_generation_ready


def _json_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _workspace(value: str) -> Path:
    workspace = Path(value).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _init(args: argparse.Namespace) -> int:
    root = project_root(_workspace(args.workspace))
    root.mkdir(parents=True, exist_ok=True)
    if not (root / "qa-state.json").exists():
        _json_write(root / "qa-state.json", {"schema_version": "1.0", "state": QAState.INTAKE.value, "confirmed": {}})
    if not (root / "defaults.json").exists():
        _json_write(root / "defaults.json", {"schema_version": "1.0"})
    print(root)
    return 0


def _asset_add(args: argparse.Namespace) -> int:
    workspace = _workspace(args.workspace)
    if not args.save_confirmed:
        return 2
    record = register_asset(
        Path(args.source), category=AssetCategory(args.category), scope=AssetScope(args.scope), workspace=workspace,
        rights_status=RightsStatus(args.rights), save_scope_confirmed=True, make_default=args.make_default,
        asset_id=args.asset_id,
    )
    print(json.dumps({"asset_id": record.asset_id, "sha256": record.sha256}, ensure_ascii=False))
    return 0


def _state_show(args: argparse.Namespace) -> int:
    path = project_root(_workspace(args.workspace)) / "qa-state.json"
    if not path.exists():
        return 2
    print(path.read_text(encoding="utf-8"))
    return 0


def _state_confirm(args: argparse.Namespace) -> int:
    path = project_root(_workspace(args.workspace)) / "qa-state.json"
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version": "1.0", "confirmed": {}}
    confirmed = payload.setdefault("confirmed", {})
    if args.key:
        value: object = args.value
        if args.value in {"true", "false"}:
            value = args.value == "true"
        confirmed[args.key] = value
    if args.state:
        payload["state"] = args.state
    _json_write(path, payload)
    return 0


def _load_brief(workspace: Path) -> BrandBrief:
    path = project_root(workspace) / "brand-brief.json"
    return read_json_dataclass(path, BrandBrief)


def _load_session(workspace: Path) -> QASession:
    path = project_root(workspace) / "qa-state.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return QASession(schema_version=str(payload.get("schema_version", "1.0")), session_id="cli", mode=TaskMode.NEW,
                     state=QAState(payload.get("state", QAState.INTAKE.value)), project_slug="cli",
                     confirmed=dict(payload.get("confirmed", {})))


def _versioned_manifest(directory: Path) -> Path:
    version = 1
    while True:
        path = directory / f"generation-manifest-v{version:02d}.json"
        if not path.exists():
            return path
        version += 1


def _compose(args: argparse.Namespace) -> int:
    workspace = _workspace(args.workspace)
    if not args.test_fixture:
        assert_generation_ready(_load_session(workspace))
    brief = _load_brief(workspace)
    slug = str(brief.project.get("slug", brief.project.get("name", "project")))
    output_dir = project_root(workspace) / "outputs" / slug
    template = Path("brandloom/templates/logo-card-1x1.json") if args.type == "logo-card" else Path("brandloom/templates/cover-2x1.json")
    records = list_assets(workspace, scope=AssetScope.PROJECT)
    logo = resolve_default(AssetCategory.COMPANY_LOGO, AssetScope.PROJECT, workspace)
    mark = resolve_default(AssetCategory.PROJECT_MARK, AssetScope.PROJECT, workspace)
    if logo is None or mark is None:
        raise ValueError("company-logo and project-mark defaults are required")
    root = project_root(workspace)
    asset_paths = {"company_logo": root / logo.relative_path, "project_mark": root / mark.relative_path}
    font_paths = {key: Path(value) for key, value in brief.fonts.items() if isinstance(value, str)}
    result = render_brand_asset(template, brief, base_image=Path(args.base), asset_paths=asset_paths,
                                font_paths=font_paths, output_dir=output_dir)
    manifest = build_generation_manifest(
        brief_path=root / "brand-brief.json", assets=records, template_path=template,
        font_paths=font_paths, base_image_path=Path(args.base), output_path=result.output_path,
        qa_state=QAState.GENERATION_READY.value if args.test_fixture else _load_session(workspace).state.value,
        rendered_copy=brief.copy, output_type=args.type,
    )
    write_manifest(_versioned_manifest(output_dir), manifest)
    print(result.output_path)
    return 0


def _validate(args: argparse.Namespace) -> int:
    directory = project_root(_workspace(args.workspace)) / "outputs" / (args.slug or "demo")
    manifests = sorted(directory.glob("generation-manifest-v*.json"))
    if not manifests:
        return 2
    payload = json.loads(manifests[-1].read_text(encoding="utf-8"))
    output = payload.get("output", {})
    return 0 if isinstance(output, dict) and Path(str(output.get("path", ""))).is_file() else 2


def _deliver(args: argparse.Namespace) -> int:
    return _validate(args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brandloom")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init"); p.add_argument("--workspace", required=True); p.set_defaults(func=_init)
    p = sub.add_parser("asset-add"); p.add_argument("--workspace", required=True); p.add_argument("--source", required=True)
    p.add_argument("--category", required=True, choices=[item.value for item in AssetCategory]); p.add_argument("--scope", required=True, choices=["project", "personal"])
    p.add_argument("--rights", required=True, choices=["user_authorized", "analysis_only"]); p.add_argument("--save-confirmed", action="store_true"); p.add_argument("--make-default", action="store_true"); p.add_argument("--asset-id"); p.set_defaults(func=_asset_add)
    p = sub.add_parser("state-show"); p.add_argument("--workspace", required=True); p.set_defaults(func=_state_show)
    p = sub.add_parser("state-confirm"); p.add_argument("--workspace", required=True); p.add_argument("--state"); p.add_argument("--key"); p.add_argument("--value", default="true"); p.add_argument("--test-fixture", action="store_true"); p.set_defaults(func=_state_confirm)
    p = sub.add_parser("compose"); p.add_argument("--workspace", required=True); p.add_argument("--type", required=True, choices=["logo-card", "cover"]); p.add_argument("--base", required=True); p.add_argument("--test-fixture", action="store_true"); p.set_defaults(func=_compose)
    for name in ("validate", "deliver"):
        p = sub.add_parser(name); p.add_argument("--workspace", required=True); p.add_argument("--type", default="logo-card"); p.add_argument("--slug"); p.set_defaults(func=_validate if name == "validate" else _deliver)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        return int(args.func(args))
    except SystemExit as exc:
        return int(exc.code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
