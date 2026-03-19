# Expert Review: Architecture & Design Patterns

**Reviewer:** Architecture & Design Patterns Expert
**Date:** 2026-03-19
**Scope:** All 5 patrol zone reports + source code validation
**Release:** 0.3

---

## Executive Summary

The agent-usage-atlas project implements a clean linear pipeline (parse -> aggregate -> render) with well-separated module boundaries. The architecture is remarkably effective for its scope: a zero-dependency, single-file HTML dashboard generator. However, several structural concerns threaten scalability and correctness as the project grows. The most critical issues are: (1) a correctness bug from dataclass mutation in the hermit parser, (2) untyped dashboard payload contract between backend and frontend, (3) dual caching layers with potential coherence risks, and (4) significant code duplication across both Python aggregation modules and JavaScript chart files.

**Total Score: 47/70**

---

## Dimension 1: Module Boundary Integrity — 7/10

### Strengths

The project has clear top-level boundaries: `parsers/`, `aggregation/`, `frontend/`, `renderers/`, plus core files (`models.py`, `cli.py`, `server.py`, `builder.py`). Each parser is a self-contained module producing the shared `ParseResult` dataclass. The aggregation package uses a clean `AggContext` intermediary that all submodules consume.

The `parsers/__init__.py` acts as a proper facade, exposing only `parse_all()` and path constants. The `aggregation/__init__.py` similarly exposes only `aggregate()`. These are well-defined module boundaries.

### Issues

**Coupling between `cli.py` and `server.py`:** `server.py` imports `build_dashboard_payload` from `cli.py` (line 23). This creates a dependency where the server depends on the CLI module. `build_dashboard_payload()` is the true orchestration function and should live in its own module (e.g., `pipeline.py` or `core.py`), not in `cli.py`.

- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/cli.py:23-80`
- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/server.py:23`

**Implicit cross-module dependency in frontend:** JavaScript files depend on global variables defined in other files, with correctness depending on alphabetical file ordering in `builder.py:29`. For example, `charts.js` defines `_isLight()` which `utils.js` and chart files depend on. This is a fragile implicit contract.

- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/builder.py:29`

**Parser path constants exported through multiple layers:** `CODEX_ROOTS`, `CLAUDE_ROOT`, etc. are defined in individual parsers, re-exported from `parsers/__init__.py`, then imported by `server.py` for file signature scanning. This creates a tight coupling between the server's change-detection mechanism and parser internals.

- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/parsers/__init__.py:11-14`
- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/server.py:24`

### Recommendations

| Priority | Recommendation |
|----------|---------------|
| HIGH | Extract `build_dashboard_payload()` from `cli.py` into a dedicated `pipeline.py` module to decouple server from CLI |
| MEDIUM | Introduce explicit JS dependency declaration (numeric prefixes or manifest) instead of relying on alphabetical ordering |
| LOW | Consider a `registry.py` that owns all parser path constants, reducing re-export chains |

---

## Dimension 2: Design Pattern Consistency — 6/10

### Strengths

**Parser pattern:** All four parsers follow a consistent pattern: `parse(start_utc, now_utc) -> ParseResult`. They all use the two-tier caching system (`result_cache_get`/`result_cache_set`). The `ParseResult.merge()` pattern for combining concurrent results is clean.

**Aggregation compute pattern:** All aggregation submodules follow `compute(ctx: AggContext) -> dict`, creating a uniform interface. The single-pass context builder in `_context.py` is an effective Mediator pattern.

**Chart render pattern:** Every chart file exports a single `renderXxx()` function with the same shape: `initChart(id) -> setOption(...)`. The `chartTheme()` base object acts as a Template Method base.

### Issues

**Inconsistent parser signatures:** `cursor.parse(start_utc, now_utc, local_tz)` takes an extra parameter while others take two. The `parsers/__init__.py:30` call shows this inconsistency:

```python
pool.submit(codex.parse, start_utc, now_utc): "codex",
pool.submit(claude.parse, start_utc, now_utc): "claude",
pool.submit(cursor.parse, start_utc, now_utc, local_tz): "cursor",  # extra arg
pool.submit(hermit.parse, start_utc, now_utc): "hermit",
```

- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/parsers/__init__.py:27-31`

**Violation of immutability (CRITICAL):** The hermit parser mutates `UsageEvent` fields after construction (lines 196-200), bypassing `__post_init__()`. This means `_total`, `_cost`, and `_cost_bd` become stale. The `UsageEvent` dataclass computes these derived values in `__post_init__` (models.py:90-107) and exposes them as properties. Post-construction mutation breaks the invariant.

- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/parsers/hermit.py:196-200`
- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/models.py:90-107`

**`ParseResult.merge()` mutates in-place:** The `merge()` method uses `extend()` to mutate the target object (models.py:202-210). While functional in the current context (the target is a fresh instance created in `parse_all`), this violates the immutability principle. A `merge_results(*results) -> ParseResult` classmethod returning a new instance would be safer.

- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/models.py:202-210`

**No Strategy or Factory pattern for parsers:** Parsers are hardcoded in `parse_all()`. Adding a new parser requires modifying `__init__.py` (adding import + submit call), `server.py` (adding path iteration in `_iter_payload_files`), and re-exporting path constants. A parser registry pattern would allow self-registration.

**Missing data guard consistency in charts:** Only ~6 of 37 chart files check for missing data before rendering. This means 15+ charts will throw if their expected data section is absent (e.g., `data.working_patterns.heatmap` in Heatmap.js). No consistent guard pattern exists.

**Dual error handling philosophies:** Parsers use `except Exception: pass` (16 instances across 4 files) while `parsers/__init__.py:40-41` properly logs with `warnings.warn()`. The aggregation layer's `insights.py:27-28` also silently swallows exceptions. This inconsistency masks bugs in some paths while surfacing them in others.

### Recommendations

| Priority | Recommendation |
|----------|---------------|
| CRITICAL | Fix hermit parser mutation: create new `UsageEvent` instances instead of mutating existing ones |
| HIGH | Standardize parser signatures to `(start_utc, now_utc) -> ParseResult` |
| HIGH | Standardize chart data guards with a common pattern or wrapper |
| MEDIUM | Introduce a parser registry/factory for self-registration |
| MEDIUM | Replace bare `except Exception: pass` with `warnings.warn()` across all 16 instances |
| LOW | Make `ParseResult.merge()` return a new instance instead of mutating |

---

## Dimension 3: Data Flow Architecture — 7/10

### Strengths

The pipeline is genuinely linear and clean:

```
parse_all() -> ParseResult + claude_stats_cache
  -> build_dashboard_payload() applies date range logic
    -> aggregate() builds AggContext then runs all compute modules
      -> returns dashboard payload dict
        -> build_html() injects into template OR server serves as JSON/SSE
```

The `AggContext` dataclass is a well-designed intermediary. The single-pass context builder (`_context.py:build_context`) processes all events, tool calls, and session metas in one iteration, then downstream modules (`totals.py`, `sessions.py`, `patterns.py`, etc.) consume the pre-computed rollups.

The ETag-based change detection in `server.py` prevents redundant SSE pushes. The double-check pattern (re-computing file signature after build, line 122) handles the TOCTOU race condition.

### Issues

**Untyped payload contract:** The dashboard dict returned by `aggregate()` is the single contract between backend and frontend. It contains ~16 top-level keys, each with nested structures. This contract is entirely untyped -- no `TypedDict`, no JSON Schema, no validation. A field rename in any aggregation module silently breaks the corresponding chart.

- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/aggregation/__init__.py:41-59`

**Redundant computation across aggregation modules:** The patrol reports correctly identified that `totals.py` and `story.py` both iterate `ordered_days` to compute grand totals. Additionally, `_active_sessions()` is duplicated between `sessions.py:10` and `totals.py:109` (28 lines each, confirmed identical). This duplication means the same expensive iteration happens multiple times per aggregation cycle.

- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/aggregation/totals.py:109`
- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/aggregation/sessions.py:10`

**Dual caching with coherence risk:** `cli.py` maintains `_dashboard_cache` (module-level globals, lines 17-18) while `server.py` maintains `_PAYLOAD_CACHE` (line 26). Both cache the dashboard payload but with different invalidation strategies. The CLI cache is keyed on `(days, since, start_utc)` and invalidated by the `changed` flag from parser caches. The server cache is keyed on `(days, since)` and invalidated by file signatures. In theory they layer correctly (server checks files, CLI checks parse results), but the `_dashboard_cache` globals in `cli.py` are **not protected by any lock**, yet `build_dashboard_payload()` is called from server request threads.

- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/cli.py:17-18,30,54-56`
- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/server.py:26-27,112`

**`generated_at` mutation on cache hit:** When `build_dashboard_payload()` returns a cached result, it mutates the cached dict to update `_meta.generated_at` (cli.py:55). This modifies a shared cached object, which in a concurrent server context could cause one thread's response to see another thread's timestamp.

