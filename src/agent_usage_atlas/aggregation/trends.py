"""Trend analysis: model costs, sankey, burn rate, efficiency."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from ._context import AggContext, _percent, _round_money


def _build_sankey(cards: list[dict], specs: list[tuple[str, str]]) -> dict:
    nodes = [{"name": c["source"], "kind": "source"} for c in cards]
    for _, label in specs:
        nodes.append({"name": label, "kind": "bucket"})
    links = []
    for c in cards:
        for key, label in specs:
            value = c.get(key, 0)
            if value > 0:
                links.append({"source": c["source"], "target": label, "value": value})
    return {"nodes": nodes, "links": links}


def compute(ctx: AggContext) -> dict:
    source_cards = ctx.source_cards
    ordered_days = ctx.ordered_days

    model_costs = sorted(
        [
            {
                "model": model,
                "cost": _round_money(stats["cost"]),
                "messages": stats["messages"],
                "input_tokens": stats["input_tokens"],
                "cache_tokens": stats["cache_tokens"],
                "output_tokens": stats["output_tokens"],
            }
            for model, stats in ctx.model_rollups.items()
            if stats["cost"] > 0
        ],
        key=lambda i: i["cost"],
        reverse=True,
    )

    top_models = model_costs[:5]
    max_input = max((i["input_tokens"] for i in top_models), default=1)
    max_output = max((i["output_tokens"] for i in top_models), default=1)
    max_cache = max((i["cache_tokens"] for i in top_models), default=1)
    max_cost = max((i["cost"] for i in top_models), default=1)
    max_messages = max((i["messages"] for i in top_models), default=1)
    model_radar = [
        {
            "name": i["model"],
            "input_tokens": i["input_tokens"],
            "output_tokens": i["output_tokens"],
            "cache_tokens": i["cache_tokens"],
            "cost": i["cost"],
            "messages": i["messages"],
            "normalized": [
                round(_percent(i["input_tokens"], max_input), 3),
                round(_percent(i["output_tokens"], max_output), 3),
                round(_percent(i["cache_tokens"], max_cache), 3),
                round(_percent(i["cost"], max_cost), 3),
                round(_percent(i["messages"], max_messages), 3),
            ],
        }
        for i in top_models
    ]

    recent_window = ordered_days[-7:] if ordered_days else []
    average_daily_burn = ctx.avg_daily_burn_7d
    projected_total_30d = round(average_daily_burn * 30, 2)
    projected_cumulative = ordered_days[-1]["cost_cumulative"] if ordered_days else 0.0
    projection = []
    for offset in range(1, 31):
        future_date = ctx.now_local.date() + timedelta(days=offset)
        projected_cumulative += average_daily_burn
        projection.append(
            {
                "date": future_date.isoformat(),
                "label": future_date.strftime("%m/%d"),
                "projected_daily_cost": average_daily_burn,
                "projected_cumulative_cost": round(projected_cumulative, 4),
            }
        )

    daily_cost_per_tool_call = [
        {
            "date": d["date"],
            "label": d["label"],
            "value": round(d["cost"] / d["tool_calls"], 4) if d["tool_calls"] else 0.0,
            "cost": d["cost"],
            "tool_calls": d["tool_calls"],
        }
        for d in ordered_days
    ]

    token_sankey = _build_sankey(
        source_cards,
        [
            ("uncached_input", "Uncached Input"),
            ("cache_read", "Cache Read"),
            ("cache_write", "Cache Write"),
            ("output", "Output"),
            ("reasoning", "Reasoning"),
        ],
    )
    cost_sankey = _build_sankey(
        source_cards,
        [
            ("cost_input", "Input Cost"),
            ("cost_cache_read", "Cache Read"),
            ("cost_cache_write", "Cache Write"),
            ("cost_output", "Output"),
            ("cost_reasoning", "Reasoning"),
        ],
    )

    return {
        "model_costs": model_costs,
        "token_sankey": token_sankey,
        "cost_sankey": cost_sankey,
        "burn_rate_30d": {
            "average_daily_cost": average_daily_burn,
            "projected_total_30d": projected_total_30d,
            "history": [
                {"date": d["date"], "label": d["label"], "cost": d["cost"], "cumulative_cost": d["cost_cumulative"]}
                for d in ordered_days
            ],
            "projection": projection,
        },
        "daily_cost_per_tool_call": daily_cost_per_tool_call,
        "model_radar": model_radar,
    }


def efficiency(ctx: AggContext) -> dict:
    ordered_days = ctx.ordered_days
    efficiency_daily = []
    for d in ordered_days:
        tracked_input = d["uncached_input"] + d["cache_read"]
        efficiency_daily.append(
            {
                "date": d["date"],
                "label": d["label"],
                "reasoning_ratio": round(_percent(d["reasoning"], d["total_tokens"]), 4),
                "cache_hit_rate": round(_percent(d["cache_read"], tracked_input), 4),
                "tokens_per_message": round(_percent(d["total_tokens"], d["messages"]), 2) if d["messages"] else 0,
            }
        )
    return {
        "daily": efficiency_daily,
        "summary": {
            "avg_reasoning_ratio": round(sum(d["reasoning_ratio"] for d in efficiency_daily) / len(efficiency_daily), 4)
            if efficiency_daily
            else 0.0,
            "avg_cache_hit_rate": round(sum(d["cache_hit_rate"] for d in efficiency_daily) / len(efficiency_daily), 4)
            if efficiency_daily
            else 0.0,
            "avg_tokens_per_message": (
                round(sum(d["tokens_per_message"] for d in efficiency_daily) / len(efficiency_daily), 1)
                if efficiency_daily
                else 0.0
            ),
        },
    }


def _token_burn_interval(ctx: AggContext, interval_min: int) -> list[dict]:
    """Bucket raw events into *interval_min*-minute bins."""
    if interval_min <= 0:
        raise ValueError(f"interval_min must be a positive integer, got {interval_min!r}")

    if not ctx._raw_events:
        return []

    bins: dict[str, dict] = defaultdict(lambda: {"total": 0, "cost": 0.0})

    for event in ctx._raw_events:
        local_ts = event.timestamp.astimezone(ctx.local_tz)
        minute = (local_ts.minute // interval_min) * interval_min
        bin_key = f"{local_ts.year:04d}-{local_ts.month:02d}-{local_ts.day:02d} {local_ts.hour:02d}:{minute:02d}"
        bins[bin_key]["total"] += event.total
        bins[bin_key]["cost"] += event.cost

    sorted_keys = sorted(bins.keys())
    result = []
    for key in sorted_keys:
        b = bins[key]
        if b["total"] == 0:
            continue
        result.append(
            {
                "t": key,
                "v": b["total"],
                "c": round(b["cost"], 4),
            }
        )

    return result


def token_burn_5min(ctx: AggContext) -> list[dict]:
    """Backward-compatible wrapper — returns 5-minute bins."""
    return _token_burn_interval(ctx, 5)


def token_burn_multi(ctx: AggContext) -> dict[str, list[dict]]:
    """Return burn bins at multiple intervals: 5, 30 min.

    Single-pass: iterate events once, bucket into all intervals simultaneously.
    """
    intervals = [5, 30]
    if not ctx._raw_events:
        return {str(iv): [] for iv in intervals}

    # Single pass over events, bucketing into all intervals at once
    bins: dict[int, dict[str, dict]] = {iv: {} for iv in intervals}
    for event in ctx._raw_events:
        local_ts = event.timestamp.astimezone(ctx.local_tz)
        total = event.total
        cost = event.cost
        prefix = f"{local_ts.year:04d}-{local_ts.month:02d}-{local_ts.day:02d} {local_ts.hour:02d}:"
        for iv in intervals:
            minute = (local_ts.minute // iv) * iv
            bin_key = f"{prefix}{minute:02d}"
            b = bins[iv].get(bin_key)
            if b is None:
                b = {"total": 0, "cost": 0.0}
                bins[iv][bin_key] = b
            b["total"] += total
            b["cost"] += cost

    results: dict[str, list[dict]] = {}
    for iv in intervals:
        sorted_keys = sorted(bins[iv].keys())
        results[str(iv)] = [
            {"t": k, "v": bins[iv][k]["total"], "c": round(bins[iv][k]["cost"], 4)}
            for k in sorted_keys
            if bins[iv][k]["total"] > 0
        ]

    return results
