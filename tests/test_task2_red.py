import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from brandloom.scripts.brandloom_core.manifests import build_generation_manifest
from brandloom.scripts.brandloom_core.models import QASession, QAState, TaskMode
from brandloom.scripts.brandloom_core.json_io import read_json_dataclass, write_json_dataclass
from brandloom.scripts.brandloom_core.state_machine import invalidate_from
from brandloom.scripts.brandloom_core.validation import validate_accepted_logo_evidence, validate_output
from brandloom.scripts import brandloom_cli
from tests.font_test_utils import find_test_font


class Task2ContractTests(unittest.TestCase):
    def _asset(self, root: Path, name: str, size: tuple[int, int], color):
        path = root / name
        Image.new("RGBA", size, color).save(path)
        return path

    def _ready_brief(self, root: Path, assets):
        runtime = root / ".brandloom"; runtime.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version":"1.0","project":{"name":"Demo","slug":"demo"},"copy":{"title":"Demo","subtitle":"Local"},"style":{"foreground":"#111111"},"fonts":{"heading":str(find_test_font()),"body":str(find_test_font())},"assets":assets,"outputs":{}}
        (runtime / "brand-brief.json").write_text(json.dumps(payload), encoding="utf-8")
        confirmed = {key: True for key in ("context","copy","style","font","company_logo","project_mark","ip_combination","ip_usage","shot_list","output_spec","coherence","generation_confirmation")}; confirmed["ip_cast"] = "tuotuo"
        (runtime / "qa-state.json").write_text(json.dumps({"schema_version":"1.0","session_id":"s","mode":"new","state":"GENERATION_READY","project_slug":"demo","confirmed":confirmed,"invalidated":[],"generation_backend":"host_builtin_image_tool"}), encoding="utf-8")
    def _files(self, root: Path):
        brief = root / "brief.json"; brief.write_text("{}")
        template = root / "template.json"; template.write_text("{}")
        base = root / "base.png"; Image.new("RGB", (2048, 2048), "white").save(base)
        output = root / "logo-card-1x1-v01.png"; Image.new("RGB", (2048, 2048), "white").save(output)
        font = root / "font.ttf"; font.write_bytes(b"font")
        return brief, template, base, output, font

    def _manifest(self, root: Path):
        brief, template, base, output, font = self._files(root)
        logo = root / "logo.png"; Image.new("RGB", (32, 32), "red").save(logo)
        return build_generation_manifest(
            brief_path=brief, assets=[{"asset_id": "logo", "category": "company-logo", "scope": "project", "rights_status": "user_authorized", "path": str(logo), "expected_sha256": hashlib.sha256(logo.read_bytes()).hexdigest()}],
            template_path=template, font_paths={"heading": font}, base_image_path=base,
            output_path=output, qa_state="INTERNAL_LOGO_QA", rendered_copy={}, output_type="logo-card",
            host_request={"schema_version": "1.0", "backend": "host_builtin_image_tool", "output_type": "logo_card", "aspect_ratio": "1:1", "dimensions": [2048, 2048], "prompt": "fixture", "reference_assets": []},
        )

    def test_missing_each_production_manifest_section_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = self._manifest(root)
            baseline_report = validate_output(root / "logo-card-1x1-v01.png", expected_dimensions=(2048, 2048), manifest=manifest, manifest_path=root / "generation-manifest-v01.json", brief_path=root / "brief.json")
            self.assertTrue(baseline_report.passed, baseline_report.failures)
            checks = {
                "brief": "manifest_brief", "assets": "manifest_assets", "template": "manifest_template",
                "fonts": "manifest_fonts", "base_image": "manifest_base_image", "output": "manifest_output",
                "host_request": "manifest_host_request", "rendered_copy": "manifest_rendered_copy", "output_type": "manifest_output_type",
            }
            for section in checks:
                broken = dict(manifest); broken.pop(section, None)
                report = validate_output(root / "logo-card-1x1-v01.png", expected_dimensions=(2048, 2048), manifest=broken, manifest_path=root / "generation-manifest-v01.json", brief_path=root / "brief.json")
                self.assertFalse(report.checks[checks[section]], section)
            broken_host = dict(manifest); broken_host["host_request"] = dict(manifest["host_request"]); broken_host["host_request"].pop("reference_assets")
            report = validate_output(root / "logo-card-1x1-v01.png", expected_dimensions=(2048, 2048), manifest=broken_host, manifest_path=root / "generation-manifest-v01.json", brief_path=root / "brief.json")
            self.assertFalse(report.checks["manifest_host_request"])

    def test_host_request_missing_canonical_fields_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = self._manifest(root)
            manifest["host_request"] = {"backend": "host_builtin_image_tool", "reference_assets": []}
            report = validate_output(root / "logo-card-1x1-v01.png", expected_dimensions=(2048, 2048), manifest=manifest, manifest_path=root / "generation-manifest-v01.json", brief_path=root / "brief.json")
            self.assertFalse(report.checks["manifest_host_request"])

    def test_validate_persists_candidate_manifest_identity_before_delivery(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._ready_brief(root, {"project_mark": None})
            base = self._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)])
            self.assertEqual(brandloom_cli.main(["validate", "--workspace", str(root), "--type", "logo-card"]), 0)
            session = json.loads((root / ".brandloom" / "qa-state.json").read_text())
            self.assertIsNone(session.get("accepted_logo"))
            self.assertIsInstance(session.get("logo_review_candidate"), dict)
            self.assertIn("manifest_sha256", session["logo_review_candidate"])

    def test_validate_slug_mismatch_returns_two_without_writing_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._ready_brief(root, {"project_mark": None}); base = self._asset(root, "base.png", (2048, 2048), (255,255,255,255))
            brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)])
            before = json.loads((root / ".brandloom" / "qa-state.json").read_text())
            self.assertEqual(brandloom_cli.main(["validate", "--workspace", str(root), "--type", "logo-card", "--slug", "other"]), 2)
            after = json.loads((root / ".brandloom" / "qa-state.json").read_text())
            self.assertIsNone(after.get("logo_review_candidate"))
            self.assertIsNone(after.get("accepted_logo"))
            self.assertEqual(after["state"], before["state"])

    def test_later_unreviewed_manifest_and_slug_mismatch_cannot_replace_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._ready_brief(root, {"project_mark": None}); base = self._asset(root, "base.png", (2048, 2048), (255,255,255,255))
            brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)]); brandloom_cli.main(["validate", "--workspace", str(root), "--type", "logo-card"])
            out = root / ".brandloom" / "outputs" / "demo"; first = out / "generation-manifest-v01.json"; (out / "generation-manifest-v02.json").write_bytes(first.read_bytes())
            self.assertEqual(brandloom_cli.main(["deliver", "--workspace", str(root), "--type", "logo-card", "--reviewed", "--slug", "other"]), 2)
            self.assertEqual(brandloom_cli.main(["deliver", "--workspace", str(root), "--type", "logo-card", "--reviewed"]), 0)
            persisted = json.loads((root / ".brandloom" / "qa-state.json").read_text())
            self.assertIsNone(persisted.get("logo_review_candidate"))
            evidence = persisted["accepted_logo"]
            self.assertTrue(evidence["manifest_path"].endswith("generation-manifest-v01.json"))

    def test_generation_manifest_latest_uses_numeric_version(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for version in (99, 100):
                (directory / f"generation-manifest-v{version}.json").write_text(json.dumps({"output_type": "logo-card", "output": {"path": "x"}}))
            path, _ = brandloom_cli._latest_manifest(directory, "logo-card")
            self.assertEqual(path.name, "generation-manifest-v100.json")

    def test_invalidation_clears_accepted_logo_evidence(self):
        session = QASession("1.0", "s", TaskMode.NEW, QAState.GENERATION_READY, "p", accepted_logo={"path": "x", "sha256": "a"}, logo_review_candidate={"path": "y"}, confirmed={"style": True})
        changed = invalidate_from(session, "style")
        self.assertIsNone(changed.accepted_logo)
        self.assertIsNone(changed.logo_review_candidate)

    def test_qasession_json_roundtrip_preserves_candidate_and_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "qa-state.json"
            session = QASession("1.0", "s", TaskMode.NEW, QAState.LOGO_USER_REVIEW, "demo", accepted_logo={"path": "/tmp/a", "sha256": "a"}, logo_review_candidate={"path": "/tmp/c", "sha256": "c"}, confirmed={"style": True})
            write_json_dataclass(path, session)
            self.assertEqual(read_json_dataclass(path, QASession), session)

    def test_legacy_or_malformed_logo_evidence_defaults_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); runtime = root / ".brandloom"; runtime.mkdir()
            payload = {"schema_version": "1.0", "session_id": "s", "mode": "new", "state": "LOGO_USER_REVIEW", "project_slug": "demo", "confirmed": {}, "invalidated": [], "accepted_logo": {"path": "relative"}, "logo_review_candidate": {"path": "relative"}}
            (runtime / "qa-state.json").write_text(json.dumps(payload), encoding="utf-8")
            loaded = brandloom_cli._load_session(root)
            self.assertIsNone(loaded.accepted_logo)
            self.assertIsNone(loaded.logo_review_candidate)
            self.assertFalse(validate_accepted_logo_evidence(payload["accepted_logo"]))
            legacy = dict(payload); legacy.pop("accepted_logo"); legacy.pop("logo_review_candidate")
            (runtime / "qa-state.json").write_text(json.dumps(legacy), encoding="utf-8")
            legacy_loaded = brandloom_cli._load_session(root)
            self.assertIsNone(legacy_loaded.accepted_logo)
            self.assertIsNone(legacy_loaded.logo_review_candidate)

    def test_successful_new_logo_compose_clears_stale_logo_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._ready_brief(root, {"project_mark": None}); state_path = root / ".brandloom" / "qa-state.json"
            payload = json.loads(state_path.read_text()); payload["accepted_logo"] = {"stale": True}; payload["logo_review_candidate"] = {"stale": True}; state_path.write_text(json.dumps(payload), encoding="utf-8")
            base = self._asset(root, "base.png", (2048, 2048), (255,255,255,255))
            self.assertEqual(brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)]), 0)
            after = json.loads(state_path.read_text())
            self.assertIsNone(after.get("accepted_logo")); self.assertIsNone(after.get("logo_review_candidate"))

    def test_malformed_project_mark_selection_hard_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._ready_brief(root, {"project_mark": {"id": "bad"}})
            base = self._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)])

    def test_unknown_string_project_mark_selection_hard_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._ready_brief(root, {"project_mark": "missing-project-mark"}); base = self._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)])

    def test_missing_project_mark_without_default_hard_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._ready_brief(root, {}); base = self._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)])

    def test_corrupt_project_mark_default_hard_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (100, 40), (10, 20, 30, 255)); mark = self._asset(root, "mark.png", (40, 40), (30, 40, 50, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(mark), "--category", "project-mark", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            asset_manifest = root / ".brandloom" / "asset-manifest.json"
            data = json.loads(asset_manifest.read_text()); entry = next(item for item in data["assets"] if item["category"] == "project-mark"); entry["relative_path"] = "library/project-mark/missing.png"; asset_manifest.write_text(json.dumps(data), encoding="utf-8")
            self._ready_brief(root, {}); base = self._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)])

    def test_numeric_zero_project_mark_is_not_treated_as_none(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._ready_brief(root, {"project_mark": 0})
            base = self._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)])

    def test_mutated_accepted_logo_blocks_cover_composition(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            self._ready_brief(root, {"project_mark": None})
            base = self._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)])
            brandloom_cli.main(["validate", "--workspace", str(root), "--type", "logo-card"])
            brandloom_cli.main(["deliver", "--workspace", str(root), "--type", "logo-card", "--reviewed"])
            accepted = json.loads((root / ".brandloom" / "qa-state.json").read_text())["accepted_logo"]
            Path(accepted["path"]).write_bytes(b"tampered")
            cover = self._asset(root, "cover.png", (2048, 1024), (240, 240, 240, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main(["compose", "--workspace", str(root), "--type", "cover", "--base", str(cover)])
