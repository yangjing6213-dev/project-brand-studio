from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from urllib.request import Request
from unittest.mock import Mock, patch

from brandloom.scripts.brandloom_core.fonts import (
    _ApprovedFontRedirectHandler,
    FontNotFoundError,
    FontProfile,
    discover_font_files,
    install_fallback_font,
    load_font_profiles,
    missing_glyphs,
    resolve_font_for_text,
    resolve_font,
)
from brandloom.scripts.brandloom_core.renderer import required_font_texts


def _format12_font(codepoints: tuple[int, ...]) -> bytes:
    groups = b"".join(struct.pack(">III", value, value, index + 1) for index, value in enumerate(sorted(codepoints)))
    cmap_subtable = struct.pack(">HHIII", 12, 0, 16 + len(groups), 0, len(codepoints)) + groups
    cmap = struct.pack(">HHHHI", 0, 1, 3, 10, 12) + cmap_subtable
    table_offset = 28
    header = struct.pack(">IHHHH", 0x00010000, 1, 0, 0, 0)
    table_record = b"cmap" + struct.pack(">III", 0, table_offset, len(cmap))
    return header + table_record + cmap


def _format4_font(codepoints: tuple[int, ...]) -> bytes:
    values = sorted(set(codepoints))
    ends = values + [0xFFFF]
    starts = values + [0xFFFF]
    deltas = [((index + 1) - value) & 0xFFFF for index, value in enumerate(values)] + [1]
    offsets = [0] * len(ends)
    seg_count = len(ends)
    arrays = (
        struct.pack(f">{seg_count}H", *ends)
        + b"\0\0"
        + struct.pack(f">{seg_count}H", *starts)
        + struct.pack(f">{seg_count}H", *deltas)
        + struct.pack(f">{seg_count}H", *offsets)
    )
    search_range = 2 * (2 ** (seg_count.bit_length() - 1))
    entry_selector = (seg_count.bit_length() - 1)
    range_shift = 2 * seg_count - search_range
    subtable_length = 14 + len(arrays)
    subtable = struct.pack(">HHHHHHH", 4, subtable_length, 0, 2 * seg_count, search_range, entry_selector, range_shift) + arrays
    cmap = struct.pack(">HHHHI", 0, 1, 3, 1, 12) + subtable
    table_offset = 28
    return (
        struct.pack(">IHHHH", 0x00010000, 1, 0, 0, 0)
        + b"cmap" + struct.pack(">III", 0, table_offset, len(cmap))
        + cmap
    )


