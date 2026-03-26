"""Data classes and pricing for agent usage tracking."""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple


class PricingTier(NamedTuple):
    input: float
    cache_read: float
    cache_write: float
    output: float
    reasoning: float


# ── Hardcoded fallback pricing (used if JSON load fails) ──
_S = PricingTier(3, 0.3, 3.75, 15, 15)
_O = PricingTier(15, 1.5, 18.75, 75, 75)
_H = PricingTier(0.8, 0.08, 1, 4, 4)
_OH = PricingTier(5, 0.5, 6.25, 25, 25)
_G5 = PricingTier(2.5, 0.25, 0, 15, 15)
_G5M = PricingTier(1.1, 0.275, 0, 4.4, 4.4)
_MM = PricingTier(0.29, 0.029, 0.36, 1.16, 1.16)

_FALLBACK_P = {
    "MiniMax-M2": _MM,
    "gpt-5.4": _G5,
    "gpt-5.3-codex-spark": _G5M,
    "gpt-5.3-codex": _G5,
    "gpt-5.2-codex": _G5,
    "gpt-5.2": _G5,
    "gpt-5.1-codex-max": _G5,
    "gpt-5.1-codex-mini": _G5M,
    "gpt-5.1-codex": _G5,
    "gpt-5.1": _G5,
    "gpt-5-codex-mini": _G5M,
    "gpt-5-codex": _G5,
    "gpt-5": _G5,
    "claude-opus-4-6": _OH,
    "claude-sonnet-4-6": _S,
    "claude-opus-4-5": _OH,
    "claude-sonnet-4-5": _S,
    "claude-opus-4-1": _O,
    "claude-opus-4-0": _O,
    "claude-opus-4-2": _O,
    "claude-sonnet-4-0": _S,
    "claude-sonnet-4-2": _S,
    "claude-haiku-4-5": PricingTier(1, 0.1, 1.25, 5, 5),
    "claude-haiku-3-5": _H,
    "claude-3-haiku": PricingTier(0.25, 0.03, 0.3, 1.25, 1.25),
    "claude-3-5-sonnet": _S,
    "claude-3-5-haiku": _H,
    "claude-3-opus": _O,
}


