import json
from pathlib import Path
import unittest


class LogoCardLayoutTests(unittest.TestCase):
    def test_features_align_with_primary_copy_left_edge(self) -> None:
        template = json.loads(Path("brandloom/templates/logo-card-1x1.json").read_text(encoding="utf-8"))
        slots = template["slots"]
        self.assertEqual(slots["features"]["x"], slots["title"]["x"])
        self.assertEqual(slots["features"]["x"], slots["subtitle"]["x"])

    def test_copy_slots_use_large_display_scale(self) -> None:
        template = json.loads(Path("brandloom/templates/logo-card-1x1.json").read_text(encoding="utf-8"))
        slots = template["slots"]
        self.assertGreaterEqual(slots["title"]["max_font_size"], 150)
        self.assertGreaterEqual(slots["subtitle"]["max_font_size"], 52)
        self.assertGreaterEqual(slots["value_line"]["max_font_size"], 42)
        self.assertGreaterEqual(slots["features"]["max_font_size"], 34)
        self.assertGreaterEqual(slots["title"]["w"], 760)
        self.assertGreaterEqual(slots["features"]["w"], 760)


if __name__ == "__main__":
    unittest.main()
