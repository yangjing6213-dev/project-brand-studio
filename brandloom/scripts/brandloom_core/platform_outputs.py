"""Validated platform-cover output targets and custom pixel dimensions."""

from __future__ import annotations

from copy import deepcopy
import json
from math import gcd
from pathlib import Path


_SPEC_PATH = Path(__file__).resolve().parents[2] / "templates" / "platform-output-specs.json"
_CUSTOM_MIN_SIDE = 320
_CUSTOM_MAX_SIDE = 8192
_CUSTOM_MAX_PIXELS = 16_000_000


def _load_targets() -> dict[str, dict[str, object]]:
    try:
        payload = json.loads(_SPEC_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid platform output specification: {_SPEC_PATH}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
        raise RuntimeError("platform output specification schema_version must be 1.0")
    targets = payload.get("targets")
    if not isinstance(targets, list):
        raise RuntimeError("platform output specification requires a targets list")
    result: dict[str, dict[str, object]] = {}
    for target in targets:
        if not isinstance(target, dict) or not isinstance(target.get("id"), str):
            raise RuntimeError("each platform output target requires an id")
        dimensions = target.get("dimensions")
        if not isinstance(dimensions, list) or len(dimensions) != 2 or any(type(item) is not int or item <= 0 for item in dimensions):
            raise RuntimeError(f"invalid dimensions for output target: {target.get('id')}")
        if target["id"] in result:
            raise RuntimeError(f"duplicate platform output target: {target['id']}")
        result[target["id"]] = target
    return result


OUTPUT_TARGETS = _load_targets()


def same_aspect_ratio(source: tuple[int, int] | list[int], target: tuple[int, int] | list[int]) -> bool:
    """Compare positive integer dimensions without floating-point rounding."""
    try:
        sw, sh = source
        tw, th = target
    except (TypeError, ValueError):
        return False
    if any(type(value) is not int or value <= 0 for value in (sw, sh, tw, th)):
        return False
    return sw * th == tw * sh


def _custom_spec(dimensions: tuple[int, int] | list[int]) -> dict[str, object]:
    try:
        values = tuple(dimensions)
    except TypeError as exc:
        raise ValueError("custom dimensions must contain exactly two integers") from exc
    if len(values) != 2 or any(type(value) is not int for value in values):
        raise ValueError("custom dimensions must contain exactly two integers")
    width, height = values
    if not (_CUSTOM_MIN_SIDE <= width <= _CUSTOM_MAX_SIDE and _CUSTOM_MIN_SIDE <= height <= _CUSTOM_MAX_SIDE):
        raise ValueError(f"custom dimensions must be between {_CUSTOM_MIN_SIDE} and {_CUSTOM_MAX_SIDE} pixels per side")
    if width * height > _CUSTOM_MAX_PIXELS:
        raise ValueError(f"custom canvas cannot exceed {_CUSTOM_MAX_PIXELS} pixels")
    divisor = gcd(width, height)
    return {
        "id": "custom",
        "platform": "custom",
        "purpose": "custom_cover",
        "dimensions": [width, height],
        "ratio": f"{width // divisor}:{height // divisor}",
        "spec_status": "user_confirmed_custom",
        "minimum_dimensions": None,
        "safe_area": None,
    }


def resolve_output_target(target_id: str, dimensions: tuple[int, int] | list[int] | None = None) -> dict[str, object]:
    """Return a copy of a known platform target or a validated custom target."""
    if target_id == "custom":
        if dimensions is None:
            raise ValueError("custom target requires confirmed width and height")
        return _custom_spec(dimensions)
    if dimensions is not None:
        raise ValueError("platform target dimensions are fixed; choose custom for other dimensions")
    try:
        return deepcopy(OUTPUT_TARGETS[target_id])
    except KeyError as exc:
        raise ValueError(f"unsupported output target: {target_id}") from exc
