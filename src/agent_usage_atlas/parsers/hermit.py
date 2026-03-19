"""Hermit agent log parser."""

from __future__ import annotations

import json
import sqlite3
import warnings
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ..models import ParseResult, SessionMeta, ToolCall, UsageEvent, UserMessage
from ._base import _si, result_cache_get, result_cache_set

_HERMIT_DIRS = [".hermit", ".hermit-test", ".hermit-dev"]
_HERMIT_SUFFIXES = ["", "-test", "-dev"]

HERMIT_HOMES = [Path.home() / d for d in _HERMIT_DIRS]
HERMIT_ROOTS = [h / "kernel" / "state.db" for h in HERMIT_HOMES]

def _epoch_ts(raw) -> datetime | None:
    """Convert a Unix epoch float to a UTC datetime."""
    if raw is None:
        return None
    try:
        return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


_ACTION_MAP = {
    "execute_command": "bash",
    "write_local": "write",
    "memory_write": "memory",
    "approval_resolution": "approval",
}


def _read_config_model(home: Path) -> str:
    """Read default model from config.toml, fallback to claude-sonnet-4-6."""
    cfg = home / "config.toml"
    if not cfg.exists():
        return "claude-sonnet-4-6"
    try:
        import tomllib

        with open(cfg, "rb") as f:
            data = tomllib.load(f)
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]

            with open(cfg, "rb") as f:
                data = tomllib.load(f)
        except ImportError:
            return "claude-sonnet-4-6"
    except Exception as exc:
        warnings.warn(f"Hermit config.toml read failed: {exc}", stacklevel=2)
        return "claude-sonnet-4-6"

    default_profile = data.get("default_profile", "")
    profiles = data.get("profiles", {})
    if default_profile and default_profile in profiles:
        return profiles[default_profile].get("model", "claude-sonnet-4-6")
    # Try first profile
    for prof in profiles.values():
        if isinstance(prof, dict) and "model" in prof:
            return prof["model"]
    return data.get("model", "claude-sonnet-4-6")


def parse(start_utc: datetime, now_utc: datetime) -> ParseResult:
    """Parse Hermit agent logs from all home directories."""
    watch = [p for p in HERMIT_ROOTS if p.exists()]
    # SQLite WAL files receive writes before the main db — watch them too
    for root in HERMIT_ROOTS:
        wal = root.parent / (root.name + "-wal")
        if wal.exists():
            watch.append(wal)
    cached = result_cache_get("hermit", watch)
    if cached is not None:
        return cached

    events: list[UsageEvent] = []
    tool_calls: list[ToolCall] = []
    session_metas: list[SessionMeta] = []
    user_messages: list[UserMessage] = []

    for home in HERMIT_HOMES:
        source = "Hermit"
        db_path = home / "kernel" / "state.db"
        if not db_path.exists():
            continue

        model = _read_config_model(home)

        # Track conversation_ids from DB to deduplicate against session JSONs.
        # Maps conversation_id → UsageEvent (or None if filtered by time range)
        # so we can supplement cache tokens when DB has zeros.
        db_conversation_events: dict[str, UsageEvent | None] = {}

        # Collect all state.db files: main kernel + archived/backup copies.
        # Multiple DB snapshots may exist due to schema migrations; we scan
        # them all and keep the highest token counts per conversation.
        db_paths: list[Path] = [db_path]
        for archive_db in home.glob("kernel-archive-*/state.db"):
            db_paths.append(archive_db)
        # kernel/archive/<date>/state.db* (e.g. state.db.v5)
        for inner_archive in (home / "kernel" / "archive").glob("*/state.db*"):
            if inner_archive.suffix not in (".db-shm", ".db-wal"):
                db_paths.append(inner_archive)
        # Backup files from schema migrations (state.db.bak, state.db.bak-v8-*, etc.)
        for bak in (home / "kernel").glob("state.db.bak*"):
            db_paths.append(bak)
        for bak in (home / "kernel").glob("state.db.pre-*"):
            db_paths.append(bak)

        for dbp in db_paths:
            try:
                conn = sqlite3.connect(str(dbp))
                conn.row_factory = sqlite3.Row
            except Exception as exc:
                warnings.warn(f"Hermit DB connect failed for {dbp}: {exc}", stacklevel=2)
                continue

            try:
                _parse_conversations(
                    conn, source, model, start_utc, now_utc, events, db_conversation_events
                )
                _parse_receipts(conn, source, start_utc, now_utc, tool_calls)
                _parse_tasks(conn, source, session_metas)
                conn.close()
            except Exception as exc:
                warnings.warn(f"Hermit DB parse failed for {dbp}: {exc}", stacklevel=2)
                try:
                    conn.close()
                except Exception:
                    pass

        _parse_sessions(
            home, source, model, start_utc, now_utc,
            user_messages, events, db_conversation_events,
        )

    result = ParseResult(
        events=events,
        tool_calls=tool_calls,
        session_metas=session_metas,
        user_messages=user_messages,
    )
    result_cache_set("hermit", watch, result)
    return result