- File: `/Users/beta/work/agent-usage-atlas/src/agent_usage_atlas/cli.py:55`

### Recommendations

| Priority | Recommendation |
|----------|---------------|
| CRITICAL | Add threading lock to `_dashboard_cache` in `cli.py`, or move caching exclusively to `server.py` |
| HIGH | Define a `DashboardPayload` TypedDict for the aggregate return value |
| HIGH | Deduplicate `_active_sessions()` -- `totals.py` should import from `sessions.py` |
| MEDIUM | Stop mutating cached dict on cache hit (cli.py:55) -- return a shallow copy with updated meta |
| MEDIUM | Precompute shared aggregates (grand totals) in `AggContext` to avoid redundant iteration |

---

## Dimension 4: Extensibility & Plugin Architecture — 6/10

### Strengths

Adding a new aggregation module is straightforward: create a new file in `aggregation/`, add a `compute(ctx) -> dict` function, and add a single line in `aggregation/__init__.py`. The `AggContext` provides all needed data.

The chart architecture is similarly extensible: create a new `.js` file in `frontend/charts/`, add a container in `index.html`, and register it in `main.js`. The alphabetical file ordering means no build configuration changes.

The `ParseResult` dataclass with its typed field lists (`events`, `tool_calls`, `session_metas`, etc.) makes it clear what data types flow through the system.

### Issues

**Adding a new parser requires 4 file edits:**
1. Create `parsers/new_agent.py` with a `parse()` function
2. Edit `parsers/__init__.py` to import and register
3. Edit `server.py`'s `_iter_payload_files()` to include new log paths
4. Re-export path constants

A self-registering parser pattern (decorator-based or entry-point-based) would reduce this to a single-file change.

**Adding a new data type to ParseResult requires changes across 3 layers:**
1. Add field to `ParseResult` dataclass
2. Update `merge()` method
3. Thread the new field through `build_dashboard_payload()` -> `aggregate()` -> `build_context()`

The recent additions of `task_events`, `turn_durations`, `code_gen`, `scored_commits`, and `user_messages` each required this multi-layer threading. A more extensible approach would be a generic `extras: dict[str, list]` field.

**Chart factory pattern missing:** The patrol-charts report correctly identified that 6 horizontal bar charts, 2 calendar heatmaps, 2 Sankey charts, and 3 stacked bar+line charts share 80%+ of their configuration. No factory or builder abstraction exists to reduce this duplication (~300 lines of redundant config).

**No plugin hooks for the aggregation pipeline:** The aggregation modules are statically imported. If a user wanted to add custom insights or metrics, they would need to modify `aggregation/__init__.py`. A plugin system (even a simple directory-scan approach) would enable extensibility without code modification.

### Recommendations

| Priority | Recommendation |
|----------|---------------|
| HIGH | Create chart factory functions: `makeHorizontalBar()`, `makeCalendarHeatmap()`, `makeStackedBarLine()` |
| MEDIUM | Implement parser self-registration pattern (decorator or registry dict) |
| MEDIUM | Add a generic `extras` dict to `ParseResult` to avoid the multi-layer threading problem for new data types |
| LOW | Consider a plugin directory scan for custom aggregation/insight modules |

---

## Dimension 5: Cross-Zone Dependency Analysis — 7/10

### Patrol-Proposed Innovations Summary

| Zone | Proposed Innovation |
|------|-------------------|
| Core | asyncio server migration, external pricing registry, incremental aggregation |
| Parsers | Incremental JSONL parsing (byte-offset tracking), adaptive parser fingerprinting |
| Aggregation | CUSUM anomaly detection, model efficiency scoring |
| Charts | Chart factory pattern, interactive drill-down, animated Sankey flow |
| Frontend Core | Preact activation, CSS paint containment, differential streaming |

### Conflict Analysis

**1. asyncio server (Core) vs. Preact activation (Frontend Core): NO CONFLICT**

These operate at different layers. The asyncio migration affects `server.py`'s HTTP handling and SSE streaming. Preact activation affects client-side rendering. They are independent and can be implemented in any order. However, if differential streaming (JSON Patch) is implemented, it requires changes in both `server.py` (producing patches) and the frontend (applying patches). This creates a coordinated dependency but not a conflict.

**Verdict:** Compatible. Implement asyncio first, then differential streaming which spans both zones.

