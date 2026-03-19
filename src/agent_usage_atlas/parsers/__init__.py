"""Parser registry and orchestration."""

from __future__ import annotations

import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models import ParseResult
from . import claude, codex, cursor, hermit
from ._base import all_caches_hit, set_active_range
from .claude import CLAUDE_HOME, CLAUDE_ROOT
from .codex import CODEX_HOME, CODEX_ROOTS
from .cursor import CURSOR_DB, CURSOR_ROOT
from .hermit import HERMIT_HOMES, HERMIT_ROOTS


def parse_all(start_utc, now_utc, *, local_tz=None) -> tuple[ParseResult, dict, bool]:
    """Run all parsers concurrently and merge results.

    Returns (merged_result, claude_stats_cache, changed).
    ``changed`` is False when every parser returned cached data.
    """
    merged = ParseResult()
    set_active_range(start_utc, now_utc)

    with ThreadPoolExecutor() as pool:
        futures = {
            pool.submit(codex.parse, start_utc, now_utc): "codex",
            pool.submit(claude.parse, start_utc, now_utc): "claude",
            pool.submit(cursor.parse, start_utc, now_utc, local_tz): "cursor",
            pool.submit(hermit.parse, start_utc, now_utc): "hermit",
        }
        f_stats = pool.submit(claude.parse_stats_cache)

        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result(timeout=30)
                merged.merge(result)
            except Exception as e:
                warnings.warn(f"Parser {name} failed: {e}")

        try:
            claude_stats = f_stats.result(timeout=10)
        except Exception:
            claude_stats = {}

    changed = not all_caches_hit()
    return merged, claude_stats, changed


# Backward-compatible exports for server.py path scanning
__all__ = [
    "parse_all",
    "CODEX_ROOTS",
    "CODEX_HOME",
    "CLAUDE_ROOT",
    "CLAUDE_HOME",
    "CURSOR_ROOT",
    "CURSOR_DB",
    "HERMIT_HOMES",
    "HERMIT_ROOTS",
]
