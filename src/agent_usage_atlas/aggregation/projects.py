"""Project analysis: ranking, branches, file types."""

from __future__ import annotations

from collections import Counter

from ._context import AggContext


def compute(ctx: AggContext) -> dict:
    active_sessions = ctx.active_sessions
    project_rollups = ctx.project_rollups
    branch_activity = Counter()
    active_session_keys = {(s["source"], s["session_id"]) for s in active_sessions}

    for key, meta in ctx.session_meta_map.items():
        if key in active_session_keys and meta.git_branch:
            branch_activity[meta.git_branch] += 1

    project_ranking = sorted(project_rollups.values(), key=lambda i: i["total_tokens"], reverse=True)[:20]

    return {
        "ranking": [
            {
                "project": i["project"],
                "sessions": i["sessions"],
                "total_tokens": i["total_tokens"],
                "cost": round(i["cost"], 4),
                "tool_calls": i["tool_calls"],
            }
            for i in project_ranking
        ],
        "branch_activity": [{"branch": b, "sessions": c} for b, c in branch_activity.most_common(20)],
        "file_types": [{"extension": e, "count": c} for e, c in ctx.file_types.most_common(20)],
        "count": len(project_rollups),
    }
