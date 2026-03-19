"""Claude Code log parser."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from ..models import ParseResult, SessionMeta, ToolCall, TurnDuration, UsageEvent, UserMessage
from ._base import _file_signature, _read_json_lines, _si, _ts, result_cache_files, result_cache_get, result_cache_set

CLAUDE_HOME = Path.home() / ".claude"
CLAUDE_ROOT = CLAUDE_HOME / "projects"

# Per-file incremental cache: path_str -> (file_sig, events_dict, calls, metas, meta_seen, turn_durations, user_messages)
_PER_FILE_CACHE: dict[str, tuple] = {}
_PER_FILE_LOCK = threading.Lock()


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


def _parse_single_file(path: Path, start_utc, now_utc):
    """Parse a single JSONL file, returning per-file data structures."""
    objs = _read_json_lines(path)

    event_dedup = {}
    calls = []
    metas = []
    meta_seen = set()
    turn_durations = []
    user_messages = []

    # First pass for err_map
    err_map = {}
    for obj in objs:
        if obj.get("type") == "user":
            for blk in (obj.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_result":
                    err_map[blk.get("tool_use_id", "")] = bool(blk.get("is_error"))

    # Main pass
    for obj in objs:
        obj_type = obj.get("type")

        if obj_type == "user":
            sid = str(obj.get("sessionId") or path.stem)
            if sid not in meta_seen:
                meta_seen.add(sid)
                cwd = obj.get("cwd")
                br = obj.get("gitBranch")
                proj = Path(cwd).name if cwd and "/" in str(cwd) else str(cwd).rsplit("-", 1)[-1] if cwd else None
                metas.append(SessionMeta("Claude", sid, cwd, proj, br))
            ts = _ts(obj.get("timestamp"))
            if ts and start_utc <= ts <= now_utc:
                content = (obj.get("message") or {}).get("content")
                text_parts = []
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
                    user_messages.append(
                        UserMessage("Claude", ts, sid, full_text[:200], len(full_text))
                    )

        if obj_type == "system" and obj.get("subtype") == "turn_duration":
            dur = obj.get("durationMs")
            ts = _ts(obj.get("timestamp"))
            if dur and ts and start_utc <= ts <= now_utc:
                sid = str(obj.get("sessionId") or path.stem)
                turn_durations.append(TurnDuration("Claude", ts, sid, int(dur)))

        for pl in _claude_msgs(obj):
            msg, u = pl["message"], pl["message"].get("usage", {})
            ts = _ts(pl.get("timestamp"))
            if not ts or ts < start_utc or ts > now_utc:
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
            if prev is None or (ev.uncached_input, ev.cache_read, ev.cache_write, ev.output) > (
                prev.uncached_input,
                prev.cache_read,
                prev.cache_write,
                prev.output,
            ):
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
        if not ts or ts < start_utc or ts > now_utc:
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
            ec = 1 if err_map.get(blk.get("id", "")) else None
            calls.append(ToolCall("Claude", ts, sid, tn, ec, fp, cmd))

    return event_dedup, calls, metas, meta_seen, turn_durations, user_messages


def parse(start_utc, now_utc) -> ParseResult:
    """Incremental Claude parser — only re-parses files whose mtime changed."""
    if not CLAUDE_ROOT.exists():
        return ParseResult()

    all_files = result_cache_files("claude")
    if all_files is None:
        all_files = sorted(p for p in CLAUDE_ROOT.rglob("*.jsonl") if p.name != "sessions-index.json")

    # Try whole-result cache first (handles case where nothing changed)
    cached = result_cache_get("claude", all_files)
    if cached is not None:
        return cached

    # Per-file incremental parse: only re-parse changed files
    time_range_key = (str(start_utc), str(now_utc))
    merged_events = {}
    merged_calls = []
    merged_metas = []
    merged_meta_seen = set()
    merged_turn_durations = []
    merged_user_messages = []

    for path in all_files:
        path_key = str(path)
        try:
            sig = _file_signature(path)
        except OSError:
            continue

        # Check per-file cache
        with _PER_FILE_LOCK:
            cached_entry = _PER_FILE_CACHE.get(path_key)

        if cached_entry is not None and cached_entry[0] == sig and cached_entry[1] == time_range_key:
            ev_dict, calls, metas, meta_seen_set, turn_durs, user_msgs = cached_entry[2:]
        else:
            ev_dict, calls, metas, meta_seen_set, turn_durs, user_msgs = _parse_single_file(path, start_utc, now_utc)
            with _PER_FILE_LOCK:
                _PER_FILE_CACHE[path_key] = (sig, time_range_key, ev_dict, calls, metas, meta_seen_set, turn_durs, user_msgs)

        # Merge per-file results
        for key, ev in ev_dict.items():
            prev = merged_events.get(key)
            if prev is None or (ev.uncached_input, ev.cache_read, ev.cache_write, ev.output) > (
                prev.uncached_input,
                prev.cache_read,
                prev.cache_write,
                prev.output,
            ):
                merged_events[key] = ev
        merged_calls.extend(calls)
        for meta in metas:
            if meta.session_id not in merged_meta_seen:
                merged_meta_seen.add(meta.session_id)
                merged_metas.append(meta)
        merged_turn_durations.extend(turn_durs)
        merged_user_messages.extend(user_msgs)

    result = ParseResult(
        events=list(merged_events.values()),
        tool_calls=merged_calls,
        session_metas=merged_metas,
        turn_durations=merged_turn_durations,
        user_messages=merged_user_messages,
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
    except Exception:
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
