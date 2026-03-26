"""Shared utilities for all parsers."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

_FILE_CACHE_LOCK = threading.Lock()
_JSONL_CACHE: OrderedDict[str, tuple[tuple[int, int], str, list[dict]]] = OrderedDict()
_JSONL_CACHE_MAX = 200

# ── Disk cache dir ──
_DISK_CACHE_DIR = Path.home() / ".cache" / "agent-usage-atlas"
_DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)

# ── Compressed log support ──


def _open_smart(path: Path):
    """Open plain or gzip-compressed files transparently."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, encoding="utf-8", errors="ignore")


# ── Content-addressable cache helpers ──


def _content_hash(path: Path) -> str:
    """Compute blake2b hash of file content for change verification."""
    h = hashlib.blake2b(digest_size=16)
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


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
            _JSONL_CACHE.move_to_end(key)
            return cached[2]

    # Fast signature changed — check content hash before invalidating
    if cached is not None:
        try:
            chash = _content_hash(path)
        except OSError:
            chash = ""
        if chash and chash == cached[1]:
            with _FILE_CACHE_LOCK:
                # Only write back if no other thread has already updated this entry.
                current = _JSONL_CACHE.get(key)
                if current is not None and current[0] == cached[0]:
                    _JSONL_CACHE[key] = (signature, chash, cached[2])
                    _JSONL_CACHE.move_to_end(key)
            return cached[2]

    rows: list[dict] = []
    skipped = 0
    try:
        with _open_smart(path) as fh:
            for raw in fh:
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except OSError:
        rows = []

    # Content hash: only compute when a previous cache entry exists (enables
    # "mtime changed but content unchanged" fast-path on future checks).
    # On cold start (cached is None) skip the extra file read entirely.
    if cached is not None and (rows or skipped):
        try:
            chash = _content_hash(path)
        except OSError:
            chash = ""
    else:
        chash = ""

    with _FILE_CACHE_LOCK:
        _JSONL_CACHE[key] = (signature, chash, rows)
        _JSONL_CACHE.move_to_end(key)
        while len(_JSONL_CACHE) > _JSONL_CACHE_MAX:
            _JSONL_CACHE.popitem(last=False)

    return rows


# ── Result-level cache ──
# Avoids re-parsing + re-globbing when no files have changed.
# Each entry stores: (result, file_list, composite_sig, monotonic_time)
# Keyed by parser_name.  Parsing always uses a fixed wide range so the
# cache is reusable across different time-range requests; the actual
# user-requested range is applied as a post-parse filter.

_RESULT_CACHE: dict[str, tuple] = {}
_RESULT_CACHE_LOCK = threading.Lock()
_RESCAN_INTERVAL = 10.0  # seconds before re-globbing directories


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
_RESULT_HIT_FLAGS_LOCK = threading.Lock()


def result_cache_get(parser_name: str, watch_paths: list[Path]) -> Any | None:
    """Return cached result if nothing changed, else None.

    Sets a per-parser hit flag so parse_all can report whether all parsers
    returned cached data (i.e. no data changed).
    """
    sig = _files_sig(watch_paths)
    with _RESULT_CACHE_LOCK:
        entry = _RESULT_CACHE.get(parser_name)
    if entry is not None and entry[2] == sig:
        with _RESULT_HIT_FLAGS_LOCK:
            _RESULT_HIT_FLAGS[parser_name] = True
        return entry[0]
    with _RESULT_HIT_FLAGS_LOCK:
        _RESULT_HIT_FLAGS[parser_name] = False
    return None


def all_caches_hit() -> bool:
    """Return True if every parser hit its result cache on the last run."""
    with _RESULT_HIT_FLAGS_LOCK:
        return bool(_RESULT_HIT_FLAGS) and all(_RESULT_HIT_FLAGS.values())


def result_cache_set(parser_name: str, watch_paths: list[Path], result: Any) -> None:
    """Store a parser result keyed on file signatures."""
    sig = _files_sig(watch_paths)
    with _RESULT_CACHE_LOCK:
        _RESULT_CACHE[parser_name] = (result, watch_paths, sig, time.monotonic())


def result_cache_files(parser_name: str) -> list[Path] | None:
    """Return cached file list if recent enough (avoids rglob)."""
    with _RESULT_CACHE_LOCK:
        entry = _RESULT_CACHE.get(parser_name)
    if entry is None:
        return None
    _, file_list, _, cached_time = entry
    if (time.monotonic() - cached_time) < _RESCAN_INTERVAL:
        return file_list
    return None


def _ts(raw: object) -> datetime | None:
    if not raw:
        return None
    s = raw if isinstance(raw, str) else str(raw)
    # Unix timestamp (integer or float, typically 10+ digits)
    # Avoid intermediate string copies: check first char is digit or '-'
    c0 = s[0]
    if c0.isdigit() or (c0 == "-" and len(s) > 1):
        stripped = s.lstrip("-")
        dot_pos = stripped.find(".")
        int_part = stripped[:dot_pos] if dot_pos >= 0 else stripped
        if int_part.isdigit() and len(int_part) >= 10:
            try:
                return datetime.fromtimestamp(float(s), tz=timezone.utc)
            except (ValueError, OSError, OverflowError):
                pass
    # Git-style date: "Thu Feb 12 15:44:45 2026 +0000"
    if len(s) > 20 and s[0].isalpha():
        try:
            return parsedate_to_datetime(s)
        except (TypeError, ValueError):
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _si(v: object) -> int:
    if isinstance(v, bool):
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0
    return 0
