"""Explicit QA state transitions and downstream invalidation rules."""

from dataclasses import replace

from .models import QAState, QASession


class GenerationGateError(RuntimeError):
    """Raised when generation is attempted without a fully confirmed session."""


# Every edge is explicit; callers cannot jump over a QA decision.
TRANSITIONS: dict[QAState, frozenset[QAState]] = {
    QAState.INTAKE: frozenset({QAState.CONTEXT_ANALYSIS, QAState.CANCELLED}),
    QAState.CONTEXT_ANALYSIS: frozenset({QAState.CONTEXT_CONFIRM_PENDING, QAState.CANCELLED}),
    QAState.CONTEXT_CONFIRM_PENDING: frozenset({QAState.COPY_DIRECTION_PENDING, QAState.CANCELLED}),
    QAState.COPY_DIRECTION_PENDING: frozenset({QAState.STYLE_PENDING, QAState.CANCELLED}),
    QAState.STYLE_PENDING: frozenset({QAState.FONT_PENDING, QAState.CANCELLED}),
    QAState.FONT_PENDING: frozenset({QAState.COMPANY_LOGO_PENDING, QAState.CANCELLED}),
    QAState.COMPANY_LOGO_PENDING: frozenset({QAState.PROJECT_MARK_PENDING, QAState.CANCELLED}),
    QAState.PROJECT_MARK_PENDING: frozenset({QAState.IP_CAST_PENDING, QAState.CANCELLED}),
    QAState.IP_CAST_PENDING: frozenset({QAState.IP_COMBINATION_PENDING, QAState.CANCELLED}),
    QAState.IP_COMBINATION_PENDING: frozenset({QAState.CUSTOM_IP_REFERENCE_PENDING, QAState.IP_USAGE_PENDING, QAState.CANCELLED}),
    QAState.CUSTOM_IP_REFERENCE_PENDING: frozenset({QAState.CUSTOM_IP_DRAFT_PENDING, QAState.CANCELLED}),
    QAState.CUSTOM_IP_DRAFT_PENDING: frozenset({QAState.RIGHTS_CONFIRM_PENDING, QAState.CANCELLED}),
    QAState.RIGHTS_CONFIRM_PENDING: frozenset({QAState.IP_USAGE_PENDING, QAState.CANCELLED}),
    QAState.IP_USAGE_PENDING: frozenset({QAState.SHOT_LIST_PENDING, QAState.CANCELLED}),
    QAState.SHOT_LIST_PENDING: frozenset({QAState.OUTPUT_SPEC_PENDING, QAState.CANCELLED}),
    QAState.OUTPUT_SPEC_PENDING: frozenset({QAState.COHERENCE_REVIEW_PENDING, QAState.CANCELLED}),
    QAState.COHERENCE_REVIEW_PENDING: frozenset({QAState.GENERATION_CONFIRM_PENDING, QAState.CANCELLED}),
    QAState.GENERATION_CONFIRM_PENDING: frozenset({QAState.GENERATION_READY, QAState.CANCELLED}),
    QAState.GENERATION_READY: frozenset({QAState.GENERATE_LOGO_BASE, QAState.CANCELLED}),
    QAState.GENERATE_LOGO_BASE: frozenset({QAState.COMPOSE_LOGO_CARD, QAState.CANCELLED}),
    QAState.COMPOSE_LOGO_CARD: frozenset({QAState.INTERNAL_LOGO_QA, QAState.CANCELLED}),
    QAState.INTERNAL_LOGO_QA: frozenset({QAState.LOGO_USER_REVIEW, QAState.CANCELLED}),
    QAState.LOGO_USER_REVIEW: frozenset({QAState.GENERATE_COVER_BASE, QAState.CANCELLED}),
    QAState.GENERATE_COVER_BASE: frozenset({QAState.COMPOSE_COVER, QAState.CANCELLED}),
    QAState.COMPOSE_COVER: frozenset({QAState.INTERNAL_COVER_QA, QAState.CANCELLED}),
    QAState.INTERNAL_COVER_QA: frozenset({QAState.USER_REVIEW, QAState.CANCELLED}),
    QAState.USER_REVIEW: frozenset({QAState.DELIVERED, QAState.CANCELLED}),
    QAState.DELIVERED: frozenset(),
    QAState.CANCELLED: frozenset(),
}


