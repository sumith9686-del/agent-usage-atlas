# Final Consolidated Opinion -- release/0.3

**Date:** 2026-03-19
**Sources:** 4 expert reviews (Architecture, Security, Performance, Innovation) + 5 patrol reports (Parsers, Aggregation, Charts, Frontend Core, Core)
**Consolidator:** Expert Opinion Consolidator

---

## 1. Executive Summary

The agent-usage-atlas v0.3 codebase is architecturally sound for its scope (local, single-user, stdlib-only dashboard) but carries two critical correctness bugs (UsageEvent mutation in hermit.py producing silently wrong cost data, and a silent-swallow of all exceptions in the server background thread), a confirmed thread-safety race condition in the CLI cache layer, multiple resource leaks, and near-zero test coverage (~5-20% across zones). The innovation portfolio contains 4 high-value proposals (CUSUM anomaly detection, model efficiency scoring, external pricing registry, calendar drill-down) and 3 low-risk improvements (SSE heartbeat, CSS content-visibility, chart factory pattern) that should proceed. Three proposals (Preact activation, asyncio server, incremental aggregation) are unanimously deferred as premature for a local single-user tool. Animated Sankey is rejected on effort/impact grounds. Fix work is divided into three agents: Agent 1 handles critical bugs and security, Agent 2 handles stability and performance, Agent 3 handles approved innovations.

---

## 2. Deduplicated Issue Registry

Issues are deduplicated across all 9 source documents. Confidence = sources_flagging / 9.

