"""Claude Code log parser."""

from __future__ import annotations

import json
import os
import threading
import warnings
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from ..models import ParseResult, SessionMeta, ToolCall, TurnDuration, UsageEvent, UserMessage
from ._base import (
    _file_signature,
    _read_json_lines,
    _si,
    _ts,
    result_cache_files,
    result_cache_get,
    result_cache_set,
)

CLAUDE_HOME = Path.home() / ".claude"
CLAUDE_ROOT = CLAUDE_HOME / "projects"

# Per-file incremental cache:
# path_str -> (file_sig, events_dict, calls, metas, meta_seen, turn_durations, user_messages)
_PER_FILE_CACHE: OrderedDict[str, tuple] = OrderedDict()
_PER_FILE_CACHE_MAX = 200
_PER_FILE_LOCK = threading.Lock()


def _token_key(ev: UsageEvent) -> tuple[int, int, int, int]:
    return (ev.uncached_input, ev.cache_read, ev.cache_write, ev.output)


def _claude_msgs(obj):
    out = []
    m = obj.get("message")
    if isinstance(m, dict) and isinstance(m.get("usage"), dict):
        out.append({"message": m, "timestamp": obj.get("timestamp"), "sessionId": obj.get("sessionId")})
    d = obj.get("data")
    if isinstance(d, dict):
        mw = d.get("message")
        if isinstance(mw, dict):
            nm = mw.get("message")
            if isinstance(nm, dict) and isinstance(nm.get("usage"), dict):
                out.append(
                    {
                        "message": nm,
                        "timestamp": mw.get("timestamp") or obj.get("timestamp"),
                        "sessionId": obj.get("sessionId"),
                    }
                )
    return out


