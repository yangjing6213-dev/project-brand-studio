import json
import os
import types
from dataclasses import MISSING, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints

from .models import AssetRecord, BrandBrief, QASession


_SUPPORTED = (QASession, AssetRecord, BrandBrief)


def _to_json(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _to_json(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_to_json(item) for item in value]
    if isinstance(value, list):
        return [_to_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_json(item) for key, item in value.items()}
    return value


def _from_json(value: Any, annotation: Any) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_from_json(item, args[0]) for item in value)
        return tuple(_from_json(item, item_type) for item, item_type in zip(value, args))
    if origin in (Union, types.UnionType):
        non_none = [item for item in args if item is not type(None)]
        if value is None:
            return None
        return _from_json(value, non_none[0]) if len(non_none) == 1 else value
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)
    if annotation in (dict, list, tuple, Any, object):
        return value
    return value


def _construct(data: Any, cls: type) -> Any:
    if cls not in _SUPPORTED:
        raise TypeError(f"unsupported dataclass type: {cls!r}")
    hints = get_type_hints(cls)
    values = {}
    for field in fields(cls):
        if field.name in data:
            values[field.name] = _from_json(data[field.name], hints[field.name])
        elif field.default is not MISSING:
            values[field.name] = field.default
        elif field.default_factory is not MISSING:
            values[field.name] = field.default_factory()
        else:
            raise KeyError(field.name)
    return cls(**values)


def write_json_dataclass(path: Path, value: Any) -> None:
    if not is_dataclass(value) or type(value) not in _SUPPORTED:
        raise TypeError(f"unsupported dataclass value: {type(value)!r}")
    destination = Path(path)
    temporary = destination.with_name(destination.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(_to_json(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)


def read_json_dataclass(path: Path, cls: type) -> Any:
    if cls not in _SUPPORTED:
        raise TypeError(f"unsupported dataclass type: {cls!r}")
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return _construct(data, cls)