def _format6_font(codepoints: tuple[int, ...]) -> bytes:
    values = sorted(set(codepoints))
    first = values[0]
    glyphs = [int(codepoint in values) for codepoint in range(first, values[-1] + 1)]
    subtable = struct.pack(">HHHHH", 6, 10 + 2 * len(glyphs), 0, first, len(glyphs))
    subtable += struct.pack(f">{len(glyphs)}H", *glyphs)
    cmap = struct.pack(">HHHHI", 0, 1, 0, 3, 12) + subtable
    table_offset = 28
    return (
        struct.pack(">IHHHH", 0x00010000, 1, 0, 0, 0)
        + b"cmap" + struct.pack(">III", 0, table_offset, len(cmap))
        + cmap
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

    def test_exact_cmap_check_detects_missing_ascii_punctuation(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "partial.ttf"
            path.write_bytes(_format12_font((ord("A"), ord("!"))))
            self.assertEqual(missing_glyphs(path, "A!"), ())
            self.assertEqual(missing_glyphs(path, "A?"), ("?",))

    def test_format4_cmap_check_detects_missing_ascii_letters_and_punctuation(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "partial.ttf"
            path.write_bytes(_format4_font((ord("A"), ord("!"))))
            self.assertEqual(missing_glyphs(path, "A!"), ())
            self.assertEqual(missing_glyphs(path, "A?"), ("?",))

    def test_format6_cmap_check_detects_missing_ascii_letters_and_punctuation(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "partial.ttf"
            path.write_bytes(_format6_font((ord("A"), ord("!"))))
            self.assertEqual(missing_glyphs(path, "A!"), ())
            self.assertEqual(missing_glyphs(path, "A?"), ("?",))

    def test_unapproved_font_redirect_is_rejected_before_following(self) -> None:
        handler = _ApprovedFontRedirectHandler()
        request = Request("https://raw.githubusercontent.com/notofonts/example/font.otf")
        with self.assertRaisesRegex(FontNotFoundError, "redirected outside the approved source"):
            handler.redirect_request(request, None, 302, "Found", {}, "https://example.com/font.otf")

    def test_text_resolution_uses_local_compatible_fallback_before_download(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            selected = root / "selected.ttf"
            fallback = root / "fallback.ttf"
            selected.touch()
            fallback.touch()
            profile = FontProfile(
                profile_id="selected",
                aliases={"heading": ("Selected",), "body": ("Selected",), "latin": ("Selected",)},
                fallback_profile_id="fallback",
            )
            fallback_profile = FontProfile(
                profile_id="fallback",
                aliases={"heading": ("Fallback",), "body": ("Fallback",), "latin": ("Fallback",)},
                fallback_profile_id="fallback",
            )
            discovered = {"selected": (selected,), "fallback": (fallback,)}
            def missing(path, text):
                return ("?",) if Path(path) == selected else ()
            with patch("brandloom.scripts.brandloom_core.fonts.discover_font_files", return_value=discovered), patch(
                "brandloom.scripts.brandloom_core.fonts.load_font_profiles",
                return_value={"selected": profile, "fallback": fallback_profile},
            ), patch("brandloom.scripts.brandloom_core.fonts.missing_glyphs", side_effect=missing), patch(
                "brandloom.scripts.brandloom_core.fonts.ImageFont.truetype", return_value=Mock()
            ), patch(
                "brandloom.scripts.brandloom_core.fonts.install_fallback_font",
                side_effect=AssertionError("download must not run when a local font is compatible"),
            ):
                resolved = resolve_font_for_text("selected", "heading", "Brand?", (root,), root / "cache")
            self.assertEqual(resolved, fallback)

    def test_text_resolution_downloads_fallback_when_local_fonts_miss_glyphs(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / "local.ttf"
            downloaded = root / "cache" / "noto.ttf"
            local.touch()
            def missing(path, text):
                return () if Path(path) == downloaded else ("?",)
            with patch("brandloom.scripts.brandloom_core.fonts.discover_font_files", return_value={"local": (local,)}), patch(
                "brandloom.scripts.brandloom_core.fonts.missing_glyphs", side_effect=missing,
            ), patch("brandloom.scripts.brandloom_core.fonts.ImageFont.truetype", return_value=Mock()):
                with patch("brandloom.scripts.brandloom_core.fonts.install_fallback_font", return_value=downloaded) as install:
                    resolved = resolve_font_for_text(None, "heading", "Brand?", (root,), root / "cache")
            self.assertEqual(resolved, downloaded)
            install.assert_called_once_with(root / "cache")

    def test_download_installer_verifies_hash_and_writes_license_provenance(self) -> None:
        with TemporaryDirectory() as directory:
            cache = Path(directory)
            font_bytes = _format12_font((ord("A"), ord("!"), ord("?")))
            license_bytes = b"test license"
            font_sha = hashlib.sha256(font_bytes).hexdigest()
            license_sha = hashlib.sha256(license_bytes).hexdigest()
            with patch.multiple(
                "brandloom.scripts.brandloom_core.fonts",
                _FALLBACK_FONT_SHA256=font_sha,
                _FALLBACK_LICENSE_SHA256=license_sha,
                _FALLBACK_FONT_SIZE=len(font_bytes),
            ), patch("brandloom.scripts.brandloom_core.fonts._fetch_bytes", side_effect=(font_bytes, license_bytes)) as fetch, patch(
                "brandloom.scripts.brandloom_core.fonts.ImageFont.truetype", return_value=Mock()
            ):
                result = install_fallback_font(cache)
                reused = install_fallback_font(cache)
            self.assertEqual(hashlib.sha256(result.read_bytes()).hexdigest(), font_sha)
            self.assertEqual(reused, result)
            self.assertEqual(fetch.call_count, 2)
            self.assertTrue((result.parent / "OFL-1.1.txt").is_file())
            provenance = json.loads((result.parent / "font-provenance.json").read_text(encoding="utf-8"))
            self.assertEqual(provenance["font_sha256"], font_sha)
            self.assertEqual(provenance["license_sha256"], license_sha)

    def test_download_installer_rejects_bad_hash_without_leaving_partial_files(self) -> None:
        with TemporaryDirectory() as directory:
            cache = Path(directory)
            with patch("brandloom.scripts.brandloom_core.fonts._fetch_bytes", return_value=b"tampered"), self.assertRaises(
                FontNotFoundError
            ):
                install_fallback_font(cache)
            self.assertEqual(tuple(cache.iterdir()), ())

    def test_download_installer_preserves_invalid_existing_cache_entry(self) -> None:
        with TemporaryDirectory() as directory:
            cache = Path(directory)
            font_bytes = _format12_font((ord("A"),))
            license_bytes = b"test license"
            font_sha = hashlib.sha256(font_bytes).hexdigest()
            base = cache / f"noto-sans-cjk-sc-2.004-{font_sha[:12]}"
            base.mkdir()
            original = base / "NotoSansCJKsc-Regular.otf"
            original.write_bytes(b"preserve this file")
            with patch.multiple(
                "brandloom.scripts.brandloom_core.fonts",
                _FALLBACK_FONT_SHA256=hashlib.sha256(font_bytes).hexdigest(),
                _FALLBACK_LICENSE_SHA256=hashlib.sha256(license_bytes).hexdigest(),
                _FALLBACK_FONT_SIZE=len(font_bytes),
            ), patch("brandloom.scripts.brandloom_core.fonts._fetch_bytes", side_effect=(font_bytes, license_bytes)), patch(
                "brandloom.scripts.brandloom_core.fonts.ImageFont.truetype", return_value=Mock()
            ):
                installed = install_fallback_font(cache)
            self.assertEqual(original.read_bytes(), b"preserve this file")
            self.assertNotEqual(installed.parent, base)
            self.assertEqual(installed.read_bytes(), font_bytes)

    def test_required_font_texts_include_ascii_punctuation_and_workflow_copy(self) -> None:
        brief = {
            "copy": {
                "language": "en",
                "title": "BrandLoom: Build!",
                "subtitle": "Create polished visuals.",
                "features": ["Step 1: review & create."],
            },
        }
        template = {
            "overlays": {
                "workflow_diagram": {
                    "heading_en": "HOW IT WORKS!",
                    "subtitle_en": "Idea -> visual",
                    "steps": [
                        {"en": "Understand?", "detail_en": "Read the project."},
                        {"en": "Deliver!", "detail_en": "Export files."},
                    ],
                },
            },
        }
        required = required_font_texts(brief, template)
        self.assertIn("BrandLoom: Build!", required["heading"])
        self.assertIn("Understand?", required["heading"])
        self.assertIn("1", required["heading"].splitlines())
        self.assertIn("2", required["heading"].splitlines())
        self.assertIn("Step 1: review & create.", required["body"])
        self.assertIn("Read the project.", required["body"])

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