| ID | Description | Severity | Confidence | Priority | Sources |
|----|-------------|----------|------------|----------|---------|
| I-01 | **UsageEvent mutation in hermit.py:196-200 and 414-416** -- post-construction field mutation bypasses `__post_init__`, producing stale `cost`, `total`, `_cost_bd` values for all Hermit events | CRITICAL | HIGH (5/9) | **P0** | Architecture, Security, Innovation (indirect), Patrol-Parsers, Patrol-Core (indirect) |
| I-02 | **Background precompute thread silently swallows all exceptions** (`server.py:140-141`) -- persistent pipeline failures produce indefinitely stale dashboard data with zero visibility | CRITICAL | MEDIUM (2/9) | **P0** | Security, Patrol-Core (implicit via error handling analysis) |
| I-03 | **Thread-unsafe `_dashboard_cache` globals** in `cli.py:17-18,30,54-56` -- no lock protects concurrent reads/writes from server request threads and background thread | HIGH | HIGH (4/9) | **P1** | Architecture, Security, Performance, Patrol-Core |
| I-04 | **SQLite connection leak in codex.py:49** -- inline `sqlite3.connect().execute().fetchall()` never closes connection | HIGH | HIGH (4/9) | **P1** | Architecture, Security, Performance, Patrol-Parsers |
| I-05 | **Silent exception swallowing in insights.py:27-28** -- `except Exception: pass` hides bugs in all 10 insight rules | HIGH | HIGH (3/9) | **P1** | Architecture, Security, Patrol-Aggregation |
| I-06 | **Permissive CORS `Access-Control-Allow-Origin: *`** (`server.py:210`) -- any website can read local agent usage data (paths, costs, session IDs) via cross-origin requests | HIGH | LOW (1/9) | **P1** | Security (gap missed by all 5 patrol reports) |
| I-07 | **Silent `except Exception: pass/continue` in parsers** -- 16 instances across codex.py, cursor.py, hermit.py hide real bugs | HIGH | HIGH (4/9) | **P1** | Architecture, Security, Patrol-Parsers, Patrol-Aggregation |
| I-08 | **Duplicated `_active_sessions()` function** -- identical 28-line implementation in `sessions.py:10` and `totals.py:109` | MEDIUM | HIGH (3/9) | **P2** | Architecture, Performance, Patrol-Aggregation |
| I-09 | **`_gp()` model matching is order-dependent** (`models.py:64-74`) -- shorter prefix can match before longer one, assigning wrong pricing tier | MEDIUM | HIGH (3/9) | **P2** | Architecture, Performance, Patrol-Core |
| I-10 | **Unbounded `_JSONL_CACHE` growth** (`_base.py:13`) -- no eviction in serve mode; could reach 500MB-1GB with 300+ days of logs | MEDIUM | HIGH (3/9) | **P2** | Security, Performance, Patrol-Parsers |
| I-11 | **Unbounded `_PAYLOAD_CACHE` growth** (`server.py:26`) -- varying query parameters create unlimited cache entries | MEDIUM | HIGH (3/9) | **P2** | Security, Performance, Patrol-Core |
| I-12 | **Cached dashboard dict mutated in-place** (`cli.py:55`) -- `_meta.generated_at` update on shared cached object; race with concurrent readers | MEDIUM | MEDIUM (2/9) | **P2** | Architecture, Security |
| I-13 | **SQLite connection leak in cursor.py:75-121** -- `conn.close()` unreachable on exception between open and close | MEDIUM | MEDIUM (2/9) | **P2** | Security, Patrol-Charts (implicit) |
| I-14 | **No SSE heartbeat** -- proxies may kill idle connections after 60-120s of inactivity | MEDIUM | HIGH (3/9) | **P2** | Performance, Innovation, Patrol-Core |
| I-15 | **Calendar `nameMap: 'ZH'` hardcoded** in CostCalendar.js and TokenCalendar.js -- English mode displays Chinese month/day names | MEDIUM | MEDIUM (2/9) | **P2** | Architecture, Patrol-Charts |
| I-16 | **Missing data guards in 15+ chart files** -- charts throw if expected nested data path is absent | MEDIUM | MEDIUM (2/9) | **P2** | Architecture, Patrol-Charts |
| I-17 | **Redundant aggregation computation** -- `grand_total`, `grand_cost`, `peak_day`, `_source_cards` computed 2-3x across totals.py, story.py, trends.py | MEDIUM | HIGH (3/9) | **P2** | Architecture, Performance, Patrol-Aggregation |
| I-18 | **Untyped dashboard payload contract** -- no TypedDict or schema for the ~16-key dict between backend and frontend | MEDIUM | HIGH (3/9) | **P2** | Architecture, Performance, Patrol-Core |
| I-19 | **CDN scripts loaded without SRI hashes** (`index.html:8-9`) -- ECharts and FontAwesome from cdn.jsdelivr.net | MEDIUM | MEDIUM (2/9) | **P2** | Security, Patrol-Frontend-Core |
| I-20 | **Unused Preact importmap** (`index.html:10-17`) -- dead CDN requests (~30KB) | LOW | HIGH (3/9) | **P3** | Architecture, Security, Patrol-Frontend-Core |
| I-21 | **Chart config duplication** -- ~300 lines of repeated boilerplate across 37 chart files | LOW | MEDIUM (2/9) | **P3** | Architecture, Patrol-Charts |
| I-22 | **15+ global mutable variables in frontend** -- `data`, `chartCache`, `lang`, etc. not encapsulated | LOW | MEDIUM (2/9) | **P3** | Security, Patrol-Frontend-Core |
| I-23 | **Theme color dual source of truth** -- CSS custom properties AND JS constants define the same colors | LOW | MEDIUM (2/9) | **P3** | Patrol-Charts, Patrol-Frontend-Core |
| I-24 | **Windows incompatibility** -- `fcntl`, `lsof` in server.py unavailable on Windows | LOW | MEDIUM (2/9) | **P3** | Architecture, Patrol-Core |
| I-25 | **`build_dashboard_payload()` lives in cli.py** -- server.py depends on CLI module; should be in `pipeline.py` | LOW | MEDIUM (2/9) | **P3** | Architecture, Patrol-Core |
| I-26 | **Full 37-chart re-render on every SSE update** -- no diffing to skip unchanged charts | MEDIUM | MEDIUM (2/9) | **P2** | Performance, Patrol-Frontend-Core |
| I-27 | **`prompts.py:65-67` re-sorts events** already sorted in `_context.py:184` -- wasted O(n log n) | LOW | MEDIUM (2/9) | **P3** | Performance, Patrol-Aggregation |
| I-28 | **No Content-Security-Policy meta tag** in HTML output | LOW | MEDIUM (2/9) | **P3** | Security, Patrol-Frontend-Core |
| I-29 | **No limit on concurrent SSE connections** -- potential thread exhaustion DoS | MEDIUM | MEDIUM (2/9) | **P2** | Security, Performance |
| I-30 | **Near-zero test coverage** (~5-20% across all zones) | HIGH | HIGH (7/9) | **P1** | Architecture, Security, Performance, Innovation, Patrol-Parsers, Patrol-Aggregation, Patrol-Core |

