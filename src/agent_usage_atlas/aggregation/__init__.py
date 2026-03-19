"""Aggregate parsed events into a rich dashboard payload."""

from __future__ import annotations

from . import daily, extended, insights, patterns, projects, prompts, sessions, story, tooling, totals, trends
from ._context import build_context


def aggregate(
    events,
    tool_calls,
    session_metas,
    *,
    start_local,
    now_local,
    local_tz,
    task_events=None,
    turn_durations=None,
    cursor_codegen=None,
    cursor_commits=None,
    claude_stats_cache=None,
    user_messages=None,
):
    ctx = build_context(
        events,
        tool_calls,
        session_metas,
        start_local=start_local,
        now_local=now_local,
        local_tz=local_tz,
        task_events=task_events,
        turn_durations=turn_durations,
        cursor_codegen=cursor_codegen,
        cursor_commits=cursor_commits,
        claude_stats_cache=claude_stats_cache,
        user_messages=user_messages,
    )

    prompt_data = prompts.compute(ctx)

    return {
        "range": ctx.range_info,
        "totals": totals.compute(ctx),
        "source_cards": totals.source_cards(ctx),
        "days": daily.compute(ctx),
        "top_sessions": sessions.compute(ctx),
        "tooling": tooling.compute(ctx),
        "commands": tooling.commands(ctx),
        "projects": projects.compute(ctx),
        "working_patterns": patterns.compute(ctx),
        "efficiency_metrics": trends.efficiency(ctx),
        "session_deep_dive": sessions.deep_dive(ctx),
        "trend_analysis": trends.compute(ctx),
        "token_burn": trends.token_burn_multi(ctx),
        "story": story.compute(ctx),
        "extended": extended.compute(ctx, claude_stats_cache),
        "prompts": prompt_data,
        "insights": insights.compute(ctx, prompt_data),
    }
