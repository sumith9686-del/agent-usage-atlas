"""Behavioral insights and optimization suggestions."""

from __future__ import annotations


def compute(ctx, prompt_data=None) -> list[dict]:
    """Run all insight rules, return sorted by severity."""
    prompt_data = prompt_data or {}
    rules = [
        _marathon_sessions,
        _model_mismatch,
        _low_cache_rate,
        _vague_prompt_waste,
        _tool_heavy,
        _off_hours,
        _budget_alert,
        _single_source,
        _cmd_failure_rate,
        _context_growth,
    ]
    results = []
    for rule in rules:
        try:
            insight = rule(ctx, prompt_data)
            if insight:
                results.append(insight)
        except Exception:
            pass

    severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    results.sort(key=lambda i: severity_order.get(i["severity"], 9))
    return results


def _marathon_sessions(ctx, _pd) -> dict | None:
    """Sessions longer than 3 hours."""
    long_sessions = []
    for key, sess in ctx.session_rollups.items():
        first, last = sess.get("first_local"), sess.get("last_local")
        if first and last:
            dur_h = (last - first).total_seconds() / 3600
            if dur_h > 3:
                long_sessions.append((key, dur_h))
    if not long_sessions:
        return None
    longest = max(long_sessions, key=lambda x: x[1])
    hours = round(longest[1], 1)
    return {
        "severity": "medium",
        "icon": "fa-hourglass-half",
        "title": f"发现 {len(long_sessions)} 个马拉松会话",
        "title_en": f"{len(long_sessions)} marathon session(s) detected",
        "body": f"最长会话持续 {hours} 小时。长时间连续使用可能导致上下文膨胀和效率下降。",
        "body_en": f"Longest session lasted {hours}h. Extended sessions may cause context bloat and reduced efficiency.",
        "action": "考虑将大任务拆分为多个短会话，每个聚焦一个目标。",
        "action_en": "Consider splitting large tasks into shorter, focused sessions.",
    }


def _model_mismatch(ctx, pd) -> dict | None:
    """Vague prompts primarily used with expensive models (Opus)."""
    expensive = pd.get("expensive_prompts", [])
    if not expensive:
        return None
    # Check if vague prompts are being sent to expensive models
    vague_on_opus = 0
    total_vague = pd.get("vague_count", 0)
    if total_vague < 3:
        return None

    for p in expensive:
        model = (p.get("model") or "").lower()
        if "opus" in model and p.get("cost", 0) > 0:
            vague_on_opus += 1

    if vague_on_opus < 2:
        return None

    return {
        "severity": "high",
        "icon": "fa-money-bill-wave",
        "title": "低质量 Prompt 用了贵模型",
        "title_en": "Vague prompts on expensive models",
        "body": f"检测到 {vague_on_opus} 个简短/模糊提示被发送到 Opus 等高价模型。",
        "body_en": f"{vague_on_opus} short/vague prompts were sent to expensive models like Opus.",
        "action": "对简单确认使用 Haiku/Sonnet，将 Opus 留给复杂推理任务。",
        "action_en": "Use Haiku/Sonnet for simple confirmations, reserve Opus for complex reasoning.",
    }


def _low_cache_rate(ctx, _pd) -> dict | None:
    """Overall cache ratio < 40%."""
    total_input = 0
    total_cache = 0
    for src in ctx.source_rollups.values():
        total_input += src["uncached_input"] + src["cache_read"]
        total_cache += src["cache_read"]
    if total_input == 0:
        return None
    rate = total_cache / total_input
    if rate >= 0.4:
        return None
    pct = round(rate * 100, 1)
    return {
        "severity": "medium",
        "icon": "fa-database",
        "title": f"缓存命中率偏低 ({pct}%)",
        "title_en": f"Low cache hit rate ({pct}%)",
        "body": "缓存命中率低于 40%，意味着大量重复内容未被缓存复用。",
        "body_en": "Cache hit rate is below 40%, meaning repeated content is not being reused.",
        "action": "尝试在同一会话中保持上下文连续性，避免频繁开启新会话。",
        "action_en": "Maintain context continuity within sessions, avoid starting new ones frequently.",
    }


def _vague_prompt_waste(ctx, pd) -> dict | None:
    """Vague ratio > 15%."""
    ratio = pd.get("vague_ratio", 0)
    if ratio <= 0.15:
        return None
    pct = round(ratio * 100, 1)
    wasted = pd.get("estimated_wasted_cost", 0)
    from ..models import fmt_usd
    return {
        "severity": "high",
        "icon": "fa-comment-slash",
        "title": f"模糊提示占比 {pct}%",
        "title_en": f"Vague prompts at {pct}%",
        "body": f"超过 15% 的提示是简短/模糊的，估计浪费 {fmt_usd(wasted)}。",
        "body_en": f"Over 15% of prompts are short/vague, estimated waste: {fmt_usd(wasted)}.",
        "action": "用具体、详细的指令替代 'yes'、'ok'、'do it' 等模糊回复。",
        "action_en": "Replace 'yes', 'ok', 'do it' with specific, detailed instructions.",
    }