INVALIDATION_RULES = {
    "context": (QAState.COPY_DIRECTION_PENDING, ("copy", "style", "font", "company_logo", "project_mark", "ip_cast", "ip_combination", "custom_ip_reference", "custom_ip_draft", "rights", "ip_usage", "shot_list", "output_spec", "coherence", "generation_confirmation")),
    "copy": (QAState.COPY_DIRECTION_PENDING, ("copy", "shot_list", "coherence", "generation_confirmation")),
    "style": (QAState.FONT_PENDING, ("font", "shot_list", "output_spec", "coherence", "generation_confirmation")),
    "font": (QAState.FONT_PENDING, ("font", "shot_list", "coherence", "generation_confirmation")),
    "company_logo": (QAState.COMPANY_LOGO_PENDING, ("company_logo", "shot_list", "coherence", "generation_confirmation")),
    "project_mark": (QAState.PROJECT_MARK_PENDING, ("project_mark", "shot_list", "coherence", "generation_confirmation")),
    "ip_cast": (QAState.IP_CAST_PENDING, ("ip_cast", "ip_combination", "custom_ip_reference", "custom_ip_draft", "rights", "ip_usage", "shot_list", "coherence", "generation_confirmation")),
    "ip_combination": (QAState.IP_COMBINATION_PENDING, ("ip_combination", "custom_ip_reference", "custom_ip_draft", "rights", "ip_usage", "shot_list", "coherence", "generation_confirmation")),
    "custom_ip_reference": (QAState.CUSTOM_IP_REFERENCE_PENDING, ("custom_ip_reference", "custom_ip_draft", "rights", "ip_usage", "shot_list", "coherence", "generation_confirmation")),
    "custom_ip_draft": (QAState.CUSTOM_IP_DRAFT_PENDING, ("custom_ip_draft", "rights", "ip_usage", "shot_list", "coherence", "generation_confirmation")),
    "rights": (QAState.RIGHTS_CONFIRM_PENDING, ("rights", "ip_usage", "shot_list", "coherence", "generation_confirmation")),
    "ip_usage": (QAState.IP_USAGE_PENDING, ("ip_usage", "shot_list", "coherence", "generation_confirmation")),
    "output_spec": (QAState.OUTPUT_SPEC_PENDING, ("output_spec", "coherence", "generation_confirmation")),
    "shot_list": (QAState.SHOT_LIST_PENDING, ("shot_list", "coherence", "generation_confirmation")),
}

_REQUIRED = ("context", "copy", "style", "font", "company_logo", "project_mark", "ip_cast", "ip_combination", "ip_usage", "shot_list", "output_spec", "coherence", "generation_confirmation")


def advance(session: QASession, target: QAState) -> QASession:
    if session.state is QAState.IP_COMBINATION_PENDING:
        is_custom = session.confirmed.get("ip_cast") == "custom"
        if is_custom and target is QAState.IP_USAGE_PENDING:
            raise ValueError("custom IP requires reference, draft, and rights confirmations")
        if not is_custom and target is QAState.CUSTOM_IP_REFERENCE_PENDING:
            raise ValueError("non-custom IP cannot enter custom reference flow")
    if target not in TRANSITIONS.get(session.state, frozenset()):
        raise ValueError(f"invalid QA transition: {session.state} -> {target}")
    return replace(session, state=target)


def confirm(session: QASession, key: str, value: object) -> QASession:
    confirmed = dict(session.confirmed)
    confirmed[key] = value
    invalidated = tuple(item for item in session.invalidated if item != key)
    return replace(session, confirmed=confirmed, invalidated=invalidated)


def invalidate_from(session: QASession, key: str) -> QASession:
    try:
        target, keys = INVALIDATION_RULES[key]
    except KeyError as exc:
        raise ValueError(f"unknown QA key: {key}") from exc
    confirmed = {name: value for name, value in session.confirmed.items() if name not in keys}
    invalidated = tuple(dict.fromkeys((*session.invalidated, *keys)))
    return replace(session, state=target, confirmed=confirmed, invalidated=invalidated)


def assert_generation_ready(session: QASession) -> None:
    if session.state is not QAState.GENERATION_READY:
        raise GenerationGateError(f"generation requires GENERATION_READY, got {session.state}")
    missing = [key for key in _REQUIRED if key not in session.confirmed]
    if session.confirmed.get("ip_cast") == "custom":
        missing.extend(key for key in ("custom_ip_reference", "custom_ip_draft", "rights") if key not in session.confirmed)
    if missing:
        raise GenerationGateError(f"missing confirmations: {', '.join(dict.fromkeys(missing))}")
