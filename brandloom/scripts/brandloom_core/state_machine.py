"""Explicit QA state transitions and downstream invalidation rules."""

from dataclasses import replace

from .models import QAState, QASession, RightsStatus


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

PENDING_CONFIRMATION_KEYS: dict[QAState, str] = {
    QAState.CONTEXT_CONFIRM_PENDING: "context",
    QAState.COPY_DIRECTION_PENDING: "copy",
    QAState.STYLE_PENDING: "style",
    QAState.FONT_PENDING: "font",
    QAState.COMPANY_LOGO_PENDING: "company_logo",
    QAState.PROJECT_MARK_PENDING: "project_mark",
    QAState.IP_CAST_PENDING: "ip_cast",
    QAState.IP_COMBINATION_PENDING: "ip_combination",
    QAState.CUSTOM_IP_REFERENCE_PENDING: "custom_ip_reference",
    QAState.CUSTOM_IP_DRAFT_PENDING: "custom_ip_draft",
    QAState.RIGHTS_CONFIRM_PENDING: "rights",
    QAState.IP_USAGE_PENDING: "ip_usage",
    QAState.SHOT_LIST_PENDING: "shot_list",
    QAState.OUTPUT_SPEC_PENDING: "output_spec",
    QAState.COHERENCE_REVIEW_PENDING: "coherence",
    QAState.GENERATION_CONFIRM_PENDING: "generation_confirmation",
}

_CONFIRMATION_ONLY = frozenset(PENDING_CONFIRMATION_KEYS.values()) - {"ip_cast", "rights"}
_KNOWN_KEYS = frozenset((*_CONFIRMATION_ONLY, "ip_cast", "rights"))


def _has_confirmation(session: QASession, key: str) -> bool:
    return _has_valid_confirmation(session, key)


def advance(session: QASession, target: QAState) -> QASession:
    if target is not QAState.CANCELLED:
        expected_key = PENDING_CONFIRMATION_KEYS.get(session.state)
        if expected_key is not None and not _has_valid_confirmation(session, expected_key):
            raise ValueError(f"{session.state} requires confirmation: {expected_key}")
    if session.state is QAState.IP_COMBINATION_PENDING:
        ip_cast = session.confirmed.get("ip_cast")
        if ip_cast not in {"author-anime", "tuotuo", "xingbi", "custom"}:
            raise ValueError("ip_cast must be confirmed before selecting the combination")
        is_custom = ip_cast == "custom"
        if is_custom and target is QAState.IP_USAGE_PENDING:
            raise ValueError("custom IP requires reference, draft, and rights confirmations")
        if not is_custom and target is QAState.CUSTOM_IP_REFERENCE_PENDING:
            raise ValueError("non-custom IP cannot enter custom reference flow")
    if target not in TRANSITIONS.get(session.state, frozenset()):
        raise ValueError(f"invalid QA transition: {session.state} -> {target}")
    return replace(session, state=target)


def confirm(session: QASession, key: str, value: object) -> QASession:
    if not isinstance(key, str) or not key.strip() or key not in _KNOWN_KEYS:
        raise ValueError(f"unknown QA key: {key}")
    expected_key = PENDING_CONFIRMATION_KEYS.get(session.state)
    if expected_key != key:
        raise ValueError(f"confirmation {key} is not accepted in state {session.state}")
    if key in _CONFIRMATION_ONLY:
        if type(value) is not bool or value is not True:
            raise ValueError(f"confirmation {key} requires the exact boolean true")
    elif key == "ip_cast":
        if not isinstance(value, str) or value not in {"author-anime", "tuotuo", "xingbi", "custom"}:
            raise ValueError("ip_cast must be author-anime, tuotuo, xingbi, or custom")
    elif key == "rights":
        if isinstance(value, RightsStatus):
            value = value.value
        if not isinstance(value, str) or value not in {status.value for status in RightsStatus}:
            raise ValueError("rights must be a documented RightsStatus value")
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
    return replace(session, state=target, confirmed=confirmed, invalidated=invalidated, accepted_logo=None)


def assert_generation_ready(session: QASession) -> None:
    if session.state is not QAState.GENERATION_READY:
        raise GenerationGateError(f"generation requires GENERATION_READY, got {session.state}")
    unknown = [key for key in session.confirmed if key not in _KNOWN_KEYS]
    if unknown:
        raise GenerationGateError(f"unknown confirmations: {', '.join(unknown)}")
    missing = [key for key in _REQUIRED if not _has_valid_confirmation(session, key)]
    ip_cast = session.confirmed.get("ip_cast")
    if ip_cast not in {"author-anime", "tuotuo", "xingbi", "custom"}:
        raise GenerationGateError("ip_cast must be a canonical routing value")
    if ip_cast == "custom":
        missing.extend(
            key for key in ("custom_ip_reference", "custom_ip_draft", "rights")
            if not _has_valid_confirmation(session, key)
        )
        if session.confirmed.get("rights") != "user_authorized":
            raise GenerationGateError("custom IP generation requires rights=user_authorized")
    if missing:
        raise GenerationGateError(f"missing confirmations: {', '.join(dict.fromkeys(missing))}")


def _has_valid_confirmation(session: QASession, key: str) -> bool:
    if key not in session.confirmed or key in session.invalidated:
        return False
    value = session.confirmed[key]
    if key in _CONFIRMATION_ONLY:
        return type(value) is bool and value is True
    if key == "ip_cast":
        return isinstance(value, str) and value in {"author-anime", "tuotuo", "xingbi", "custom"}
    if key == "rights":
        return isinstance(value, str) and value in {status.value for status in RightsStatus}
    return False
