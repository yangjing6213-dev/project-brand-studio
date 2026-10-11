import json
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops

from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.renderer import render_brand_asset


class CoverLayoutTests(unittest.TestCase):
    def test_cover_feature_slot_supports_detailed_key_points(self) -> None:
        template = json.loads(Path("brandloom/templates/cover-2x1.json").read_text(encoding="utf-8"))
        slots = template["slots"]
        self.assertEqual(slots["features"]["x"], slots["title"]["x"])
        self.assertGreaterEqual(slots["features"]["w"], 760)
        self.assertGreaterEqual(slots["features"]["h"], 240)

    def test_cover_declares_full_right_workflow_without_backdrop_or_outer_frame(self) -> None:
        template = json.loads(Path("brandloom/templates/cover-2x1.json").read_text(encoding="utf-8"))
        overlays = template["overlays"]
        self.assertNotIn("text_backdrop", overlays)
        self.assertIn("workflow_diagram", overlays)
        workflow = overlays["workflow_diagram"]
        self.assertLessEqual(workflow["x"], 960)
        self.assertGreaterEqual(workflow["w"], 760)
        self.assertGreaterEqual(workflow["h"], 700)
        self.assertNotIn("fill", workflow)
        self.assertNotIn("border", workflow)
        self.assertEqual(overlays["workflow_diagram"]["blur_radius"], 0)
        self.assertGreaterEqual(len(overlays["workflow_diagram"]["steps"]), 4)

    def test_cover_overlays_are_rendered_on_cover_only(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "base.png"
            logo = root / "logo.png"
            Image.new("RGBA", (1774, 887), (255, 255, 255, 255)).save(base)
            Image.new("RGBA", (80, 24), (255, 255, 255, 255)).save(logo)
            brief = BrandBrief(
                "1.0",
                {"name": "demo", "slug": "demo"},
                {"language": "en", "title": "BrandLoom", "subtitle": "Subtitle", "value_line": "Value", "features": ["One"]},
                {"foreground": "#111111"},
                {},
                {"project_mark": None},
                {},
            )
            result = render_brand_asset(
                Path("brandloom/templates/cover-2x1.json"),
                brief,
                base_image=base,
                asset_paths={"company_logo": logo},
                font_paths={"heading": "C:/Windows/Fonts/msyh.ttc", "body": "C:/Windows/Fonts/msyh.ttc"},
                output_dir=root / "out",
            )
            with Image.open(result.output_path) as rendered:
                self.assertEqual(rendered.getpixel((10, 10))[:3], (255, 255, 255))
                self.assertEqual(rendered.getpixel((900, 40))[:3], (255, 255, 255))
                workflow_crop = rendered.crop((942, 142, 1728, 284))
                white = Image.new("RGB", workflow_crop.size, (255, 255, 255))
                self.assertIsNotNone(ImageChops.difference(workflow_crop.convert("RGB"), white).getbbox())


if __name__ == "__main__":
    unittest.main()
