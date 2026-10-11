from __future__ import annotations

import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image

from brandloom.scripts import brandloom_cli
from tests.font_test_utils import find_test_font


class PlatformPipelineTests(unittest.TestCase):
    def _image(self, root: Path, name: str, dimensions: tuple[int, int], color: str) -> Path:
        path = root / name
        Image.new("RGBA", dimensions, color).save(path)
        return path

    def _ready_state(self) -> dict[str, object]:
        confirmed = {
            key: True for key in (
                "context", "output_targets", "output_spec", "copy", "style", "font",
                "company_logo", "project_mark", "ip_combination", "ip_usage", "shot_list",
                "coherence", "generation_confirmation",
            )
        }
        confirmed["ip_cast"] = "tuotuo"
        return {
            "schema_version": "1.0", "session_id": "platform-pipeline", "mode": "new",
            "state": "GENERATION_READY", "project_slug": "demo", "source_refs": [],
            "confirmed": confirmed, "invalidated": [],
            "generation_backend": "host_builtin_image_tool", "updated_at": "",
        }

    def _brief(self) -> dict[str, object]:
        cjk_font = Path("C:/Windows/Fonts/msyh.ttc")
        font = str(cjk_font if cjk_font.is_file() else find_test_font())
        return {
            "schema_version": "1.0",
            "project": {"name": "Demo project", "slug": "demo"},
            "copy": {"title": "Useful project", "subtitle": "Clear results"},
            "style": {"foreground": "#ffffff"},
            "fonts": {"heading": font, "body": font},
            "assets": {"company_logo": "none"},
            "outputs": {
                "targets": [
                    {
                        "id": "github-social-preview", "dimensions": [1280, 640], "language": "en",
                        "copy": {"title": "GitHub cover", "features": ["Versioned workflow"]},
                        "workflow_steps": [{"en": "Understand"}, {"en": "Deliver"}],
                    },
                    {
                        "id": "douyin-cover", "dimensions": [1080, 1440], "language": "zh",
                        "copy": {"title": "抖音封面", "features": ["按平台适配"]},
                        "workflow_steps": [{"zh": "理解项目"}, {"zh": "交付结果"}],
                    },
                ]
            },
        }

    def _prepare_workspace(self, root: Path, *, omit_logo_selection: bool = False) -> None:
        brandloom_cli.main(["init", "--workspace", str(root)])
        logo = self._image(root, "logo.png", (240, 80), "white")
        mark = self._image(root, "mark.png", (100, 100), "#36c1ff")
        for path, category in ((logo, "company-logo"), (mark, "project-mark")):
            self.assertEqual(brandloom_cli.main([
                "asset-add", "--workspace", str(root), "--source", str(path), "--category", category,
                "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default",
            ]), 0)
        runtime = root / ".brandloom"
        brief = self._brief()
        if omit_logo_selection:
            brief["assets"].pop("company_logo")
        brief_path = runtime / "brand-brief.json"
        brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
        state = self._ready_state()
        state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
        (runtime / "qa-state.json").write_text(json.dumps(state), encoding="utf-8")

    def _request_target(self, root: Path, target_id: str) -> str:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(brandloom_cli.main([
                "request", "--workspace", str(root), "--target-id", target_id,
            ]), 0)
        return json.loads(output.getvalue())["request_id"]

    def test_multiple_confirmed_targets_have_independent_manifests_and_reviews(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            github_base = self._image(root, "github-base.png", (640, 320), "#25486e")
            original_hash = hashlib.sha256(github_base.read_bytes()).hexdigest()
            github_request_id = self._request_target(root, "github-social-preview")
            self.assertEqual(brandloom_cli.main([
                "compose", "--workspace", str(root), "--type", "cover",
                "--target-id", "github-social-preview", "--request-id", github_request_id, "--base", str(github_base),
            ]), 0)
            output_dir = root / ".brandloom" / "outputs" / "demo"
            github_manifest = json.loads((output_dir / "generation-manifest-v01.json").read_text(encoding="utf-8"))
            self.assertEqual(github_manifest["target_id"], "github-social-preview")
            self.assertEqual(github_manifest["generated_base_dimensions"], [640, 320])
            self.assertEqual(hashlib.sha256(github_base.read_bytes()).hexdigest(), original_hash)
            github_output = Path(github_manifest["output"]["path"])
            with Image.open(github_output) as image:
                self.assertEqual(image.size, (1280, 640))
            github_manifest["generated_base_dimensions"] = [1280, 640]
            (output_dir / "generation-manifest-v01.json").write_text(json.dumps(github_manifest), encoding="utf-8")
            self.assertEqual(brandloom_cli.main([
                "validate", "--workspace", str(root), "--type", "cover", "--target-id", "github-social-preview",
            ]), 2)
            github_manifest["generated_base_dimensions"] = [640, 320]
            (output_dir / "generation-manifest-v01.json").write_text(json.dumps(github_manifest), encoding="utf-8")
            self.assertEqual(brandloom_cli.main([
                "validate", "--workspace", str(root), "--type", "cover", "--target-id", "github-social-preview",
            ]), 0)
            self.assertEqual(brandloom_cli.main([
                "deliver", "--workspace", str(root), "--type", "cover", "--target-id", "github-social-preview", "--reviewed",
            ]), 0)
            state = json.loads((root / ".brandloom" / "qa-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["state"], "GENERATION_READY")
            self.assertEqual(state["delivered_targets"], ["github-social-preview"])

            douyin_base = self._image(root, "douyin-base.png", (540, 720), "#402d56")
            douyin_request_id = self._request_target(root, "douyin-cover")
            self.assertEqual(brandloom_cli.main([
                "compose", "--workspace", str(root), "--type", "cover",
                "--target-id", "douyin-cover", "--request-id", douyin_request_id, "--base", str(douyin_base),
            ]), 0)
            self.assertEqual(brandloom_cli.main([
                "validate", "--workspace", str(root), "--type", "cover", "--target-id", "douyin-cover",
            ]), 0)
            self.assertEqual(brandloom_cli.main([
                "deliver", "--workspace", str(root), "--type", "cover", "--target-id", "douyin-cover", "--reviewed",
            ]), 0)
            state = json.loads((root / ".brandloom" / "qa-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["state"], "DELIVERED")
            self.assertEqual(set(state["delivered_targets"]), {"github-social-preview", "douyin-cover"})
            self.assertTrue((output_dir / "generation-manifest-v02.json").is_file())

    def test_new_platform_workflow_rejects_square_logo_card_output(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            square_base = self._image(root, "square.png", (1254, 1254), "#ffffff")
            with self.assertRaisesRegex(ValueError, "square logo-card generation is disabled"):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "logo-card", "--base", str(square_base),
                ])
            self.assertFalse((root / ".brandloom" / "outputs" / "demo").exists())

    def test_platform_cover_rejects_legacy_state_that_bypasses_new_qa_gate(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["state"] = "GENERATE_COVER_BASE"
            state["confirmed"] = {"ip_cast": "tuotuo", "company_logo": True}
            state_path.write_text(json.dumps(state), encoding="utf-8")
            base = self._image(root, "github-base.png", (640, 320), "#25486e")

            with self.assertRaisesRegex(RuntimeError, "GENERATION_READY"):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "cover",
                    "--target-id", "github-social-preview", "--base", str(base),
                ])
            self.assertFalse((root / ".brandloom" / "outputs" / "demo").exists())

    def test_platform_workflow_rejects_legacy_targetless_cover(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["state"] = "GENERATE_COVER_BASE"
            state["accepted_logo"] = {"path": "legacy-approved.png"}
            state_path.write_text(json.dumps(state), encoding="utf-8")
            base = self._image(root, "legacy-base.png", (1774, 887), "#25486e")

            with self.assertRaisesRegex(ValueError, "requires a confirmed platform target"):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "cover", "--base", str(base),
                ])

    def test_legacy_targetless_cover_requires_accepted_logo_before_state_transition(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["outputs"].pop("targets")
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")
            base = self._image(root, "legacy-base.png", (1774, 887), "#25486e")

            with self.assertRaisesRegex(ValueError, "requires an accepted logo-card"):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "cover", "--base", str(base),
                ])
            self.assertFalse((root / ".brandloom" / "outputs" / "demo").exists())

    def test_request_returns_confirmed_target_prompt_before_generation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(brandloom_cli.main([
                    "request", "--workspace", str(root), "--target-id", "github-social-preview",
                ]), 0)

            request = json.loads(output.getvalue())
            self.assertEqual(request["target_id"], "github-social-preview")
            self.assertTrue(request["request_id"])
            self.assertEqual(request["dimensions"], [1280, 640])
            self.assertIn("Target aspect ratio: 2:1, canvas 1280x640", request["prompt"])
            self.assertFalse((root / ".brandloom" / "outputs" / "demo").exists())
            state = json.loads((root / ".brandloom" / "qa-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["generation_request"]["request_id"], request["request_id"])
            self.assertEqual(state["generation_request"]["target_id"], "github-social-preview")

    def test_platform_composition_requires_current_target_preflight(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            base = self._image(root, "github-base.png", (640, 320), "#25486e")

            with self.assertRaisesRegex(ValueError, "request preflight ID"):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "cover",
                    "--target-id", "github-social-preview", "--base", str(base),
                ])
            self.assertFalse((root / ".brandloom" / "outputs" / "demo").exists())

    def test_platform_composition_rejects_request_id_for_another_target(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            request_id = self._request_target(root, "github-social-preview")
            base = self._image(root, "douyin-base.png", (540, 720), "#402d56")

            with self.assertRaisesRegex(ValueError, "request preflight ID"):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "cover",
                    "--target-id", "douyin-cover", "--request-id", request_id, "--base", str(base),
                ])

    def test_request_rejects_changed_brief_before_generation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["outputs"]["targets"][0]["copy"]["title"] = "Changed after confirmation"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "changed after QA confirmation"):
                brandloom_cli.main([
                    "request", "--workspace", str(root), "--target-id", "github-social-preview",
                ])

    def test_request_rejects_malformed_workflow_before_generation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["outputs"]["targets"][0]["workflow_steps"] = [
                {"zh": "理解项目"}, {"zh": "交付结果"},
            ]
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing its confirmed en title"):
                brandloom_cli.main([
                    "request", "--workspace", str(root), "--target-id", "github-social-preview",
                ])
            self.assertNotIn("generation_request", json.loads(state_path.read_text(encoding="utf-8")))

    def test_request_rejects_unresolved_project_mark_before_generation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["assets"]["project_mark"] = "missing-project-mark"
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "explicit asset not found: missing-project-mark"):
                brandloom_cli.main([
                    "request", "--workspace", str(root), "--target-id", "github-social-preview",
                ])
            self.assertNotIn("generation_request", json.loads(state_path.read_text(encoding="utf-8")))

    def test_request_recovers_unavailable_font_before_generation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["fonts"]["heading"] = str(root / "missing-font.ttf")
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with patch("brandloom.scripts.brandloom_cli.resolve_font_for_text", return_value=find_test_font()) as resolve, patch(
                "brandloom.scripts.brandloom_cli.validate_composition_layout"
            ):
                brandloom_cli.main([
                    "request", "--workspace", str(root), "--target-id", "github-social-preview",
                ])
            self.assertTrue(resolve.called)
            self.assertEqual(resolve.call_args_list[0].args[-1], str(root / "missing-font.ttf"))
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["generation_request"]["target_id"],
                "github-social-preview",
            )

    def test_request_recovers_font_without_copy_glyphs_before_generation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["outputs"]["targets"][0]["copy"]["title"] = "BrandLoom: 中文项目标题?!"
            brief["fonts"]["heading"] = str(root / "font-without-punctuation.ttf")
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with patch("brandloom.scripts.brandloom_cli.resolve_font_for_text", return_value=find_test_font()) as resolve, patch(
                "brandloom.scripts.brandloom_cli.validate_composition_layout"
            ):
                brandloom_cli.main([
                    "request", "--workspace", str(root), "--target-id", "github-social-preview",
                ])
            heading_call = next(call for call in resolve.call_args_list if call.args[1] == "heading")
            self.assertIn("?!", heading_call.args[2])
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["generation_request"]["target_id"],
                "github-social-preview",
            )

    def test_request_recovers_workflow_font_and_checks_workflow_text_before_generation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["fonts"]["heading"] = str(root / "font-without-chinese.ttf")
            brief["outputs"]["targets"][0]["language"] = "zh"
            brief["outputs"]["targets"][0]["workflow_steps"] = [
                {"zh": "理解项目"}, {"zh": "交付结果"},
            ]
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with patch("brandloom.scripts.brandloom_cli.resolve_font_for_text", return_value=find_test_font()) as resolve, patch(
                "brandloom.scripts.brandloom_cli.validate_composition_layout"
            ):
                brandloom_cli.main([
                    "request", "--workspace", str(root), "--target-id", "github-social-preview",
                ])
            heading_call = next(call for call in resolve.call_args_list if call.args[1] == "heading")
            self.assertIn("理解项目", heading_call.args[2])
            self.assertIn("交付结果", heading_call.args[2])
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["generation_request"]["target_id"],
                "github-social-preview",
            )

    def test_request_rejects_copy_that_cannot_fit_before_generation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["outputs"]["targets"][0]["copy"]["title"] = "A" * 1000
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "text does not fit box"):
                brandloom_cli.main([
                    "request", "--workspace", str(root), "--target-id", "github-social-preview",
                ])
            self.assertNotIn("generation_request", json.loads(state_path.read_text(encoding="utf-8")))

    def test_request_rejects_workflow_label_that_cannot_fit_before_generation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["outputs"]["targets"][0]["workflow_steps"] = [
                {"en": "A" * 1000}, {"en": "Deliver"},
            ]
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "workflow text does not fit"):
                brandloom_cli.main([
                    "request", "--workspace", str(root), "--target-id", "github-social-preview",
                ])
            self.assertNotIn("generation_request", json.loads(state_path.read_text(encoding="utf-8")))

    def test_platform_composition_rejects_reference_changed_after_preflight(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["style"]["profile"] = "light-saas-product-showcase"
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            reference_dir = root / ".brandloom" / "style-reference-library"
            reference_dir.mkdir(parents=True)
            reference_path = reference_dir / "style-04-light-saas-product.png"
            Image.new("RGB", (32, 20), "white").save(reference_path)
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")
            request_id = self._request_target(root, "github-social-preview")
            Image.new("RGB", (32, 20), "black").save(reference_path)
            base = self._image(root, "github-base.png", (640, 320), "#25486e")

            with self.assertRaisesRegex(ValueError, "request preflight ID"):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "cover",
                    "--target-id", "github-social-preview", "--request-id", request_id,
                    "--base", str(base),
                ])
            self.assertFalse((root / ".brandloom" / "outputs" / "demo").exists())

    def test_missing_logo_selection_does_not_fall_back_to_default_logo(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root, omit_logo_selection=True)

            with self.assertRaisesRegex(ValueError, "company_logo selection is unresolved"):
                self._request_target(root, "github-social-preview")

    def test_blank_logo_selection_is_not_treated_as_confirmed_no_logo(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["assets"]["company_logo"] = ""
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "asset ID or explicit none"):
                brandloom_cli.main([
                    "request", "--workspace", str(root), "--target-id", "github-social-preview",
                ])

    def test_platform_composition_rejects_brief_changed_after_confirmation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["outputs"]["targets"][0]["dimensions"] = [1600, 800]
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            base = self._image(root, "github-base.png", (640, 320), "#25486e")

            with self.assertRaisesRegex(ValueError, "changed after QA confirmation"):
                brandloom_cli.main([
                    "compose", "--workspace", str(root), "--type", "cover",
                    "--target-id", "github-social-preview", "--base", str(base),
                ])
            self.assertFalse((root / ".brandloom" / "outputs" / "demo").exists())

    def test_generation_confirmation_binds_current_brief_hash(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["state"] = "GENERATION_CONFIRM_PENDING"
            state["confirmed"].pop("generation_confirmation")
            state.pop("confirmed_brief_sha256", None)
            state_path.write_text(json.dumps(state), encoding="utf-8")

            self.assertEqual(brandloom_cli.main([
                "state-confirm", "--workspace", str(root), "--key", "generation_confirmation",
                "--value", "true", "--state", "GENERATION_READY",
            ]), 0)
            updated = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["confirmed_brief_sha256"], hashlib.sha256(brief_path.read_bytes()).hexdigest())

    def test_explicit_no_logo_choice_composes_without_default_logo(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            base = self._image(root, "github-base.png", (640, 320), "#25486e")
            request_id = self._request_target(root, "github-social-preview")
            self.assertEqual(brandloom_cli.main([
                "compose", "--workspace", str(root), "--type", "cover",
                "--target-id", "github-social-preview", "--request-id", request_id, "--base", str(base),
            ]), 0)
            manifest = json.loads((root / ".brandloom" / "outputs" / "demo" / "generation-manifest-v01.json").read_text(encoding="utf-8"))
            self.assertFalse(any(item.get("category") == "company-logo" for item in manifest["assets"]))

    def test_explicit_no_logo_and_no_project_mark_can_pass_output_validation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["assets"]["project_mark"] = "none"
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")
            base = self._image(root, "github-base.png", (640, 320), "#25486e")
            request_id = self._request_target(root, "github-social-preview")

            self.assertEqual(brandloom_cli.main([
                "compose", "--workspace", str(root), "--type", "cover",
                "--target-id", "github-social-preview", "--request-id", request_id, "--base", str(base),
            ]), 0)
            manifest_path = root / ".brandloom" / "outputs" / "demo" / "generation-manifest-v01.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["assets"], [])
            self.assertEqual(brandloom_cli.main([
                "validate", "--workspace", str(root), "--type", "cover", "--target-id", "github-social-preview",
            ]), 0)

    def test_style_reference_assets_do_not_block_platform_validation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._prepare_workspace(root)
            brief_path = root / ".brandloom" / "brand-brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["style"]["profile"] = "light-saas-product-showcase"
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            reference_dir = root / ".brandloom" / "style-reference-library"
            reference_dir.mkdir(parents=True)
            Image.new("RGB", (32, 20), "white").save(reference_dir / "style-04-light-saas-product.png")
            state_path = root / ".brandloom" / "qa-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["confirmed_brief_sha256"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")
            base = self._image(root, "github-base.png", (640, 320), "#25486e")
            request_id = self._request_target(root, "github-social-preview")

            self.assertEqual(brandloom_cli.main([
                "compose", "--workspace", str(root), "--type", "cover",
                "--target-id", "github-social-preview", "--request-id", request_id, "--base", str(base),
            ]), 0)
            manifest_path = root / ".brandloom" / "outputs" / "demo" / "generation-manifest-v01.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(any(asset["category"] == "style-reference" for asset in manifest["assets"]))
            self.assertEqual(brandloom_cli.main([
                "validate", "--workspace", str(root), "--type", "cover", "--target-id", "github-social-preview",
            ]), 0)


if __name__ == "__main__":
    unittest.main()