def _load_pricing_json(path: Path) -> dict[str, PricingTier]:
    """Load a pricing JSON file, returning a dict of model -> PricingTier."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for key, value in raw.items():
        if key.startswith("_"):
            continue  # skip metadata keys like _comment
        if (
            isinstance(value, list)
            and len(value) == 5
            and all(isinstance(x, (int, float)) for x in value)
        ):
            result[key] = PricingTier(*value)
    return result


def _build_pricing() -> dict[str, PricingTier]:
    """Build the pricing dict: bundled JSON -> user override -> fallback."""
    # 1. Try loading bundled pricing.json
    bundled_path = Path(__file__).resolve().parent / "data" / "pricing.json"
    try:
        pricing = _load_pricing_json(bundled_path)
    except Exception as exc:
        warnings.warn(f"Failed to load bundled pricing.json, using fallback: {exc}")
        pricing = dict(_FALLBACK_P)

    # 2. Merge user override (takes precedence, always attempted)
    user_path = Path.home() / ".config" / "agent-usage-atlas" / "pricing.json"
    if user_path.is_file():
        try:
            user_pricing = _load_pricing_json(user_path)
            pricing.update(user_pricing)
        except Exception as exc:
            warnings.warn(f"Failed to load user pricing override: {exc}")

    return pricing


_P = _build_pricing()

# Pre-sorted pricing keys by length descending for longest-prefix-first matching
# Keys are pre-lowercased to avoid repeated .lower() calls in _gp()
_P_SORTED = sorted(((k.lower(), v) for k, v in _P.items()), key=lambda kv: len(kv[0]), reverse=True)


@lru_cache(maxsize=256)
def _gp(model: str) -> PricingTier:
    ml = model.lower()
    best_sub = None
    best_sub_len = 0
    for k, v in _P_SORTED:
        if ml.startswith(k) and (len(ml) == len(k) or ml[len(k)] in "-_./ "):
            return v
        if k in ml and len(k) > best_sub_len:
            best_sub = v
            best_sub_len = len(k)
    if best_sub is not None:
        return best_sub
    warnings.warn(f"No pricing for model {model!r}, using default")
    return _S


@dataclass
class UsageEvent:
    source: str
    timestamp: datetime
    session_id: str
    model: str
    uncached_input: int = 0
    cache_read: int = 0
    cache_write: int = 0
    output: int = 0
    reasoning: int = 0
    activity_messages: int = 0
    _total: int = field(init=False, repr=False, compare=False)
    _cost: float = field(init=False, repr=False, compare=False)
    _cost_bd: dict[str, float] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        p = _gp(self.model)
        self._total = self.uncached_input + self.cache_read + self.cache_write + self.output + self.reasoning
        ci = self.uncached_input * p[0] / 1e6
        ccr = self.cache_read * p[1] / 1e6
        ccw = self.cache_write * p[2] / 1e6
        co = self.output * p[3] / 1e6
        cr = self.reasoning * p[4] / 1e6
        self._cost = ci + ccr + ccw + co + cr
        self._cost_bd = {
            "input": ci,
            "cache_read": ccr,
            "cache_write": ccw,
            "output": co,
            "reasoning": cr,
            "cache_read_full": self.cache_read * p[0] / 1e6,
        }

    @property
    def total(self):
        return self._total

    @property
    def cost(self):
        return self._cost

    @property
    def cost_breakdown(self):
        return self._cost_bd


@dataclass
class ToolCall:
    source: str
    timestamp: datetime
    session_id: str
    tool_name: str
    exit_code: int | None = None
    file_path: str | None = None
    command: str | None = None


@dataclass
class SessionMeta:
    source: str
    session_id: str
    cwd: str | None = None
    project: str | None = None
    git_branch: str | None = None


@dataclass
class TurnDuration:
    source: str
    timestamp: datetime
    session_id: str
    duration_ms: int


@dataclass
class TaskEvent:
    source: str
    timestamp: datetime
    session_id: str
    event_type: str  # "started" | "complete"


@dataclass
class CodeGenRecord:
    source: str
    timestamp: datetime
    model: str
    file_extension: str
    conversation_id: str
    gen_source: str  # "composer" | "tab" | "human"


@dataclass
class UserMessage:
    source: str
    timestamp: datetime
    session_id: str
    text: str  # first 200 chars
    char_count: int  # original length


@dataclass
class ScoredCommit:
    commit_hash: str
    commit_date: datetime | None
    lines_added: int = 0
    lines_deleted: int = 0
    composer_added: int = 0
    composer_deleted: int = 0
    human_added: int = 0
    human_deleted: int = 0
    tab_added: int = 0
    tab_deleted: int = 0


@dataclass
class ParseResult:
    events: list[UsageEvent] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    session_metas: list[SessionMeta] = field(default_factory=list)
    turn_durations: list[TurnDuration] = field(default_factory=list)
    task_events: list[TaskEvent] = field(default_factory=list)
    code_gen: list[CodeGenRecord] = field(default_factory=list)
    scored_commits: list[ScoredCommit] = field(default_factory=list)
    user_messages: list[UserMessage] = field(default_factory=list)

    def merge(self, other: ParseResult) -> None:
        self.events.extend(other.events)
        self.tool_calls.extend(other.tool_calls)
        self.session_metas.extend(other.session_metas)
        self.turn_durations.extend(other.turn_durations)
        self.task_events.extend(other.task_events)
        self.code_gen.extend(other.code_gen)
        self.scored_commits.extend(other.scored_commits)
        self.user_messages.extend(other.user_messages)


# Formatting helpers


def fmt_int(v: int) -> str:
    return f"{v:,}"


def fmt_usd(v: float) -> str:
    if v == 0:
        return "$0.00"
    sign = "-" if v < 0 else ""
    av = abs(v)
    return f"{sign}${av:,.0f}" if av >= 1000 else f"{sign}${av:.2f}" if av >= 1 else f"{sign}${av:.4f}"


def fmt_short(v: float | int) -> str:
    if abs(v) >= 1e9:
        return f"{v / 1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"{v / 1e6:.2f}M"
    if abs(v) >= 1e3:
        return f"{v / 1e3:.1f}K"
    return str(v)


def fmt_pct(v: float) -> str:
    """Format a float as a percentage string."""
    if v >= 10:
        return f"{v:.0f}%"
    if v >= 1:
        return f"{v:.1f}%"
    return f"{v:.2f}%"


def fmt_duration(minutes: float) -> str:
    """Format minutes into a human-readable duration."""
    if not math.isfinite(minutes):
        return "N/A"
    if minutes < 1:
        return f"{minutes * 60:.0f}s"
    if minutes < 60:
        return f"{minutes:.0f}m"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h{m:02d}m" if m else f"{h}h"