**2. Incremental aggregation (Core) vs. CUSUM anomaly detection (Aggregation): POTENTIAL CONFLICT**

CUSUM requires access to the full historical cost time series to compute running means, standard deviations, and cumulative sums. Incremental aggregation proposes maintaining running accumulators and only processing deltas. If incremental aggregation only maintains rollups (sums, counts), the raw daily cost history needed by CUSUM would be lost.

**Resolution:** The CUSUM insight currently reads from `ctx.ordered_days`, which is built from `daily_rollups` in `_context.py`. If incremental aggregation preserves `ordered_days` as an append-only structure (new days appended, existing days updated in-place), CUSUM can still function. The conflict is avoidable but requires careful design.

**Verdict:** Conditionally compatible. Incremental aggregation must preserve the full `ordered_days` list, not just running totals.

**3. Chart factory pattern (Charts) vs. data guard improvements (Charts): SYNERGISTIC**

The chart factory pattern is the ideal place to centralize data guards. Instead of adding guards to 37 individual files, the factory functions can include guards by default (e.g., `makeHorizontalBar({dataPath: 'tooling.ranking', ...})` automatically checks that `data.tooling?.ranking` exists).

**Verdict:** Strongly synergistic. Implement factory first, include guards in factory.

**4. Incremental JSONL parsing (Parsers) vs. incremental aggregation (Core): DEPENDENCY**

Incremental aggregation depends on incremental parsing to provide deltas. If parsers still return full `ParseResult` objects (not deltas), the aggregation layer has no way to know what's new. These must be designed together.

**Verdict:** Hard dependency. Must be co-designed. Implement incremental parsing first, then incremental aggregation.

**5. External pricing registry (Core) vs. model efficiency scoring (Aggregation): SYNERGISTIC**

The model efficiency insight (`_model_efficiency_ranking`) scores models by cost-per-output-token. If pricing moves to an external JSON file, the efficiency scores automatically stay current with pricing changes. No code modification needed when prices change.

**Verdict:** Strongly synergistic.

### Hidden Dependencies Missed by Patrol Agents

**A. `_dashboard_cache` thread safety:** The patrol-core report mentions this as "Issue 2" but does not flag it as blocking for the asyncio migration. In an asyncio server, the cache would need to be protected differently (no threading locks needed, but coroutine-safe access patterns required). This is a hidden dependency between the asyncio proposal and the existing cache architecture.

**B. Preact activation vs. chart lazy loading:** The current lazy loading system uses `IntersectionObserver` + `registerLazy()` with a global `lazyRendered` set. If Preact manages component lifecycle, the lazy loading mechanism would need to integrate with Preact's render cycle. The patrol agents proposed both independently without noting this integration requirement.

**C. SSE heartbeat vs. differential streaming:** The core patrol proposes SSE heartbeats (P1) and the frontend-core patrol proposes differential streaming. If both are implemented, the heartbeat interval and the differential patch interval must be coordinated to avoid sending patches more frequently than the heartbeat, which would make heartbeats redundant.

**D. Calendar i18n fix vs. chart factory:** The charts patrol identified a `nameMap: 'ZH'` hardcoding bug in both calendar charts. If the chart factory is implemented first, this fix needs to be in the factory, not patched in the individual files.

### Recommendations

| Priority | Recommendation |
|----------|---------------|
| HIGH | Co-design incremental parsing and incremental aggregation as a single feature |
| MEDIUM | Ensure incremental aggregation preserves `ordered_days` for CUSUM compatibility |
| MEDIUM | Implement chart factory before individual chart fixes to avoid double-work |
| LOW | Coordinate SSE heartbeat and differential streaming intervals |

---

## Dimension 6: Technical Debt Assessment — 7/10

### Load-Bearing Technical Debt

These debts are structural and affect correctness or stability:

| Debt | Severity | Files | Impact |
|------|----------|-------|--------|
| Untyped dashboard payload contract | HIGH | `aggregation/__init__.py`, all chart files | Silent breakage on schema changes |
| `UsageEvent` mutation in hermit parser | CRITICAL | `parsers/hermit.py:196-200` | Incorrect cost/total values for Hermit events |
| Thread-unsafe `_dashboard_cache` in cli.py | HIGH | `cli.py:17-18,30,54-56` | Potential data races in server mode |
| `_gp()` order-dependent prefix matching | MEDIUM | `models.py:64-74` | Wrong pricing tier for some model name variants |
| SQLite connection leak in codex parser | MEDIUM | `parsers/codex.py:49` | File handle exhaustion in long-running server |