def _parse_conversations(
    conn: sqlite3.Connection,
    source: str,
    model: str,
    start_utc: datetime,
    now_utc: datetime,
    out: list[UsageEvent],
    db_conversation_events: dict[str, UsageEvent | None],
) -> None:
    try:
        rows = conn.execute(
            "SELECT conversation_id, created_at, updated_at, total_input_tokens, total_output_tokens, "
            "total_cache_read_tokens, total_cache_creation_tokens "
            "FROM conversations WHERE created_at IS NOT NULL"
        ).fetchall()
    except Exception as exc:
        warnings.warn(f"Hermit conversations query failed: {exc}", stacklevel=2)
        return

    for r in rows:
        cid = str(r["conversation_id"])

        # Use updated_at (last activity) so active conversations stay current
        ts = _epoch_ts(r["updated_at"]) or _epoch_ts(r["created_at"])
        if ts is None or ts < start_utc or ts > now_utc:
            db_conversation_events.setdefault(cid, None)
            continue

        inp = _si(r["total_input_tokens"])
        out_tok = _si(r["total_output_tokens"])
        cache_read = _si(r["total_cache_read_tokens"])
        cache_write = _si(r["total_cache_creation_tokens"])
        uncached = max(0, inp - cache_read - cache_write)

        if inp or out_tok:
            existing = db_conversation_events.get(cid)
            if existing is not None:
                # Same conversation seen in a previous DB snapshot.
                # Keep the higher token counts (migration may have reset them).
                old_total = (
                    existing.uncached_input
                    + existing.cache_read
                    + existing.cache_write
                    + existing.output
                )
                new_total = inp + out_tok
                if new_total > old_total:
                    updated = replace(
                        existing,
                        uncached_input=uncached,
                        cache_read=cache_read,
                        cache_write=cache_write,
                        output=out_tok,
                        timestamp=ts,
                    )
                    # Replace in the out list at the same position
                    idx = out.index(existing)
                    out[idx] = updated
                    db_conversation_events[cid] = updated
                # Either way, already in out list — skip append.
            else:
                evt = UsageEvent(
                    source=source,
                    timestamp=ts,
                    session_id=cid,
                    model=model,
                    uncached_input=uncached,
                    cache_read=cache_read,
                    cache_write=cache_write,
                    output=out_tok,
                )
                out.append(evt)
                db_conversation_events[cid] = evt
        else:
            db_conversation_events.setdefault(cid, None)


def _parse_receipts(
    conn: sqlite3.Connection,
    source: str,
    start_utc: datetime,
    now_utc: datetime,
    out: list[ToolCall],
) -> None:
    # Check if result_code column exists (schema varies across versions)
    has_result_code = False
    try:
        cols = {
            info[1] for info in conn.execute("PRAGMA table_info(receipts)").fetchall()
        }
        has_result_code = "result_code" in cols
    except Exception:
        pass

    select_cols = "r.task_id, r.action_type, r.created_at, t.conversation_id"
    if has_result_code:
        select_cols = "r.task_id, r.action_type, r.result_code, r.created_at, t.conversation_id"

    try:
        rows = conn.execute(
            f"SELECT {select_cols} "
            "FROM receipts r LEFT JOIN tasks t ON r.task_id = t.task_id "
            "WHERE r.created_at IS NOT NULL"
        ).fetchall()
    except Exception as exc:
        warnings.warn(f"Hermit receipts query failed: {exc}", stacklevel=2)
        return

    for r in rows:
        if has_result_code:
            ts = _epoch_ts(r["created_at"])
            action = r["action_type"] or "unknown"
            rc = r["result_code"]
        else:
            ts = _epoch_ts(r["created_at"])
            action = r["action_type"] or "unknown"
            rc = None
        if ts is None or ts < start_utc or ts > now_utc:
            continue

        tool_name = _ACTION_MAP.get(action, action)
        exit_code = 0 if rc == "succeeded" else (1 if rc and rc != "succeeded" else None)

        out.append(
            ToolCall(
                source=source,
                timestamp=ts,
                session_id=str(r["conversation_id"] or r["task_id"] or ""),
                tool_name=tool_name,
                exit_code=exit_code,
            )
        )


