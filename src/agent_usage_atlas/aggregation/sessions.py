"""Session analysis: top sessions, duration histogram, complexity scatter."""

from __future__ import annotations

from statistics import median

from ._context import AggContext, _percentile


def _active_sessions(ctx: AggContext) -> list[dict]:
    """Return precomputed active sessions from ctx."""
    return ctx.active_sessions


def compute(ctx: AggContext) -> list[dict]:
    return ctx.active_sessions[:20]


def deep_dive(ctx: AggContext) -> dict:
    active_sessions = ctx.active_sessions
    complexity_scatter = active_sessions[:50]

    duration_buckets = [
        ("<5m", 0, 5),
        ("5-15m", 5, 15),
        ("15-30m", 15, 30),
        ("30-60m", 30, 60),
        (">60m", 60, float("inf")),
    ]
    # Single-pass histogram instead of N linear scans
    bucket_counts = [0] * len(duration_buckets)
    for s in active_sessions:
        m = s["minutes"]
        for i, (_, start, end) in enumerate(duration_buckets):
            if start <= m < end:
                bucket_counts[i] += 1
                break
    duration_histogram = [
        {"label": duration_buckets[i][0], "count": bucket_counts[i]} for i in range(len(duration_buckets))
    ]

    sorted_minutes = sorted(s["minutes"] for s in active_sessions if s["minutes"] > 0)
    tokens_per_minute = [s["total"] / s["minutes"] for s in active_sessions if s["minutes"] > 0 and s["total"] > 0]
    sorted_tools = sorted(s["tool_calls"] for s in active_sessions)
    latency_stats = {
        "median_session_minutes": round(median(sorted_minutes), 1) if sorted_minutes else 0.0,
        "p90_session_minutes": round(_percentile(sorted_minutes, 0.9), 1) if sorted_minutes else 0.0,
        "avg_tokens_per_minute": (
            round(sum(tokens_per_minute) / len(tokens_per_minute), 1) if tokens_per_minute else 0.0
        ),
        "median_tools_per_session": round(median(sorted_tools), 1) if sorted_tools else 0.0,
    }

    return {
        "duration_histogram": duration_histogram,
        "complexity_scatter": [
            {
                "source": s["source"],
                "session_id": s["session_id"],
                "duration_minutes": s["minutes"],
                "total_tokens": s["total"],
                "cache_total": s["cache_read"] + s["cache_write"],
                "tool_calls": s["tool_calls"],
                "cost": s["cost"],
            }
            for s in complexity_scatter
        ],
        "latency_stats": latency_stats,
    }
