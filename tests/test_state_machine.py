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
    confirmed = {
        "context", "output_targets", "copy", "style", "font", "company_logo", "project_mark",
        "ip_combination", "ip_usage", "shot_list", "output_spec", "coherence",
        "generation_confirmation",
    }
    values = {key: True for key in confirmed}
    values["ip_cast"] = ip_cast
    if rights is not None:
        values.update(custom_ip_reference=True, custom_ip_draft=True, rights=rights)
    return QASession(schema_version="1.0", session_id="test", mode=TaskMode.NEW,
                     state=QAState.GENERATION_READY, project_slug="demo", confirmed=values)


class StateMachineTests(unittest.TestCase):
    def test_cannot_skip_from_intake_to_generation_ready(self) -> None:
        with self.assertRaises(ValueError):
            advance(session_at(QAState.INTAKE), QAState.GENERATION_READY)

    def test_generation_gate_blocks_pending_state(self) -> None:
        with self.assertRaises(GenerationGateError):
            assert_generation_ready(session_at(QAState.OUTPUT_SPEC_PENDING))

    def test_generation_gate_requires_exact_builtin_backend(self) -> None:
        for backend in ("external_api", "", None):
            with self.subTest(backend=backend):
                session = ready_session()
                session = QASession(**{**session.__dict__, "generation_backend": backend})
                with self.assertRaises(GenerationGateError):
                    assert_generation_ready(session)

    def test_style_change_invalidates_font_and_downstream(self) -> None:
        session = session_at(QAState.STYLE_PENDING)
        session = confirm(session, "style", True)
        changed = invalidate_from(session, "style")
        self.assertIn("font", changed.invalidated)
        self.assertIn("shot_list", changed.invalidated)
        self.assertIn("generation_confirmation", changed.invalidated)

    def test_invalidating_brief_choices_clears_pending_generation_request(self) -> None:
        session = QASession(**{
            **ready_session().__dict__,
            "generation_request": {
                "request_id": "request-1",
                "target_id": "github-social-preview",
                "brief_sha256": "brief-hash",
            },
        })

        changed = invalidate_from(session, "style")

        self.assertIsNone(changed.generation_request)
        self.assertEqual(changed.state, QAState.FONT_PENDING)

    def test_builtin_ip_combination_can_advance_to_usage(self) -> None:
        session = QASession(**{**session_at(QAState.IP_COMBINATION_PENDING).__dict__, "confirmed": {"ip_cast": "tuotuo", "ip_combination": True}})
        self.assertEqual(advance(session, QAState.IP_USAGE_PENDING).state, QAState.IP_USAGE_PENDING)

    def test_custom_ip_combination_enters_reference_flow(self) -> None:
        session = QASession(**{**session_at(QAState.IP_COMBINATION_PENDING).__dict__, "confirmed": {"ip_cast": "custom", "ip_combination": True}})
        self.assertEqual(advance(session, QAState.CUSTOM_IP_REFERENCE_PENDING).state, QAState.CUSTOM_IP_REFERENCE_PENDING)

    def test_ready_gate_rejects_missing_confirmation(self) -> None:
        session = session_at(QAState.GENERATION_READY)
        with self.assertRaises(GenerationGateError):
            assert_generation_ready(session)

    def test_confirm_clears_matching_invalidation(self) -> None:
        session = invalidate_from(session_at(QAState.GENERATION_CONFIRM_PENDING), "style")
        confirmed = confirm(session, "font", True)
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

    def test_confirmation_only_keys_require_exact_true(self) -> None:
        for value in ("yes", "no", "false", "拒绝", "0", 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                confirm(session_at(QAState.CONTEXT_CONFIRM_PENDING), "context", value)

    def test_unknown_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            confirm(session_at(QAState.CONTEXT_CONFIRM_PENDING), "not_a_key", True)

    def test_valid_key_in_wrong_pending_state_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            confirm(session_at(QAState.STYLE_PENDING), "context", True)

    def test_pending_state_cannot_advance_without_matching_confirmation(self) -> None:
        with self.assertRaises(ValueError):
            advance(session_at(QAState.CONTEXT_CONFIRM_PENDING), QAState.COPY_DIRECTION_PENDING)

    def test_platform_targets_are_confirmed_before_copy_and_required_for_generation(self) -> None:
        session = session_at(QAState.CONTEXT_CONFIRM_PENDING)
        session = confirm(session, "context", True)
        session = advance(session, QAState.OUTPUT_TARGET_PENDING)
        with self.assertRaises(ValueError):
            advance(session, QAState.OUTPUT_SPEC_PENDING)
        session = confirm(session, "output_targets", True)
        session = advance(session, QAState.OUTPUT_SPEC_PENDING)
        with self.assertRaises(ValueError):
            advance(session, QAState.COPY_DIRECTION_PENDING)
        session = confirm(session, "output_spec", True)
        session = advance(session, QAState.COPY_DIRECTION_PENDING)
        self.assertEqual(session.state, QAState.COPY_DIRECTION_PENDING)

        missing_target = ready_session()
        confirmed = dict(missing_target.confirmed)
        confirmed.pop("output_targets")
        missing_target = QASession(**{**missing_target.__dict__, "confirmed": confirmed})
        with self.assertRaises(GenerationGateError):
            assert_generation_ready(missing_target)

    def test_platform_target_change_invalidates_dependent_copy_and_layout_confirmations(self) -> None:
        session = ready_session()
        changed = invalidate_from(session, "output_targets")
        self.assertEqual(changed.state, QAState.OUTPUT_TARGET_PENDING)
        for key in ("output_targets", "output_spec", "copy", "shot_list", "coherence", "generation_confirmation"):
            self.assertIn(key, changed.invalidated)
            self.assertNotIn(key, changed.confirmed)

    def test_cover_review_can_return_to_generation_gate_for_next_confirmed_target(self) -> None:
        session = QASession(
            schema_version="1.0", session_id="test", mode=TaskMode.NEW,
            state=QAState.USER_REVIEW, project_slug="demo", active_output_target="youtube-long-video",
        )
        self.assertEqual(advance(session, QAState.GENERATION_READY).state, QAState.GENERATION_READY)

    def test_upstream_invalidation_clears_platform_delivery_progress(self) -> None:
        session = QASession(
            schema_version="1.0", session_id="test", mode=TaskMode.NEW,
            state=QAState.GENERATION_READY, project_slug="demo",
            active_output_target="youtube-long-video", delivered_targets=("github-social-preview",),
        )
        changed = invalidate_from(session, "output_targets")
        self.assertIsNone(changed.active_output_target)
        self.assertEqual(changed.delivered_targets, ())

    def test_routing_values_are_strict(self) -> None:
        for value in (True, "anime", "AUTHOR-ANIME", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                confirm(session_at(QAState.IP_CAST_PENDING), "ip_cast", value)
        for value in (True, "authorized", "USER_AUTHORIZED", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                confirm(session_at(QAState.RIGHTS_CONFIRM_PENDING), "rights", value)

    def test_legacy_ambiguous_ready_session_fails_closed(self) -> None:
        session = ready_session()
        session = QASession(**{**session.__dict__, "confirmed": {key: "yes" for key in session.confirmed}})
        with self.assertRaises(GenerationGateError):
            assert_generation_ready(session)

    def test_complete_legal_builtin_flow_reaches_ready(self) -> None:
        session = session_at(QAState.CONTEXT_CONFIRM_PENDING)
        flow = [("context", QAState.OUTPUT_TARGET_PENDING), ("output_targets", QAState.OUTPUT_SPEC_PENDING),
                ("output_spec", QAState.COPY_DIRECTION_PENDING), ("copy", QAState.STYLE_PENDING),
                ("style", QAState.FONT_PENDING), ("font", QAState.COMPANY_LOGO_PENDING),
                ("company_logo", QAState.PROJECT_MARK_PENDING), ("project_mark", QAState.IP_CAST_PENDING),
                ("ip_cast", QAState.IP_COMBINATION_PENDING), ("ip_combination", QAState.IP_USAGE_PENDING),
                ("ip_usage", QAState.SHOT_LIST_PENDING), ("shot_list", QAState.COHERENCE_REVIEW_PENDING),
                ("coherence", QAState.GENERATION_CONFIRM_PENDING),
                ("generation_confirmation", QAState.GENERATION_READY)]
        for key, target in flow:
            value = "tuotuo" if key == "ip_cast" else True
            session = confirm(session, key, value)
            session = advance(session, target)
        assert_generation_ready(session)

    def test_complete_legal_custom_flow_reaches_ready(self) -> None:
        session = session_at(QAState.CONTEXT_CONFIRM_PENDING)
        flow = [
            ("context", QAState.OUTPUT_TARGET_PENDING), ("output_targets", QAState.OUTPUT_SPEC_PENDING),
            ("output_spec", QAState.COPY_DIRECTION_PENDING), ("copy", QAState.STYLE_PENDING),
            ("style", QAState.FONT_PENDING), ("font", QAState.COMPANY_LOGO_PENDING),
            ("company_logo", QAState.PROJECT_MARK_PENDING), ("project_mark", QAState.IP_CAST_PENDING),
            ("ip_cast", QAState.IP_COMBINATION_PENDING), ("ip_combination", QAState.CUSTOM_IP_REFERENCE_PENDING),
            ("custom_ip_reference", QAState.CUSTOM_IP_DRAFT_PENDING),
            ("custom_ip_draft", QAState.RIGHTS_CONFIRM_PENDING),
            ("rights", QAState.IP_USAGE_PENDING), ("ip_usage", QAState.SHOT_LIST_PENDING),
            ("shot_list", QAState.COHERENCE_REVIEW_PENDING),
            ("coherence", QAState.GENERATION_CONFIRM_PENDING),
            ("generation_confirmation", QAState.GENERATION_READY),
        ]
        for key, target in flow:
            value = "custom" if key == "ip_cast" else "user_authorized" if key == "rights" else True
            session = confirm(session, key, value)
            session = advance(session, target)
        assert_generation_ready(session)


if __name__ == "__main__":
    unittest.main()
