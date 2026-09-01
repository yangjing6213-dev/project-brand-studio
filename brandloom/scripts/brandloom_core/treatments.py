"""Canonical company-logo operation to render-treatment mapping."""

from __future__ import annotations

from typing import Final


OPERATION_TO_TREATMENT: Final[dict[str, str]] = {
    "default": "default",
    "recolor_monochrome": "monochrome-black",
    "monochrome-black": "monochrome-black",
}


def canonicalize_logo_treatment(value: object) -> str:
    if value in (None, ""):
        return "default"
    if not isinstance(value, str):
        raise ValueError("company logo treatment must be a JSON string")
    try:
        return OPERATION_TO_TREATMENT[value]
    except KeyError as exc:
        raise ValueError(f"unsupported company logo treatment: {value}") from exc


def operation_for_treatment(treatment: str) -> str:
    canonical = canonicalize_logo_treatment(treatment)
    return "recolor_monochrome" if canonical == "monochrome-black" else "default"