### Accumulated Debt

These debts slow development but don't cause incorrect behavior:

| Debt | Severity | Scope | Effort to Fix |
|------|----------|-------|--------------|
| Near-zero test coverage (~5-15% across zones) | HIGH | All zones | 20-30 hours |
| 16 bare `except Exception: pass` patterns | MEDIUM | Parsers, aggregation | 1 hour |
| `_active_sessions()` duplication | MEDIUM | `sessions.py`, `totals.py` | 15 minutes |
| Chart config duplication (~300 lines) | MEDIUM | 37 chart files | 3 hours |
| 15+ global mutable variables in frontend | MEDIUM | `store.js`, `sse.js`, `charts.js` | 4 hours |
| Unused Preact importmap (~30KB dead requests) | LOW | `index.html` | 5 minutes to remove OR significant effort to activate |
| Theme color dual source of truth (CSS + JS) | LOW | `main.css`, `utils.js` | 3 hours |
| Windows incompatibility (`fcntl`, `lsof`) | LOW | `server.py` | 4 hours |
| CSS light-theme duplication (~180 lines) | LOW | `main.css` | 3 hours |

### Debt Trajectory

The project is accumulating debt faster than it is retiring it. The recent additions (hermit parser, token burn curve, efficiency gauges, extended metrics) each added functionality without corresponding tests. The test coverage has been declining as a percentage as the codebase grows. This is unsustainable beyond 1-2 more releases.

### Recommendations

| Priority | Recommendation |
|----------|---------------|
| CRITICAL | Fix hermit `UsageEvent` mutation bug (30 min) |
| CRITICAL | Add thread lock to `_dashboard_cache` or eliminate dual caching (1 hour) |
| HIGH | Establish test coverage baseline and enforce 80% for new code (ongoing) |
| HIGH | Define `DashboardPayload` TypedDict (2 hours) |
| MEDIUM | Fix `_gp()` ordering: sort by key length descending (15 min) |
| MEDIUM | Fix SQLite connection leak in codex.py (10 min) |

---

## Dimension 7: Innovation Architectural Feasibility — 7/10

### Innovation Risk Assessment

| Innovation | Feasibility | Risk | Architecture Impact | Recommendation |
|-----------|-------------|------|-------------------|----------------|
| External pricing registry | HIGH | LOW | Minimal -- replaces `_P` dict loading, keeps `_gp()` | APPROVE |
| CUSUM anomaly detection | HIGH | LOW | Additive -- new insight rule, no structural change | APPROVE |
| Model efficiency scoring | HIGH | LOW | Additive -- new insight rule | APPROVE |
| Chart factory pattern | HIGH | LOW | Refactoring -- reduces code, improves consistency | APPROVE |
| SSE heartbeat + cache eviction | HIGH | LOW | Minimal -- adds 10 lines to `_write_stream` | APPROVE |
| CSS paint containment | HIGH | LOW | CSS-only change, zero JS impact | APPROVE |
| Interactive drill-down (calendar) | MEDIUM | LOW | Requires ECharts `connect()` setup + event handlers | APPROVE |
| Preact activation | MEDIUM | MEDIUM | Significant -- replaces imperative DOM updates, affects all sections | APPROVE with phased rollout |
| asyncio server migration | MEDIUM | MEDIUM | Rewrites `server.py`, changes threading model | APPROVE after test coverage improves |
| Incremental aggregation | LOW | HIGH | Fundamental change to pipeline model, affects parsers + aggregation + caching | DEFER until architecture supports it |
| Differential streaming (JSON Patch) | LOW | HIGH | Requires server-side diff computation + client-side patch application | DEFER until Preact is active |
| FS-Event pipeline (kqueue/inotify) | LOW | HIGH | Platform-specific ctypes code, complex error handling | DEFER -- polling is adequate |

### Phased Innovation Roadmap

**Phase 1 (Low risk, high value -- 1-2 days):**
- External pricing registry
- CUSUM anomaly detection + model efficiency scoring
- SSE heartbeat + cache eviction
- CSS paint containment
- Fix all CRITICAL bugs first

**Phase 2 (Medium risk, structural improvement -- 3-5 days):**
- Chart factory pattern + data guard standardization
- Interactive calendar drill-down
- Preact activation (pilot: hero section, source cards, cost cards)
- `DashboardPayload` TypedDict

