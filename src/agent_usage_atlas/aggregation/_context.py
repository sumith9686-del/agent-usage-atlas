"""Single-pass context builder for aggregation submodules."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

SOURCE_ORDER = ["Codex", "Claude", "Cursor"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _source_rank(name: str) -> int:
    return SOURCE_ORDER.index(name) if name in SOURCE_ORDER else len(SOURCE_ORDER)


def _round_money(value: float) -> float:
    return round(value, 4)


def _percent(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round((len(sorted_values) - 1) * fraction)))
    return sorted_values[index]


@dataclass
class AggContext:
    """Shared context built from a single pass over events and tool_calls."""

    start_local: Any
    now_local: Any
    local_tz: Any

    # Source rollups
    source_rollups: dict = field(default_factory=dict)
    # Daily rollups
    daily_rollups: dict = field(default_factory=dict)
    # Session rollups
    session_rollups: dict = field(default_factory=dict)
    # Session meta map
    session_meta_map: dict = field(default_factory=dict)

    # Hourly / heatmap indexes
    hourly_source_totals: dict = field(default_factory=dict)
    weekday_hour_heatmap: dict = field(default_factory=dict)

    # Tool indexes
    tool_counts_by_source: dict = field(default_factory=dict)
    tool_sequences: dict = field(default_factory=dict)
    tool_calls_by_hour: Counter = field(default_factory=Counter)
    command_counts: Counter = field(default_factory=Counter)
    command_failures: Counter = field(default_factory=Counter)
    file_types: Counter = field(default_factory=Counter)

    # Model indexes
    model_cost_totals: dict = field(default_factory=dict)
    model_rollups: dict = field(default_factory=dict)

    # Ordered days (filled in after single pass)
    ordered_days: list = field(default_factory=list)

    # Extended data (passed through)
    task_events: list = field(default_factory=list)
    turn_durations: list = field(default_factory=list)
    cursor_codegen: list = field(default_factory=list)
    cursor_commits: list = field(default_factory=list)
    claude_stats_cache: dict = field(default_factory=dict)
    user_messages: list = field(default_factory=list)
    _raw_events: list = field(default_factory=list)

    @property
    def range_info(self) -> dict:
        return {
            "start_local": self.start_local.isoformat(timespec="minutes"),
            "end_local": self.now_local.isoformat(timespec="minutes"),
            "day_count": len(self.ordered_days),
        }


def build_context(
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
) -> AggContext:
    """Single-pass context builder."""
    source_rollups = defaultdict(
        lambda: {
            "source": "",
            "total_tokens": 0,
            "uncached_input": 0,
            "cache_read": 0,
            "cache_write": 0,
            "output": 0,
            "reasoning": 0,
            "messages": 0,
            "sessions": set(),
            "models": Counter(),
            "token_capable": False,
            "cost": 0.0,
            "cost_input": 0.0,
            "cost_cache_read": 0.0,
            "cost_cache_write": 0.0,
            "cost_output": 0.0,
            "cost_reasoning": 0.0,
            "cost_cache_read_full": 0.0,
        }
    )
    daily_rollups = defaultdict(
        lambda: {
            "date": "",
            "label": "",
            "total_tokens": 0,
            "uncached_input": 0,
            "cache_read": 0,
            "cache_write": 0,
            "output": 0,
            "reasoning": 0,
            "messages": 0,
            "cost": 0.0,
            "cost_input": 0.0,
            "cost_cache_read": 0.0,
            "cost_cache_write": 0.0,
            "cost_output": 0.0,
            "cost_reasoning": 0.0,
            "source_totals": defaultdict(int),
            "cost_sources": defaultdict(float),
            "tool_calls": 0,
            "command_successes": 0,
            "command_failures": 0,
        }
    )
    session_rollups = defaultdict(
        lambda: {
            "source": "",
            "session_id": "",
            "first_local": None,
            "last_local": None,
            "total_tokens": 0,
            "uncached_input": 0,
            "cache_read": 0,
            "cache_write": 0,
            "output": 0,
            "reasoning": 0,
            "messages": 0,
            "tool_calls": 0,
            "models": Counter(),
            "cost": 0.0,
        }
    )
    hourly_source_totals = defaultdict(lambda: defaultdict(int))
    weekday_hour_heatmap = defaultdict(lambda: defaultdict(int))
    tool_counts_by_source = defaultdict(Counter)
    tool_sequences = defaultdict(list)
    tool_calls_by_hour = Counter()
    command_counts = Counter()
    command_failures = Counter()
    file_types = Counter()
    model_cost_totals = defaultdict(float)
    model_rollups = defaultdict(
        lambda: {"input_tokens": 0, "output_tokens": 0, "cache_tokens": 0, "cost": 0.0, "messages": 0}
    )

    session_meta_map = {(meta.source, meta.session_id): meta for meta in session_metas}

    # ── Pass 1: events ──
    for event in sorted(events, key=lambda item: item.timestamp):
        local_ts = event.timestamp.astimezone(local_tz)
        date_key = local_ts.date().isoformat()
        day = daily_rollups[date_key]
        day["date"] = date_key
        day["label"] = local_ts.strftime("%m/%d")

        total_tokens = event.total
        cost = event.cost
        cost_breakdown = event.cost_breakdown

        source = source_rollups[event.source]
        source["source"] = event.source
        source["total_tokens"] += total_tokens
        source["uncached_input"] += event.uncached_input
        source["cache_read"] += event.cache_read
        source["cache_write"] += event.cache_write
        source["output"] += event.output
        source["reasoning"] += event.reasoning
        source["messages"] += event.activity_messages
        source["sessions"].add(event.session_id)
        source["models"][event.model] += max(1, event.activity_messages)
        source["token_capable"] = source["token_capable"] or total_tokens > 0
        source["cost"] += cost
        source["cost_input"] += cost_breakdown["input"]
        source["cost_cache_read"] += cost_breakdown["cache_read"]
        source["cost_cache_write"] += cost_breakdown["cache_write"]
        source["cost_output"] += cost_breakdown["output"]
        source["cost_reasoning"] += cost_breakdown["reasoning"]
        source["cost_cache_read_full"] += cost_breakdown["cache_read_full"]

        day["total_tokens"] += total_tokens
        day["uncached_input"] += event.uncached_input
        day["cache_read"] += event.cache_read
        day["cache_write"] += event.cache_write
        day["output"] += event.output
        day["reasoning"] += event.reasoning
        day["messages"] += event.activity_messages
        day["cost"] += cost
        day["cost_input"] += cost_breakdown["input"]
        day["cost_cache_read"] += cost_breakdown["cache_read"]
        day["cost_cache_write"] += cost_breakdown["cache_write"]
        day["cost_output"] += cost_breakdown["output"]
        day["cost_reasoning"] += cost_breakdown["reasoning"]
        day["source_totals"][event.source] += total_tokens
        day["cost_sources"][event.source] += cost

        hourly_source_totals[local_ts.hour][event.source] += total_tokens
        weekday_hour_heatmap[local_ts.weekday()][local_ts.hour] += total_tokens

        session = session_rollups[(event.source, event.session_id)]
        session["source"] = event.source
        session["session_id"] = event.session_id
        session["first_local"] = session["first_local"] or local_ts
        session["last_local"] = local_ts
        session["total_tokens"] += total_tokens
        session["uncached_input"] += event.uncached_input
        session["cache_read"] += event.cache_read
        session["cache_write"] += event.cache_write
        session["output"] += event.output
        session["reasoning"] += event.reasoning
        session["messages"] += event.activity_messages
        session["models"][event.model] += max(1, event.activity_messages)
        session["cost"] += cost

        model_cost_totals[event.model] += cost
        model_data = model_rollups[event.model]
        model_data["input_tokens"] += event.uncached_input
        model_data["cache_tokens"] += event.cache_read + event.cache_write
        model_data["output_tokens"] += event.output + event.reasoning
        model_data["cost"] += cost
        model_data["messages"] += event.activity_messages

    # ── Pass 2: tool_calls ──
    for tool_call in sorted(tool_calls, key=lambda item: item.timestamp):
        local_ts = tool_call.timestamp.astimezone(local_tz)
        date_key = local_ts.date().isoformat()
        day = daily_rollups[date_key]
        day["date"] = date_key
        day["label"] = local_ts.strftime("%m/%d")
        day["tool_calls"] += 1

        tool_counts_by_source[tool_call.source][tool_call.tool_name] += 1
        tool_sequences[(tool_call.source, tool_call.session_id)].append(tool_call.tool_name)
        tool_calls_by_hour[local_ts.hour] += 1

        session = session_rollups[(tool_call.source, tool_call.session_id)]
        session["source"] = tool_call.source
        session["session_id"] = tool_call.session_id
        session["first_local"] = session["first_local"] or local_ts
        session["last_local"] = session["last_local"] or local_ts
        session["first_local"] = min(session["first_local"], local_ts)
        session["last_local"] = max(session["last_local"], local_ts)
        session["tool_calls"] += 1

        if tool_call.file_path:
            file_types[Path(tool_call.file_path).suffix or "(none)"] += 1

        if tool_call.command:
            first_word = tool_call.command.split()[0] if tool_call.command.split() else "(empty)"
            command_counts[first_word] += 1
            if tool_call.exit_code is not None and tool_call.exit_code != 0:
                command_failures[first_word] += 1
                day["command_failures"] += 1
            else:
                day["command_successes"] += 1

    # ── Build ordered_days ──
    ordered_days = []
    cumulative_tokens = 0
    cumulative_cost = 0.0
    current_date = start_local.date()
    while current_date <= now_local.date():
        date_key = current_date.isoformat()
        day = daily_rollups[date_key]
        day["date"] = date_key
        day["label"] = current_date.strftime("%m/%d")
        cumulative_tokens += day["total_tokens"]
        cumulative_cost += day["cost"]
        ordered_days.append(
            {
                "date": day["date"],
                "label": day["label"],
                "total_tokens": day["total_tokens"],
                "uncached_input": day["uncached_input"],
                "cache_read": day["cache_read"],
                "cache_write": day["cache_write"],
                "output": day["output"],
                "reasoning": day["reasoning"],
                "messages": day["messages"],
                "source_totals": dict(day["source_totals"]),
                "cumulative_tokens": cumulative_tokens,
                "cost": _round_money(day["cost"]),
                "cost_sources": {k: _round_money(v) for k, v in day["cost_sources"].items()},
                "cost_cumulative": _round_money(cumulative_cost),
                "cost_input": _round_money(day["cost_input"]),
                "cost_cache_read": _round_money(day["cost_cache_read"]),
                "cost_cache_write": _round_money(day["cost_cache_write"]),
                "cost_output": _round_money(day["cost_output"]),
                "cost_reasoning": _round_money(day["cost_reasoning"]),
                "tool_calls": day["tool_calls"],
                "command_successes": day["command_successes"],
                "command_failures": day["command_failures"],
            }
        )
        current_date += timedelta(days=1)

    return AggContext(
        start_local=start_local,
        now_local=now_local,
        local_tz=local_tz,
        source_rollups=dict(source_rollups),
        daily_rollups=dict(daily_rollups),
        session_rollups=dict(session_rollups),
        session_meta_map=session_meta_map,
        hourly_source_totals=dict(hourly_source_totals),
        weekday_hour_heatmap=dict(weekday_hour_heatmap),
        tool_counts_by_source=dict(tool_counts_by_source),
        tool_sequences=dict(tool_sequences),
        tool_calls_by_hour=tool_calls_by_hour,
        command_counts=command_counts,
        command_failures=command_failures,
        file_types=file_types,
        model_cost_totals=dict(model_cost_totals),
        model_rollups=dict(model_rollups),
        ordered_days=ordered_days,
        task_events=task_events or [],
        turn_durations=turn_durations or [],
        cursor_codegen=cursor_codegen or [],
        cursor_commits=cursor_commits or [],
        claude_stats_cache=claude_stats_cache or {},
        user_messages=user_messages or [],
        _raw_events=events,
    )
