"""Data classes and pricing for agent usage tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import NamedTuple


class PricingTier(NamedTuple):
    input: float
    cache_read: float
    cache_write: float
    output: float
    reasoning: float


# Model pricing (USD / 1M tokens)
_S = PricingTier(3, 0.3, 3.75, 15, 15)
_O = PricingTier(15, 1.5, 18.75, 75, 75)
_H = PricingTier(0.8, 0.08, 1, 4, 4)
_OH = PricingTier(5, 0.5, 6.25, 25, 25)
_G5 = PricingTier(2.5, 0.25, 0, 15, 15)
_G5M = PricingTier(1.1, 0.275, 0, 4.4, 4.4)
_MM = PricingTier(0.29, 0.029, 0.36, 1.16, 1.16)  # MiniMax CNY÷7.25

_P = {
    # MiniMax family
    "MiniMax-M2": _MM,
    # OpenAI GPT-5 family
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
    # Anthropic Claude family
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


@lru_cache(maxsize=128)
def _gp(model):
    ml = model.lower()
    # Exact prefix match first (longest match wins due to dict order)
    for k, v in _P.items():
        if ml.startswith(k.lower()):
            return v
    # Fallback: substring match
    for k, v in _P.items():
        if k.lower() in ml:
            return v
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

    @property
    def total(self):
        return self.uncached_input + self.cache_read + self.cache_write + self.output + self.reasoning

    @property
    def _pricing(self):
        return _gp(self.model)

    @property
    def cost(self):
        p = self._pricing
        return (
            self.uncached_input * p[0]
            + self.cache_read * p[1]
            + self.cache_write * p[2]
            + self.output * p[3]
            + self.reasoning * p[4]
        ) / 1e6

    @property
    def cost_breakdown(self):
        p = self._pricing
        return {
            "input": self.uncached_input * p[0] / 1e6,
            "cache_read": self.cache_read * p[1] / 1e6,
            "cache_write": self.cache_write * p[2] / 1e6,
            "output": self.output * p[3] / 1e6,
            "reasoning": self.reasoning * p[4] / 1e6,
            "cache_read_full": self.cache_read * p[0] / 1e6,
        }


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


def fmt_int(v):
    return f"{v:,}"


def fmt_usd(v):
    return f"${v:,.0f}" if v >= 1000 else f"${v:.2f}" if v >= 1 else f"${v:.4f}"


def fmt_short(v):
    if abs(v) >= 1e9:
        return f"{v / 1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"{v / 1e6:.2f}M"
    if abs(v) >= 1e3:
        return f"{v / 1e3:.1f}K"
    return str(v)