def _parse_tasks(
    conn: sqlite3.Connection,
    source: str,
    out: list[SessionMeta],
) -> None:
    try:
        # Pick the first (root) task per conversation as the project name
        rows = conn.execute(
            "SELECT conversation_id, title, source_channel FROM tasks "
            "WHERE parent_task_id IS NULL "
            "ORDER BY created_at ASC"
        ).fetchall()
    except Exception as exc:
        warnings.warn(f"Hermit tasks query failed: {exc}", stacklevel=2)
        return

    seen: set[str] = set()
    for r in rows:
        cid = r["conversation_id"]
        if not cid or cid in seen:
            continue
        seen.add(cid)
        out.append(
            SessionMeta(
                source=source,
                session_id=str(cid),
                project=r["title"] or None,
            )
        )


def _find_db_event(
    session_id: str, db_conversation_events: dict[str, UsageEvent | None]
) -> tuple[str | None, UsageEvent | None]:
    """Find a matching DB conversation for a session_id.

    Returns ``(matched_cid, event_or_none)``.  ``matched_cid`` is ``None``
    when there is no overlap at all.
    """
    if session_id in db_conversation_events:
        return session_id, db_conversation_events[session_id]
    base = session_id.split(":")[0]
    if base in db_conversation_events:
        return base, db_conversation_events[base]
    return None, None


def _parse_sessions(
    home: Path,
    source: str,
    model: str,
    start_utc: datetime,
    now_utc: datetime,
    out_messages: list[UserMessage],
    out_events: list[UsageEvent],
    db_conversation_events: dict[str, UsageEvent | None],
) -> None:
    sessions_dir = home / "sessions"
    if not sessions_dir.is_dir():
        return

    # Scan both active sessions and the archive sub-directory
    json_files: list[Path] = list(sessions_dir.glob("*.json"))
    archive_dir = sessions_dir / "archive"
    if archive_dir.is_dir():
        json_files.extend(archive_dir.glob("*.json"))

    # First pass: aggregate session token totals per DB-matched conversation
    # so we can supplement cache tokens on the DB event once (not per file).
    cache_supplement: dict[str, list[int]] = {}  # matched_cid → [cr, cw]

    for jf in json_files:
        try:
            with open(jf, encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
        except Exception as exc:
            warnings.warn(f"Hermit session JSON load failed for {jf}: {exc}", stacklevel=2)
            continue

        if not isinstance(data, dict):
            continue

        # Prefer last_active_at so active sessions stay in range
        session_ts = _epoch_ts(data.get("last_active_at") or data.get("created_at"))
        if session_ts is None or session_ts < start_utc or session_ts > now_utc:
            continue

        session_id = data.get("session_id") or jf.stem

        # --- Extract UsageEvent from session-level token totals ---
        inp = _si(data.get("total_input_tokens"))
        out_tok = _si(data.get("total_output_tokens"))
        cache_read = _si(data.get("total_cache_read_tokens"))
        cache_write = _si(data.get("total_cache_creation_tokens"))

        matched_cid, db_evt = _find_db_event(
            str(session_id), db_conversation_events
        )

        if matched_cid is not None:
            # Session overlaps with a DB conversation.  Accumulate cache
            # tokens so we can supplement the DB event if it has zeros.
            if cache_read or cache_write:
                bucket = cache_supplement.setdefault(matched_cid, [0, 0])
                bucket[0] += cache_read
                bucket[1] += cache_write
        elif inp or out_tok:
            # No DB match — create a brand-new UsageEvent.
            uncached = max(0, inp - cache_read - cache_write)
            out_events.append(
                UsageEvent(
                    source=source,
                    timestamp=session_ts,
                    session_id=str(session_id),
                    model=model,
                    uncached_input=uncached,
                    cache_read=cache_read,
                    cache_write=cache_write,
                    output=out_tok,
                )
            )

        # --- Extract UserMessages ---
        messages = data.get("messages", [])
        for msg in messages:
            if not isinstance(msg, dict) or msg.get("role") != "user":
                continue

            content = msg.get("content", "")
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        parts.append(block)
                content = " ".join(parts)
            if not isinstance(content, str) or not content.strip():
                continue

            text = content.strip()
            out_messages.append(
                UserMessage(
                    source=source,
                    timestamp=session_ts,
                    session_id=str(session_id),
                    text=text[:200],
                    char_count=len(text),
                )
            )

    # Supplement DB events that have zero cache tokens with aggregated
    # session JSON cache data.
    for cid, (sup_cr, sup_cw) in cache_supplement.items():
        db_evt = db_conversation_events.get(cid)
        if db_evt is not None and db_evt.cache_read == 0 and db_evt.cache_write == 0:
            # DB had cache=0, so uncached_input currently equals total input.
            # Re-split now that we know the real cache breakdown.
            total_inp = db_evt.uncached_input
            updated = replace(
                db_evt,
                cache_read=sup_cr,
                cache_write=sup_cw,
                uncached_input=max(0, total_inp - sup_cr - sup_cw),
            )
            # Replace in the out_events list at the same position
            idx = out_events.index(db_evt)
            out_events[idx] = updated
            db_conversation_events[cid] = updated
