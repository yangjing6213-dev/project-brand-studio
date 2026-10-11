import json
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory

from PIL import Image

from brandloom.scripts.brandloom_core.platform_outputs import resolve_output_target
from brandloom.scripts.brandloom_core.renderer import render_brand_asset
from brandloom.scripts.brandloom_core.platform_templates import write_cover_template


class PlatformCoverTemplateTests(unittest.TestCase):
    def test_every_supported_platform_can_build_a_target_sized_json_template(self):
        for target_id, dimensions in {
            "youtube-long-video": (3840, 2160),
            "youtube-shorts": (2160, 3840),
            "youtube-channel-banner": (2560, 1440),
            "douyin-cover": (1080, 1440),
            "xiaohongshu-cover": (1080, 1440),
            "github-social-preview": (1280, 640),
        }.items():
            with self.subTest(target_id=target_id), TemporaryDirectory() as directory:
                path = write_cover_template(Path(directory), resolve_output_target(target_id), language="en")
                template = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual((template["canvas"]["width"], template["canvas"]["height"]), dimensions)

    def test_wide_and_vertical_targets_get_adapted_workflow_density_and_local_frosted_cards(self):
        steps = [
            {"zh": "看懂项目", "en": "Understand"},
            {"zh": "选好方向", "en": "Choose"},
            {"zh": "生成画面", "en": "Create"},
            {"zh": "拿到结果", "en": "Deliver"},
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            wide_path = write_cover_template(
                root, resolve_output_target("github-social-preview"), language="zh", workflow_steps=steps
            )
            tall_path = write_cover_template(
                root, resolve_output_target("douyin-cover"), language="zh", workflow_steps=steps[:3]
            )
            wide = json.loads(wide_path.read_text(encoding="utf-8"))
            tall = json.loads(tall_path.read_text(encoding="utf-8"))
            self.assertEqual(wide["canvas"], {"width": 1280, "height": 640, "safe_margin": 26})
            self.assertEqual(len(wide["overlays"]["workflow_diagram"]["steps"]), 4)
            self.assertEqual(len(tall["overlays"]["workflow_diagram"]["steps"]), 3)
            workflow = tall["overlays"]["workflow_diagram"]
            self.assertEqual(workflow["card_fill_opacity"], 0.4)
            self.assertEqual(workflow["card_blur_radius_ratio"], 0.008)
            self.assertNotIn("text_backdrop", tall["overlays"])
            self.assertNotIn("outer_frame", workflow)

    def test_channel_banner_copy_and_diagram_stay_inside_conservative_center_safe_area(self):
        with TemporaryDirectory() as directory:
            template_path = write_cover_template(
                Path(directory),
                resolve_output_target("youtube-channel-banner"),
                language="en",
                workflow_steps=[{"en": "Understand"}, {"en": "Choose"}, {"en": "Create"}, {"en": "Deliver"}],
            )
            template = json.loads(template_path.read_text(encoding="utf-8"))
            height, width = template["canvas"]["height"], template["canvas"]["width"]
            safe_left, safe_right = round(width * 0.198), round(width * 0.802)
            safe_top, safe_bottom = round(height * 0.353), round(height * 0.647)
            for name in ("company_logo", "project_mark", "title", "subtitle", "value_line", "features"):
                slot = template["slots"][name]
                self.assertGreaterEqual(slot["x"], safe_left)
                self.assertLessEqual(slot["x"] + slot["w"], safe_right)
                self.assertGreaterEqual(slot["y"], safe_top)
                self.assertLessEqual(slot["y"] + slot["h"], safe_bottom)
            workflow = template["overlays"]["workflow_diagram"]
            self.assertGreaterEqual(workflow["x"], safe_left)
            self.assertLessEqual(workflow["x"] + workflow["w"], safe_right)
            self.assertGreaterEqual(workflow["y"], safe_top)
            self.assertLessEqual(workflow["y"] + workflow["h"], safe_bottom)

    def test_stage_style_places_title_outside_the_right_hand_display_and_copy_on_screen(self):
        steps = [{"en": "Understand"}, {"en": "Create"}, {"en": "Deliver"}]
        for target_id in ("github-social-preview", "douyin-cover"):
            with self.subTest(target_id=target_id), TemporaryDirectory() as directory:
                template_path = write_cover_template(
                    Path(directory),
                    resolve_output_target(target_id),
                    language="en",
                    workflow_steps=steps,
                    style_profile="stage-screen-poster",
                )
                template = json.loads(template_path.read_text(encoding="utf-8"))
                width = template["canvas"]["width"]
                self.assertLess(template["slots"]["title"]["x"] + template["slots"]["title"]["w"], width * 0.5)
                for name in ("subtitle", "value_line", "features"):
                    self.assertGreaterEqual(template["slots"][name]["x"], width * 0.5)
                workflow = template["overlays"]["workflow_diagram"]
                self.assertGreaterEqual(workflow["x"], width * 0.5)
                feature = template["slots"]["features"]
                self.assertLessEqual(feature["y"] + feature["h"], workflow["y"])

    def test_renderer_blurs_only_inside_each_workflow_card_and_uses_exact_canvas(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = resolve_output_target("github-social-preview")
            template_path = write_cover_template(
                root,
                target,
                language="en",
                workflow_steps=[{"en": "Understand"}, {"en": "Deliver"}],
            )
            base_path = root / "base.png"
            Image.new("RGBA", (1280, 640), (35, 70, 110, 255)).save(base_path)
            logo_path = root / "logo.png"
            Image.new("RGBA", (80, 24), (255, 255, 255, 255)).save(logo_path)
            result = render_brand_asset(
                template_path,
                {"project": {}, "copy": {"language": "en", "title": "Example"}, "style": {}, "assets": {}},
                base_image=base_path,
                asset_paths={"company_logo": logo_path},
                font_paths={"heading": "C:/Windows/Fonts/arial.ttf", "body": "C:/Windows/Fonts/arial.ttf"},
                output_dir=root / "out",
            )
            with Image.open(result.output_path) as output:
                self.assertEqual(output.size, (1280, 640))
                self.assertEqual(output.getpixel((10, 10)), (35, 70, 110, 255))
                workflow = json.loads(template_path.read_text(encoding="utf-8"))["overlays"]["workflow_diagram"]
                x, y, width, height = (workflow[key] for key in ("x", "y", "w", "h"))
                self.assertNotEqual(output.getpixel((x + width // 2, y + height // 3)), (35, 70, 110, 255))
                self.assertEqual(result.width, 1280)
                self.assertEqual(result.height, 640)

    def test_renderer_allows_only_proportional_up_or_down_scaling_and_keeps_source_unchanged(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            template = write_cover_template(root, resolve_output_target("github-social-preview"), language="en")
            base_path = root / "base.png"
            Image.new("RGB", (640, 320), (80, 90, 100)).save(base_path)
            original = base_path.read_bytes()
            logo_path = root / "logo.png"
            Image.new("RGBA", (80, 24), (255, 255, 255, 255)).save(logo_path)
            result = render_brand_asset(
                template,
                {"project": {}, "copy": {"language": "en", "title": "Example"}, "style": {}, "assets": {}},
                base_image=base_path,
                asset_paths={"company_logo": logo_path},
                font_paths={"heading": "C:/Windows/Fonts/arial.ttf", "body": "C:/Windows/Fonts/arial.ttf"},
                output_dir=root / "out",
            )
            self.assertEqual(base_path.read_bytes(), original)
            with Image.open(result.output_path) as output:
                self.assertEqual(output.size, (1280, 640))

            mismatched = root / "mismatched.png"
            Image.new("RGB", (640, 360), (80, 90, 100)).save(mismatched)
            with self.assertRaisesRegex(ValueError, "aspect ratio"):
                render_brand_asset(
                    template,
                    {"project": {}, "copy": {}, "style": {}, "assets": {}},
                    base_image=mismatched,
                    asset_paths={"company_logo": logo_path},
                    font_paths={},
                    output_dir=root / "out-2",
                )


if __name__ == "__main__":
    unittest.main()
