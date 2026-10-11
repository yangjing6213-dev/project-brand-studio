from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.prompt_builder import (
    build_base_prompt,
    validate_generated_path,
)
from brandloom.scripts.brandloom_core.validation import _host_request_integrity
from brandloom.scripts.brandloom_core import prompt_builder


class PromptBuilderTests(unittest.TestCase):
    def _brief(self) -> BrandBrief:
        return BrandBrief(
            schema_version="1.0",
            project={"name": "Demo", "slug": "demo"},
            copy={"title": "Readable title", "subtitle": "Do not render this copy"},
            style={
                "profile": "bright-saas-real-scene",
                "family": "reference-adaptive",
                "reserved_text_zones": ["left third", "bottom band"],
            },
            fonts={},
            assets={
                "ip_profiles": [
                    {"id": "author-anime", "role": "presenter"},
                    {"id": "tuotuo", "role": "execution/system"},
                    {"id": "xingbi", "role": "feedback/result"},
                ]
            },
            outputs={"logo_card": {"width": 1254, "height": 1254}},
        )

    def test_logo_card_prompt_describes_safe_scene_and_selected_roles(self) -> None:
        prompt = build_base_prompt(self._brief(), "logo_card")
        self.assertIn("1:1", prompt)
        self.assertIn("bright-saas-real-scene", prompt)
        self.assertIn("reserved blank text zones", prompt)
        self.assertIn("left third", prompt)
        self.assertIn("author-anime", prompt)
        self.assertIn("presenter", prompt)
        self.assertIn("tuotuo", prompt)
        self.assertIn("execution/system", prompt)
        self.assertIn("xingbi", prompt)
        self.assertIn("feedback/result", prompt)
        self.assertIn("no visible company logo", prompt)
        self.assertIn("no readable final marketing text", prompt)

    def test_cover_prompt_is_full_bleed_without_fixed_copy_panel_or_logo_square_inheritance(self) -> None:
        prompt = build_base_prompt(self._brief(), "cover")
        self.assertIn("2:1", prompt)
        self.assertIn("full-bleed", prompt)
        self.assertIn("Do not reserve a fixed left copy panel", prompt)
        self.assertNotIn("left third", prompt)
        self.assertNotIn("reuse the accepted LOGO visual DNA", prompt)
        self.assertIn("no readable final marketing text", prompt)

    def test_canonical_assets_select_ip_per_output_type(self) -> None:
        brief = self._brief()
        brief = BrandBrief(
            schema_version=brief.schema_version,
            project=brief.project,
            copy=brief.copy,
            style=brief.style,
            fonts=brief.fonts,
            assets={"logo_card_ip": ["tuotuo"], "cover_ip": ["author-anime", "xingbi"]},
            outputs=brief.outputs,
        )
        logo_prompt = build_base_prompt(brief, "logo_card")
        cover_prompt = build_base_prompt(brief, "cover")
        self.assertIn("tuotuo", logo_prompt)
        self.assertNotIn("author-anime", logo_prompt)
        self.assertIn("author-anime", cover_prompt)
        self.assertIn("xingbi", cover_prompt)

    def test_validate_generated_path_can_enforce_output_type_dimensions(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            square = root / "square.png"
            wide = root / "wide.png"
            Image.new("RGB", (2048, 2048), "white").save(square)
            Image.new("RGB", (1774, 887), "white").save(wide)
            with self.assertRaises(ValueError):
                validate_generated_path(wide, expected="logo_card")
            with self.assertRaises(ValueError):
                validate_generated_path(square, expected="cover")

    def test_prompt_has_no_secret_or_provider_fallback_language(self) -> None:
        prompt = build_base_prompt(self._brief(), "logo_card")
        forbidden = ("OPENAI_API_KEY", "Images API", "image_gen.py", "redraw the company logo")
        for term in forbidden:
            self.assertNotIn(term, prompt)

    def test_expected_dimensions_are_checked_when_requested(self) -> None:
        brief = self._brief()
        with self.assertRaises(ValueError):
            build_base_prompt(brief, "logo_card", expected=(1024, 1024))

    def test_validate_generated_path_rejects_missing_and_non_images(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                validate_generated_path(root / "missing.png")
            text_file = root / "not-image.png"
            text_file.write_text("not an image", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_generated_path(text_file)

    def test_validate_generated_path_returns_dimensions_and_rejects_unsupported_ratio(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "generated.png"
            Image.new("RGB", (1774, 887), "white").save(path)
            self.assertEqual(validate_generated_path(path), (1774, 887))
            wrong = Path(directory) / "wrong.png"
            Image.new("RGB", (100, 100), "white").save(wrong)
            with self.assertRaises(ValueError):
                validate_generated_path(wrong)

    def test_custom_dimensions_require_explicit_tuple_revalidation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            custom = root / "custom.png"
            Image.new("RGB", (1000, 500), "white").save(custom)
            # The local template/renderer API may opt into a custom canvas only
            # when its exact dimensions are supplied for revalidation.
            self.assertEqual(validate_generated_path(custom, expected=(1000, 500)), (1000, 500))
            with self.assertRaises(ValueError):
                validate_generated_path(custom)

    def test_structured_host_request_exposes_authorized_builtin_ip_references(self) -> None:
        brief = self._brief()
        brief = BrandBrief(
            brief.schema_version,
            brief.project,
            brief.copy,
            brief.style,
            brief.fonts,
            {"logo_card_ip": ["author-anime", "tuotuo", "xingbi"]},
            brief.outputs,
        )
        request = prompt_builder.build_host_request(brief, "logo_card")
        self.assertEqual(request["output_type"], "logo_card")
        self.assertEqual(request["dimensions"], [1254, 1254])
        references = request["reference_assets"]
        reference_ids = [entry["asset_id"] for entry in references]
        self.assertEqual(reference_ids[:3], ["author-anime", "tuotuo", "xingbi"])
        self.assertEqual(reference_ids[3:], ["tuotuo-xingbi-front-v1", "tuotuo-geometry-v1", "xingbi-geometry-v1"])
        expected_cues = {
            "author-anime": "black tousled hair",
            "tuotuo": "square black glasses",
            "xingbi": "yellow five-point star",
        }
        for entry in references:
            path = Path(entry["path"])
            self.assertTrue(path.is_absolute())
            self.assertTrue(path.is_file())
            self.assertEqual(entry["category"], "ip-character")
            self.assertEqual(entry["rights_status"], "user_authorized")
            self.assertEqual(entry["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            if entry["asset_id"] in expected_cues:
                self.assertIn(expected_cues[entry["asset_id"]], entry["profile_cues"].lower())
                self.assertIn(expected_cues[entry["asset_id"]], request["prompt"].lower())

    def test_cover_host_request_audits_the_accepted_logo_path_and_hash(self) -> None:
        with TemporaryDirectory() as directory:
            accepted_logo = Path(directory) / "logo-card-v01.png"
            Image.new("RGBA", (1254, 1254), "white").save(accepted_logo)
            request = prompt_builder.build_host_request(
                self._brief(),
                "cover",
                accepted_logo_path=accepted_logo,
            )
            self.assertEqual(request["accepted_logo"]["path"], str(accepted_logo.resolve()))
            self.assertEqual(
                request["accepted_logo"]["sha256"],
                hashlib.sha256(accepted_logo.read_bytes()).hexdigest(),
            )

    def test_stage_style_request_includes_authorized_person_and_both_local_style_references(self) -> None:
        with TemporaryDirectory() as directory:
            workspace = Path(directory)
            reference_root = workspace / ".brandloom" / "style-reference-library"
            reference_root.mkdir(parents=True)
            for name in ("style-02-talk-stage.jpg", "style-03-bold-cover-type.jpg"):
                Image.new("RGB", (12, 8), "navy").save(reference_root / name)
            person = workspace / "presenter.png"
            Image.new("RGB", (12, 16), "white").save(person)
            source = self._brief()
            brief = BrandBrief(
                source.schema_version,
                source.project,
                {"title": "Codex project safety"},
                {
                    "profile": "stage-screen-poster",
                    "title_base_color": "#FFFFFF",
                    "title_emphasis_color": "#FFD72F",
                    "title_emphasis_text": "Codex",
                    "presenter_outfit": "科技休闲：简洁深蓝连帽衫",
                    "person_reference": {
                        "path": str(person),
                        "rights_status": "user_authorized",
                        "save_scope": "this_run",
                        "default_scope": "none",
                    },
                },
                source.fonts,
                {},
                source.outputs,
            )

            request = prompt_builder.build_host_request(brief, "cover", workspace=workspace)
            references = request["reference_assets"]
            by_category = {entry["category"]: entry for entry in references}
            self.assertEqual(by_category["person-reference"]["rights_status"], "user_authorized")
            self.assertEqual(by_category["person-reference"]["scope"], "this_run")
            self.assertEqual(
                {entry["asset_id"] for entry in references if entry["category"] == "style-reference"},
                {"style-02-talk-stage", "style-03-bold-cover-type"},
            )
            self.assertIn("main presenter", request["prompt"])
            self.assertIn("large presentation screen", request["prompt"])
            self.assertIn("#FFFFFF", request["prompt"])
            self.assertIn("#FFD72F", request["prompt"])
            self.assertIn("Confirmed presenter outfit: 科技休闲：简洁深蓝连帽衫", request["prompt"])
            self.assertTrue(_host_request_integrity(
                request,
                base=None,
                expected_output_type="cover",
                expected_dimensions=(1774, 887),
            ))

    def test_stage_style_request_fails_closed_without_authorized_person_reference(self) -> None:
        source = self._brief()
        brief = BrandBrief(
            source.schema_version,
            source.project,
            source.copy,
            {"profile": "stage-screen-poster", "title_emphasis_color": "#FFD72F"},
            source.fonts,
            source.assets,
            source.outputs,
        )
        with self.assertRaisesRegex(ValueError, "authorized person reference"):
            prompt_builder.build_host_request(brief, "cover")

    def test_stage_style_requires_confirmed_presenter_outfit(self) -> None:
        source = self._brief()
        brief = BrandBrief(
            source.schema_version,
            source.project,
            {"title": "Codex project safety"},
            {
                "profile": "stage-screen-poster",
                "title_base_color": "#FFFFFF",
                "title_emphasis_color": "#FFD72F",
                "title_emphasis_text": "Codex",
            },
            source.fonts,
            {},
            source.outputs,
        )

        with self.assertRaisesRegex(ValueError, "confirmed presenter outfit"):
            prompt_builder.build_base_prompt(brief, "cover")

    def test_stage_style_rejects_low_contrast_emphasis_color(self) -> None:
        source = self._brief()
        brief = BrandBrief(
            source.schema_version,
            source.project,
            {"title": "Codex project safety"},
            {
                "profile": "stage-screen-poster",
                "title_base_color": "#FFFFFF",
                "title_emphasis_color": "#102030",
                "title_emphasis_text": "Codex",
                "presenter_outfit": "简洁日常：纯色 T 恤",
            },
            source.fonts,
            {},
            source.outputs,
        )

        with self.assertRaisesRegex(ValueError, "contrast ratio of at least 3:1"):
            prompt_builder.build_base_prompt(brief, "cover")

    def test_style_reference_can_be_supplied_for_one_run_as_analysis_only(self) -> None:
        with TemporaryDirectory() as directory:
            workspace = Path(directory)
            reference = workspace / "uploaded-style.png"
            Image.new("RGB", (12, 8), "white").save(reference)
            source = self._brief()
            brief = BrandBrief(
                source.schema_version,
                source.project,
                source.copy,
                {
                    "profile": "light-saas-product-showcase",
                    "reference_mode": "provided",
                    "reference_paths": [{
                        "path": str(reference),
                        "rights_status": "analysis_only",
                        "save_scope": "this_run",
                        "default_scope": "none",
                    }],
                },
                source.fonts,
                {},
                source.outputs,
            )

            request = prompt_builder.build_host_request(brief, "cover", workspace=workspace)
            style_reference = next(item for item in request["reference_assets"] if item["category"] == "style-reference")
            self.assertEqual(style_reference["rights_status"], "analysis_only")
            self.assertEqual(style_reference["scope"], "this_run")
            self.assertEqual(style_reference["path"], str(reference.resolve()))

    def test_style_references_can_be_explicitly_skipped_using_text_only_mode(self) -> None:
        with TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = self._brief()
            brief = BrandBrief(
                source.schema_version,
                source.project,
                source.copy,
                {"profile": "light-saas-product-showcase", "reference_mode": "text-only"},
                source.fonts,
                {},
                source.outputs,
            )

            request = prompt_builder.build_host_request(brief, "cover", workspace=workspace)
            self.assertFalse(any(item["category"] == "style-reference" for item in request["reference_assets"]))

    def test_missing_style_reference_requires_explicit_fallback(self) -> None:
        with TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = self._brief()
            brief = BrandBrief(
                source.schema_version,
                source.project,
                source.copy,
                {"profile": "light-saas-product-showcase"},
                source.fonts,
                {},
                source.outputs,
            )

            with self.assertRaisesRegex(ValueError, "reference_mode to text-only"):
                prompt_builder.build_host_request(brief, "cover", workspace=workspace)

    def test_existing_project_style_accepts_confirmed_prior_visual_as_reference(self) -> None:
        with TemporaryDirectory() as directory:
            workspace = Path(directory)
            reference = workspace / "approved-cover.png"
            Image.new("RGB", (12, 8), "white").save(reference)
            source = self._brief()
            brief = BrandBrief(
                source.schema_version,
                source.project,
                source.copy,
                {
                    "profile": "project-existing-style",
                    "reference_mode": "provided",
                    "source_confirmed": True,
                    "source_description": "已确认的上一版项目封面视觉方向",
                    "reference_paths": [{
                        "path": str(reference),
                        "rights_status": "analysis_only",
                        "save_scope": "this_run",
                        "default_scope": "none",
                    }],
                },
                source.fonts,
                {},
                source.outputs,
            )

            request = prompt_builder.build_host_request(brief, "cover", workspace=workspace)
            references = [item for item in request["reference_assets"] if item["category"] == "style-reference"]
            self.assertEqual(len(references), 1)
            self.assertEqual(references[0]["path"], str(reference.resolve()))

    def test_existing_project_style_requires_explicit_source_confirmation(self) -> None:
        with TemporaryDirectory() as directory:
            source = self._brief()
            brief = BrandBrief(
                source.schema_version,
                source.project,
                source.copy,
                {"profile": "project-existing-style", "reference_mode": "text-only"},
                source.fonts,
                {},
                source.outputs,
            )

            with self.assertRaisesRegex(ValueError, "confirmed source_description and source_confirmed"):
                prompt_builder.build_host_request(brief, "cover", workspace=Path(directory))


if __name__ == "__main__":
    unittest.main()
