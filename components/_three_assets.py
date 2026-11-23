"""Offline Three.js r128 script loader for standalone desktop & air-gapped HTML viewers."""

from functools import lru_cache
from pathlib import Path
import sys

_CDN_FALLBACK = (
    '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n'
    '  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>'
)


def _base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def get_three_script_tags() -> str:
    """Return inline <script> tags for bundled Three.js r128 + OrbitControls (offline-safe)."""
    js_dir = _base_dir() / "assets" / "js"
    three_path = js_dir / "three.min.js"
    orbit_path = js_dir / "OrbitControls.js"

    if not (three_path.is_file() and orbit_path.is_file()):
        return _CDN_FALLBACK

    three_js = three_path.read_text(encoding="utf-8").replace("</script>", r"<\/script>")
    orbit_js = orbit_path.read_text(encoding="utf-8").replace("</script>", r"<\/script>")
    return f"<script>\n{three_js}\n  </script>\n  <script>\n{orbit_js}\n  </script>"
