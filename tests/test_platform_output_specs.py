import unittest

from brandloom.scripts.brandloom_core.platform_outputs import (
    OUTPUT_TARGETS,
    resolve_output_target,
    same_aspect_ratio,
)
from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.prompt_builder import build_host_request, validate_generated_path
from brandloom.scripts.brandloom_core.validation import _within_target_file_size_limit
from PIL import Image
from pathlib import Path
from tempfile import TemporaryDirectory


class PlatformOutputSpecTests(unittest.TestCase):
    def test_all_confirmed_platform_targets_have_exact_dimensions(self):
        expected = {
            "youtube-long-video": (3840, 2160),
            "youtube-shorts": (2160, 3840),
            "youtube-channel-banner": (2560, 1440),
            "douyin-cover": (1080, 1440),
            "xiaohongshu-cover": (1080, 1440),
            "github-social-preview": (1280, 640),
        }
        self.assertEqual(set(expected), set(OUTPUT_TARGETS))
        for target_id, dimensions in expected.items():
            with self.subTest(target_id=target_id):
                self.assertEqual(resolve_output_target(target_id)["dimensions"], list(dimensions))

    def test_custom_target_requires_bounded_positive_integer_dimensions(self):
        self.assertEqual(resolve_output_target("custom", (1600, 900))["dimensions"], [1600, 900])
        for dimensions in ((0, 900), (1, 1), (900, 900.0), (8193, 900), (8192, 8192)):
            with self.subTest(dimensions=dimensions), self.assertRaises(ValueError):
                resolve_output_target("custom", dimensions)

    def test_aspect_ratio_comparison_avoids_float_rounding(self):
        self.assertTrue(same_aspect_ratio((16, 9), (3840, 2160)))
        self.assertFalse(same_aspect_ratio((16, 9), (1774, 887)))

    def test_target_spec_distinguishes_official_requirement_from_recommendation(self):
        youtube = resolve_output_target("youtube-long-video")
        douyin = resolve_output_target("douyin-cover")
        self.assertEqual(youtube["spec_status"], "official_recommendation")
        self.assertEqual(douyin["spec_status"], "practical_recommendation")

    def test_target_file_size_limits_follow_platform_inclusive_or_exclusive_boundary(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "output.bin"
            path.write_bytes(b"x" * (1_048_576 - 1))
            self.assertTrue(_within_target_file_size_limit(path, "github-social-preview"))
            path.write_bytes(b"x" * 1_048_576)
            self.assertFalse(_within_target_file_size_limit(path, "github-social-preview"))
            path.write_bytes(b"x" * 6_291_456)
            self.assertTrue(_within_target_file_size_limit(path, "youtube-channel-banner"))
            path.write_bytes(b"x" * (6_291_456 + 1))
            self.assertFalse(_within_target_file_size_limit(path, "youtube-channel-banner"))

    def test_host_request_uses_confirmed_platform_dimensions_and_full_bleed_scene(self):
        brief = BrandBrief("1.0", {"name": "Demo"}, {"title": "Demo"}, {}, {}, {}, {})
        request = build_host_request(
            brief,
            "cover",
            target_id="youtube-shorts",
            expected=(2160, 3840),
        )
        self.assertEqual(request["target_id"], "youtube-shorts")
        self.assertEqual(request["dimensions"], [2160, 3840])
        self.assertIn("9:16", request["prompt"])
        self.assertIn("full-bleed", request["prompt"])

    def test_generated_path_accepts_only_the_exact_confirmed_custom_canvas(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "custom.png"
            Image.new("RGB", (1600, 900), "white").save(path)
            self.assertEqual(validate_generated_path(path, expected=(1600, 900)), (1600, 900))
            smaller = Path(directory) / "same-ratio.png"
            Image.new("RGB", (800, 450), "white").save(smaller)
            self.assertEqual(
                validate_generated_path(smaller, expected=(1600, 900), allow_same_aspect_resize=True),
                (800, 450),
            )
            with self.assertRaisesRegex(ValueError, "aspect ratio"):
                validate_generated_path(smaller, expected=(1600, 1000), allow_same_aspect_resize=True)
            with self.assertRaises(ValueError):
                validate_generated_path(path, expected=(1920, 1080))


if __name__ == "__main__":
    unittest.main()