def _tool_heavy(ctx, _pd) -> dict | None:
    """Session with tool_calls > 50 but messages < 10."""
    heavy = []
    for key, sess in ctx.session_rollups.items():
        if sess.get("tool_calls", 0) > 50 and sess.get("messages", 0) < 10:
            heavy.append(key)
    if not heavy:
        return None
    return {
        "severity": "low",
        "icon": "fa-gears",
        "title": f"{len(heavy)} 个工具密集型会话",
        "title_en": f"{len(heavy)} tool-heavy session(s)",
        "body": "这些会话工具调用超过 50 次但消息不到 10 条，可能是自动化循环。",
        "body_en": "These sessions had 50+ tool calls but fewer than 10 messages, possibly automated loops.",
        "action": "检查是否存在不必要的工具调用循环，考虑优化 Agent 的工具使用策略。",
        "action_en": "Check for unnecessary tool call loops, consider optimizing the agent's tool strategy.",
    }


def _off_hours(ctx, _pd) -> dict | None:
    """22:00-06:00 token share > 30%."""
    off_hour_tokens = 0
    total_tokens = 0
    for hour, sources in ctx.hourly_source_totals.items():
        hour_total = sum(sources.values())
        total_tokens += hour_total
        if hour >= 22 or hour < 6:
            off_hour_tokens += hour_total
    if total_tokens == 0:
        return None
    ratio = off_hour_tokens / total_tokens
    if ratio <= 0.3:
        return None
    pct = round(ratio * 100, 1)
    return {
        "severity": "info",
        "icon": "fa-moon",
        "title": f"深夜使用占比 {pct}%",
        "title_en": f"Off-hours usage at {pct}%",
        "body": "22:00-06:00 期间的 Token 使用超过总量的 30%。",
        "body_en": "Token usage between 22:00-06:00 exceeds 30% of total.",
        "action": "注意作息平衡。如果是自动化任务，可以考虑在低峰时段运行。",
        "action_en": "Mind work-life balance. If automated, consider scheduling during off-peak hours.",
    }


def _budget_alert(ctx, _pd) -> dict | None:
    """30-day projection > $100."""
    days = ctx.ordered_days
    if not days:
        return None
    total_cost = sum(d["cost"] for d in days)
    active_days = sum(1 for d in days if d["cost"] > 0)
    if active_days == 0:
        return None
    daily_avg = total_cost / active_days
    projection = daily_avg * 30
    if projection <= 100:
        return None
    from ..models import fmt_usd
    return {
        "severity": "high",
        "icon": "fa-fire",
        "title": f"30 天投影 {fmt_usd(projection)}",
        "title_en": f"30-day projection: {fmt_usd(projection)}",
        "body": f"按当前日均花费 {fmt_usd(daily_avg)} 推算，30 天预计花费超过 $100。",
        "body_en": f"At current daily avg {fmt_usd(daily_avg)}, 30-day projected spend exceeds $100.",
        "action": "审查高成本会话和模型选择，考虑使用更经济的模型。",
        "action_en": "Review high-cost sessions and model choices, consider more economical models.",
    }


def _single_source(ctx, _pd) -> dict | None:
    """One source accounts for > 90% of tokens."""
    total = sum(s["total_tokens"] for s in ctx.source_rollups.values())
    if total == 0:
        return None
    for name, src in ctx.source_rollups.items():
        ratio = src["total_tokens"] / total
        if ratio > 0.9:
            pct = round(ratio * 100, 1)
            return {
                "severity": "info",
                "icon": "fa-bullseye",
                "title": f"{name} 占比 {pct}%",
                "title_en": f"{name} dominates at {pct}%",
                "body": f"几乎所有 Token 使用都来自 {name}。",
                "body_en": f"Almost all token usage comes from {name}.",
                "action": "如果你使用多个 Agent，确保日志路径配置正确以获取完整视图。",
                "action_en": "If using multiple agents, ensure log paths are configured correctly for a complete view.",
            }
    return None


def _cmd_failure_rate(ctx, _pd) -> dict | None:
    """Command failure rate > 20%."""
    total_cmds = sum(ctx.command_counts.values())
    total_fails = sum(ctx.command_failures.values())
    if total_cmds < 10:
        return None
    rate = total_fails / total_cmds
    if rate <= 0.2:
        return None
    pct = round(rate * 100, 1)
    # Top failing commands
    top_fails = ctx.command_failures.most_common(3)
    fail_list = ", ".join(f"`{cmd}` ({n})" for cmd, n in top_fails)
    return {
        "severity": "medium",
        "icon": "fa-triangle-exclamation",
        "title": f"命令失败率 {pct}%",
        "title_en": f"Command failure rate: {pct}%",
        "body": f"失败最多: {fail_list}",
        "body_en": f"Top failures: {fail_list}",
        "action": "检查常见失败命令，确保环境依赖和权限配置正确。",
        "action_en": "Check common failing commands, ensure dependencies and permissions are correct.",
    }


def _context_growth(ctx, _pd) -> dict | None:
    """Session where cache_read grew > 10x."""
    growth_sessions = []
    for key, sess in ctx.session_rollups.items():
        cr = sess.get("cache_read", 0)
        ui = sess.get("uncached_input", 0)
        if cr > 0 and ui > 0 and cr / ui > 10:
            growth_sessions.append(key)
    if not growth_sessions:
        return None
    return {
        "severity": "low",
        "icon": "fa-expand",
        "title": f"{len(growth_sessions)} 个会话上下文膨胀",
        "title_en": f"{len(growth_sessions)} session(s) with context bloat",
        "body": "这些会话的缓存读取量远超新输入，表明上下文持续膨胀。",
        "body_en": "These sessions had cache reads far exceeding new input, indicating context growth.",
        "action": "考虑在上下文过大时开启新会话，或使用 /compact 压缩上下文。",
        "action_en": "Consider starting a new session when context grows too large, or use /compact.",
    }
