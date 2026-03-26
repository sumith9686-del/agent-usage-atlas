"""Extended analytics: turn durations, task events, cursor codegen, AI contribution."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from statistics import median

from ._context import AggContext, _percent, _percentile


def compute(ctx: AggContext, claude_stats=None) -> dict:
    claude_stats = ctx.claude_stats_cache if claude_stats is None else claude_stats
    return {
        "turn_durations": _turn_durations(ctx),
        "task_events": _task_stats(ctx),
        "cursor_codegen": _cursor_codegen(ctx),
        "ai_contribution": _ai_contribution(ctx),
        "claude_stats": _claude_stats(claude_stats),
    }


def _turn_durations(ctx: AggContext) -> dict:
    dur_by_source = defaultdict(list)
    daily_dur = defaultdict(list)
    dur_all = []
    for td in ctx.turn_durations:
        dur_by_source[td.source].append(td.duration_ms)
        dur_all.append(td.duration_ms)
        local_ts = td.timestamp.astimezone(ctx.local_tz)
        daily_dur[local_ts.date().isoformat()].append(td.duration_ms)
    sorted_dur = sorted(dur_all)

    stats = {
        "total_turns": len(dur_all),
        "median_ms": round(median(sorted_dur)) if sorted_dur else 0,
        "p90_ms": round(_percentile(sorted_dur, 0.9)) if sorted_dur else 0,
        "p99_ms": round(_percentile(sorted_dur, 0.99)) if sorted_dur else 0,
        "by_source": {},
    }
    for src, vals in dur_by_source.items():
        sv = sorted(vals)
        stats["by_source"][src] = {
            "count": len(sv),
            "median_ms": round(median(sv)),
            "p90_ms": round(_percentile(sv, 0.9)),
        }

    dur_buckets = [
        ("<5s", 0, 5000),
        ("5-15s", 5000, 15000),
        ("15-30s", 15000, 30000),
        ("30-60s", 30000, 60000),
        ("1-5m", 60000, 300000),
        (">5m", 300000, float("inf")),
    ]
    # Single-pass histogram instead of N linear scans
    bucket_counts = [0] * len(dur_buckets)
    for d in dur_all:
        for i, (_, lo, hi) in enumerate(dur_buckets):
            if lo <= d < hi:
                bucket_counts[i] += 1
                break
    histogram = [{"label": dur_buckets[i][0], "count": bucket_counts[i]} for i in range(len(dur_buckets))]

    daily = []
    current_date = ctx.start_local.date()
    while current_date <= ctx.now_local.date():
        dk = current_date.isoformat()
        vals = daily_dur.get(dk, [])
        daily.append(
            {
                "date": dk,
                "label": current_date.strftime("%m/%d"),
                "median_ms": round(median(sorted(vals))) if vals else 0,
                "count": len(vals),
            }
        )
        current_date += timedelta(days=1)

    return {"stats": stats, "histogram": histogram, "daily": daily}


def _task_stats(ctx: AggContext) -> dict:
    started = 0
    completed = 0
    for te in ctx.task_events:
        if te.event_type == "started":
            started += 1
        elif te.event_type == "complete":
            completed += 1
    return {
        "started": started,
        "completed": completed,
        "completion_rate": round(_percent(completed, started), 3),
    }


def _cursor_codegen(ctx: AggContext) -> dict:
    codegen_by_model = Counter()
    codegen_by_ext = Counter()
    codegen_by_source = Counter()
    codegen_daily = defaultdict(int)
    for cg in ctx.cursor_codegen:
        codegen_by_model[cg.model] += 1
        if cg.file_extension:
            codegen_by_ext[cg.file_extension] += 1
        codegen_by_source[cg.gen_source] += 1
        local_ts = cg.timestamp.astimezone(ctx.local_tz)
        codegen_daily[local_ts.date().isoformat()] += 1

    return {
        "total": len(ctx.cursor_codegen),
        "by_model": [{"model": m, "count": c} for m, c in codegen_by_model.most_common(10)],
        "by_extension": [{"ext": e, "count": c} for e, c in codegen_by_ext.most_common(15)],
        "by_source": [{"source": s, "count": c} for s, c in codegen_by_source.most_common()],
        "daily": [
            {"date": dk, "label": dk[5:].replace("-", "/"), "count": codegen_daily.get(dk, 0)}
            for dk in (d["date"] for d in ctx.ordered_days)
        ],
    }


def _ai_contribution(ctx: AggContext) -> dict:
    commits = ctx.cursor_commits
    total_ai_added = sum(c.composer_added + c.tab_added for c in commits)
    total_human_added = sum(c.human_added for c in commits)
    total_ai_deleted = sum(c.composer_deleted + c.tab_deleted for c in commits)
    total_human_deleted = sum(c.human_deleted for c in commits)
    total_lines = total_ai_added + total_human_added + total_ai_deleted + total_human_deleted
    return {
        "total_commits": len(commits),
        "ai_lines_added": total_ai_added,
        "human_lines_added": total_human_added,
        "ai_lines_deleted": total_ai_deleted,
        "human_lines_deleted": total_human_deleted,
        "ai_ratio": round(_percent(total_ai_added + total_ai_deleted, total_lines), 3),
        "commits": [
            {
                "hash": c.commit_hash[:8],
                "ai_added": c.composer_added + c.tab_added,
                "human_added": c.human_added,
                "ai_deleted": c.composer_deleted + c.tab_deleted,
                "human_deleted": c.human_deleted,
            }
            for c in sorted(commits, key=lambda x: x.composer_added + x.tab_added, reverse=True)[:20]
        ],
    }


def _claude_stats(cache: dict) -> dict:
    if not cache:
        return {}
    return {
        "hour_counts": cache.get("hour_counts", []),
        "total_sessions": cache.get("total_sessions", 0),
        "total_messages": cache.get("total_messages", 0),
        "longest_session": cache.get("longest_session"),
        "first_session_date": cache.get("first_session_date"),
    }