---

## 3. Innovation Final Verdicts

| Innovation | Architecture | Security | Performance | Innovation Expert | Final Verdict | Reasoning |
|------------|-------------|----------|-------------|-------------------|---------------|-----------|
| **CUSUM cost anomaly detection** | APPROVE | n/a | n/a | GO (P0) | **GO** | Unanimous. ~50 lines stdlib math, additive, graceful degradation. Highest analytical value. Use adaptive threshold. |
| **Model efficiency scoring** | APPROVE | n/a | n/a | GO (P0) | **GO** | Unanimous. Simple arithmetic on existing rollups. Highest user-value innovation. Add capability disclaimer. |
| **External pricing JSON** | APPROVE | n/a | n/a | GO (P0) | **GO** | Unanimous. Low risk, high utility. Bundle default, support user override. |
| **SSE heartbeat** | APPROVE | n/a | P0 | GO (P0) | **GO** | Unanimous. Trivial (~10 lines), immediate reliability gain. |
| **CSS content-visibility:auto** | APPROVE | n/a | P1 | GO (P0) | **GO** | Unanimous. CSS-only, zero risk, progressive enhancement. |
| **Calendar click-to-filter drill-down** | APPROVE (medium feasibility) | n/a | n/a | GO (P1) | **GO** | Unanimous. Well-documented ECharts API. Scope to cost calendar initially. |
| **Chart factory pattern** | APPROVE (high feasibility) | n/a | n/a | GO (as maintenance) | **GO** | Unanimous. Refactoring, not innovation. Implement incrementally (calendars first, then horizontal bars). |
| **JSON Patch differential SSE** | DEFER | n/a | P2 | CONDITIONAL GO | **DEFER to v0.4** | Tiebreaker: Architecture expert's DEFER + Innovation expert's conditions (requires heartbeat first, resync fallback) make this premature for v0.3. Effort underestimated. |
| **Preact activation** | APPROVE with phased rollout | n/a | n/a | NO-GO for v0.3 | **NO-GO** | Innovation expert's NO-GO overrides Architecture's conditional APPROVE. Effort severely underestimated (3-5 days, not 4 hours). Zero Preact code exists. Enormous regression surface. Remove unused importmap instead. |
| **Asyncio server migration** | APPROVE after test coverage | n/a | P3 | NO-GO for v0.3 | **NO-GO** | Both Architecture and Innovation agree: only after test coverage > 60%. This is a single-user local tool; thread-per-connection is not a practical problem. Effort underestimated (4-5 days, not 2). |
| **Incremental aggregation** | DEFER | n/a | P1 long-term | NO-GO for v0.3 | **NO-GO** | Unanimous DEFER. Premature optimization; current pipeline completes in <500ms. Requires co-design with incremental parsing. 7-10 days realistic effort. |
| **Animated Sankey particle flow** | n/a | n/a | n/a | NO-GO | **NO-GO** | Aesthetic only, no analytical value. ECharts `graphic` API not designed for path-following animation. 6-8h effort for decoration. |
| **FS-Event pipeline (kqueue/inotify)** | DEFER | n/a | n/a | n/a (implicit defer) | **NO-GO** | Cross-platform complexity. 30s polling is adequate for local tool. ctypes FFI for file events is fragile. |

