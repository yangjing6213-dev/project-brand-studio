from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest

from PIL import Image

from brandloom.scripts.brandloom_core.asset_library import (
    list_assets,
    register_asset,
    resolve_default,
)
from brandloom.scripts.brandloom_core.models import AssetCategory, AssetScope, RightsStatus


class AssetLibraryTests(unittest.TestCase):
    def _image(self, directory: Path, name: str = "logo.png", color=(12, 34, 56, 255)) -> Path:
        path = directory / name
        Image.new("RGBA", (32, 16), color).save(path)
        return path

    def test_duplicate_hash_reuses_existing_record(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._image(root)
            first = register_asset(
                source, category=AssetCategory.PROJECT_MARK, scope=AssetScope.PROJECT,
                workspace=root, rights_status=RightsStatus.USER_AUTHORIZED,
                save_scope_confirmed=True, make_default=False,
            )
            second = register_asset(
                source, category=AssetCategory.PROJECT_MARK, scope=AssetScope.PROJECT,
                workspace=root, rights_status=RightsStatus.USER_AUTHORIZED,
                save_scope_confirmed=True, make_default=False,
            )
            self.assertEqual(first.asset_id, second.asset_id)
            self.assertEqual(len(list_assets(root, scope=AssetScope.PROJECT)), 1)

    def test_new_default_replaces_flag_without_deleting_old_asset(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first_source = self._image(root, "first.png")
            second_source = self._image(root, "second.png", (99, 20, 5, 255))
            first = register_asset(
                first_source, category=AssetCategory.PROJECT_MARK, scope=AssetScope.PROJECT,
                workspace=root, rights_status=RightsStatus.USER_AUTHORIZED,
                save_scope_confirmed=True, make_default=True,
            )
            second = register_asset(
                second_source, category=AssetCategory.PROJECT_MARK, scope=AssetScope.PROJECT,
                workspace=root, rights_status=RightsStatus.USER_AUTHORIZED,
                save_scope_confirmed=True, make_default=True,
            )
            self.assertEqual(resolve_default(AssetCategory.PROJECT_MARK, AssetScope.PROJECT, root).asset_id, second.asset_id)
            self.assertTrue((root / ".brandloom" / first.relative_path).exists())
            self.assertIsNone(next(a for a in list_assets(root) if a.asset_id == first.asset_id).default_scope)

    def test_unconfirmed_save_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._image(root)
            with self.assertRaises(ValueError):
                register_asset(
                    source, category=AssetCategory.PROJECT_MARK, scope=AssetScope.PROJECT,
                    workspace=root, rights_status=RightsStatus.USER_AUTHORIZED,
                    save_scope_confirmed=False,
                )

    def test_company_logo_forbids_redraw_and_geometry_changes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            record = register_asset(
                self._image(root), category=AssetCategory.COMPANY_LOGO, scope=AssetScope.PROJECT,
                workspace=root, rights_status=RightsStatus.USER_AUTHORIZED,
                save_scope_confirmed=True,
            )
            for operation in ("redraw", "distort", "change_letterforms", "change_geometry", "use_as_training_reference"):
                self.assertIn(operation, record.forbidden_operations)

    def test_analysis_only_reference_can_be_saved_locally(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            previous = os.environ.get("CODEX_HOME")
            os.environ["CODEX_HOME"] = str(root / "codex")
            try:
                record = register_asset(
                    self._image(root), category=AssetCategory.STYLE_REFERENCE, scope=AssetScope.PERSONAL,
                    rights_status=RightsStatus.ANALYSIS_ONLY, save_scope_confirmed=True,
                )
            finally:
                if previous is None:
                    os.environ.pop("CODEX_HOME", None)
                else:
                    os.environ["CODEX_HOME"] = previous
            self.assertEqual(record.rights_status, RightsStatus.ANALYSIS_ONLY)

    def test_unknown_rights_are_rejected_for_generation_assets(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                register_asset(
                    self._image(root), category=AssetCategory.IP_CHARACTER, scope=AssetScope.PROJECT,
                    workspace=root, rights_status=RightsStatus.UNKNOWN, save_scope_confirmed=True,
                )

    def test_same_requested_id_gets_unique_identity_and_default(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = register_asset(
                self._image(root, "first.png", (1, 2, 3, 255)), asset_id="mark",
                category=AssetCategory.PROJECT_MARK, scope=AssetScope.PROJECT,
                workspace=root, rights_status=RightsStatus.USER_AUTHORIZED,
                save_scope_confirmed=True, make_default=True,
            )
            second = register_asset(
                self._image(root, "second.png", (4, 5, 6, 255)), asset_id="mark",
                category=AssetCategory.PROJECT_MARK, scope=AssetScope.PROJECT,
                workspace=root, rights_status=RightsStatus.USER_AUTHORIZED,
                save_scope_confirmed=True, make_default=False,
            )
            self.assertNotEqual(first.asset_id, second.asset_id)
            from brandloom.scripts.brandloom_core.asset_library import set_default
            set_default(second, workspace=root)
            defaults = [a for a in list_assets(root, scope=AssetScope.PROJECT) if a.default_scope is AssetScope.PROJECT]
            self.assertEqual([a.asset_id for a in defaults], [second.asset_id])
            self.assertEqual(resolve_default(AssetCategory.PROJECT_MARK, AssetScope.PROJECT, root).asset_id, second.asset_id)


if __name__ == "__main__":
    unittest.main()
