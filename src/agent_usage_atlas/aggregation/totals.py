"""Grand totals and source card computation."""

from __future__ import annotations

from statistics import median

from ._context import AggContext, _percent


def compute(ctx: AggContext) -> dict:
    source_cards = ctx.source_cards
    active_sessions = ctx.active_sessions
    ordered_days = ctx.ordered_days

    grand_total = ctx.grand_total
    grand_cost = ctx.grand_cost
    grand_cache_read = ctx.grand_cache_read
    grand_cache_write = ctx.grand_cache_write

    # Single-pass summation over ordered_days
    grand_output = 0
    grand_reasoning = 0
    sum_cost_input = 0.0
    sum_cost_cache_read = 0.0
    sum_cost_cache_write = 0.0
    sum_cost_output = 0.0
    sum_cost_reasoning = 0.0
    for d in ordered_days:
        grand_output += d["output"]
        grand_reasoning += d["reasoning"]
        sum_cost_input += d["cost_input"]
        sum_cost_cache_read += d["cost_cache_read"]
        sum_cost_cache_write += d["cost_cache_write"]
        sum_cost_output += d["cost_output"]
        sum_cost_reasoning += d["cost_reasoning"]

    cache_ratio = _percent(grand_cache_read + grand_cache_write, grand_total)
    token_capable_cards = [c for c in source_cards if c["token_capable"]]
    tracked_messages = sum(c["messages"] for c in token_capable_cards)

    session_tokens = [s["total"] for s in active_sessions if s["total"] > 0]
    session_minutes = [s["minutes"] for s in active_sessions if s["minutes"] > 0]
    session_costs = [s["cost"] for s in active_sessions if s["cost"] > 0]

    peak_day = ctx.peak_day
    cost_peak_day = ctx.cost_peak_day
    total_cache_read_full = sum(c["cost_cache_read_full"] for c in source_cards)
    total_cost_cache_read = sum(c["cost_cache_read"] for c in source_cards)
    cache_savings_usd = max(0.0, total_cache_read_full - total_cost_cache_read)
    cache_savings_ratio = _percent(cache_savings_usd, total_cache_read_full)

    combined_tool_counts = ctx.combined_tool_counts
    project_count = len(ctx.project_rollups)

    average_daily_burn = ctx.avg_daily_burn_7d
    projected_total_30d = round(average_daily_burn * 30, 2)

    return {
        "grand_total": grand_total,
        "grand_cost": round(grand_cost, 2),
        "cache_read": grand_cache_read,
        "cache_write": grand_cache_write,
        "output": grand_output,
        "reasoning": grand_reasoning,
        "cache_ratio": cache_ratio,
        "tracked_session_count": sum(c["sessions"] for c in token_capable_cards),
        "average_per_day": round(grand_total / max(1, len(ordered_days))),
        "median_session_tokens": round(median(session_tokens)) if session_tokens else 0,
        "median_session_minutes": round(median(session_minutes), 1) if session_minutes else 0.0,
        "median_session_cost": round(median(session_costs), 4) if session_costs else 0.0,
        "peak_day_label": peak_day["label"] if peak_day else "-",
        "peak_day_total": peak_day["total_tokens"] if peak_day else 0,
        "cost_peak_day_label": cost_peak_day["label"] if cost_peak_day else "-",
        "cost_peak_day_total": round(cost_peak_day["cost"], 4) if cost_peak_day else 0.0,
        "average_cost_per_day": round(grand_cost / max(1, len(ordered_days)), 2),
        "cost_per_message": round(grand_cost / max(1, tracked_messages), 4),
        "cost_input": round(sum_cost_input, 2),
        "cost_cache_read": round(sum_cost_cache_read, 2),
        "cost_cache_write": round(sum_cost_cache_write, 2),
        "cost_output": round(sum_cost_output, 2),
        "cost_reasoning": round(sum_cost_reasoning, 2),
        "cache_savings_usd": round(cache_savings_usd, 2),
        "cache_savings_ratio": cache_savings_ratio,
        "tool_call_total": sum(combined_tool_counts.values()),
        "project_count": project_count,
        "avg_daily_burn": round(average_daily_burn, 2),
        "burn_rate_projection_30d": projected_total_30d,
    }


def source_cards(ctx: AggContext) -> list[dict]:
    return ctx.source_cards


def _source_cards(ctx: AggContext) -> list[dict]:
    """Backward-compatible alias — delegates to precomputed ctx.source_cards."""
    return ctx.source_cards
