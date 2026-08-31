import unittest

from brandloom.scripts.brandloom_core.models import QAState, QASession, TaskMode
from brandloom.scripts.brandloom_core.state_machine import (
    GenerationGateError,
    advance,
    assert_generation_ready,
    confirm,
    invalidate_from,
)


def session_at(state: QAState) -> QASession:
    return QASession(
        schema_version="1.0",
        session_id="test",
        mode=TaskMode.NEW,
        state=state,
        project_slug="demo",
    )


class StateMachineTests(unittest.TestCase):
    def test_cannot_skip_from_intake_to_generation_ready(self) -> None:
        with self.assertRaises(ValueError):
            advance(session_at(QAState.INTAKE), QAState.GENERATION_READY)

    def test_generation_gate_blocks_pending_state(self) -> None:
        with self.assertRaises(GenerationGateError):
            assert_generation_ready(session_at(QAState.OUTPUT_SPEC_PENDING))

    def test_style_change_invalidates_font_and_downstream(self) -> None:
        session = session_at(QAState.GENERATION_CONFIRM_PENDING)
        session = confirm(session, "style", "bright-saas-real-scene")
        changed = invalidate_from(session, "style")
        self.assertIn("font", changed.invalidated)
        self.assertIn("shot_list", changed.invalidated)
        self.assertIn("generation_confirmation", changed.invalidated)
        self.assertEqual(changed.state, QAState.FONT_PENDING)


if __name__ == "__main__":
    unittest.main()
