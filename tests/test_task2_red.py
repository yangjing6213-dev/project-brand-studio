import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from brandloom.scripts.brandloom_core.manifests import build_generation_manifest
from brandloom.scripts.brandloom_core.models import QASession, QAState, TaskMode
from brandloom.scripts.brandloom_core.state_machine import invalidate_from
from brandloom.scripts.brandloom_core.validation import validate_output
from brandloom.scripts import brandloom_cli
from tests.test_pipeline import PipelineTests


class Task2ContractTests(unittest.TestCase):
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
            host_request={"backend": "host_builtin_image_tool", "reference_assets": []},
        )

    def test_missing_each_production_manifest_section_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = self._manifest(root)
            for section in ("brief", "assets", "template", "fonts", "base_image", "output", "host_request", "rendered_copy", "output_type"):
                broken = dict(manifest); broken.pop(section, None)
                report = validate_output(root / "logo-card-1x1-v01.png", expected_dimensions=(2048, 2048), manifest=broken, manifest_path=root / "generation-manifest-v01.json", brief_path=root / "brief.json")
                self.assertFalse(report.passed, section)

    def test_generation_manifest_latest_uses_numeric_version(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for version in (99, 100):
                (directory / f"generation-manifest-v{version}.json").write_text(json.dumps({"output_type": "logo-card", "output": {"path": "x"}}))
            path, _ = brandloom_cli._latest_manifest(directory, "logo-card")
            self.assertEqual(path.name, "generation-manifest-v100.json")

    def test_invalidation_clears_accepted_logo_evidence(self):
        session = QASession("1.0", "s", TaskMode.NEW, QAState.GENERATION_READY, "p", accepted_logo={"path": "x", "sha256": "a"}, confirmed={"style": True})
        self.assertIsNone(invalidate_from(session, "style").accepted_logo)

    def test_malformed_project_mark_selection_hard_stops(self):
        helper = PipelineTests()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            brandloom_cli.main(["init", "--workspace", str(root)])
            logo = helper._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            helper._write_ready_brief(root, assets={"project_mark": {"id": "bad"}})
            base = helper._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)])

    def test_mutated_accepted_logo_blocks_cover_composition(self):
        helper = PipelineTests()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            brandloom_cli.main(["init", "--workspace", str(root)])
            logo = helper._asset(root, "logo.png", (100, 40), (10, 20, 30, 255))
            brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(logo), "--category", "company-logo", "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            helper._write_ready_brief(root, assets={"project_mark": None})
            base = helper._asset(root, "base.png", (2048, 2048), (255, 255, 255, 255))
            brandloom_cli.main(["compose", "--workspace", str(root), "--type", "logo-card", "--base", str(base)])
            brandloom_cli.main(["validate", "--workspace", str(root), "--type", "logo-card"])
            brandloom_cli.main(["deliver", "--workspace", str(root), "--type", "logo-card", "--reviewed"])
            accepted = json.loads((root / ".brandloom" / "qa-state.json").read_text())["accepted_logo"]
            Path(accepted["path"]).write_bytes(b"tampered")
            cover = helper._asset(root, "cover.png", (2048, 1024), (240, 240, 240, 255))
            with self.assertRaises(ValueError):
                brandloom_cli.main(["compose", "--workspace", str(root), "--type", "cover", "--base", str(cover)])