---

## 4. Fix Agent 1 Assignment: Critical Bugs and Security

**Scope:** 6 issues, estimated 2-3 hours total.

### 4.1 Issues to Fix

| ID | Issue | File(s) | Acceptance Criteria |
|----|-------|---------|---------------------|
| I-01 | UsageEvent mutation in hermit.py | `parsers/hermit.py:196-200, 414-416` | All `UsageEvent` field updates create new instances via constructor. No post-construction assignment to `uncached_input`, `cache_read`, `cache_write`, `output`, `timestamp`. Verify `__post_init__` runs on each new instance. |
| I-02 | Background thread silent exception swallowing | `server.py:140-141` | `except Exception` block logs full traceback to stderr. Persistent failures are visible in server output. |
| I-06 | Permissive CORS header | `server.py:210` | `Access-Control-Allow-Origin: *` header removed entirely (localhost server needs no CORS). |
| I-04 | SQLite connection leak in codex.py | `parsers/codex.py:49` | `sqlite3.connect()` wrapped in `with` context manager. |
| I-13 | SQLite connection leak in cursor.py | `parsers/cursor.py:75-121` | Connection wrapped in `try/finally` ensuring `conn.close()`. |
| I-05 | Silent exception in insights.py | `aggregation/insights.py:27-28` | `except Exception` replaced with `except Exception as exc: warnings.warn(f"Insight rule {rule.__name__} failed: {exc}")`. |

### 4.2 Files to Touch
- `src/agent_usage_atlas/parsers/hermit.py`
- `src/agent_usage_atlas/parsers/codex.py`
- `src/agent_usage_atlas/parsers/cursor.py`
- `src/agent_usage_atlas/server.py`
- `src/agent_usage_atlas/aggregation/insights.py`

### 4.3 Dependencies
- None. Agent 1 can begin immediately and must complete before Agent 3 starts (innovations depend on correct data).

---

## 5. Fix Agent 2 Assignment: Stability, Performance, and Quality

**Scope:** 13 issues, estimated 6-8 hours total.

### 5.1 Issues to Fix

| ID | Issue | File(s) | Acceptance Criteria |
|----|-------|---------|---------------------|
| I-03 | Thread-unsafe `_dashboard_cache` | `cli.py:17-18, 30, 54-56, 78-79` | Add `threading.Lock` around all reads and writes to `_dashboard_cache` and `_dashboard_cache_key`. OR eliminate CLI-level caching and use server-level cache exclusively. |
| I-07 | Silent `except Exception: pass` (16 instances) | `parsers/codex.py:53,77,80`, `parsers/cursor.py:103,122`, `parsers/hermit.py:129,132,165,233,269,331`, `server.py:140` (if not fixed by Agent 1) | All `except Exception: pass` replaced with `except Exception as exc: warnings.warn(...)` at minimum. Accept: `hermit.py:132` (conn.close cleanup) and `_base.py:40,44` (skip corrupt lines) may remain as-is. |
| I-08 | Duplicated `_active_sessions()` | `aggregation/totals.py:109`, `aggregation/sessions.py:10` | `totals.py` imports `_active_sessions` from `sessions.py`. Duplicate removed. |
| I-09 | `_gp()` order-dependent matching | `models.py:64-74` | `_P.items()` sorted by key length descending before prefix scan in `_gp()`. Longest match wins deterministically. |
| I-10 | Unbounded `_JSONL_CACHE` | `parsers/_base.py:13` | LRU eviction added; max 200 entries. Oldest by access time evicted. |
| I-11 | Unbounded `_PAYLOAD_CACHE` | `server.py:26` | Max 8 entries; LRU eviction. |
| I-12 | Cached dict mutated in-place | `cli.py:55` | Return a shallow copy of cached dict with updated `_meta.generated_at` instead of mutating the cached object. |
| I-14 | No SSE heartbeat | `server.py` (`_write_stream`) | Send `": heartbeat\n\n"` every 15 seconds during SSE idle periods. |
| I-15 | Calendar `nameMap: 'ZH'` hardcoded | `frontend/charts/CostCalendar.js`, `frontend/charts/TokenCalendar.js` | `nameMap` uses `lang` variable: `'ZH'` when `lang === 'zh'`, omitted/`'en'` otherwise. |
| I-17 | Redundant aggregation computation | `aggregation/_context.py`, `aggregation/totals.py`, `aggregation/story.py` | `grand_total`, `grand_cost`, `grand_cache_read`, `grand_cache_write`, `peak_day`, `cost_peak_day` precomputed in `AggContext` during `build_context`. Downstream modules read from context instead of re-computing. |
| I-27 | Redundant sort in prompts.py | `aggregation/prompts.py:65-67` | Remove redundant `sorted()` call; use events already sorted in `_context.py`. |
| I-29 | No SSE connection limit | `server.py` | Add a counter; reject with 503 when exceeding 10 concurrent SSE connections. |
| I-20 | Unused Preact importmap | `frontend/index.html:10-17` | Remove the `<script type="importmap">` block and associated Preact/htm references. |

