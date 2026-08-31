from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from brandloom.scripts.brandloom_core.fonts import (
    FontNotFoundError,
    FontProfile,
    discover_font_files,
    load_font_profiles,
    resolve_font,
)


class FontResolutionTests(unittest.TestCase):
    def test_preset_profiles_have_ordered_role_aliases_and_fallbacks(self) -> None:
        profiles = load_font_profiles()
        self.assertGreaterEqual(len(profiles), 5)
        for profile in profiles.values():
            self.assertIsInstance(profile, FontProfile)
            self.assertTrue(profile.fallback_profile_id)
            for role in ("heading", "body", "latin"):
                self.assertIsInstance(profile.aliases[role], tuple)
                self.assertTrue(profile.aliases[role])

        preset_path = Path("brandloom/references/font-presets.json")
        payload = json.loads(preset_path.read_text(encoding="utf-8"))
        self.assertEqual(set(payload), set(profiles))

    def test_discovery_uses_explicit_project_roots_and_matches_alias(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Microsoft YaHei.ttf").write_bytes(b"fake-font")
            discovered = discover_font_files((root,))
            self.assertIn("microsoft yahei", discovered)

            profile = FontProfile(
                profile_id="test",
                aliases={"heading": ("Microsoft YaHei",), "body": ("Microsoft YaHei",), "latin": ("Microsoft YaHei",)},
                fallback_profile_id="fallback",
            )
            self.assertEqual(resolve_font(profile, "heading", (root,)), root / "Microsoft YaHei.ttf")

    def test_missing_confirmed_font_raises_instead_of_silent_substitution(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Another Font.ttf").write_bytes(b"fake-font")
            profile = FontProfile(
                profile_id="confirmed",
                aliases={
                    "heading": ("Confirmed Missing Font",),
                    "body": ("Confirmed Missing Font",),
                    "latin": ("Confirmed Missing Font",),
                },
                fallback_profile_id="fallback",
            )
            with self.assertRaises(FontNotFoundError):
                resolve_font(profile, "heading", (root,))

    def test_discovery_does_not_scan_unlisted_sibling_roots(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            listed = root / "listed"
            unlisted = root / "unlisted"
            listed.mkdir()
            unlisted.mkdir()
            (unlisted / "Hidden Font.ttf").write_bytes(b"fake-font")
            discovered = discover_font_files((listed,))
            self.assertNotIn("hidden font", discovered)

    def test_discovery_matches_embedded_family_name_when_filename_is_obscure(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            font_file = root / "msyh.ttc"
            font_file.write_bytes(b"fake-font")
            fake_font = Mock()
            fake_font.getname.return_value = ("Microsoft YaHei", "Regular")
            with patch("brandloom.scripts.brandloom_core.fonts._font_roots", return_value=(root,)), patch(
                "PIL.ImageFont.truetype", return_value=fake_font
            ):
                discovered = discover_font_files((root,))
            self.assertEqual(discovered["microsoft yahei"], (font_file,))


if __name__ == "__main__":
    unittest.main()