def _parse_single_file(
    path: Path,
) -> tuple[dict, list[ToolCall], list[SessionMeta], set[str], list[TurnDuration], list[UserMessage]]:
    """Parse a single JSONL file, returning per-file data structures.

    No time-range filtering is applied here so the result can be cached
    across different date-range requests.
    """
    objs = _read_json_lines(path)

    event_dedup: dict[tuple[str, str], UsageEvent] = {}
    calls: list[ToolCall] = []
    metas: list[SessionMeta] = []
    meta_seen: set[str] = set()
    turn_durations: list[TurnDuration] = []
    user_messages: list[UserMessage] = []
    err_set: set[str] = set()  # tool_use_ids that had errors

    # Single pass: build err_set and process events simultaneously.
    # Tool-result blocks in "user" messages always appear before the
    # assistant response that references them, so err_set is populated
    # in time for the tool_use block lookup below.
    for obj in objs:
        obj_type = obj.get("type")

        if obj_type == "user":
            # Build err_set inline (replaces the old separate first pass)
            for blk in (obj.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_result" and blk.get("is_error"):
                    err_set.add(blk.get("tool_use_id", ""))
            sid = str(obj.get("sessionId") or path.stem)
            if sid not in meta_seen:
                meta_seen.add(sid)
                cwd = obj.get("cwd")
                br = obj.get("gitBranch")
                proj = (Path(cwd).name or None) if cwd and "/" in str(cwd) else str(cwd).rsplit("-", 1)[-1] if cwd else None
                metas.append(SessionMeta("Claude", sid, cwd, proj, br))
            ts = _ts(obj.get("timestamp"))
            if ts:
                content = (obj.get("message") or {}).get("content")
                text_parts: list[str] = []
                if isinstance(content, str):
                    text_parts.append(content)
                elif isinstance(content, list):
                    for blk in content:
                        if isinstance(blk, dict) and blk.get("type") == "text":
                            text_parts.append(blk.get("text", ""))
                        elif isinstance(blk, str):
                            text_parts.append(blk)
                full_text = " ".join(text_parts).strip()
                if full_text:
                    user_messages.append(UserMessage("Claude", ts, sid, full_text[:200], len(full_text)))

        if obj_type == "system" and obj.get("subtype") == "turn_duration":
            dur = obj.get("durationMs")
            ts = _ts(obj.get("timestamp"))
            if dur is not None and ts:
                sid = str(obj.get("sessionId") or path.stem)
                turn_durations.append(TurnDuration("Claude", ts, sid, _si(dur)))

        for pl in _claude_msgs(obj):
            msg, u = pl["message"], pl["message"].get("usage", {})
            ts = _ts(pl.get("timestamp"))
            if not ts:
                continue
            mid = str(msg.get("id") or obj.get("uuid") or pl.get("timestamp"))
            sid = str(pl.get("sessionId") or obj.get("sessionId") or path.stem)
            ev = UsageEvent(
                "Claude",
                ts,
                sid,
                str(msg.get("model") or "Claude"),
                _si(u.get("input_tokens")),
                _si(u.get("cache_read_input_tokens")),
                _si(u.get("cache_creation_input_tokens")),
                _si(u.get("output_tokens")),
                0,
                1,
            )
            key = (sid, mid)
            prev = event_dedup.get(key)
            if prev is None or _token_key(ev) > _token_key(prev):
                event_dedup[key] = ev

        msg = None
        if obj_type == "assistant":
            msg = obj.get("message", {})
        else:
            m = obj.get("message")
            if isinstance(m, dict) and m.get("role") == "assistant":
                msg = m
        if not isinstance(msg, dict):
            continue
        ts = _ts(obj.get("timestamp"))
        if not ts:
            continue
        sid = str(obj.get("sessionId") or path.stem)
        for blk in msg.get("content") or []:
            if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                continue
            tn, inp = blk.get("name", "unknown"), blk.get("input") or {}
            if not isinstance(inp, dict):
                inp = {}
            cmd = inp.get("command") if tn in ("Bash", "bash") else None
            fp = (
                inp.get("file_path")
                if tn in ("Read", "Write", "Edit")
                else inp.get("path")
                if tn in ("Grep", "Glob")
                else None
            )
            ec = 1 if blk.get("id", "") in err_set else None
            calls.append(ToolCall("Claude", ts, sid, tn, ec, fp, cmd))

    return event_dedup, calls, metas, meta_seen, turn_durations, user_messages


def _process_one_file(path: Path):
    """Parse or retrieve cached result for a single file (thread-safe).

    Check order: in-memory cache → full parse.
    """
    path_key = str(path)
    try:
        sig = _file_signature(path)
    except OSError:
        return None

    # 1. In-memory cache
    with _PER_FILE_LOCK:
        cached_entry = _PER_FILE_CACHE.get(path_key)
        if cached_entry is not None:
            _PER_FILE_CACHE.move_to_end(path_key)

    if cached_entry is not None and cached_entry[0] == sig:
        return cached_entry[1:]

    # 2. Full parse
    result = _parse_single_file(path)
    entry = (sig, *result)

    with _PER_FILE_LOCK:
        _PER_FILE_CACHE[path_key] = entry
        _PER_FILE_CACHE.move_to_end(path_key)
        while len(_PER_FILE_CACHE) > _PER_FILE_CACHE_MAX:
            _PER_FILE_CACHE.popitem(last=False)

    return result


def _safe_mtime(path: Path) -> float:
    """Return file mtime or 0 on error."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def parse(start_utc: datetime, now_utc: datetime, *, mtime_floor: datetime | None = None) -> ParseResult:
    """Incremental Claude parser with mtime filtering and parallel I/O."""
    if not CLAUDE_ROOT.exists():
        return ParseResult()

    all_files = result_cache_files("claude")
    if all_files is None:
        all_files = sorted(p for p in CLAUDE_ROOT.rglob("*.jsonl") if p.name != "sessions-index.json")

    # Optimization: skip files not modified since before the requested range.
    if mtime_floor is not None:
        cutoff = (mtime_floor - timedelta(hours=1)).timestamp()
        all_files = [f for f in all_files if _safe_mtime(f) >= cutoff]

    # Try whole-result in-memory cache first
    cached = result_cache_get("claude", all_files)
    if cached is not None:
        return cached

    # Parallel per-file parse — each file checks memory → full parse
    workers = min(8, len(all_files)) or 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        file_results = list(pool.map(_process_one_file, all_files))

    # Merge per-file results
    merged_events: dict[tuple[str, str], UsageEvent] = {}
    merged_calls: list[ToolCall] = []
    merged_metas: list[SessionMeta] = []
    merged_meta_seen: set[str] = set()
    merged_turn_durations: list[TurnDuration] = []
    merged_user_messages: list[UserMessage] = []

    for file_result in file_results:
        if file_result is None:
            continue
        ev_dict, calls, metas, meta_seen_set, turn_durs, user_msgs = file_result
        for key, ev in ev_dict.items():
            prev = merged_events.get(key)
            if prev is None or _token_key(ev) > _token_key(prev):
                merged_events[key] = ev
        merged_calls.extend(calls)
        for meta in metas:
            if meta.session_id not in merged_meta_seen:
                merged_meta_seen.add(meta.session_id)
                merged_metas.append(meta)
        merged_turn_durations.extend(turn_durs)
        merged_user_messages.extend(user_msgs)

    # Apply time-range filtering after merge (keeps per-file cache range-agnostic)
    filtered_events = [ev for ev in merged_events.values() if start_utc <= ev.timestamp <= now_utc]
    filtered_calls = [c for c in merged_calls if start_utc <= c.timestamp <= now_utc]
    filtered_turn_durations = [td for td in merged_turn_durations if start_utc <= td.timestamp <= now_utc]
    filtered_user_messages = [um for um in merged_user_messages if start_utc <= um.timestamp <= now_utc]

    result = ParseResult(
        events=filtered_events,
        tool_calls=filtered_calls,
        session_metas=merged_metas,
        turn_durations=filtered_turn_durations,
        user_messages=filtered_user_messages,
    )
    result_cache_set("claude", all_files, result)

    return result


def parse_stats_cache():
    """Parse ~/.claude/stats-cache.json for daily activity and model token stats."""
    cache_path = CLAUDE_HOME / "stats-cache.json"
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        warnings.warn(f"Failed to read stats-cache.json: {exc}", stacklevel=2)
        return {}
    return {
        "daily_activity": raw.get("dailyActivity", []),
        "daily_model_tokens": raw.get("dailyModelTokens", []),
        "model_usage": raw.get("modelUsage", {}),
        "longest_session": raw.get("longestSession"),
        "hour_counts": raw.get("hourCounts", []),
        "total_sessions": raw.get("totalSessions", 0),
        "total_messages": raw.get("totalMessages", 0),
        "first_session_date": raw.get("firstSessionDate"),
    }
