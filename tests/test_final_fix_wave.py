from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from brandloom.scripts.brandloom_core.fonts import missing_glyphs
from brandloom.scripts.brandloom_core.models import QAState, QASession, TaskMode
from brandloom.scripts.brandloom_core.renderer import BrandIntegrityError, canonicalize_logo_treatment, render_brand_asset
from brandloom.scripts.brandloom_core.state_machine import assert_generation_ready, confirm, invalidate_from
from brandloom.scripts.brandloom_core.validation import validate_output
from brandloom.scripts.brandloom_core.manifests import build_generation_manifest
from brandloom.scripts import brandloom_cli
from tests.font_test_utils import find_test_font


class FinalFixWaveTests(unittest.TestCase):
    def _session(self, *, treatment: str | None = None) -> QASession:
        confirmed = {key: True for key in ("context", "copy", "style", "font", "company_logo", "project_mark", "ip_combination", "ip_usage", "shot_list", "output_spec", "coherence", "generation_confirmation")}
        confirmed["ip_cast"] = "tuotuo"
        if treatment is not None:
            confirmed["company_logo_treatment"] = treatment
        return QASession("1.0", "s", TaskMode.NEW, QAState.GENERATION_READY, "demo", confirmed=confirmed)

    def test_emoji_capable_font_is_not_rejected_by_missing_sentinel(self):
        font = Path(r"C:\Windows\Fonts\seguiemj.ttf")
        if not font.is_file():
            self.skipTest("emoji font unavailable")
        self.assertEqual(missing_glyphs(font, "Hello 😀"), ())

    def test_operation_mapping_is_canonical_and_auditable(self):
        self.assertEqual(canonicalize_logo_treatment("recolor_monochrome"), "monochrome-black")
        self.assertEqual(canonicalize_logo_treatment("monochrome-black"), "monochrome-black")

    def test_state_bound_treatment_confirmation_and_invalidation(self):
        pending = QASession("1.0", "s", TaskMode.NEW, QAState.COMPANY_LOGO_PENDING, "demo")
        confirmed = confirm(pending, "company_logo_treatment", "recolor_monochrome")
        self.assertEqual(confirmed.confirmed["company_logo_treatment"], "monochrome-black")
        with self.assertRaises(ValueError):
            confirm(QASession("1.0", "s", TaskMode.NEW, QAState.STYLE_PENDING, "demo"), "company_logo_treatment", "monochrome-black")
        invalidated = invalidate_from(self._session(treatment="monochrome-black"), "company_logo")
        self.assertNotIn("company_logo_treatment", invalidated.confirmed)

    def test_cli_session_loader_rejects_non_builtin_generation_backend(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / ".brandloom"
            runtime.mkdir()
            payload = {
                "schema_version": "1.0", "session_id": "s", "mode": "new",
                "state": "GENERATION_READY", "project_slug": "demo",
                "confirmed": {}, "invalidated": [], "generation_backend": "external_api",
            }
            (runtime / "qa-state.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                brandloom_cli._load_session(root)

    def test_white_variant_forbids_recolor_in_direct_renderer(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "base.png"; Image.new("RGBA", (1254, 1254), "white").save(base)
            logo = Path("brandloom/assets/defaults/company-logo/enhe-white-v2/reference.png")
            brief = {"copy": {"title": "Hello"}, "style": {}, "assets": {"company_logo": "enhe-white-v2", "company_logo_treatment": "monochrome-black"}}
            with self.assertRaises(BrandIntegrityError):
                render_brand_asset(Path("brandloom/templates/logo-card-1x1.json"), brief, base_image=base,
                                   asset_paths={"company_logo": logo}, font_paths={"heading": find_test_font()}, output_dir=root / "out",
                                   confirmed_treatment="monochrome-black")

    def test_non_default_manifest_fields_are_required_and_tamper_checked(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); output = root / "logo-card-1x1-v01.png"; Image.new("RGBA", (1254, 1254), "white").save(output)
            logo = root / "logo.png"; Image.new("RGBA", (20, 20), "black").save(logo)
            brief = root / "brief.json"; brief.write_text(json.dumps({"copy": {"title": "Hello"}}), encoding="utf-8")
            template = Path("brandloom/templates/logo-card-1x1.json"); base = root / "base.png"; Image.new("RGBA", (1254, 1254), "white").save(base)
            digest = hashlib.sha256(logo.read_bytes()).hexdigest()
            manifest = build_generation_manifest(brief_path=brief, assets=[{"asset_id": "logo", "category": "company-logo", "scope": "project", "rights_status": "user_authorized", "path": str(logo), "sha256": digest}], template_path=template, font_paths={"heading": find_test_font()}, base_image_path=base, output_path=output, qa_state="INTERNAL_LOGO_QA", rendered_copy={"title": "Hello"}, output_type="logo-card", logo_treatment="monochrome-black", logo_source_hash=digest)
            report = validate_output(output, manifest=manifest, output_type="logo_card", manifest_path=root / "generation-manifest-v01.json")
            self.assertTrue(report.checks.get("manifest_logo_treatment"))
            missing_treatment = dict(manifest)
            missing_treatment.pop("logo_treatment")
            non_default_brief = {
                "project": {}, "copy": {}, "style": {}, "fonts": {},
                "assets": {"company_logo_treatment": "monochrome-black"}, "outputs": {},
            }
            self.assertFalse(
                validate_output(
                    output,
                    manifest=missing_treatment,
                    brief=non_default_brief,
                    output_type="logo_card",
                    manifest_path=root / "generation-manifest-v01.json",
                ).checks["manifest_logo_treatment"]
            )
            alias_treatment = dict(manifest)
            alias_treatment["logo_treatment"] = "recolor_monochrome"
            self.assertFalse(
                validate_output(
                    output,
                    manifest=alias_treatment,
                    output_type="logo_card",
                    manifest_path=root / "generation-manifest-v01.json",
                ).checks["manifest_logo_treatment"]
            )
            manifest.pop("logo_source_hash")
            self.assertFalse(validate_output(output, manifest=manifest, output_type="logo_card", manifest_path=root / "generation-manifest-v01.json").passed)

    def test_default_manifest_may_omit_concrete_logo_treatment_confirmation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "logo-card-1x1-v01.png"; Image.new("RGBA", (1254, 1254), "white").save(output)
            logo = root / "logo.png"; Image.new("RGBA", (20, 20), "black").save(logo)
            brief = root / "brief.json"; brief.write_text(json.dumps({"copy": {"title": "Hello"}}), encoding="utf-8")
            base = root / "base.png"; Image.new("RGBA", (1254, 1254), "white").save(base)
            digest = hashlib.sha256(logo.read_bytes()).hexdigest()
            manifest = build_generation_manifest(
                brief_path=brief,
                assets=[{"asset_id": "logo", "category": "company-logo", "scope": "project", "rights_status": "user_authorized", "path": str(logo), "sha256": digest}],
                template_path=Path("brandloom/templates/logo-card-1x1.json"),
                font_paths={"heading": find_test_font()},
                base_image_path=base,
                output_path=output,
                qa_state="INTERNAL_LOGO_QA",
                rendered_copy={"title": "Hello"},
                output_type="logo-card",
            )
            self.assertNotIn("logo_treatment", manifest)
            report = validate_output(output, manifest=manifest, output_type="logo_card", manifest_path=root / "generation-manifest-v01.json")
            self.assertTrue(report.checks["manifest_logo_treatment"], report.failures)


if __name__ == "__main__":
    unittest.main()
