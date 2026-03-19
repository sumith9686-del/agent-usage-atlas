"""Vague prompt detection and per-prompt cost ranking."""

from __future__ import annotations

from collections import Counter, defaultdict

VAGUE_SET = frozenset(
    {
        "yes",
        "no",
        "ok",
        "y",
        "n",
        "sure",
        "go",
        "do it",
        "fix it",
        "continue",
        "go ahead",
        "try again",
        "looks good",
        "lgtm",
        "please",
        "thanks",
        "retry",
        "again",
        "run it",
        "proceed",
        "k",
        "yep",
        "yea",
        "yeah",
        "nope",
        "nah",
        "fine",
        "done",
        "next",
        "correct",
        "right",
        "good",
        "great",
        "nice",
        "sounds good",
        "that works",
        "perfect",
        "exactly",
    }
)

_MAX_VAGUE_LEN = 30
_MIN_VAGUE_LEN = 5


def _is_vague(text: str, char_count: int) -> bool:
    if char_count <= _MIN_VAGUE_LEN:
        return True
    if char_count <= _MAX_VAGUE_LEN and text.strip().lower().rstrip(".!?,") in VAGUE_SET:
        return True
    return False


def compute(ctx) -> dict:
    """Compute vague prompt stats and expensive prompt ranking."""
    msgs = ctx.user_messages
    # Events are already sorted by timestamp in _context.py build_context
    events = [e for e in _iter_events(ctx) if e.total > 0]

    # Build session → sorted events index for pairing
    session_events = defaultdict(list)
    for ev in events:
        session_events[(ev.source, ev.session_id)].append(ev)

    # Vague detection
    vague_counter: Counter[str] = Counter()
    vague_count = 0
    total_user_messages = len(msgs)

    # Per-prompt cost tracking
    prompt_costs = []

    for msg in msgs:
        is_v = _is_vague(msg.text, msg.char_count)
        if is_v:
            vague_count += 1
            normalized = msg.text.strip().lower().rstrip(".!?,")
            vague_counter[normalized] += 1

        # Pair with nearest following event in same session
        paired_event = _find_next_event(
            session_events.get((msg.source, msg.session_id), []),
            msg.timestamp,
        )
        if paired_event:
            response_tokens = paired_event.output + paired_event.reasoning
            response_cost = paired_event.cost
            prompt_costs.append(
                {
                    "text": msg.text,
                    "tokens": response_tokens,
                    "cost": response_cost,
                    "model": paired_event.model,
                    "source": msg.source,
                    "timestamp": msg.timestamp.isoformat(timespec="minutes"),
                    "is_vague": is_v,
                }
            )

    # Compute estimated waste from vague prompts
    vague_costs = [p for p in prompt_costs if p["is_vague"]]
    wasted_tokens = sum(p["tokens"] for p in vague_costs)
    wasted_cost = sum(p["cost"] for p in vague_costs)

    vague_ratio = vague_count / total_user_messages if total_user_messages else 0.0

    # Top vague prompts by frequency
    top_vague = [{"text": text, "count": count} for text, count in vague_counter.most_common(20)]

    # Expensive prompts (top 50 by cost, exclude vague)
    expensive = sorted(prompt_costs, key=lambda p: p["cost"], reverse=True)[:50]
    expensive_out = [
        {
            "text": p["text"],
            "tokens": p["tokens"],
            "cost": round(p["cost"], 6),
            "model": p["model"],
            "source": p["source"],
            "timestamp": p["timestamp"],
        }
        for p in expensive
    ]

    return {
        "vague_count": vague_count,
        "total_user_messages": total_user_messages,
        "vague_ratio": round(vague_ratio, 4),
        "estimated_wasted_tokens": wasted_tokens,
        "estimated_wasted_cost": round(wasted_cost, 4),
        "top_vague_prompts": top_vague,
        "expensive_prompts": expensive_out,
    }


def _iter_events(ctx):
    """Return raw UsageEvent objects stashed on context."""
    return ctx._raw_events


def _find_next_event(sorted_events, after_ts):
    """Find the first event with timestamp >= after_ts (binary search)."""
    lo, hi = 0, len(sorted_events)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_events[mid].timestamp < after_ts:
            lo = mid + 1
        else:
            hi = mid
    return sorted_events[lo] if lo < len(sorted_events) else None