### 5.2 Files to Touch
- `src/agent_usage_atlas/cli.py`
- `src/agent_usage_atlas/server.py`
- `src/agent_usage_atlas/models.py`
- `src/agent_usage_atlas/parsers/_base.py`
- `src/agent_usage_atlas/parsers/codex.py`
- `src/agent_usage_atlas/parsers/cursor.py`
- `src/agent_usage_atlas/parsers/hermit.py`
- `src/agent_usage_atlas/aggregation/_context.py`
- `src/agent_usage_atlas/aggregation/totals.py`
- `src/agent_usage_atlas/aggregation/story.py`
- `src/agent_usage_atlas/aggregation/prompts.py`
- `src/agent_usage_atlas/aggregation/sessions.py`
- `src/agent_usage_atlas/frontend/index.html`
- `src/agent_usage_atlas/frontend/charts/CostCalendar.js`
- `src/agent_usage_atlas/frontend/charts/TokenCalendar.js`

### 5.3 Dependencies
- Agent 1 must complete first (I-01 fix in hermit.py must land before Agent 2 touches the same file for I-07).
- I-14 (SSE heartbeat) should land before Agent 3's innovations that depend on live mode.

---

## 6. Fix Agent 3 Assignment: Approved Innovations

**Scope:** 7 innovations, estimated 5-7 days total.

### 6.1 Phase 1: Quick Wins (1-2 days)

| Innovation | File(s) | Acceptance Criteria |
|------------|---------|---------------------|
| **SSE heartbeat** | `server.py` | (If not done by Agent 2) `": heartbeat\n\n"` sent every 15s. |
| **CSS content-visibility:auto** | `frontend/styles/main.css` | `content-visibility: auto` and `contain-intrinsic-size` applied to `.section-more` and `.section-wrap.collapsed`. |
| **CUSUM cost anomaly detection** | `aggregation/insights.py` | New `_cost_anomaly_cusum` insight rule. Uses adaptive threshold (scaled to data variance). Minimum 7 active days required. Graceful `None` return if insufficient data. |
| **Model efficiency scoring** | `aggregation/insights.py` | New `_model_efficiency_ranking` insight rule. Reports cost-per-1K-output-token ratio. Only fires when efficiency gap >= 3x. Includes disclaimer about capability differences. |

### 6.2 Phase 2: Core Infrastructure (2-3 days)

