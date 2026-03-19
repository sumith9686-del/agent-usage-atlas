"""Codex CLI log parser."""

from __future__ import annotations

import json
import re
import sqlite3
import warnings
from collections import defaultdict
from pathlib import Path

from ..models import ParseResult, SessionMeta, TaskEvent, ToolCall, TurnDuration, UsageEvent, UserMessage
from ._base import _read_json_lines, _si, _ts, result_cache_files, result_cache_get, result_cache_set

CODEX_ROOTS = [Path.home() / ".codex/archived_sessions", Path.home() / ".codex/sessions"]
CODEX_HOME = Path.home() / ".codex"

_ECR = re.compile(r"Process exited with code (\d+)")


def parse(start_utc, now_utc) -> ParseResult:
    """Single-pass Codex parser."""
    # Collect all JSONL + DB files for cache signature
    watch = result_cache_files("codex")
    if watch is None:
        watch = []
        for root in CODEX_ROOTS:
            if root.exists():
                watch.extend(sorted(root.rglob("*.jsonl")))
        state_db = CODEX_HOME / "state_5.sqlite"
        for db in [CODEX_HOME / "codex.db", state_db]:
            if db.exists():
                watch.append(db)
    cached = result_cache_get("codex", watch)
    if cached is not None:
        return cached

    ses = defaultdict(list)
    calls = []
    metas, meta_seen = [], set()
    task_events = []
    turn_durations = []
    user_messages = []

    # SQLite meta + session durations
    for root in CODEX_ROOTS:
        db = root.parent / "codex.db"
        if db.exists():
            try:
                with sqlite3.connect(str(db)) as conn:
                    for r in conn.execute("SELECT id,cwd,git_branch FROM threads").fetchall():
                        sid, cwd, br = str(r[0]), r[1], r[2]
                        metas.append(SessionMeta("Codex", sid, cwd, Path(cwd).name if cwd else None, br))
                        meta_seen.add(sid)
            except Exception as exc:
                warnings.warn(f"Codex codex.db read failed: {exc}", stacklevel=2)

    state_db = CODEX_HOME / "state_5.sqlite"
    if state_db.exists():
        try:
            conn = sqlite3.connect(str(state_db))
            for r in conn.execute(
                "SELECT id, cwd, git_branch, created_at, updated_at, tokens_used, source FROM threads"
            ).fetchall():
                sid = str(r[0])
                if sid not in meta_seen:
                    cwd, br = r[1], r[2]
                    metas.append(SessionMeta("Codex", sid, cwd, Path(cwd).name if cwd else None, br))
                    meta_seen.add(sid)
                created, updated = r[3], r[4]
                if created and updated:
                    try:
                        t0 = _ts(created)
                        t1 = _ts(updated)
                        if t0 and t1 and t1 > t0 and start_utc <= t0 <= now_utc:
                            dur_ms = int((t1 - t0).total_seconds() * 1000)
                            if dur_ms > 0:
                                turn_durations.append(TurnDuration("Codex", t0, sid, dur_ms))
                    except Exception as exc:
                        warnings.warn(f"Codex turn duration parse failed for {sid}: {exc}", stacklevel=2)
            conn.close()
        except Exception as exc:
            warnings.warn(f"Codex state_5.sqlite read failed: {exc}", stacklevel=2)

    # Single iteration over each JSONL file
    for root in CODEX_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.jsonl"):
            sid, token_seen, model_name = None, {}, "GPT-5 Codex"
            pending_calls = {}

            for obj in _read_json_lines(path):
                obj_type = obj.get("type")
                pl = obj.get("payload") or {}

                if obj_type == "session_meta":
                    sid = str(pl.get("id") or path.stem)
                    if sid not in meta_seen:
                        cwd = pl.get("cwd")
                        metas.append(
                            SessionMeta("Codex", sid, cwd, Path(cwd).name if cwd else None, pl.get("git_branch"))
                        )
                        meta_seen.add(sid)
                    continue

                if obj_type == "turn_context":
                    m = pl.get("model")
                    if isinstance(m, str) and m.strip():
                        model_name = m.strip()
                    cm = pl.get("collaboration_mode")
                    if isinstance(cm, dict):
                        ms = (cm.get("settings") or {}).get("model")
                        if isinstance(ms, str) and ms.strip():
                            model_name = ms.strip()
                    continue

                if obj_type != "event_msg":
                    continue

                pl_type = pl.get("type")
                ts = _ts(obj.get("timestamp"))
                if not ts:
                    continue
                s = sid or path.stem

                if pl_type == "token_count":
                    u = (pl.get("info") or {}).get("total_token_usage")
                    if isinstance(u, dict):
                        cur = {
                            "ts": ts,
                            "input": _si(u.get("input_tokens")),
                            "cached": _si(u.get("cached_input_tokens")),
                            "output": _si(u.get("output_tokens")),
                            "reasoning": _si(u.get("reasoning_output_tokens")),
                            "model": model_name or "GPT-5 Codex",
                        }
                        prev = token_seen.get(ts)
                        if prev is None or (cur["input"], cur["cached"], cur["output"], cur["reasoning"]) > (
                            prev["input"],
                            prev["cached"],
                            prev["output"],
                            prev["reasoning"],
                        ):
                            token_seen[ts] = cur

                elif pl_type == "response_item":
                    item = pl.get("item") or pl
                    it = item.get("type", "")
                    if it == "function_call":
                        cid = item.get("call_id") or item.get("id", "")
                        try:
                            args = json.loads(item.get("arguments", "") or "{}")
                        except Exception:
                            args = {}
                        tc = ToolCall(
                            "Codex",
                            ts,
                            s,
                            item.get("name", "unknown"),
                            command=args.get("command") or args.get("cmd"),
                            file_path=args.get("file_path") or args.get("path"),
                        )
                        if cid:
                            pending_calls[cid] = tc
                        if start_utc <= ts <= now_utc:
                            calls.append(tc)
                    elif it == "function_call_output":
                        m = _ECR.search(str(item.get("output", "")))
                        cid = item.get("call_id", "")
                        if m and cid in pending_calls:
                            pending_calls[cid].exit_code = int(m.group(1))
                    elif it == "web_search_call":
                        if start_utc <= ts <= now_utc:
                            calls.append(ToolCall("Codex", ts, s, "web_search"))

                elif pl_type == "custom_tool_call":
                    cid = pl.get("id", "")
                    tc = ToolCall("Codex", ts, s, pl.get("name", "custom_tool"))
                    if cid:
                        pending_calls[cid] = tc
                    if start_utc <= ts <= now_utc:
                        calls.append(tc)

                elif pl_type == "custom_tool_call_output":
                    cid, md = pl.get("id", ""), pl.get("metadata")
                    if isinstance(md, dict) and cid in pending_calls:
                        ec = md.get("exit_code")
                        if ec is not None:
                            try:
                                pending_calls[cid].exit_code = int(ec)
                            except (ValueError, TypeError):
                                pass

                elif pl_type == "message":
                    # User input message
                    role = pl.get("role")
                    if role == "user" and start_utc <= ts <= now_utc:
                        content = pl.get("content")
                        text_parts = []
                        if isinstance(content, str):
                            text_parts.append(content)
                        elif isinstance(content, list):
                            for blk in content:
                                if isinstance(blk, dict) and blk.get("type") == "input_text":
                                    text_parts.append(blk.get("text", ""))
                                elif isinstance(blk, str):
                                    text_parts.append(blk)
                        full_text = " ".join(text_parts).strip()
                        if full_text:
                            user_messages.append(
                                UserMessage(
                                    "Codex",
                                    ts,
                                    s,
                                    full_text[:200],
                                    len(full_text),
                                )
                            )

                elif pl_type in ("task_started", "task_complete"):
                    if start_utc <= ts <= now_utc:
                        etype = "started" if pl_type == "task_started" else "complete"
                        task_events.append(TaskEvent("Codex", ts, s, etype))

            if token_seen:
                ses[sid or str(path)].extend(token_seen.values())

    # Build cumulative-delta events
    events = []
    for sid, rows in ses.items():
        bl = {"input": 0, "cached": 0, "output": 0, "reasoning": 0}
        for r in sorted(rows, key=lambda x: x["ts"]):
            if r["ts"] < start_utc:
                bl = r
                continue
            events.append(
                UsageEvent(
                    "Codex",
                    r["ts"],
                    sid,
                    str(r.get("model") or "GPT-5 Codex"),
                    max(0, r["input"] - bl["input"] - (r["cached"] - bl["cached"])),
                    max(0, r["cached"] - bl["cached"]),
                    0,
                    max(0, r["output"] - bl["output"]),
                    max(0, r["reasoning"] - bl["reasoning"]),
                    1,
                )
            )
            bl = r

    result = ParseResult(
        events=events,
        tool_calls=calls,
        session_metas=metas,
        turn_durations=turn_durations,
        task_events=task_events,
        user_messages=user_messages,
    )
    result_cache_set("codex", watch, result)
    return result
