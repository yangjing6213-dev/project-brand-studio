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


def ready_session(*, ip_cast: str = "tuotuo", rights: str | None = None) -> QASession:
    session = session_at(QAState.GENERATION_READY)
    for key in (
        "context", "copy", "style", "font", "company_logo", "project_mark",
        "ip_combination", "ip_usage", "shot_list", "output_spec", "coherence",
        "generation_confirmation",
    ):
        session = confirm(session, key, True)
    session = confirm(session, "ip_cast", ip_cast)
    if rights is not None:
        for key in ("custom_ip_reference", "custom_ip_draft"):
            session = confirm(session, key, True)
        session = confirm(session, "rights", rights)
    return session


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

    def test_builtin_ip_combination_can_advance_to_usage(self) -> None:
        session = confirm(session_at(QAState.IP_COMBINATION_PENDING), "ip_cast", "tuotuo")
        self.assertEqual(advance(session, QAState.IP_USAGE_PENDING).state, QAState.IP_USAGE_PENDING)

    def test_custom_ip_combination_enters_reference_flow(self) -> None:
        session = confirm(session_at(QAState.IP_COMBINATION_PENDING), "ip_cast", "custom")
        self.assertEqual(advance(session, QAState.CUSTOM_IP_REFERENCE_PENDING).state, QAState.CUSTOM_IP_REFERENCE_PENDING)

    def test_ready_gate_rejects_missing_confirmation(self) -> None:
        session = session_at(QAState.GENERATION_READY)
        with self.assertRaises(GenerationGateError):
            assert_generation_ready(session)

    def test_confirm_clears_matching_invalidation(self) -> None:
        session = invalidate_from(session_at(QAState.GENERATION_CONFIRM_PENDING), "style")
        confirmed = confirm(session, "font", "Inter")
        self.assertNotIn("font", confirmed.invalidated)

    def test_false_or_empty_values_are_not_confirmations(self) -> None:
        for value in (False, None, "", (), [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                confirm(session_at(QAState.CONTEXT_CONFIRM_PENDING), "context", value)

    def test_custom_ip_rights_must_be_explicitly_user_authorized(self) -> None:
        for status in ("missing", "unknown", "draft_unconfirmed", "analysis_only"):
            with self.subTest(status=status), self.assertRaises(GenerationGateError):
                assert_generation_ready(ready_session(ip_cast="custom", rights=status))
        assert_generation_ready(ready_session(ip_cast="custom", rights="user_authorized"))


if __name__ == "__main__":
    unittest.main()