| Innovation | File(s) | Acceptance Criteria |
|------------|---------|---------------------|
| **External pricing JSON** | `models.py`, new `data/pricing.json`, `cli.py` | Default `pricing.json` bundled. Loaded at import. User override from `~/.config/agent-usage-atlas/pricing.json`. `_gp()` fuzzy matching preserved. Optional `update-prices` subcommand. |
| **Calendar click-to-filter drill-down** | `frontend/charts/CostCalendar.js`, `frontend/charts/DailyCostChart.js`, `frontend/charts/CostBreakdownChart.js`, `frontend/lib/store.js` | Click on cost calendar day cell filters connected charts to that day. "Reset filter" affordance provided. Scoped to cost family initially (cost calendar -> daily cost -> cost breakdown). |

### 6.3 Phase 3: Refactoring (1-2 days)

| Innovation | File(s) | Acceptance Criteria |
|------------|---------|---------------------|
| **Chart factory pattern** | New `frontend/lib/chart-factories.js`, `frontend/charts/CostCalendar.js`, `frontend/charts/TokenCalendar.js`, `frontend/charts/ToolRanking.js`, `frontend/charts/TopCommands.js`, `frontend/charts/ProjectRanking.js`, `frontend/charts/BranchActivity.js`, `frontend/charts/ModelCostChart.js`, `frontend/charts/CodegenModel.js` | `makeCalendarHeatmap()` and `makeHorizontalBar()` factory functions created. Calendar charts and 6 horizontal bar charts refactored to use factories. Data guards built into factory functions. Net reduction of at least 100 lines. |

### 6.4 Files to Touch
- `src/agent_usage_atlas/aggregation/insights.py`
- `src/agent_usage_atlas/models.py`
- `src/agent_usage_atlas/cli.py`
- `src/agent_usage_atlas/server.py`
- `src/agent_usage_atlas/frontend/styles/main.css`
- `src/agent_usage_atlas/frontend/lib/store.js`
- `src/agent_usage_atlas/frontend/charts/CostCalendar.js`
- `src/agent_usage_atlas/frontend/charts/TokenCalendar.js`
- `src/agent_usage_atlas/frontend/charts/DailyCostChart.js`
- `src/agent_usage_atlas/frontend/charts/CostBreakdownChart.js`
- `src/agent_usage_atlas/frontend/charts/ToolRanking.js` (and 5 other horizontal bar charts)
- New: `src/agent_usage_atlas/data/pricing.json`
- New: `src/agent_usage_atlas/frontend/lib/chart-factories.js`

### 6.5 Dependencies
- Agent 1 must complete (correct cost data required for CUSUM and efficiency scoring).
- Agent 2's I-15 (calendar i18n fix) should land before Agent 3 refactors calendar charts via factory pattern.
- Agent 2's I-14 (SSE heartbeat) should land before or with Agent 3's Phase 1.
- Agent 2's I-17 (precomputed aggregation values) should land before Agent 3's CUSUM/efficiency insights if they read from context.

---

## 7. Quality Gate Criteria

All three agents' work must pass these gates before any commit to the release branch:

### Gate 1: Correctness
- [ ] `python -m agent_usage_atlas` completes without errors on a system with Hermit, Claude, and Codex logs
- [ ] Hermit source cost values in generated dashboard match manual calculation from raw log data (validates I-01 fix)
- [ ] No `warnings.warn` output from insight rules during normal operation (validates I-05 fix)

### Gate 2: Stability
- [ ] `python -m agent_usage_atlas --serve --interval 5` runs for 10 minutes without memory growth exceeding 50MB above baseline (validates I-10, I-11)
- [ ] Server stderr shows no unhandled exception tracebacks during normal operation
- [ ] Server handles 5 concurrent SSE clients without thread-related errors (validates I-03, I-29)

### Gate 3: Security
- [ ] No `Access-Control-Allow-Origin` header in server responses (validates I-06)
- [ ] `sqlite3.connect()` calls all use context managers or try/finally (validates I-04, I-13)

