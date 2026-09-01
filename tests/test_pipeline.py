from __future__ import annotations

import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from brandloom.scripts import brandloom_cli
from brandloom.scripts.brandloom_core.manifests import build_generation_manifest
from tests.font_test_utils import find_test_font


class PipelineTests(unittest.TestCase):
    def _font(self) -> Path:
        return find_test_font()

    def _asset(self, root: Path, name: str, size: tuple[int, int], color: tuple[int, int, int, int]) -> Path:
        path = root / name
        Image.new("RGBA", size, color).save(path)
        return path

    def _ready_state(self) -> dict[str, object]:
        payload = {
            "schema_version": "1.0",
            "session_id": "pipeline-test",
            "mode": "new",
            "state": "GENERATION_READY",
            "project_slug": "demo",
            "source_refs": [],
            "confirmed": {
                key: True
                for key in (
                    "context", "copy", "style", "font", "company_logo", "project_mark",
                    "ip_combination", "ip_usage", "shot_list", "output_spec",
                    "coherence", "generation_confirmation",
                )
            },
            "invalidated": [],
            "generation_backend": "host_builtin_image_tool",
            "updated_at": "2026-09-01T00:00:00+00:00",
        }
        payload["confirmed"]["ip_cast"] = "tuotuo"
        return payload

    def _write_ready_brief(self, root: Path, *, slug: str = "demo", assets: dict[str, object] | None = None) -> None:
        brief = {
            "schema_version": "1.0",
            "project": {"name": "Demo", "slug": slug},
            "copy": {"title": "Demo Brand", "subtitle": "Local pipeline"},
            "style": {"foreground": "#111111"},
            "fonts": {"heading": str(self._font()), "body": str(self._font())},
            "assets": assets or {},
            "outputs": {},
        }
        runtime = root / ".brandloom"
        runtime.mkdir(parents=True, exist_ok=True)
        (runtime / "brand-brief.json").write_text(json.dumps(brief), encoding="utf-8")
        (runtime / "qa-state.json").write_text(json.dumps(self._ready_state()), encoding="utf-8")

    def test_local_cli_pipeline_versions_outputs_and_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(brandloom_cli.main(["init", "--workspace", str(root)]), 0)
            logo = self._asset(root, "logo.png", (400, 100), (10, 80, 180, 255))
            mark = self._asset(root, "mark.png", (200, 200), (220, 160, 10, 255))
            self.assertEqual(brandloom_cli.main([
                "asset-add", "--workspace", str(root), "--source", str(logo),
                "--category", "company-logo", "--scope", "project",
                "--rights", "user_authorized", "--save-confirmed", "--make-default",
            ]), 0)
            self.assertEqual(brandloom_cli.main([
                "asset-add", "--workspace", str(root), "--source", str(mark),
                "--category", "project-mark", "--scope", "project",
                "--rights", "user_authorized", "--save-confirmed", "--make-default",
            ]), 0)
            self._write_ready_brief(root)
            base = self._asset(root, "base.png", (2048, 2048), (245, 245, 245, 255))
            self.assertEqual(brandloom_cli.main([
                "compose", "--workspace", str(root), "--type", "logo-card",
                "--base", str(base),
            ]), 0)
            output_dir = root / ".brandloom" / "outputs" / "demo"
            first = sorted(output_dir.glob("*.png"))
            self.assertTrue(first)
            self.assertTrue(first[0].name.endswith("-v01.png"))
            self.assertTrue((output_dir / "generation-manifest-v01.json").is_file())
            self.assertEqual(json.loads((root / ".brandloom" / "qa-state.json").read_text())["state"], "INTERNAL_LOGO_QA")
            self.assertEqual(brandloom_cli.main([
                "validate", "--workspace", str(root), "--type", "logo-card",
            ]), 0)
            self.assertEqual(json.loads((root / ".brandloom" / "qa-state.json").read_text())["state"], "LOGO_USER_REVIEW")
            self.assertEqual(brandloom_cli.main([
                "deliver", "--workspace", str(root), "--type", "logo-card", "--reviewed",
            ]), 0)
            self.assertEqual(json.loads((root / ".brandloom" / "qa-state.json").read_text())["state"], "GENERATE_COVER_BASE")
            cover_base = self._asset(root, "cover-base.png", (2048, 1024), (235, 235, 235, 255))
            self.assertEqual(brandloom_cli.main([
                "compose", "--workspace", str(root), "--type", "cover", "--base", str(cover_base),
            ]), 0)
            self.assertTrue((output_dir / "generation-manifest-v02.json").is_file())
            self.assertEqual(json.loads((root / ".brandloom" / "qa-state.json").read_text())["state"], "INTERNAL_COVER_QA")
            self.assertEqual(brandloom_cli.main(["validate", "--workspace", str(root), "--type", "cover"]), 0)
            self.assertEqual(json.loads((root / ".brandloom" / "qa-state.json").read_text())["state"], "USER_REVIEW")
            self.assertEqual(brandloom_cli.main([
                "deliver", "--workspace", str(root), "--type", "cover", "--reviewed",
            ]), 0)
            self.assertEqual(json.loads((root / ".brandloom" / "qa-state.json").read_text())["state"], "DELIVERED")

    def test_asset_add_requires_save_confirmation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            source = self._asset(root, "logo.png", (32, 16), (1, 2, 3, 255))
            self.assertEqual(brandloom_cli.main([
                "asset-add", "--workspace", str(root), "--source", str(source),
                "--category", "company-logo", "--scope", "project", "--rights", "user_authorized",
            ]), 2)

    def test_compose_rejects_base_with_wrong_output_dimensions(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (40, 20), (1, 2, 3, 255))
            mark = self._asset(root, "mark.png", (20, 20), (4, 5, 6, 255))
            for source, category in ((logo, "company-logo"), (mark, "project-mark")):
                brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(source), "--category", category,
                                    "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._write_ready_brief(root, slug="other")
            Image.new("RGBA", (2048, 1024), "white").save(root / "base.png")
            with self.assertRaises(ValueError):
                brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(root / "base.png")])

    def test_validate_uses_brief_slug_and_manifest_relative_paths(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            brief = {"schema_version": "1.0", "project": {"name": "Demo", "slug": "other"},
                     "copy": {}, "style": {}, "fonts": {}, "assets": {}, "outputs": {}}
            (root / ".brandloom" / "brand-brief.json").write_text(json.dumps(brief), encoding="utf-8")
            state = self._ready_state(); state["state"] = "INTERNAL_LOGO_QA"
            (root / ".brandloom" / "qa-state.json").write_text(json.dumps(state), encoding="utf-8")
            output_dir = root / ".brandloom" / "outputs" / "other"
            output_dir.mkdir(parents=True)
            image = output_dir / "logo-card-1x1-v01.png"
            Image.new("RGBA", (2048, 2048), "white").save(image)
            template = root / ".brandloom" / "template.json"; template.write_text('{"schema_version":"1.0","canvas":{},"slots":{}}')
            base = root / ".brandloom" / "base.png"; Image.new("RGBA", (2048, 2048), "white").save(base)
            logo = root / ".brandloom" / "logo.png"; Image.new("RGBA", (32, 32), "red").save(logo)
            manifest = build_generation_manifest(
                brief_path=root / ".brandloom" / "brand-brief.json",
                assets=[{"asset_id": "natural-logo", "category": "company-logo", "scope": "project", "rights_status": "user_authorized", "path": str(logo), "sha256": hashlib.sha256(logo.read_bytes()).hexdigest()}],
                template_path=template, font_paths={"heading": self._font()}, base_image_path=base,
                output_path=image, qa_state="INTERNAL_LOGO_QA", rendered_copy={}, output_type="logo-card",
                host_request={"schema_version":"1.0","backend":"host_builtin_image_tool","output_type":"logo_card","aspect_ratio":"1:1","dimensions":[2048,2048],"prompt":"fixture","reference_assets":[]},
            )
            (output_dir / "generation-manifest-v01.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(brandloom_cli.main(["validate", "--workspace", str(root), "--type", "logo-card"]), 0)

    def test_validate_blocks_manifest_without_canonical_copy_or_logo_hash(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            brief = {"schema_version": "1.0", "project": {"name": "Demo", "slug": "qa"},
                     "copy": {}, "style": {}, "fonts": {}, "assets": {}, "outputs": {}}
            (root / ".brandloom" / "brand-brief.json").write_text(json.dumps(brief), encoding="utf-8")
            state = self._ready_state(); state["state"] = "INTERNAL_LOGO_QA"
            (root / ".brandloom" / "qa-state.json").write_text(json.dumps(state), encoding="utf-8")
            output_dir = root / ".brandloom" / "outputs" / "qa"
            output_dir.mkdir(parents=True)
            Image.new("RGBA", (2048, 2048), "white").save(output_dir / "logo-card-1x1-v01.png")
            (output_dir / "generation-manifest-v01.json").write_text(json.dumps({"output_type": "logo-card", "output": {"path": "logo-card-1x1-v01.png"}}), encoding="utf-8")
            self.assertEqual(brandloom_cli.main(["validate", "--workspace", str(root), "--type", "logo-card"]), 2)

    def test_deliver_blocks_too_many_logo_card_ips(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            brief = {"schema_version": "1.0", "project": {"name": "Demo", "slug": "deliver-ip"},
                     "copy": {}, "style": {}, "fonts": {}, "assets": {"logo_card_ip": ["a", "b", "c", "d"]}, "outputs": {}}
            (root / ".brandloom" / "brand-brief.json").write_text(json.dumps(brief), encoding="utf-8")
            state = self._ready_state(); state["state"] = "LOGO_USER_REVIEW"
            (root / ".brandloom" / "qa-state.json").write_text(json.dumps(state), encoding="utf-8")
            output_dir = root / ".brandloom" / "outputs" / "deliver-ip"; output_dir.mkdir(parents=True)
            Image.new("RGBA", (2048, 2048), "white").save(output_dir / "logo-card-1x1-v01.png")
            manifest = {"output_type": "logo-card", "output": {"path": "logo-card-1x1-v01.png"}, "rendered_copy": {},
                        "assets": [{"asset_id": "natural-logo", "category": "company-logo", "rights_status": "user_authorized", "sha256": "fixture-logo-hash"}]}
            (output_dir / "generation-manifest-v01.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(brandloom_cli.main(["deliver", "--workspace", str(root), "--type", "logo-card", "--reviewed"]), 2)

    def test_deliver_blocks_analysis_only_custom_ip(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            brief = {"schema_version": "1.0", "project": {"name": "Demo", "slug": "deliver-rights"},
                     "copy": {}, "style": {}, "fonts": {}, "assets": {"custom_ip_rights": ["analysis_only"]}, "outputs": {}}
            (root / ".brandloom" / "brand-brief.json").write_text(json.dumps(brief), encoding="utf-8")
            state = self._ready_state(); state["state"] = "LOGO_USER_REVIEW"
            (root / ".brandloom" / "qa-state.json").write_text(json.dumps(state), encoding="utf-8")
            output_dir = root / ".brandloom" / "outputs" / "deliver-rights"; output_dir.mkdir(parents=True)
            Image.new("RGBA", (2048, 2048), "white").save(output_dir / "logo-card-1x1-v01.png")
            manifest = {"output_type": "logo-card", "output": {"path": "logo-card-1x1-v01.png"}, "rendered_copy": {},
                        "assets": [{"asset_id": "natural-logo", "category": "company-logo", "rights_status": "user_authorized", "sha256": "fixture-logo-hash"}]}
            (output_dir / "generation-manifest-v01.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(brandloom_cli.main(["deliver", "--workspace", str(root), "--type", "logo-card", "--reviewed"]), 2)

    def test_state_confirm_rejects_unknown_state(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            self.assertEqual(brandloom_cli.main(["state-confirm", "--workspace", str(root), "--state", "NOT_A_STATE"]), 2)

    def test_state_confirm_cannot_jump_or_record_false_or_missing_confirmation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            self.assertEqual(brandloom_cli.main([
                "state-confirm", "--workspace", str(root), "--key", "context",
            ]), 2)
            self.assertEqual(brandloom_cli.main([
                "state-confirm", "--workspace", str(root), "--key", "context", "--value", "false",
            ]), 2)
            self.assertEqual(brandloom_cli.main([
                "state-confirm", "--workspace", str(root), "--state", "GENERATION_READY",
            ]), 2)
            payload = json.loads((root / ".brandloom" / "qa-state.json").read_text())
            self.assertEqual(payload["state"], "INTAKE")
            self.assertNotIn("context", payload["confirmed"])

    def test_state_confirm_uses_legal_advance_and_invalidation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            self.assertEqual(brandloom_cli.main([
                "state-confirm", "--workspace", str(root), "--state", "CONTEXT_ANALYSIS",
            ]), 0)
            state_path = root / ".brandloom" / "qa-state.json"
            payload = self._ready_state()
            payload["state"] = "GENERATION_CONFIRM_PENDING"
            state_path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(brandloom_cli.main([
                "state-confirm", "--workspace", str(root), "--invalidate", "style",
            ]), 0)
            invalidated = json.loads(state_path.read_text())
            self.assertEqual(invalidated["state"], "FONT_PENDING")
            self.assertNotIn("font", invalidated["confirmed"])

    def test_public_cli_has_no_test_fixture_gate_bypass(self) -> None:
        for argv in (
            ["compose", "--workspace", ".", "--type", "logo-card", "--base", "base.png", "--test-fixture"],
            ["state-confirm", "--workspace", ".", "--test-fixture"],
        ):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                brandloom_cli._parser().parse_args(argv)

    def test_cover_cannot_compose_before_logo_acceptance(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            for source, category in (
                (self._asset(root, "logo.png", (40, 20), (1, 2, 3, 255)), "company-logo"),
                (self._asset(root, "mark.png", (20, 20), (4, 5, 6, 255)), "project-mark"),
            ):
                brandloom_cli.main([
                    "asset-add", "--workspace", str(root), "--source", str(source),
                    "--category", category, "--scope", "project", "--rights", "user_authorized",
                    "--save-confirmed", "--make-default",
                ])
            self._write_ready_brief(root)
            cover = self._asset(root, "cover.png", (2048, 1024), (255, 255, 255, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "cover", "--base", str(cover),
                ])

    def test_compose_rejects_unsafe_project_slug_without_escape(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            for source, category in (
                (self._asset(root, "logo.png", (40, 20), (1, 2, 3, 255)), "company-logo"),
                (self._asset(root, "mark.png", (20, 20), (4, 5, 6, 255)), "project-mark"),
            ):
                brandloom_cli.main([
                    "asset-add", "--workspace", str(root), "--source", str(source),
                    "--category", category, "--scope", "project", "--rights", "user_authorized",
                    "--save-confirmed", "--make-default",
                ])
            self._write_ready_brief(root, slug="../escaped")
            base = self._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base),
                ])
            self.assertFalse((root / ".brandloom" / "escaped").exists())

    def test_compose_rehashes_selected_asset_and_rejects_tampering(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (40, 20), (1, 2, 3, 255))
            brandloom_cli.main([
                "asset-add", "--workspace", str(root), "--source", str(logo),
                "--category", "company-logo", "--scope", "project", "--rights", "user_authorized",
                "--save-confirmed", "--make-default",
            ])
            mark = self._asset(root, "mark.png", (20, 20), (4, 5, 6, 255))
            brandloom_cli.main([
                "asset-add", "--workspace", str(root), "--source", str(mark),
                "--category", "project-mark", "--scope", "project", "--rights", "user_authorized",
                "--save-confirmed", "--make-default",
            ])
            self._write_ready_brief(root)
            manifest = json.loads((root / ".brandloom" / "asset-manifest.json").read_text())
            logo_entry = next(entry for entry in manifest["assets"] if entry["category"] == "company-logo")
            stored = root / ".brandloom" / logo_entry["relative_path"]
            Image.new("RGBA", (40, 20), (250, 0, 0, 255)).save(stored)
            base = self._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base),
                ])

    def test_compose_allows_confirmed_no_project_mark_and_skill_default_logo(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old_home = __import__("os").environ.get("CODEX_HOME")
            __import__("os").environ["CODEX_HOME"] = str(root / "empty-codex")
            try:
                brandloom_cli.main(["init", "--workspace", str(root)])
                self._write_ready_brief(root, assets={"project_mark": None})
                payload = json.loads((root / ".brandloom" / "qa-state.json").read_text())
                payload["confirmed"]["project_mark"] = True
                (root / ".brandloom" / "qa-state.json").write_text(json.dumps(payload), encoding="utf-8")
                base = self._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
                self.assertEqual(brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base),
                ]), 0)
            finally:
                if old_home is None:
                    __import__("os").environ.pop("CODEX_HOME", None)
                else:
                    __import__("os").environ["CODEX_HOME"] = old_home

    def test_manifest_preserves_raw_host_returned_base_path(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (40, 20), (1, 2, 3, 255))
            mark = self._asset(root, "mark.png", (20, 20), (4, 5, 6, 255))
            for source, category in ((logo, "company-logo"), (mark, "project-mark")):
                brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(source), "--category", category,
                                    "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._write_ready_brief(root, slug="raw")
            Image.new("RGBA", (2048, 2048), "white").save(root / "base.png")
            raw_return = "base.png"
            self.assertEqual(brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card",
                                                 "--base", raw_return]), 0)
            manifest = json.loads(next((root / ".brandloom" / "outputs" / "raw").glob("generation-manifest-v01.json")).read_text(encoding="utf-8"))
            self.assertEqual(manifest["image_tool_returned_path"], raw_return)


if __name__ == "__main__":
    unittest.main()
