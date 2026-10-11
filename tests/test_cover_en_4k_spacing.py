import unittest

from brandloom.scripts.brandloom_core.layout import fit_text_box
from brandloom.scripts.brandloom_core.platform_templates import build_cover_template
from tests.font_test_utils import find_test_font


class EnglishCover4KSpacingTests(unittest.TestCase):
    def _template(self):
        return build_cover_template(
            {"id": "youtube-thumbnail", "dimensions": (4096, 2048)},
            language="en",
            workflow_steps=[
                {"en": "Understand", "detail_en": "Project · chat · files"},
                {"en": "Choose", "detail_en": "Copy · look · assets"},
                {"en": "Create", "detail_en": "Base image + brand layout"},
                {"en": "Get results", "detail_en": "Platform covers · localized"},
            ],
        )

    def test_4k_feature_spacing_comes_from_the_production_template(self):
        template = self._template()
        features = template["slots"]["features"]
        spacing = int(features["line_spacing"])
        self.assertGreaterEqual(spacing, 24)

        copy = "\n".join(
            f"• {item}"
            for item in (
                "Not sure what to ask for? It reads your project and finds a clear visual direction",
                "Tired of inconsistent results? Confirm the copy, colors, and assets step by step",
                "Get more than one image: platform-specific covers and bilingual versions",
                "More reliable than a one-off agent prompt: every choice is visible, reusable, and versioned",
            )
        )
        layout = fit_text_box(
            copy,
            (int(features["w"]), int(features["h"])),
            find_test_font(),
            max_font_size=int(features["max_font_size"]),
            min_font_size=int(features["min_font_size"]),
            spacing=spacing,
        )
        text_bottom = int(features["y"]) + layout.bbox[3]
        canvas = template["canvas"]
        self.assertLessEqual(text_bottom, int(canvas["height"]) - int(canvas["safe_margin"]))

    def test_4k_workflow_heading_and_subtitle_gap_comes_from_template(self):
        template = self._template()
        workflow = template["overlays"]["workflow_diagram"]
        self.assertGreaterEqual(int(workflow["heading_subtitle_gap"]), 40)


if __name__ == "__main__":
    unittest.main()
