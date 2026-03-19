"""Shared utilities for all parsers."""

from __future__ import annotations

import json
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

_FILE_CACHE_LOCK = threading.Lock()
_JSONL_CACHE: OrderedDict[str, tuple[tuple[int, int], list[dict]]] = OrderedDict()
_JSONL_CACHE_MAX = 200


def _file_signature(path: Path) -> tuple[int, int]:
    st = path.stat()
    return st.st_size, int(st.st_mtime_ns)


def _read_json_lines(path: Path) -> list[dict]:
    key = str(path)
    try:
        signature = _file_signature(path)
    except OSError:
        with _FILE_CACHE_LOCK:
            _JSONL_CACHE.pop(key, None)
        return []

    with _FILE_CACHE_LOCK:
        cached = _JSONL_CACHE.get(key)
        if cached is not None and cached[0] == signature:
            _JSONL_CACHE.move_to_end(key)  # Mark as recently used
            return cached[1]

    rows: list[dict] = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for raw in fh:
                try:
                    obj = json.loads(raw)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except Exception:
        rows = []

    with _FILE_CACHE_LOCK:
        _JSONL_CACHE[key] = (signature, rows)
        _JSONL_CACHE.move_to_end(key)
        while len(_JSONL_CACHE) > _JSONL_CACHE_MAX:
            _JSONL_CACHE.popitem(last=False)

    return rows


# ── Result-level cache ──
# Avoids re-parsing + re-globbing when no files have changed.
# Each entry stores: (result, file_list, composite_sig, monotonic_time, time_range)
# Keyed by parser_name; time_range = (start_utc, now_utc) ensures different
# date ranges don't return stale results.

_RESULT_CACHE: dict[str, tuple] = {}
_RESULT_CACHE_LOCK = threading.Lock()
_RESCAN_INTERVAL = 10.0  # seconds before re-globbing directories

# Active time range — set by parse_all before invoking parsers.
_ACTIVE_RANGE: tuple | None = None


def set_active_range(start_utc, now_utc) -> None:
    """Set the current parse time range (called by parse_all)."""
    global _ACTIVE_RANGE
    _ACTIVE_RANGE = (str(start_utc), str(now_utc))


def _files_sig(paths: list[Path]) -> tuple:
    """Fast composite signature: (count, total_size, max_mtime_ns)."""
    count = 0
    total_size = 0
    max_mtime = 0
    for p in paths:
        try:
            st = os.stat(p)
            count += 1
            total_size += st.st_size
            mt = int(st.st_mtime_ns)
            if mt > max_mtime:
                max_mtime = mt
        except OSError:
            pass
    return (count, total_size, max_mtime)


_RESULT_HIT_FLAGS: dict[str, bool] = {}  # set per-call by result_cache_get


def result_cache_get(parser_name: str, watch_paths: list[Path]):
    """Return cached result if nothing changed, else None.

    Sets a per-parser hit flag so parse_all can report whether all parsers
    returned cached data (i.e. no data changed).
    """
    sig = _files_sig(watch_paths)
    with _RESULT_CACHE_LOCK:
        entry = _RESULT_CACHE.get(parser_name)
    if entry is not None and entry[2] == sig and entry[4] == _ACTIVE_RANGE:
        _RESULT_HIT_FLAGS[parser_name] = True
        return entry[0]
    _RESULT_HIT_FLAGS[parser_name] = False
    return None


def all_caches_hit() -> bool:
    """Return True if every parser hit its result cache on the last run."""
    return bool(_RESULT_HIT_FLAGS) and all(_RESULT_HIT_FLAGS.values())


def result_cache_set(parser_name: str, watch_paths: list[Path], result):
    """Store a parser result keyed on file signatures + time range."""
    sig = _files_sig(watch_paths)
    with _RESULT_CACHE_LOCK:
        _RESULT_CACHE[parser_name] = (result, watch_paths, sig, time.monotonic(), _ACTIVE_RANGE)


def result_cache_files(parser_name: str) -> list[Path] | None:
    """Return cached file list if recent enough (avoids rglob)."""
    with _RESULT_CACHE_LOCK:
        entry = _RESULT_CACHE.get(parser_name)
    if entry is None:
        return None
    _, file_list, _, cached_time, _ = entry
    if (time.monotonic() - cached_time) < _RESCAN_INTERVAL:
        return file_list
    return None


def _ts(raw):
    if not raw:
        return None
    s = str(raw)
    # Unix timestamp (integer or float, typically 10+ digits)
    if s.replace(".", "", 1).replace("-", "", 1).isdigit() and len(s.split(".")[0].lstrip("-")) >= 10:
        try:
            return datetime.fromtimestamp(float(s), tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            pass
    # Git-style date: "Thu Feb 12 15:44:45 2026 +0000"
    if len(s) > 20 and s[0].isalpha():
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(s)
        except Exception:
            pass
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _si(v):
    return int(v or 0)
