#!/usr/bin/env python3
"""CLI entry point for agent-usage-atlas."""

from __future__ import annotations

import argparse
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .aggregation import aggregate
from .models import fmt_int, fmt_usd
from .parsers import parse_all

# ── Dashboard-level cache (skip aggregation when no data changed) ─────
_dashboard_cache: dict[str, Any] | None = None
_dashboard_cache_key: tuple | None = None
_dashboard_cache_lock = threading.Lock()

# ── Core payload builder (shared by all commands) ──────────────────────


def build_dashboard_payload(
    *,
    days: int = 30,
    since: str | None = None,
    now_local: datetime | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    global _dashboard_cache, _dashboard_cache_key

    local_tz = now_local.tzinfo if now_local and now_local.tzinfo else datetime.now(timezone.utc).astimezone().tzinfo
    now_local = now_local or datetime.now(local_tz)
    if now_local.tzinfo is None:
        now_local = now_local.replace(tzinfo=local_tz)
    now_utc = now_utc or now_local.astimezone(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    if since:
        start_local = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=local_tz)
    else:
        start_local = (now_local - timedelta(days=days)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    start_utc = start_local.astimezone(timezone.utc)

    cache_key = (days, since, str(start_utc))
    result, claude_stats_cache, changed = parse_all(start_utc, now_utc, local_tz=local_tz)

    with _dashboard_cache_lock:
        if not changed and _dashboard_cache is not None and _dashboard_cache_key == cache_key:
            # Return a shallow copy so callers don't mutate the cached object
            snapshot = {**_dashboard_cache}
            snapshot["_meta"] = {**snapshot["_meta"], "generated_at": now_local.isoformat(timespec="seconds")}
            return snapshot

    dashboard = aggregate(
        result.events,
        result.tool_calls,
        result.session_metas,
        start_local=start_local,
        now_local=now_local,
        local_tz=local_tz,
        task_events=result.task_events,
        turn_durations=result.turn_durations,
        cursor_codegen=result.code_gen,
        cursor_commits=result.scored_commits,
        claude_stats_cache=claude_stats_cache,
        user_messages=result.user_messages,
    )
    dashboard["_meta"] = {
        "generated_at": now_local.isoformat(timespec="seconds"),
        "since": since,
        "days": days,
        "local_timezone": str(local_tz),
    }
    with _dashboard_cache_lock:
        _dashboard_cache = dashboard
        _dashboard_cache_key = cache_key
    return dashboard


def print_summary(dashboard: dict[str, Any]) -> None:
    totals = dashboard["totals"]
    print(
        f"Tokens: {fmt_int(totals['grand_total'])}  Cost: {fmt_usd(totals['grand_cost'])}  "
        f"Tools: {fmt_int(totals['tool_call_total'])}  Projects: {totals['project_count']}"
    )
    for card in dashboard["source_cards"]:
        label = fmt_int(card["total"]) if card["token_capable"] else f"{fmt_int(card['messages'])} msgs"
        cost = fmt_usd(card["cost"]) if card["token_capable"] else "-"
        print(f"  {card['source']}: usage={label} cost={cost} sessions={card['sessions']}")


# ── CLI parser ─────────────────────────────────────────────────────────


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    """Add options shared across subcommands."""
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of recent days to include (default: 30)",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Custom start date (overrides --days)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Output file path",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        dest="open_browser",
        help="Open the result in the default browser",
    )


def _build_parser() -> argparse.ArgumentParser:
    from .commands import billing, export, generate, mcp, serve

    parser = argparse.ArgumentParser(
        prog="agent-usage-atlas",
        description="Generate a local agent usage dashboard from Codex CLI / Claude Code / Cursor logs.",
    )

    # Legacy --serve flag (backward compat)
    parser.add_argument(
        "--serve",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )
    # Legacy flags for --serve mode
    parser.add_argument("--host", type=str, default="127.0.0.1", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8765, help=argparse.SUPPRESS)
    parser.add_argument("--interval", type=int, default=5, help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(dest="command")

    # generate (default)
    gen_parser = generate.add_parser(subparsers)
    _add_common_options(gen_parser)

    # serve
    srv_parser = serve.add_parser(subparsers)
    _add_common_options(srv_parser)

    # export
    exp_parser = export.add_parser(subparsers)
    _add_common_options(exp_parser)

    # billing
    billing.add_parser(subparsers)

    # mcp
    mcp.add_parser(subparsers)

    return parser


def _is_subcommand(arg: str) -> bool:
    return arg in {"generate", "serve", "export", "billing", "mcp"}


def main() -> None:
    parser = _build_parser()

    # If no subcommand given, insert "generate" as default
    # Check sys.argv: if first non-flag arg isn't a known subcommand, prepend "generate"
    argv = sys.argv[1:]
    if not any(_is_subcommand(a) for a in argv if not a.startswith("-")):
        argv = ["generate"] + argv

    args = parser.parse_args(argv)

    # Legacy: `agent-usage-atlas --serve` → delegate to serve command
    if args.serve:
        from .server import run_server

        run_server(
            host=args.host,
            port=args.port,
            days=getattr(args, "days", 30),
            since=getattr(args, "since", None),
            interval=args.interval,
            open_browser=getattr(args, "open_browser", False),
        )
        return

    # Dispatch to subcommand
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
