"""Deterministic font discovery with verified app-local fallback recovery."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import unicodedata
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid

from PIL import ImageFont


_ROLES = ("heading", "body", "latin")
_FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc"}
_STYLE_SUFFIXES = {
    "regular", "normal", "book", "medium", "semibold", "demibold", "bold",
    "extrabold", "black", "light", "thin", "italic", "oblique",
}
_FALLBACK_VERSION = "2.004"
_FALLBACK_COMMIT = "523d033d6cb47f4a80c58a35753646f5c3608a78"
_FALLBACK_FONT_NAME = "NotoSansCJKsc-Regular.otf"
_FALLBACK_FONT_URL = (
    "https://raw.githubusercontent.com/notofonts/noto-cjk/"
    f"{_FALLBACK_COMMIT}/Sans/OTF/SimplifiedChinese/{_FALLBACK_FONT_NAME}"
)
_FALLBACK_LICENSE_URL = f"https://raw.githubusercontent.com/notofonts/noto-cjk/{_FALLBACK_COMMIT}/LICENSE"
_FALLBACK_FONT_SHA256 = "2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b"
_FALLBACK_LICENSE_SHA256 = "6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2"
_FALLBACK_FONT_SIZE = 16_437_364
_MAX_LICENSE_SIZE = 64 * 1024


class FontNotFoundError(LookupError):
    """Raised when no verified local or downloaded font can render required text."""


def _visible_characters(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        char for char in text
        if unicodedata.category(char) not in {"Cc", "Cf"}
        and not (0xFE00 <= ord(char) <= 0xFE0F or 0xE0100 <= ord(char) <= 0xE01EF)
    ))


def _sfnt_cmap(font_data: bytes) -> bytes | None:
    """Extract the first face's cmap table from a TrueType, OpenType, or TTC file."""
    try:
        if font_data[:4] == b"ttcf":
            if len(font_data) < 16:
                return None
            face_count = struct.unpack_from(">I", font_data, 8)[0]
            if not face_count or len(font_data) < 12 + face_count * 4:
                return None
            sfnt_offset = struct.unpack_from(">I", font_data, 12)[0]
        else:
            sfnt_offset = 0
        if sfnt_offset < 0 or sfnt_offset + 12 > len(font_data):
            return None
        table_count = struct.unpack_from(">H", font_data, sfnt_offset + 4)[0]
        directory_end = sfnt_offset + 12 + table_count * 16
        if directory_end > len(font_data):
            return None
        for index in range(table_count):
            record = sfnt_offset + 12 + index * 16
            tag = font_data[record:record + 4]
            if tag != b"cmap":
                continue
            offset, length = struct.unpack_from(">II", font_data, record + 8)
            if offset + length > len(font_data) or length < 4:
                return None
            return font_data[offset:offset + length]
    except (IndexError, struct.error, OverflowError):
        return None
    return None


def _cmap_subtables(cmap: bytes) -> tuple[tuple[int, bytes], ...]:
    try:
        if len(cmap) < 4:
            return ()
        version, count = struct.unpack_from(">HH", cmap, 0)
        if version != 0 or 4 + count * 8 > len(cmap):
            return ()
        supported: list[tuple[int, bytes]] = []
        for index in range(count):
            record = 4 + index * 8
            platform, encoding, offset = struct.unpack_from(">HHI", cmap, record)
            if not (platform == 0 or (platform == 3 and encoding in (1, 10))):
                continue
            if offset + 2 > len(cmap):
                continue
            fmt = struct.unpack_from(">H", cmap, offset)[0]
            if fmt not in (4, 6, 12, 13) or offset + 4 > len(cmap):
                continue
            if fmt in (4, 6):
                length = struct.unpack_from(">H", cmap, offset + 2)[0]
            else:
                if offset + 8 > len(cmap):
                    continue
                length = struct.unpack_from(">I", cmap, offset + 4)[0]
            if length < 4 or offset + length > len(cmap):
                continue
            supported.append((fmt, cmap[offset:offset + length]))
        return tuple(supported)
    except (IndexError, struct.error, OverflowError):
        return ()


