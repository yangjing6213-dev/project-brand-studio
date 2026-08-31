"""Deterministic, local-only font discovery and strict resolution."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys

from PIL import ImageFont


_ROLES = ("heading", "body", "latin")
_FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc"}
_STYLE_SUFFIXES = {
    "regular", "normal", "book", "medium", "semibold", "demibold", "bold",
    "extrabold", "black", "light", "thin", "italic", "oblique",
}


@dataclass(frozen=True)
class FontProfile:
    profile_id: str
    aliases: dict[str, tuple[str, ...]]
    fallback_profile_id: str

    def __post_init__(self) -> None:
        if not self.profile_id or not self.fallback_profile_id:
            raise ValueError("font profile ids must be non-empty")
        missing = set(_ROLES) - set(self.aliases)
        if missing:
            raise ValueError(f"font profile missing roles: {sorted(missing)}")
        for role in _ROLES:
            values = self.aliases[role]
            if not values or any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"font aliases for {role} must be non-empty strings")


class FontNotFoundError(LookupError):
    """Raised when a confirmed font profile role cannot be resolved."""


def _preset_path() -> Path:
    return Path(__file__).resolve().parents[2] / "references" / "font-presets.json"


def load_font_profiles(path: Path | None = None) -> dict[str, FontProfile]:
    """Load the checked-in JSON presets without applying any fallback."""
    source = Path(path) if path is not None else _preset_path()
    payload = json.loads(source.read_text(encoding="utf-8"))
    profiles: dict[str, FontProfile] = {}
    for profile_id, data in payload.items():
        aliases = {
            role: tuple(str(alias) for alias in data["aliases"][role])
            for role in _ROLES
        }
        profiles[profile_id] = FontProfile(
            profile_id=profile_id,
            aliases=aliases,
            fallback_profile_id=str(data["fallback_profile_id"]),
        )
    return profiles


def _font_roots(extra_roots: tuple[Path, ...]) -> tuple[Path, ...]:
    roots: list[Path] = [Path(root).expanduser() for root in extra_roots]
    if sys.platform.startswith("win"):
        roots.append(Path(os.environ.get("WINDIR", r"C:\\Windows")) / "Fonts")
    elif sys.platform == "darwin":
        roots.extend((Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path("~/Library/Fonts").expanduser()))
    else:
        roots.extend((Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path("~/.local/share/fonts").expanduser()))
    # Preserve caller ordering while avoiding duplicate roots.
    return tuple(dict.fromkeys(roots))


def _family_key(value: str) -> str:
    stem = Path(value).stem
    stem = re.sub(r"[_-]+", " ", stem)
    words = stem.split()
    while words and words[-1].casefold() in _STYLE_SUFFIXES:
        words.pop()
    return re.sub(r"\s+", " ", " ".join(words)).strip().casefold()


def _embedded_family_key(path: Path) -> str | None:
    """Read a font's embedded family name, tolerating invalid test fixtures."""
    try:
        font = ImageFont.truetype(str(path), size=16)
        name = font.getname()[0]
    except Exception:
        return None
    return _family_key(str(name)) if name else None


def discover_font_files(extra_roots: tuple[Path, ...] = ()) -> dict[str, tuple[Path, ...]]:
    """Discover fonts under explicitly supplied or platform font directories only."""
    found: dict[str, list[Path]] = {}
    for root in _font_roots(extra_roots):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if path.is_file() and path.suffix.casefold() in _FONT_SUFFIXES:
                stem_key = _family_key(path.name)
                found.setdefault(stem_key, []).append(path)
                embedded_key = _embedded_family_key(path)
                if embedded_key and embedded_key != stem_key:
                    found.setdefault(embedded_key, []).append(path)
    return {key: tuple(paths) for key, paths in sorted(found.items())}


def resolve_font(profile: FontProfile, role: str, extra_roots: tuple[Path, ...] = ()) -> Path:
    """Resolve the first confirmed alias for ``role``; never silently falls back."""
    if role not in _ROLES:
        raise ValueError(f"unsupported font role: {role}")
    discovered = discover_font_files(extra_roots)
    for alias in profile.aliases[role]:
        matches = discovered.get(_family_key(alias), ())
        if matches:
            return matches[0]
    aliases = ", ".join(profile.aliases[role])
    raise FontNotFoundError(
        f"confirmed {role} font not found for profile {profile.profile_id}: {aliases}"
    )
