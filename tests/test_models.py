from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from brandloom.scripts.brandloom_core.json_io import read_json_dataclass, write_json_dataclass
from brandloom.scripts.brandloom_core.models import (
    AssetCategory,
    AssetRecord,
    AssetScope,
    BrandBrief,
    QAState,
    QASession,
    RightsStatus,
    TaskMode,
)


class ModelTests(unittest.TestCase):
    def test_session_round_trip(self) -> None:
        session = QASession(
            schema_version="1.0",
            session_id="20260831-test",
            mode=TaskMode.NEW,
            state=QAState.INTAKE,
            project_slug="agentguardian",
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "qa-state.json"
            write_json_dataclass(path, session)
            loaded = read_json_dataclass(path, QASession)
        self.assertEqual(loaded, session)
        self.assertEqual(loaded.state, QAState.INTAKE)

    def test_json_is_utf8_and_temporary_file_is_removed(self) -> None:
        session = QASession("1.0", "测试", TaskMode.NEW, QAState.INTAKE, "项目")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            write_json_dataclass(path, session)
            self.assertIn("测试", path.read_text(encoding="utf-8"))
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_brand_brief_requires_top_level_mappings(self) -> None:
        with self.assertRaises(TypeError):
            BrandBrief("1.0", {}, [], {}, {}, {}, {})

    def test_unsupported_dataclass_type_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "value.json"
            with self.assertRaises(TypeError):
                read_json_dataclass(path, dict)

    def test_asset_record_round_trip_restores_enums_and_tuples(self) -> None:
        from brandloom.scripts.brandloom_core.models import AssetRecord

        record = AssetRecord(
            "logo", AssetCategory.COMPANY_LOGO, AssetScope.PROJECT, "logo.png", "hash",
            10, 20, RightsStatus.USER_AUTHORIZED, True, AssetScope.PERSONAL,
            ("scale",), ("redraw",), "now",
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "asset.json"
            write_json_dataclass(path, record)
            loaded = read_json_dataclass(path, AssetRecord)
        self.assertEqual(loaded, record)
        self.assertIs(type(loaded.category), AssetCategory)
        self.assertIs(type(loaded.default_scope), AssetScope)

    def test_enum_values_match_public_schema(self) -> None:
        self.assertEqual(TaskMode.PLAN_ONLY.value, "plan-only")
        self.assertEqual(AssetCategory.COMPANY_LOGO.value, "company-logo")
        self.assertEqual(AssetCategory.UI_SCREENSHOT.value, "ui-screenshot")
        self.assertEqual(AssetScope.SKILL_DEFAULTS.value, "skill-defaults")
        self.assertEqual(RightsStatus.USER_AUTHORIZED.value, "user_authorized")

    def test_ui_screenshot_category_round_trip(self) -> None:
        record = AssetRecord(
            "screen", AssetCategory.UI_SCREENSHOT, AssetScope.PROJECT, "screen.png", "hash",
            10, 20, RightsStatus.USER_AUTHORIZED, True, None,
            (), (), "now",
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "asset.json"
            write_json_dataclass(path, record)
            loaded = read_json_dataclass(path, AssetRecord)
        self.assertIs(loaded.category, AssetCategory.UI_SCREENSHOT)


if __name__ == "__main__":
    unittest.main()