def _format4_has_glyph(subtable: bytes, codepoint: int) -> bool:
    try:
        if codepoint > 0xFFFF or len(subtable) < 16:
            return False
        seg_count = struct.unpack_from(">H", subtable, 6)[0] // 2
        if not seg_count:
            return False
        end_start = 14
        end_codes = struct.unpack_from(f">{seg_count}H", subtable, end_start)
        start_start = end_start + 2 * seg_count + 2
        start_codes = struct.unpack_from(f">{seg_count}H", subtable, start_start)
        delta_start = start_start + 2 * seg_count
        deltas = struct.unpack_from(f">{seg_count}h", subtable, delta_start)
        range_start = delta_start + 2 * seg_count
        range_offsets = struct.unpack_from(f">{seg_count}H", subtable, range_start)
        low, high = 0, seg_count
        while low < high:
            middle = (low + high) // 2
            if end_codes[middle] < codepoint:
                low = middle + 1
            else:
                high = middle
        segment = low
        if segment >= seg_count or codepoint < start_codes[segment]:
            return False
        range_offset = range_offsets[segment]
        if range_offset == 0:
            glyph = (codepoint + deltas[segment]) & 0xFFFF
        else:
            address = range_start + 2 * segment + range_offset + 2 * (codepoint - start_codes[segment])
            if address + 2 > len(subtable):
                return False
            glyph = struct.unpack_from(">H", subtable, address)[0]
            if glyph:
                glyph = (glyph + deltas[segment]) & 0xFFFF
        return glyph != 0
    except (IndexError, struct.error, OverflowError):
        return False


def _format6_has_glyph(subtable: bytes, codepoint: int) -> bool:
    try:
        if codepoint > 0xFFFF or len(subtable) < 10:
            return False
        first_code, entry_count = struct.unpack_from(">HH", subtable, 6)
        if 10 + entry_count * 2 > len(subtable) or not first_code <= codepoint < first_code + entry_count:
            return False
        glyph = struct.unpack_from(">H", subtable, 10 + (codepoint - first_code) * 2)[0]
        return glyph != 0
    except (IndexError, struct.error, OverflowError):
        return False


def _group_has_glyph(subtable: bytes, codepoint: int, *, constant: bool) -> bool:
    try:
        if len(subtable) < 16:
            return False
        groups = struct.unpack_from(">I", subtable, 12)[0]
        if 16 + groups * 12 > len(subtable):
            return False
        low, high = 0, groups
        while low < high:
            middle = (low + high) // 2
            start, end, _ = struct.unpack_from(">III", subtable, 16 + middle * 12)
            if end < codepoint:
                low = middle + 1
            else:
                high = middle
        if low >= groups:
            return False
        start, end, glyph = struct.unpack_from(">III", subtable, 16 + low * 12)
        if not start <= codepoint <= end:
            return False
        return (glyph if constant else glyph + codepoint - start) != 0
    except (IndexError, struct.error, OverflowError):
        return False


def _cmap_has_glyph(subtables: tuple[tuple[int, bytes], ...], codepoint: int) -> bool:
    for fmt, subtable in subtables:
        if fmt == 4 and _format4_has_glyph(subtable, codepoint):
            return True
        if fmt == 6 and _format6_has_glyph(subtable, codepoint):
            return True
        if fmt == 12 and codepoint > 0xFFFF and _group_has_glyph(subtable, codepoint, constant=False):
            return True
        if fmt == 13 and _group_has_glyph(subtable, codepoint, constant=True):
            return True
        if fmt in (12, 13) and codepoint <= 0xFFFF and _group_has_glyph(subtable, codepoint, constant=(fmt == 13)):
            return True
    return False


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


@lru_cache(maxsize=256)
def _font_subtables(font_path: str, modified_ns: int, byte_size: int) -> tuple[tuple[int, bytes], ...]:
    del modified_ns, byte_size  # Values key the cache so a replaced font is read again.
    try:
        cmap = _sfnt_cmap(Path(font_path).read_bytes())
    except OSError:
        return ()
    return _cmap_subtables(cmap) if cmap is not None else ()