### Gate 4: Frontend
- [ ] Dashboard renders correctly in both `lang=zh` and `lang=en` modes -- calendar charts show correct locale labels (validates I-15)
- [ ] Collapsing/expanding sections does not cause JavaScript errors (validates I-16 via factory guards)
- [ ] No network requests to `esm.sh` (validates I-20 Preact importmap removal)

### Gate 5: Innovation
- [ ] CUSUM insight fires on synthetic test data with a known cost spike
- [ ] Model efficiency insight fires when two models differ by >= 3x in cost-per-output-token
- [ ] Calendar drill-down filters connected charts and provides reset affordance
- [ ] `pricing.json` is loadable and `_gp()` returns correct tiers for all models in the current `_P` dict

---

## 8. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | **Hermit parser fix breaks Hermit data flow** -- creating new UsageEvent instances instead of mutating may miss edge cases in the dedup/supplement logic | Medium | High | Agent 1 must trace all code paths that reference `existing` and `db_evt` after mutation points. Verify that replacement events are correctly inserted into both `out` list and lookup dicts (`db_conversation_events`, etc.). Test with real Hermit DB data. |
| R2 | **Chart factory refactor introduces visual regressions** -- 8+ chart files modified simultaneously | Medium | Medium | Agent 3 implements factories incrementally (2 calendar charts first, verify, then 6 horizontal bars). Screenshot comparison before/after for each chart. |
| R3 | **External pricing JSON format instability** -- LiteLLM's `model_prices_and_context_window.json` format may change without notice | Low | Medium | Bundle a static `pricing.json` as the default. LiteLLM fetch is an optional CLI command, not automatic. Fallback to bundled pricing on fetch failure. |
| R4 | **CUSUM false alarms** -- fixed threshold parameters may alarm on normal high-variance users | Medium | Low | Use adaptive threshold scaled to user's own data distribution. Require minimum 14 active days. Surface as "info" severity initially, not "critical." |
| R5 | **Agent coordination conflicts** -- Agents 1, 2, and 3 touch overlapping files (hermit.py, server.py, insights.py, calendar charts) | Medium | Medium | Strict sequencing: Agent 1 completes fully before Agent 2 begins. Agent 2 completes I-15 (calendar i18n) before Agent 3 starts Phase 3 (chart factory). Agent 3 Phase 1 (insights.py innovations) can run after Agent 1's I-05 fix lands. |

---

## Appendix: Source Concordance Matrix

For each critical/high issue, which sources flagged it:

| Issue | Arch | Security | Perf | Innovation | P-Parsers | P-Agg | P-Charts | P-FE | P-Core |
|-------|------|----------|------|-----------|-----------|-------|----------|------|--------|
| I-01 UsageEvent mutation | CRITICAL | CRITICAL | -- | indirect | MEDIUM* | -- | -- | -- | -- |
| I-02 Background thread swallow | -- | CRITICAL | -- | -- | -- | -- | -- | -- | implicit |
| I-03 Cache thread safety | CRITICAL | MEDIUM | mentioned | -- | -- | -- | -- | -- | HIGH |
| I-04 Codex SQLite leak | HIGH | HIGH | P3 | -- | CRITICAL | -- | -- | -- | -- |
| I-05 Insights exception swallow | -- | HIGH | -- | -- | -- | CRITICAL | -- | -- | -- |
| I-06 CORS wildcard | -- | HIGH | -- | -- | -- | -- | -- | -- | -- |
| I-07 Silent except pass (16x) | MEDIUM | HIGH | -- | -- | MEDIUM | MEDIUM | -- | -- | -- |
| I-30 Test coverage gap | HIGH | implicit | implicit | mentioned | HIGH | HIGH | -- | -- | HIGH |

*Patrol-Parsers rated I-01 as MEDIUM; all expert reviewers escalated to CRITICAL after confirming the stale-cost impact. The CRITICAL rating is adopted as the final assessment.
