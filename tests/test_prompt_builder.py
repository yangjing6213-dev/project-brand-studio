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

    def test_cover_prompt_requests_reused_visual_dna_and_expected_ratio(self) -> None:
        prompt = build_base_prompt(self._brief(), "cover")
        self.assertIn("2:1", prompt)
        self.assertIn("reuse the accepted LOGO visual DNA", prompt)

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


if __name__ == "__main__":
    unittest.main()
