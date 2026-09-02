import json
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.renderer import _draw_workflow_diagram, render_brand_asset, _text_spacing
from tests.font_test_utils import find_test_font


class CoverLayoutTests(unittest.TestCase):
    def test_text_slot_can_declare_custom_multiline_spacing(self) -> None:
        self.assertEqual(_text_spacing({"line_spacing": 24}), 24)
        self.assertEqual(_text_spacing({}), 8)

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
        self.assertEqual(overlays["workflow_diagram"]["node_blur_radius"], 12)
        self.assertEqual(overlays["workflow_diagram"]["node_blur_transparency"], 0.6)
        self.assertEqual(overlays["workflow_diagram"]["node_border_width"], 2)
        self.assertEqual(overlays["workflow_diagram"]["node_corner_radius"], 16)
        self.assertGreaterEqual(len(overlays["workflow_diagram"]["steps"]), 4)

    def _workflow_config(self, **overrides: object) -> dict[str, object]:
        config: dict[str, object] = {
            "x": 40,
            "y": 20,
            "w": 360,
            "h": 580,
            "blur_radius": 0,
            "node_gap": 20,
            "node_height": 100,
            "inner_padding": 24,
            "steps": [
                {"en": "A", "detail_en": "one"},
                {"en": "B", "detail_en": "two"},
                {"en": "C", "detail_en": "three"},
                {"en": "D", "detail_en": "four"},
            ],
        }
        config.update(overrides)
        return config

    def _textured_base(self) -> Image.Image:
        image = Image.new("RGBA", (500, 620))
        pixels = image.load()
        for y in range(image.height):
            for x in range(image.width):
                pixels[x, y] = ((x * 37 + y * 11) % 256, (x * 7 + y * 53) % 256, (x * 19 + y * 29) % 256, 255)
        return image

    def test_workflow_blur_changes_each_card_interior_and_matches_gaussian_reference(self) -> None:
        base = self._textured_base()
        config = self._workflow_config(node_blur_radius=12, node_blur_transparency=0.9)
        rendered = base.copy()
        _draw_workflow_diagram(rendered, config, font_paths={"heading": find_test_font(), "body": find_test_font()}, language="en")

        node_x, node_w, node_height, node_gap = 64, 312, 100, 20
        node_tops = [118 + index * (node_height + node_gap) for index in range(4)]
        for top in node_tops:
            sample = (node_x + node_w - 22, top + 80)
            self.assertNotEqual(rendered.getpixel(sample), base.getpixel(sample))

        top = node_tops[0]
        inner_x, inner_y = node_x + 2, top + 2
        inner_right, inner_bottom = node_x + node_w - 3, top + node_height - 3
        reference = base.crop((inner_x, inner_y, inner_right + 1, inner_bottom + 1)).filter(ImageFilter.GaussianBlur(12))
        expected = base.copy()
        mask = Image.new("L", reference.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, reference.width - 1, reference.height - 1), radius=14, fill=26)
        expected.paste(reference, (inner_x, inner_y), mask)
        sample = (node_x + node_w - 22, top + 80)
        self.assertEqual(rendered.getpixel(sample), expected.getpixel(sample))

    def test_workflow_blur_is_clipped_and_does_not_filter_crisp_diagram(self) -> None:
        base = self._textured_base()
        config = self._workflow_config(node_blur_radius=12, node_blur_transparency=0.9)
        plain = base.copy()
        rendered = base.copy()
        fonts = {"heading": find_test_font(), "body": find_test_font()}
        _draw_workflow_diagram(plain, self._workflow_config(), font_paths=fonts, language="en")
        _draw_workflow_diagram(rendered, config, font_paths=fonts, language="en")

        # Every pixel outside the inset rounded interiors retains the clear render.
        interior_mask = Image.new("L", base.size, 0)
        mask_draw = ImageDraw.Draw(interior_mask)
        for top in (118, 238, 358, 478):
            mask_draw.rounded_rectangle((66, top + 2, 373, top + 97), radius=14, fill=255)
        changed = ImageChops.difference(rendered.convert("RGB"), plain.convert("RGB"))
        self.assertIsNone(ImageChops.multiply(changed, ImageChops.invert(interior_mask).convert("RGB")).getbbox())
        # All opaque stroke, icon and glyph pixels remain exactly sharp.
        foreground = Image.new("RGBA", base.size, (0, 0, 0, 0))
        _draw_workflow_diagram(foreground, self._workflow_config(), font_paths=fonts, language="en")
        opaque = foreground.getchannel("A").point(lambda value: 255 if value == 255 else 0)
        self.assertIsNotNone(opaque.getbbox())
        self.assertIsNone(ImageChops.multiply(changed, opaque.convert("RGB")).getbbox())

    def test_workflow_blur_defaults_are_disabled_without_node_options(self) -> None:
        base = self._textured_base()
        fonts = {"heading": find_test_font(), "body": find_test_font()}
        without_options = base.copy()
        explicit_disabled = base.copy()
        _draw_workflow_diagram(without_options, self._workflow_config(), font_paths=fonts, language="en")
        _draw_workflow_diagram(explicit_disabled, self._workflow_config(node_blur_radius=0, node_blur_transparency=0.9), font_paths=fonts, language="en")
        self.assertEqual(without_options.tobytes(), explicit_disabled.tobytes())

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
                font_paths={"heading": find_test_font(), "body": find_test_font()},
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
