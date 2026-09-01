"""Command-line entry point for the local, offline BrandLoom pipeline."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import sys
from typing import Any

from PIL import ImageFont

if __package__ in {None, ""}:  # direct execution from an installed Skill directory
    package_parent = str(Path(__file__).resolve().parents[2])
    if package_parent not in sys.path:
        sys.path.insert(0, package_parent)

try:
    from .brandloom_core.asset_library import list_assets, register_asset, resolve_asset
    from .brandloom_core.fonts import FontNotFoundError, load_font_profiles, resolve_font
    from .brandloom_core.json_io import read_json_dataclass, write_json_dataclass
    from .brandloom_core.manifests import build_generation_manifest, write_manifest
    from .brandloom_core.models import AssetCategory, AssetScope, BrandBrief, QAState, QASession, RightsStatus, TaskMode
    from .brandloom_core.paths import project_output_dir, project_root, safe_project_slug
    from .brandloom_core.renderer import render_brand_asset, rendered_copy_values
    from .brandloom_core.state_machine import advance, assert_generation_ready, confirm, invalidate_from
    from .brandloom_core.prompt_builder import build_host_request, validate_generated_path
    from .brandloom_core.validation import validate_output
except ImportError:  # pragma: no cover - supports direct script execution
    from brandloom.scripts.brandloom_core.asset_library import list_assets, register_asset, resolve_asset
    from brandloom.scripts.brandloom_core.fonts import FontNotFoundError, load_font_profiles, resolve_font
    from brandloom.scripts.brandloom_core.json_io import read_json_dataclass, write_json_dataclass
    from brandloom.scripts.brandloom_core.manifests import build_generation_manifest, write_manifest
    from brandloom.scripts.brandloom_core.models import AssetCategory, AssetScope, BrandBrief, QAState, QASession, RightsStatus, TaskMode
    from brandloom.scripts.brandloom_core.paths import project_output_dir, project_root, safe_project_slug
    from brandloom.scripts.brandloom_core.renderer import render_brand_asset, rendered_copy_values
    from brandloom.scripts.brandloom_core.state_machine import advance, assert_generation_ready, confirm, invalidate_from
    from brandloom.scripts.brandloom_core.prompt_builder import build_host_request, validate_generated_path
    from brandloom.scripts.brandloom_core.validation import validate_output


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
        write_json_dataclass(
            root / "qa-state.json",
            QASession(
                schema_version="1.0",
                session_id=f"cli-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                mode=TaskMode.NEW,
                state=QAState.INTAKE,
                project_slug="project",
                updated_at=datetime.now(timezone.utc).isoformat(),
            ),
        )
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
    if not path.is_file() or not any((args.key, args.invalidate, args.state)):
        return 2
    if args.key and args.invalidate:
        return 2
    if args.key and args.value is None:
        return 2
    try:
        session = _load_session(_workspace(args.workspace))
        if args.key:
            try:
                value: object = json.loads(args.value)
            except json.JSONDecodeError:
                value = args.value
            session = confirm(session, args.key, value)
        if args.invalidate:
            session = invalidate_from(session, args.invalidate)
        if args.state:
            session = advance(session, QAState(args.state))
    except (ValueError, TypeError, json.JSONDecodeError):
        return 2
    _write_session(path, session)
    return 0


def _load_brief(workspace: Path) -> BrandBrief:
    path = project_root(workspace) / "brand-brief.json"
    return read_json_dataclass(path, BrandBrief)


def _load_session(workspace: Path) -> QASession:
    path = project_root(workspace) / "qa-state.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    accepted_raw = payload.get("accepted_logo")
    accepted_logo = None
    if isinstance(accepted_raw, dict):
        if all(isinstance(accepted_raw.get(key), str) and accepted_raw.get(key) for key in ("path", "sha256", "manifest_path")):
            accepted_logo = {key: str(accepted_raw[key]) for key in ("path", "sha256", "manifest_path")}
    return QASession(
        schema_version=str(payload.get("schema_version", "1.0")),
        session_id=str(payload.get("session_id", "cli")),
        mode=TaskMode(payload.get("mode", TaskMode.NEW.value)),
        state=QAState(payload.get("state", QAState.INTAKE.value)),
        project_slug=str(payload.get("project_slug", "project")),
        source_refs=tuple(payload.get("source_refs", ())),
        confirmed=dict(payload.get("confirmed", {})),
        invalidated=tuple(payload.get("invalidated", ())),
        generation_backend=str(payload.get("generation_backend", "host_builtin_image_tool")),
        accepted_logo=accepted_logo,
        updated_at=str(payload.get("updated_at", "")),
    )


def _write_session(path: Path, session: QASession) -> None:
    write_json_dataclass(
        path,
        replace(session, updated_at=datetime.now(timezone.utc).isoformat()),
    )


def _versioned_manifest(directory: Path) -> Path:
    version = 1
    while True:
        path = directory / f"generation-manifest-v{version:02d}.json"
        if not path.exists():
            return path
        version += 1


def _manifest_documents(directory: Path) -> list[tuple[Path, dict[str, object]]]:
    documents: list[tuple[Path, dict[str, object]]] = []
    def version(path: Path) -> int:
        match = re.search(r"generation-manifest-v(\d+)\.json$", path.name, flags=re.IGNORECASE)
        return int(match.group(1)) if match else -1
    for path in sorted(directory.glob("generation-manifest-v*.json"), key=lambda item: (version(item), item.name)):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"generation manifest must be a mapping: {path}")
        documents.append((path, payload))
    return documents


def _latest_manifest(directory: Path, output_type: str) -> tuple[Path, dict[str, object]]:
    aliases = {output_type, output_type.replace("-", "_"), output_type.replace("_", "-")}
    for path, payload in reversed(_manifest_documents(directory)):
        if str(payload.get("output_type", "")) in aliases:
            return path, payload
    raise FileNotFoundError(f"generation manifest missing for {output_type}")


def _manifest_output_path(manifest_path: Path, payload: dict[str, object]) -> Path:
    entry = payload.get("output")
    if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not entry["path"]:
        raise ValueError("manifest output path is missing")
    path = Path(entry["path"])
    return path.resolve() if path.is_absolute() else (manifest_path.parent / path).resolve()


def _resolve_font_paths(brief: BrandBrief) -> dict[str, Path]:
    rendered = rendered_copy_values(brief)
    required: list[str] = []
    if rendered.get("title"):
        required.append("heading")
    if any(rendered.get(name) for name in ("subtitle", "value_line", "features")):
        required.append("body")
    roots_value = brief.fonts.get("project_paths", ())
    roots = tuple(Path(value).expanduser() for value in roots_value) if isinstance(roots_value, (list, tuple)) else ()
    profiles = load_font_profiles()
    profile_id = brief.fonts.get("profile")
    profile = profiles.get(str(profile_id)) if profile_id else None
    resolved: dict[str, Path] = {}
    for role in required:
        explicit = brief.fonts.get(role)
        if explicit is not None:
            if not isinstance(explicit, str) or not explicit.strip():
                raise FontNotFoundError(f"confirmed {role} font path must be a non-empty string")
            path = Path(explicit).expanduser().resolve()
            if not path.is_file():
                raise FontNotFoundError(f"confirmed {role} font does not exist: {path}")
            try:
                ImageFont.truetype(str(path), size=16)
            except OSError as exc:
                raise FontNotFoundError(f"confirmed {role} font is unreadable: {path}") from exc
            resolved[role] = path
        elif profile is not None:
            resolved[role] = resolve_font(profile, role, roots).resolve()
        else:
            raise FontNotFoundError(f"confirmed {role} font path/profile is required")
    return resolved


def _asset_manifest_entry(resolved) -> dict[str, object]:
    record = resolved.record
    return {
        "asset_id": record.asset_id,
        "category": record.category.value,
        "scope": record.scope.value,
        "rights_status": record.rights_status.value,
        "path": str(resolved.path),
        "sha256": record.sha256,
    }


def _post_compose_session(session: QASession, output_type: str) -> QASession:
    if output_type == "logo-card":
        session = advance(session, QAState.GENERATE_LOGO_BASE)
        session = advance(session, QAState.COMPOSE_LOGO_CARD)
        return advance(session, QAState.INTERNAL_LOGO_QA)
    session = advance(session, QAState.COMPOSE_COVER)
    return advance(session, QAState.INTERNAL_COVER_QA)


def _compose(args: argparse.Namespace) -> int:
    workspace = _workspace(args.workspace)
    session = _load_session(workspace)
    if args.type == "logo-card":
        assert_generation_ready(session)
    elif session.state is not QAState.GENERATE_COVER_BASE:
        raise ValueError("cover composition requires an accepted logo-card")
    brief = _load_brief(workspace)
    slug = safe_project_slug(brief.project.get("slug", brief.project.get("name", "project")))
    output_dir = project_output_dir(workspace, slug)
    base_path = Path(args.base)
    if not base_path.is_absolute():
        base_path = (workspace / base_path).resolve()
    prompt_type = "logo_card" if args.type == "logo-card" else "cover"
    dimensions = validate_generated_path(base_path, expected=prompt_type)
    skill_root = Path(__file__).resolve().parents[1]
    accepted_logo_path = None
    accepted_logo_evidence = None
    if args.type == "cover":
        accepted_logo_evidence = session.accepted_logo
        if not isinstance(accepted_logo_evidence, dict):
            raise ValueError("cover composition requires accepted logo evidence")
        accepted_logo_path = Path(str(accepted_logo_evidence.get("path", ""))).resolve()
        accepted_manifest_path = Path(str(accepted_logo_evidence.get("manifest_path", ""))).resolve()
        digest = str(accepted_logo_evidence.get("sha256", ""))
        if not accepted_logo_path.is_file() or not accepted_manifest_path.is_file() or len(digest) != 64:
            raise ValueError("accepted logo evidence is incomplete")
        if hashlib.sha256(accepted_logo_path.read_bytes()).hexdigest() != digest.lower():
            raise ValueError("accepted logo output changed after review")
        accepted_manifest = json.loads(accepted_manifest_path.read_text(encoding="utf-8"))
        if not isinstance(accepted_manifest, dict) or str(accepted_manifest.get("output_type", "")).replace("-", "_") != "logo_card":
            raise ValueError("accepted logo manifest is invalid")
        if _manifest_output_path(accepted_manifest_path, accepted_manifest) != accepted_logo_path:
            raise ValueError("accepted logo evidence does not match manifest")
    host_request = build_host_request(
        brief,
        prompt_type,
        expected=dimensions,
        accepted_logo_path=accepted_logo_path,
        accepted_logo_evidence=accepted_logo_evidence,
        skill_root=skill_root,
    )
    template = skill_root / ("templates/logo-card-1x1.json" if args.type == "logo-card" else "templates/cover-2x1.json")
    explicit_logo = brief.assets.get("company_logo")
    logo = resolve_asset(
        AssetCategory.COMPANY_LOGO,
        workspace=workspace,
        explicit_asset_id=str(explicit_logo) if isinstance(explicit_logo, str) and explicit_logo else None,
        skill_root=skill_root,
    )
    if logo is None:
        raise ValueError("an authorized company-logo is required")
    mark_value = brief.assets.get("project_mark")
    mark_absent = "project_mark" in brief.assets and mark_value in (None, False, "", "none")
    if "project_mark" in brief.assets and not mark_absent and not isinstance(mark_value, str):
        raise ValueError("project_mark must be a valid asset ID or explicit none")
    if "project_mark" not in brief.assets and resolve_asset(AssetCategory.PROJECT_MARK, workspace=workspace, skill_root=skill_root) is None:
        raise ValueError("project_mark selection is unresolved")
    explicit_mark = mark_value
    mark = None if mark_absent else resolve_asset(
        AssetCategory.PROJECT_MARK,
        workspace=workspace,
        explicit_asset_id=str(explicit_mark) if isinstance(explicit_mark, str) and explicit_mark else None,
        skill_root=skill_root,
    )
    root = project_root(workspace)
    asset_paths = {"company_logo": logo.path}
    used_assets = [_asset_manifest_entry(logo)]
    if mark is not None:
        asset_paths["project_mark"] = mark.path
        used_assets.append(_asset_manifest_entry(mark))
    for reference in host_request.get("reference_assets", []):
        if isinstance(reference, dict):
            used_assets.append(dict(reference))
    font_paths = _resolve_font_paths(brief)
    result = render_brand_asset(template, brief, base_image=base_path, asset_paths=asset_paths,
                                font_paths=font_paths, output_dir=output_dir)
    next_session = _post_compose_session(session, args.type)
    manifest = build_generation_manifest(
        brief_path=root / "brand-brief.json", assets=used_assets, template_path=template,
        font_paths=font_paths, base_image_path=base_path, output_path=result.output_path,
        qa_state=next_session.state.value,
        rendered_copy=result.rendered_copy, output_type=args.type,
        base_prompt=str(host_request["prompt"]), image_tool_returned_path=args.base,
        host_request=host_request,
    )
    write_manifest(_versioned_manifest(output_dir), manifest)
    if args.type == "logo-card":
        next_session = replace(next_session, accepted_logo=None)
    _write_session(root / "qa-state.json", next_session)
    print(result.output_path)
    return 0


def _output_qa_report(args: argparse.Namespace, *, manual_visual_checks: bool):
    workspace = _workspace(args.workspace)
    root = project_root(workspace)
    slug = args.slug
    if not slug:
        brief_path = root / "brand-brief.json"
        if brief_path.is_file():
            try:
                slug = str(json.loads(brief_path.read_text(encoding="utf-8")).get("project", {}).get("slug", "project"))
            except (OSError, json.JSONDecodeError, AttributeError) as exc:
                raise ValueError("cannot derive project slug from brand brief") from exc
        else:
            raise FileNotFoundError("brand brief missing")
    slug = safe_project_slug(slug)
    directory = project_output_dir(workspace, slug)
    manifest_path, payload = _latest_manifest(directory, args.type)
    output_path = _manifest_output_path(manifest_path, payload)
    output_type = "logo_card" if args.type == "logo-card" else args.type.replace("-", "_")
    validate_generated_path(output_path, expected=output_type)
    brief = _load_brief(workspace) if (root / "brand-brief.json").is_file() else None
    previous_outputs = []
    for previous, previous_payload in _manifest_documents(directory):
        if previous != manifest_path:
            previous_outputs.append(_manifest_output_path(previous, previous_payload))
    assets = brief.assets if isinstance(brief, BrandBrief) else {}
    logo_ips = assets.get("logo_card_ip", []) if isinstance(assets, dict) else []
    rights = assets.get("custom_ip_rights", []) if isinstance(assets, dict) else []
    return validate_output(output_path, manifest=payload, brief=brief, output_type=output_type,
                           existing_output_paths=previous_outputs, logo_card_ip=logo_ips,
                           custom_ip_rights=rights, manual_visual_checks=manual_visual_checks,
                           brief_path=root / "brand-brief.json", manifest_path=manifest_path,
                           output_root=root / "outputs")


def _validate(args: argparse.Namespace) -> int:
    workspace = _workspace(args.workspace)
    try:
        session = _load_session(workspace)
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
        return 2
    expected_state = QAState.INTERNAL_LOGO_QA if args.type == "logo-card" else QAState.INTERNAL_COVER_QA
    target_state = QAState.LOGO_USER_REVIEW if args.type == "logo-card" else QAState.USER_REVIEW
    if session.state is not expected_state:
        return 2
    try:
        report = _output_qa_report(args, manual_visual_checks=False)
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
        return 2
    if not report.passed:
        return 2
    _write_session(project_root(workspace) / "qa-state.json", advance(session, target_state))
    return 0


def _deliver(args: argparse.Namespace) -> int:
    if not args.reviewed:
        return 3
    workspace = _workspace(args.workspace)
    try:
        session = _load_session(workspace)
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
        return 2
    expected_state = QAState.LOGO_USER_REVIEW if args.type == "logo-card" else QAState.USER_REVIEW
    target_state = QAState.GENERATE_COVER_BASE if args.type == "logo-card" else QAState.DELIVERED
    if session.state is not expected_state:
        return 2
    try:
        report = _output_qa_report(args, manual_visual_checks=True)
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
        return 2
    if not report.passed:
        return 2
    next_session = advance(session, target_state)
    if args.type == "logo-card":
        directory = project_output_dir(workspace, safe_project_slug(_load_brief(workspace).project.get("slug", "project")))
        manifest_path, payload = _latest_manifest(directory, "logo-card")
        output_path = _manifest_output_path(manifest_path, payload)
        if not output_path.is_file():
            return 2
        evidence = {"path": str(output_path.resolve()), "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(), "manifest_path": str(manifest_path.resolve())}
        next_session = replace(next_session, accepted_logo=evidence)
    _write_session(project_root(workspace) / "qa-state.json", next_session)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brandloom")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init"); p.add_argument("--workspace", required=True); p.set_defaults(func=_init)
    p = sub.add_parser("asset-add"); p.add_argument("--workspace", required=True); p.add_argument("--source", required=True)
    p.add_argument("--category", required=True, choices=[item.value for item in AssetCategory]); p.add_argument("--scope", required=True, choices=["project", "personal"])
    p.add_argument("--rights", required=True, choices=["user_authorized", "analysis_only"]); p.add_argument("--save-confirmed", action="store_true"); p.add_argument("--make-default", action="store_true"); p.add_argument("--asset-id"); p.set_defaults(func=_asset_add)
    p = sub.add_parser("state-show"); p.add_argument("--workspace", required=True); p.set_defaults(func=_state_show)
    p = sub.add_parser("state-confirm", help="record the pending state's confirmation (use --value true for confirmation-only keys)"); p.add_argument("--workspace", required=True); p.add_argument("--state"); p.add_argument("--key"); p.add_argument("--value", help="JSON value; confirmation-only keys require exact true"); p.add_argument("--invalidate"); p.set_defaults(func=_state_confirm)
    p = sub.add_parser("compose"); p.add_argument("--workspace", required=True); p.add_argument("--type", required=True, choices=["logo-card", "cover"]); p.add_argument("--base", required=True); p.set_defaults(func=_compose)
    for name in ("validate", "deliver"):
        p = sub.add_parser(name); p.add_argument("--workspace", required=True); p.add_argument("--type", default="logo-card", choices=["logo-card", "cover"]); p.add_argument("--slug")
        if name == "deliver":
            p.add_argument("--reviewed", action="store_true", help="confirm manual visual review")
        p.set_defaults(func=_validate if name == "validate" else _deliver)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        return int(args.func(args))
    except SystemExit as exc:
        return int(exc.code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
