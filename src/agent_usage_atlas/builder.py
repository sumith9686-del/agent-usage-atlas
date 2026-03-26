"""Build single-file HTML dashboard from frontend/ directory files."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

_FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

_template_cache: str | None = None
_template_lock = threading.Lock()


def _read_frontend(relative_path: str) -> str:
    return (_FRONTEND_DIR / relative_path).read_text(encoding="utf-8")


def _frontend_subdir(category: str) -> Path:
    return _FRONTEND_DIR / category


def _assemble_template() -> str:
    """Read frontend/ files and assemble the HTML skeleton (CSS + JS)."""
    html_skeleton = _read_frontend("index.html")
    css = _read_frontend("styles/main.css")

    # Collect all JS files in dependency order
    js_parts: list[str] = []
    for category in ["lib", "components", "charts", "sections"]:
        subdir = _frontend_subdir(category)
        if subdir.is_dir():
            for f in sorted(subdir.iterdir()):
                if f.suffix == ".js":
                    js_parts.append(f.read_text(encoding="utf-8"))
    js = "\n".join(js_parts)

    # Guard against placeholder collisions in CSS source
    # (__DATA__ and __POLL_MS__ intentionally appear in JS as substitution targets)
    for _placeholder in ("__DATA__", "__POLL_MS__", "__LIVE_MODE__"):
        if _placeholder in css:
            raise ValueError(f"CSS must not contain {_placeholder} placeholder")

    return html_skeleton.replace("__CSS__", css).replace("__JS__", js)


def _get_template() -> str:
    """Return the assembled HTML skeleton, cached after first read (thread-safe)."""
    global _template_cache
    if _template_cache is not None:
        return _template_cache
    with _template_lock:
        if _template_cache is None:
            _template_cache = _assemble_template()
        return _template_cache


_PLACEHOLDER_RE = re.compile(r"__DATA__|__POLL_MS__|__LIVE_MODE__")


def build_html(data: dict | None = None, *, poll_interval_ms: int = 0, live: bool = False) -> str:
    """Build a complete self-contained HTML dashboard."""
    template = _get_template()

    # Precompute replacement values
    payload = "null" if data is None else json.dumps(data, ensure_ascii=False).replace("</", r"<\/")
    _ms = int(poll_interval_ms or 0)
    interval = str(max(1000, _ms) if _ms > 0 else 0)
    live_flag = "true" if live else "false"
    replacements = {"__DATA__": payload, "__POLL_MS__": interval, "__LIVE_MODE__": live_flag}

    # Single-pass replacement via re.sub callback — avoids 3 intermediate string copies
    return _PLACEHOLDER_RE.sub(lambda m: replacements[m.group()], template)