def missing_glyphs(font_path: Path | str, text: str, *, size: int = 32) -> tuple[str, ...]:
    """Return every visible character absent from a font's Unicode cmap table."""
    del size  # Kept for compatibility with callers that used rendered-mask checks.
    characters = _visible_characters(text)
    if not characters:
        return ()
    path = Path(font_path)
    try:
        stat = path.stat()
    except OSError:
        return characters
    subtables = _font_subtables(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    if not subtables:
        return characters
    return tuple(char for char in characters if not _cmap_has_glyph(subtables, ord(char)))


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


def _is_approved_font_url(url: str) -> bool:
    parts = urlsplit(url)
    return (
        parts.scheme == "https"
        and parts.hostname == "raw.githubusercontent.com"
        and parts.port in (None, 443)
        and not parts.username
        and not parts.password
    )


class _ApprovedFontRedirectHandler(HTTPRedirectHandler):
    """Reject an unapproved redirect before urllib sends a request to it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        resolved = urljoin(req.full_url, newurl)
        if not _is_approved_font_url(resolved):
            raise FontNotFoundError("font download redirected outside the approved source")
        return super().redirect_request(req, fp, code, msg, headers, resolved)


def _fetch_bytes(url: str, *, max_bytes: int) -> bytes:
    if not _is_approved_font_url(url):
        raise FontNotFoundError("font download URL is not an approved HTTPS source")
    request = Request(url, headers={"User-Agent": "BrandLoom local font recovery"})
    try:
        opener = build_opener(_ApprovedFontRedirectHandler())
        with opener.open(request, timeout=30) as response:
            if not _is_approved_font_url(response.geturl()):
                raise FontNotFoundError("font download redirected outside the approved source")
            data = response.read(max_bytes + 1)
    except FontNotFoundError:
        raise
    except Exception as exc:
        raise FontNotFoundError(f"could not download the verified fallback font: {exc}") from exc
    if len(data) > max_bytes:
        raise FontNotFoundError("downloaded font resource exceeds its permitted size")
    return data


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_cached_fallback(directory: Path) -> Path | None:
    font_path = directory / _FALLBACK_FONT_NAME
    license_path = directory / "OFL-1.1.txt"
    provenance_path = directory / "font-provenance.json"
    try:
        font_bytes = font_path.read_bytes()
        license_bytes = license_path.read_bytes()
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        if _sha256(font_bytes) != _FALLBACK_FONT_SHA256 or _sha256(license_bytes) != _FALLBACK_LICENSE_SHA256:
            return None
        if not isinstance(provenance, dict) or (
            provenance.get("font_sha256") != _FALLBACK_FONT_SHA256
            or provenance.get("license_sha256") != _FALLBACK_LICENSE_SHA256
            or provenance.get("source_url") != _FALLBACK_FONT_URL
            or provenance.get("version") != _FALLBACK_VERSION
        ):
            return None
        ImageFont.truetype(str(font_path), size=16)
        return font_path
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def install_fallback_font(cache_dir: Path | str) -> Path:
    """Download and verify the pinned OFL fallback into an app-local cache."""
    cache_root = Path(cache_dir).expanduser().resolve()
    try:
        cache_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FontNotFoundError(f"cannot create the local font cache directory: {cache_root}") from exc
    base_name = f"noto-sans-cjk-sc-{_FALLBACK_VERSION}-{_FALLBACK_FONT_SHA256[:12]}"
    for existing_dir in sorted(cache_root.glob(f"{base_name}*")):
        existing = _valid_cached_fallback(existing_dir)
        if existing is not None:
            return existing

    font_bytes = _fetch_bytes(_FALLBACK_FONT_URL, max_bytes=_FALLBACK_FONT_SIZE)
    license_bytes = _fetch_bytes(_FALLBACK_LICENSE_URL, max_bytes=_MAX_LICENSE_SIZE)
    if len(font_bytes) != _FALLBACK_FONT_SIZE or _sha256(font_bytes) != _FALLBACK_FONT_SHA256:
        raise FontNotFoundError("downloaded fallback font failed its published size or SHA-256 check")
    if _sha256(license_bytes) != _FALLBACK_LICENSE_SHA256:
        raise FontNotFoundError("downloaded fallback font license failed its SHA-256 check")

    candidate = cache_root / base_name
    if candidate.exists():
        # Preserve an invalid existing cache entry; install the verified copy beside it.
        candidate = cache_root / f"{base_name}-recovered-{uuid.uuid4().hex[:8]}"
    try:
        with tempfile.TemporaryDirectory(prefix=".font-stage-", dir=cache_root) as staging_name:
            staging = Path(staging_name)
            staged_font = staging / _FALLBACK_FONT_NAME
            staged_font.write_bytes(font_bytes)
            ImageFont.truetype(str(staged_font), size=16)
            (staging / "OFL-1.1.txt").write_bytes(license_bytes)
            provenance = {
                "font_family": "Noto Sans CJK SC",
                "version": _FALLBACK_VERSION,
                "source_url": _FALLBACK_FONT_URL,
                "source_commit": _FALLBACK_COMMIT,
                "font_sha256": _FALLBACK_FONT_SHA256,
                "license": "SIL Open Font License 1.1",
                "license_url": _FALLBACK_LICENSE_URL,
                "license_sha256": _FALLBACK_LICENSE_SHA256,
            }
            (staging / "font-provenance.json").write_text(
                json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
            )
            staging.rename(candidate)
    except FontNotFoundError:
        raise
    except Exception as exc:
        raise FontNotFoundError(f"could not save the verified fallback font in the local cache: {exc}") from exc
    return candidate / _FALLBACK_FONT_NAME


def _profile_chain(profile_id: str | None, profiles: dict[str, FontProfile]) -> tuple[FontProfile, ...]:
    start_id = profile_id if profile_id in profiles else "microsoft-yahei-segoe"
    result: list[FontProfile] = []
    visited: set[str] = set()
    current_id = start_id
    while current_id in profiles and current_id not in visited:
        profile = profiles[current_id]
        visited.add(current_id)
        result.append(profile)
        current_id = profile.fallback_profile_id
    return tuple(result)


def _supports_text(path: Path, text: str) -> bool:
    if missing_glyphs(path, text):
        return False
    try:
        ImageFont.truetype(str(path), size=16)
    except (OSError, ValueError):
        return False
    return True


def resolve_font_for_text(
    profile_id: str | None,
    role: str,
    text: str,
    extra_roots: tuple[Path, ...],
    cache_dir: Path | str,
    explicit_path: Path | str | None = None,
) -> Path:
    """Use the confirmed font if possible, then local fallbacks, then a verified download."""
    if role not in _ROLES:
        raise ValueError(f"unsupported font role: {role}")
    if explicit_path is not None:
        explicit = Path(explicit_path).expanduser()
        if _supports_text(explicit, text):
            return explicit.resolve()
    profiles = load_font_profiles()
    chain = _profile_chain(profile_id, profiles)
    discovered = discover_font_files(extra_roots)
    candidates: list[Path] = []
    if explicit_path is not None:
        candidates.append(Path(explicit_path).expanduser())
    for profile in chain:
        for alias in profile.aliases[role]:
            candidates.extend(discovered.get(_family_key(alias), ()))
    # Search all installed fonts as a final local fallback before downloading.
    for paths in discovered.values():
        candidates.extend(paths)

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            path = candidate.resolve()
        except OSError:
            continue
        if path in seen:
            continue
        seen.add(path)
        if _supports_text(path, text):
            return path

    downloaded = install_fallback_font(cache_dir)
    missing = missing_glyphs(downloaded, text)
    if missing:
        characters = " ".join(repr(char) for char in missing)
        raise FontNotFoundError(
            f"the installed fallback font also lacks required characters: {characters}; "
            "the copy includes characters this verified font cannot render"
        )
    try:
        ImageFont.truetype(str(downloaded), size=16)
    except (OSError, ValueError) as exc:
        raise FontNotFoundError("the downloaded fallback font cannot be opened by Pillow") from exc
    return downloaded
