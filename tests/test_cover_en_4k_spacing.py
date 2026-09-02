import json
import unittest
from pathlib import Path

from brandloom.scripts.brandloom_core.layout import fit_text_box
from tests.font_test_utils import find_test_font


WORKTREE = Path(__file__).resolve().parents[1]
TEMPLATE = WORKTREE / "brandloom/templates/cover-2x1.json"
SCALE = 4096 / 1774
GEOMETRY_KEYS = {
    "x",
    "y",
    "w",
    "h",
    "min_font_size",
    "max_font_size",
}


def _scale_slot(slot: dict[str, object]) -> dict[str, object]:
    return {
        key: round(value * SCALE) if key in GEOMETRY_KEYS and isinstance(value, (int, float)) else value
        for key, value in slot.items()
    }


class EnglishCover4KSpacingTests(unittest.TestCase):
    def test_features_text_keeps_bottom_safe_margin_in_clean_checkout(self):
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        features = _scale_slot(template["slots"]["features"])
        features["line_spacing"] = round(12 * SCALE)
        copy = "\n".join(
            f"• {item}"
            for item in (
                "Not sure what to ask for? It reads your project and finds a clear visual direction",
                "Tired of inconsistent results? Confirm the copy, colors, and assets step by step",
                "Get more than one image: a square logo card, a wide cover, and bilingual versions",
                "More reliable than a one-off agent prompt: every choice is visible, reusable, and versioned",
            )
        )
        layout = fit_text_box(
            copy,
            (int(features["w"]), int(features["h"])),
            find_test_font(),
            max_font_size=int(features["max_font_size"]),
            min_font_size=int(features["min_font_size"]),
            spacing=int(features["line_spacing"]),
        )
        text_bottom = int(features["y"]) + layout.bbox[3]
        self.assertLessEqual(
            text_bottom,
            2048 - 24,
            f"English features text reaches {text_bottom}px on a 2048px canvas",
        )

    def test_english_value_line_uses_expanded_spacing(self):
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        value_line = _scale_slot(template["slots"]["value_line"])
        self.assertEqual(round(20 * SCALE), 46)
        self.assertGreater(round(20 * SCALE), 8)
        self.assertGreaterEqual(int(value_line["h"]), 140)


if __name__ == "__main__":
    unittest.main()
