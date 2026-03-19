"""Narrative text, jokes, source notes, tempo notes."""

from __future__ import annotations

from collections import Counter

from ._context import SOURCE_ORDER, AggContext, _percent


def compute(ctx: AggContext) -> dict:
    from .totals import _source_cards

    source_cards = _source_cards(ctx)

    grand_total = ctx.grand_total
    grand_cost = ctx.grand_cost
    grand_cache_read = ctx.grand_cache_read
    grand_cache_write = ctx.grand_cache_write
    cache_ratio = _percent(grand_cache_read + grand_cache_write, grand_total)

    total_cache_read_full = sum(c["cost_cache_read_full"] for c in source_cards)
    total_cost_cache_read = sum(c["cost_cache_read"] for c in source_cards)
    cache_savings_usd = max(0.0, total_cache_read_full - total_cost_cache_read)

    combined = Counter()
    for counts in ctx.tool_counts_by_source.values():
        combined.update(counts)
    _tool_total = sum(combined.values())

    successful_commands = sum(d["command_successes"] for d in ctx.ordered_days)
    total_commands = sum(ctx.command_counts.values())
    _cmd_rate = _percent(successful_commands, total_commands)

    peak_day = ctx.peak_day
    cost_peak_day = ctx.cost_peak_day
    _peak_label = (peak_day or {}).get("label", "-")
    _peak_tokens = (peak_day or {}).get("total_tokens", 0)
    _cache_total = grand_cache_read + grand_cache_write

    story_narrative = [
        {"icon": "fa-bolt", "text": f"统计窗口内共处理 {grand_total:,} tokens，估算成本 ${grand_cost:,.2f}。"},
        {"icon": "fa-fire", "text": f"峰值日是 {_peak_label}, 当天跑了 {_peak_tokens:,} tokens。"},
        {"icon": "fa-database", "text": f"缓存读写共 {_cache_total:,} tokens，省下约 ${cache_savings_usd:,.2f}。"},
        {"icon": "fa-wrench", "text": f"全局工具调用 {_tool_total:,} 次，命令成功率 {_cmd_rate:.1%}。"},
    ]
    story_narrative_en = [
        {
            "icon": "fa-bolt",
            "text": f"Processed {grand_total:,} tokens in this window, estimated cost ${grand_cost:,.2f}.",
        },
        {"icon": "fa-fire", "text": f"Peak day was {_peak_label}, with {_peak_tokens:,} tokens."},
        {
            "icon": "fa-database",
            "text": f"Cache read/write totalled {_cache_total:,} tokens, saving ~${cache_savings_usd:,.2f}.",
        },
        {"icon": "fa-wrench", "text": f"Total tool calls: {_tool_total:,}, command success rate {_cmd_rate:.1%}."},
    ]

    source_notes = [
        f"{c['source']} 主力模型 {c['top_model']}，{c['sessions']} 个 session，{c['messages']} 条消息。"
        for c in source_cards
    ]
    source_notes_en = [
        f"{c['source']} primary model {c['top_model']}, {c['sessions']} sessions, {c['messages']} messages."
        for c in source_cards
    ]

    jokes = []
    jokes_en = []
    if cache_ratio > 0.75:
        jokes.append("缓存占比高得像给模型办了无限次回访卡。")
        jokes_en.append("Cache ratio so high it's like the model has an unlimited loyalty card.")
    if peak_day and peak_day["total_tokens"] > 300_000_000:
        jokes.append("峰值日像给 Agent 背后装了双涡轮。")
        jokes_en.append("Peak day looks like the Agent had twin turbos installed.")
    if any(not c["token_capable"] for c in source_cards):
        jokes.append("有些来源很勤奋，但没有留下完整 token 小票。")
        jokes_en.append("Some sources work hard but don't leave a full token receipt.")

    # Build hourly rows for tempo notes
    hourly_rows = []
    for hour in range(24):
        row = {"hour": hour}
        for src in SOURCE_ORDER:
            hst = ctx.hourly_source_totals.get(hour, {})
            row[src] = hst.get(src, 0) if isinstance(hst, dict) else 0
        hourly_rows.append(row)

    tempo_notes = []
    tempo_notes_en = []
    hottest_hour = max(hourly_rows, key=lambda r: sum(r.get(s, 0) for s in SOURCE_ORDER), default=None)
    if hottest_hour:
        tempo_notes.append(f"最热小时是 {hottest_hour['hour']:02d}:00。")
        tempo_notes_en.append(f"Hottest hour is {hottest_hour['hour']:02d}:00.")
    if cost_peak_day:
        tempo_notes.append(f"最烧钱的一天是 {cost_peak_day['label']}，花了 ${cost_peak_day['cost']:.2f}。")
        tempo_notes_en.append(f"Most expensive day was {cost_peak_day['label']}, spent ${cost_peak_day['cost']:.2f}.")

    return {
        "narrative": story_narrative,
        "jokes": jokes,
        "source_notes": source_notes,
        "tempo_notes": tempo_notes,
        "narrative_en": story_narrative_en,
        "jokes_en": jokes_en,
        "source_notes_en": source_notes_en,
        "tempo_notes_en": tempo_notes_en,
    }
