from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
IP_ROOT = ROOT / "brandloom" / "assets" / "defaults" / "ip"
COMPANY_ROOT = ROOT / "brandloom" / "assets" / "defaults" / "company-logo" / "enhe"


EXPECTED = {
    "author-anime": {"profile.md", "provenance.json", "reference.png"},
    "tuotuo": {"profile.md", "provenance.json", "reference.png"},
    "xingbi": {"profile.md", "provenance.json", "reference.png"},
}


class IPProfileTests(unittest.TestCase):
    def test_builtin_ip_profiles_have_required_files(self) -> None:
        for profile_id, required in EXPECTED.items():
            profile_dir = IP_ROOT / profile_id
            self.assertTrue(profile_dir.is_dir(), profile_id)
            self.assertEqual(
                {path.name for path in profile_dir.iterdir()}, required, profile_id
            )

    def test_profiles_record_authorized_public_provenance(self) -> None:
        for profile_id in EXPECTED:
            provenance = json.loads((IP_ROOT / profile_id / "provenance.json").read_text())
            self.assertEqual(provenance["source_reference"], "user-provided project asset")
            self.assertRegex(provenance["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(provenance["confirmation_source"], "user_confirmed")
            self.assertEqual(provenance["authorization_status"], "user_authorized")
            self.assertEqual(provenance["distribution_scope"], "public_skill_package")

    def test_company_logo_default_has_required_files(self) -> None:
        self.assertTrue(COMPANY_ROOT.is_dir())
        self.assertEqual(
            {path.name for path in COMPANY_ROOT.iterdir()},
            {"profile.md", "provenance.json", "reference.png"},
        )

    def test_combinations_reference_all_builtin_options(self) -> None:
        combinations = (ROOT / "brandloom" / "references" / "ip-combinations.md").read_text()
        for option in (
            "author-only",
            "tuotuo-only",
            "xingbi-only",
            "tuotuo-xingbi",
            "author-tuotuo",
            "author-xingbi",
            "author-tuotuo-xingbi",
        ):
            self.assertIn(option, combinations)


if __name__ == "__main__":
    unittest.main()
