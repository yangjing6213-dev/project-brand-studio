from pathlib import Path
from functools import lru_cache

from PIL import ImageFont

from brandloom.scripts.brandloom_core.fonts import discover_font_files


@lru_cache(maxsize=1)
def find_test_font() -> Path:
    """Return a real readable platform font, failing loudly when CI has none."""
    for paths in discover_font_files().values():
        for path in paths:
            try:
                ImageFont.truetype(str(path), size=16)
            except (OSError, ValueError):
                continue
            return path
    raise AssertionError("no readable cross-platform system font is available")
