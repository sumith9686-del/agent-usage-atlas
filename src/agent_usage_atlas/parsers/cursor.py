"""Cursor log parser."""

from __future__ import annotations

import sqlite3
import warnings
from datetime import datetime, timezone
from pathlib import Path

from ..models import CodeGenRecord, ParseResult, ScoredCommit, UsageEvent
from ._base import _read_json_lines, _si, _ts, result_cache_files, result_cache_get, result_cache_set

CURSOR_ROOT = Path.home() / ".cursor/projects"
CURSOR_DB = Path.home() / ".cursor/ai-tracking/ai-code-tracking.db"


def parse(start_utc, now_utc, local_tz=None) -> ParseResult:
    """Parse Cursor agent transcripts and AI code tracking DB."""
    watch = result_cache_files("cursor")
    if watch is None:
        watch = []
        if CURSOR_ROOT.exists():
            watch.extend(sorted(p for p in CURSOR_ROOT.rglob("*.jsonl") if "agent-transcripts" in str(p)))
        if CURSOR_DB.exists():
            watch.append(CURSOR_DB)
    cached = result_cache_get("cursor", watch)
    if cached is not None:
        return cached

    events = []
    if CURSOR_ROOT.exists():
        for path in CURSOR_ROOT.rglob("*.jsonl"):
            if "agent-transcripts" not in str(path):
                continue
            try:
                st = path.stat()
                # Use birthtime (creation) as session start on macOS;
                # fall back to mtime on Linux where birthtime is unavailable.
                btime_ts = getattr(st, "st_birthtime", None) or st.st_mtime
                session_start = datetime.fromtimestamp(btime_ts, tz=timezone.utc)
                session_end = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
            except Exception as exc:
                warnings.warn(f"Cursor transcript stat failed for {path}: {exc}", stacklevel=2)
                continue
            # Session overlaps requested range if it started before range end
            # AND ended after range start.
            if session_end < start_utc or session_start > now_utc:
                continue
            uc, ac = 0, 0
            for obj in _read_json_lines(path):
                r = obj.get("role") if isinstance(obj, dict) else None
                if r == "user":
                    uc += 1
                elif r == "assistant":
                    ac += 1
            if uc or ac:
                events.append(UsageEvent("Cursor", session_start, path.stem, "Cursor Agent", activity_messages=uc + ac))

    code_gen, scored = _parse_codegen(start_utc, now_utc)

    result = ParseResult(
        events=events,
        code_gen=code_gen,
        scored_commits=scored,
    )
    result_cache_set("cursor", watch, result)
    return result


def _parse_codegen(start_utc, now_utc):
    """Parse Cursor ai-code-tracking.db for code generation records and scored commits."""
    code_gen: list[CodeGenRecord] = []
    scored: list[ScoredCommit] = []
    if not CURSOR_DB.exists():
        return code_gen, scored
    conn = None
    try:
        conn = sqlite3.connect(str(CURSOR_DB))
        for r in conn.execute(
            "SELECT timestamp, model, fileExtension, conversationId, source "
            "FROM ai_code_hashes WHERE timestamp IS NOT NULL"
        ).fetchall():
            try:
                ts_ms = int(r[0])
                ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                continue
            if ts < start_utc or ts > now_utc:
                continue
            model = r[1] or "unknown"
            ext = r[2] or ""
            cid = r[3] or ""
            src = r[4] or "composer"
            code_gen.append(CodeGenRecord("Cursor", ts, model, ext, cid, src))
        for r in conn.execute(
            "SELECT commitHash, commitDate, linesAdded, linesDeleted, "
            "composerLinesAdded, composerLinesDeleted, "
            "humanLinesAdded, humanLinesDeleted, "
            "tabLinesAdded, tabLinesDeleted "
            "FROM scored_commits"
        ).fetchall():
            commit_date = None
            if r[1]:
                try:
                    commit_date = _ts(r[1])
                except Exception as exc:
                    warnings.warn(f"Cursor commit date parse failed: {exc}", stacklevel=2)
            if commit_date and (commit_date < start_utc or commit_date > now_utc):
                continue
            scored.append(
                ScoredCommit(
                    commit_hash=r[0] or "",
                    commit_date=commit_date,
                    lines_added=_si(r[2]),
                    lines_deleted=_si(r[3]),
                    composer_added=_si(r[4]),
                    composer_deleted=_si(r[5]),
                    human_added=_si(r[6]),
                    human_deleted=_si(r[7]),
                    tab_added=_si(r[8]),
                    tab_deleted=_si(r[9]),
                )
            )
    except Exception as exc:
        warnings.warn(f"Cursor ai-code-tracking.db read failed: {exc}", stacklevel=2)
    finally:
        if conn is not None:
            conn.close()
    return code_gen, scored