**Phase 3 (Higher risk, requires Phase 2 -- 5-10 days):**
- asyncio server migration (after test coverage > 60%)
- Incremental parsing + incremental aggregation (co-designed)
- Differential streaming (after Preact is active)

### Recommendations

| Priority | Recommendation |
|----------|---------------|
| HIGH | Execute Phase 1 innovations immediately -- all are additive and low-risk |
| HIGH | Fix CRITICAL bugs before any innovation work |
| MEDIUM | Gate Phase 3 on test coverage reaching 60% minimum |
| LOW | Defer FS-event pipeline indefinitely -- the 30s polling interval is sufficient for the use case |

---

## Scoring Summary

| # | Dimension | Score | Max | Key Factor |
|---|-----------|-------|-----|------------|
| 1 | Module Boundary Integrity | 7 | 10 | Clean top-level boundaries; fragile frontend ordering; CLI/server coupling |
| 2 | Design Pattern Consistency | 6 | 10 | Good compute/render patterns; hermit mutation bug; missing factories |
| 3 | Data Flow Architecture | 7 | 10 | Clean linear pipeline; untyped contract; thread-unsafe cache |
| 4 | Extensibility & Plugin Architecture | 6 | 10 | Adding parsers requires 4 edits; no chart factories; no plugin hooks |
| 5 | Cross-Zone Dependency Analysis | 7 | 10 | Most innovations compatible; incremental parse+aggregate must co-design |
| 6 | Technical Debt Assessment | 7 | 10 | Two CRITICAL bugs; test debt growing; manageable if addressed now |
| 7 | Innovation Architectural Feasibility | 7 | 10 | Phase 1 innovations safe; Phase 3 needs architectural prerequisites |
| **Total** | | **47** | **70** | |

---

## Top 10 Prioritized Recommendations

| # | Priority | Recommendation | Effort | Impact |
|---|----------|---------------|--------|--------|
| 1 | CRITICAL | Fix `UsageEvent` mutation in `hermit.py:196-200` -- create new instances | 30 min | Correctness |
| 2 | CRITICAL | Add threading lock to `_dashboard_cache` in `cli.py` or eliminate dual caching | 1 hour | Thread safety |
| 3 | HIGH | Fix SQLite connection leak in `codex.py:49` -- use context manager | 10 min | Stability |
| 4 | HIGH | Define `DashboardPayload` TypedDict for the aggregate return contract | 2 hours | Maintainability |
| 5 | HIGH | Deduplicate `_active_sessions()` -- `totals.py:109` should import from `sessions.py` | 15 min | DRY |
| 6 | HIGH | Extract `build_dashboard_payload()` from `cli.py` into `pipeline.py` | 30 min | Decoupling |
| 7 | HIGH | Create chart factory functions to eliminate ~300 lines of duplication | 3 hours | Maintainability |
| 8 | MEDIUM | Standardize parser signatures to `(start_utc, now_utc) -> ParseResult` | 30 min | Consistency |
| 9 | MEDIUM | Replace 16 bare `except Exception: pass` with `warnings.warn()` | 1 hour | Debuggability |
| 10 | MEDIUM | Fix `_gp()` model matching: sort `_P.items()` by key length descending | 15 min | Correctness |

---

## Appendix: Cross-Reference Validation

Claims from patrol reports that were **validated** against source code:

- `_active_sessions()` duplication in `sessions.py:10` and `totals.py:109` -- **CONFIRMED**
- Hermit parser mutation of `UsageEvent` fields at lines 196-200 -- **CONFIRMED**
- Silent `except Exception: pass` in `insights.py:27-28` -- **CONFIRMED** (plus 15 more across parsers)
- Unprotected `_dashboard_cache` globals in `cli.py:17-18` -- **CONFIRMED**
- Unused Preact importmap in `index.html:10-17` -- **CONFIRMED**
- Calendar `nameMap: 'ZH'` hardcoding in `CostCalendar.js:8` -- **CONFIRMED**
- `_gp()` order-dependent matching in `models.py:64-74` -- **CONFIRMED**, with comment on line 66 claiming "longest match wins due to dict order" which is incorrect (dict order is insertion order, not length order)

Claims that were **not fully validated**:

- "Redundant hourly row construction in `patterns.py` and `story.py`" -- Not independently verified due to scope constraints. Patrol report claim is plausible based on architectural patterns observed.
- "30KB dead network requests from unused Preact" -- The importmap declares CDN URLs but actual download depends on browser behavior (importmaps are not eagerly fetched in all browsers).
