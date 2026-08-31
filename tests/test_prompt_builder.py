from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.prompt_builder import (
    build_base_prompt,
    validate_generated_path,
)


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
            outputs={"logo_card": {"width": 2048, "height": 2048}},
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
            Image.new("RGB", (2048, 1024), "white").save(path)
            self.assertEqual(validate_generated_path(path), (2048, 1024))
            wrong = Path(directory) / "wrong.png"
            Image.new("RGB", (100, 100), "white").save(wrong)
            with self.assertRaises(ValueError):
                validate_generated_path(wrong)


if __name__ == "__main__":
    unittest.main()
