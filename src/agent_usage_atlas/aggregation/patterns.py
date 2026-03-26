"""Working patterns: heatmap, hourly, productivity, radar, timeline."""

from __future__ import annotations

from ._context import WEEKDAYS, AggContext, _percent


def compute(ctx: AggContext) -> dict:
    source_cards = _source_cards_for_radar(ctx)
    ordered_days = ctx.ordered_days

    hourly_rows = ctx.hourly_rows

    heatmap_rows = []
    for idx in range(7):
        wh = ctx.weekday_hour_heatmap.get(idx, {})
        values = [wh.get(h, 0) if isinstance(wh, dict) else 0 for h in range(24)]
        heatmap_rows.append({"weekday": WEEKDAYS[idx], "values": values})

    max_daily_tokens = max((d["total_tokens"] for d in ordered_days), default=0)
    max_daily_messages = max((d["messages"] for d in ordered_days), default=0)
    max_daily_tools = max((d["tool_calls"] for d in ordered_days), default=0)
    max_daily_cost = max((d["cost"] for d in ordered_days), default=0.0)
    daily_productivity = []
    for d in ordered_days:
        score = (
            0.3 * _percent(d["total_tokens"], max_daily_tokens)
            + 0.2 * _percent(d["messages"], max_daily_messages)
            + 0.3 * _percent(d["tool_calls"], max_daily_tools)
            + 0.2 * _percent(d["cost"], max_daily_cost)
        )
        daily_productivity.append(
            {
                "date": d["date"],
                "label": d["label"],
                "score": round(score, 3),
                "tokens": d["total_tokens"],
                "messages": d["messages"],
                "tool_calls": d["tool_calls"],
                "cost": d["cost"],
            }
        )

    peak_markers = [
        {
            "date": d["date"],
            "label": d["label"],
            "total_tokens": d["total_tokens"],
            "cumulative_tokens": d["cumulative_tokens"],
        }
        for d in sorted(
            [i for i in ordered_days if i["total_tokens"] > 0],
            key=lambda i: i["total_tokens"],
            reverse=True,
        )[:4]
    ]
    peak_markers.sort(key=lambda i: i["date"])

    return {
        "heatmap": heatmap_rows,
        "hourly_source_totals": hourly_rows,
        "hourly_tool_density": [{"hour": h, "count": ctx.tool_calls_by_hour[h]} for h in range(24)],
        "daily_productivity": daily_productivity,
        "source_radar": source_cards,
        "timeline": {
            "days": [
                {
                    "date": d["date"],
                    "label": d["label"],
                    "total_tokens": d["total_tokens"],
                    "cumulative_tokens": d["cumulative_tokens"],
                }
                for d in ordered_days
            ],
            "peak_markers": peak_markers,
        },
    }


def _source_cards_for_radar(ctx: AggContext) -> list[dict]:
    from ._context import _source_rank

    cards = []
    for source_name in sorted(ctx.source_rollups, key=_source_rank):
        s = ctx.source_rollups[source_name]
        if not s["token_capable"]:
            continue
        cards.append(
            {
                "name": source_name,
                "total_tokens": s["total_tokens"],
                "cache_total": s["cache_read"] + s["cache_write"],
                "output_total": s["output"] + s["reasoning"],
                "sessions": len(s["sessions"]),
            }
        )
    return cards
