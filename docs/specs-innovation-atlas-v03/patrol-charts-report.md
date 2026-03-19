# Frontend Charts Zone Patrol Report

**Zone:** `src/agent_usage_atlas/frontend/charts/`
**Date:** 2026-03-19
**Files Analyzed:** 37 chart files + 4 infrastructure files (charts.js, utils.js, store.js, i18n.js) + 1 orchestration file (main.js)

---

## 1. Zone Inventory

| Chart File | Chart Type | Lines | Data Source | ECharts Series Type |
|---|---|---|---|---|
| Timeline.js | Bar + Line combo | 35 | `working_patterns.timeline` | bar, line |
| CostSankey.js | Sankey | 25 | `trend_analysis.cost_sankey` | sankey |
| TokenSankey.js | Sankey + DOM notes | 28 | `trend_analysis.token_sankey` + `story` | sankey |
| Heatmap.js | Heatmap (weekday x hour) | 13 | `working_patterns.heatmap` | heatmap |
| ModelRadar.js | Radar | 38 | `trend_analysis.model_radar` | radar |
| RoseChart.js | Nightingale Rose | 20 | `source_cards` | pie (roseType) |
| DailyCostChart.js | Stacked bar + line | 35 | `days`, `source_cards` | bar (stack), line |
| DailyTokenChart.js | Stacked bar + line | 21 | `days` | bar (stack), line |
| CostBreakdownChart.js | Donut | 24 | `totals` | pie |
| CostCalendar.js | Calendar heatmap | 11 | `days`, `range` | heatmap (calendar) |
| TokenCalendar.js | Calendar heatmap | 11 | `days`, `range` | heatmap (calendar) |
| SourceRadar.js | Radar | 36 | `working_patterns.source_radar` | radar |
| FileTypes.js | Donut | 21 | `projects.file_types` | pie |
| EfficiencyGauges.js | 3x Gauge | 51 | `efficiency_metrics`, `totals` | gauge |
| TokenBurnCurve.js | Bar + MA lines + tabs | 127 | `token_burn` (multi-interval) | bar, line |
| AiContribution.js | Donut | 21 | `extended.ai_contribution` | pie |
| BranchActivity.js | Horizontal bar | 16 | `projects.branch_activity` | bar |
| BurnRate.js | Dual line (actual + projected) | 23 | `trend_analysis.burn_rate_30d` | line |
| CodegenDaily.js | Bar | 18 | `extended.cursor_codegen.daily` | bar |
| CodegenModel.js | Horizontal bar | 18 | `extended.cursor_codegen.by_model` | bar |
| CommandSuccess.js | Dual area line | 16 | `commands.daily_success` | line |
| CostPerTool.js | Area line | 20 | `trend_analysis.daily_cost_per_tool_call` | line |
| DailyCostTypeChart.js | Stacked bar | 18 | `days` | bar (stack) |
| DailyTurnDuration.js | Area line | 20 | `extended.turn_durations.daily` | line |
| EfficiencyChart.js | Multi-axis line | 20 | `efficiency_metrics.daily` | line |
| HourlyTempo.js | Bar + line by source | 22 | `working_patterns.hourly_source_totals` | bar, line |
| ModelCostChart.js | Horizontal bar | 17 | `trend_analysis.model_costs` | bar |
| ProductivityChart.js | Area line | 21 | `working_patterns.daily_productivity` | line |
| ProjectRanking.js | Horizontal bar | 17 | `projects.ranking` | bar |
| SessionBubble.js | Scatter | 24 | `session_deep_dive.complexity_scatter` | scatter |
| SessionDuration.js | Bar histogram | 11 | `session_deep_dive.duration_histogram` | bar |
| TaskRate.js | Donut | 21 | `extended.task_events` | pie |
| ToolBigram.js | Force graph (circular) | 24 | `tooling.bigram_chord` | graph |
| ToolDensity.js | Bar | 11 | `working_patterns.hourly_tool_density` | bar |
| ToolRanking.js | Horizontal bar | 16 | `tooling.ranking` | bar |
| TopCommands.js | Horizontal bar | 19 | `commands.top_commands` | bar |
| TurnDuration.js | Bar histogram | 17 | `extended.turn_durations.histogram` | bar |

**Total:** 37 files, ~895 lines of chart code

---

## 2. Twelve-Dimension Scoring Table (120 points max)

### 2.1 Maintainability (20 pts) — Score: 14/20

**Strengths:**
- Remarkably consistent single-function-per-file pattern. Every chart is a standalone `renderXxx()` function.
- Shared theme via `chartTheme()` and color palette via `C` proxy eliminates per-chart theme boilerplate.
- Lazy rendering via `IntersectionObserver` + `registerLazy()` is well-factored in `charts.js`.
- i18n is handled uniformly via `t()` for all user-facing strings.

**Weaknesses:**
- **Duplicate boilerplate across charts:** Grid config (`{top: 24, left: 56, right: 24, bottom: 44}`), axis styling (`axisLine: {lineStyle: {color: AX}}`), tooltip setup, and bar styling are repeated verbatim across 30+ files. A builder or preset system would reduce ~40% of duplicated config.
- **Hardcoded color arrays** appear in 6+ charts (ModelRadar, FileTypes, CodegenModel, ModelCostChart, ToolBigram) with no shared palette constant.
- **No type checking or JSDoc** -- all functions operate on untyped global `data`, making refactoring risky.
- **Mixed DOM manipulation in chart files**: TokenSankey.js writes to `#source-notes`, HourlyTempo.js writes to `#tempo-notes` -- these break the single-responsibility principle of chart rendering.

### 2.2 Performance/Stability Risk (20 pts) — Score: 15/20

**Strengths:**
- IntersectionObserver lazy loading prevents rendering 30+ charts on page load.
- Canvas renderer is the default (good for many charts).
- `isFirstRender` flag disables animation on re-render, preventing jank on SSE updates.
- Data slicing (e.g., `.slice(0, 12)`, `.slice(0, 50)`) prevents unbounded series.
- `dataZoom` on TokenBurnCurve enables interaction with large time-series data.

**Weaknesses:**
- **Heatmap `Math.max(...points.map(...))` spreads large arrays** -- for 168 data points (7x24) this is fine, but the pattern is fragile for larger datasets.
- **Calendar charts compute `Math.max(...data.days.map(...))` inline** -- same spread risk with many days.
- **No chart disposal on re-render**: `initChart()` reuses cached instances via `chartCache`, but `clearCharts()` is only called on theme toggle, not on data update. On SSE updates, all 37 chart options are set again without clearing previous series, which can accumulate memory if series structure changes.
- **TokenBurnCurve `_movingAvg` is O(n*w)** -- acceptable for typical sizes but not optimized.
- **All chart files are global scope** -- no module isolation. Name collisions are possible (e.g., `_burnInterval` is a global mutable).

### 2.3 Architecture Consistency (15 pts) — Score: 12/15

**Strengths:**
- Uniform pattern: `function renderXxx() { const chart = initChart('xxx'); chart.setOption({...chartTheme(), ...}); }`
- Consistent use of `chartTheme()` spread as base.
- Color references via `C.xxx` proxy handle dark/light themes automatically.
- Lazy vs. eager split is clearly defined in `main.js` orchestration.

**Weaknesses:**
- **Inconsistent guard patterns**: Some charts have early returns for missing data (e.g., `AiContribution.js`: `if (!ext || !ext.ai_contribution...)`), others assume data exists (e.g., `Heatmap.js` -- would throw if `data.working_patterns.heatmap` is undefined).
- **Inconsistent naming**: `renderBubble()` vs `renderToolBigramChart()` vs `renderTempo()` -- no consistent naming convention.
- **Two Sankey charts** with nearly identical structure but no shared factory function.
- **Calendar charts** (Cost/Token) are 95% identical -- prime candidate for a factory.

### 2.4 Innovation Potential (25 pts) — Score: 17/25

**Current innovation highlights:**
- TokenBurnCurve with moving averages and interval tabs is the most innovative chart -- mimics stock/trading terminal UX.
- EfficiencyGauges with 3 gauge instances show dashboard thinking.
- ToolBigram circular graph layout for tool transition analysis is unique.
- SessionBubble scatter with 3 dimensions (duration, tokens, cache) is effective.

**Untapped opportunities:**
1. **Animated flow visualization**: The Sankey charts are static. Animated particle flows (like Observable's animated Sankey) would show token/cost "flowing" through the system in real time during SSE updates.
2. **Comparative small multiples**: No chart currently supports comparing two time ranges side by side (e.g., this week vs last week). ECharts `graphic` component can overlay ghost series.
3. **Drill-down from calendar to daily detail**: Calendar heatmaps are terminal -- clicking a day cell could zoom into that day's hourly breakdown.
4. **WebGL scatter for large session data**: SessionBubble caps at 50 points. ECharts has a `scatterGL` extension that handles 100K+ points.

### 2.5 Community/Paper Frontier Match (20 pts) — Score: 14/20

**ECharts 5.x features not yet used:**
- `universalTransition` -- morph between chart types (e.g., bar to pie on click).
- `dataset` component -- decouple data from series. Currently every chart does inline `.map()` transforms.
- `decal` patterns for accessibility (colorblind-safe chart differentiation).
- `aria` configuration for screen reader support.
- Custom chart series via `registerCustomSeries`.

**Visualization research applicable to this domain:**
- **Marey charts** (time-space diagrams) for session timelines -- show concurrent sessions as parallel tracks.
- **Horizon charts** (Heer et al., 2009) for dense time-series comparison -- could replace 5+ daily trend lines in one compact view.
- **Bump charts** for ranking changes over time (model cost ranking evolution).
- **Beeswarm plots** for session distribution -- alternative to the current histogram.

### 2.6 ROI (20 pts) — Score: 16/20

**High ROI improvements:**

| Improvement | Effort | Benefit | ROI |
|---|---|---|---|
| Chart factory for repeated patterns (calendar, horizontal bar, stacked bar+line) | 2h | Eliminate ~300 lines of duplication, easier to add new charts | Very High |
| Shared color palette constant | 30min | Consistent theming, single source of truth | Very High |
| Data guard standardization | 1h | Prevent runtime crashes from missing data sections | High |
| ECharts `dataset` migration | 4h | Cleaner data binding, enable chart transitions | Medium |
| Calendar click-to-zoom drill-down | 3h | Significant UX improvement for daily analysis | High |
| `universalTransition` for chart morphing | 2h | "Wow factor" with minimal code | High |
| Accessibility (`decal` + `aria`) | 2h | Compliance, broader user base | Medium |

---

## 3. Aggregate Score

| Dimension | Score | Max |
|---|---|---|
| Maintainability | 14 | 20 |
| Performance/Stability Risk | 15 | 20 |
| Architecture Consistency | 12 | 15 |
| Innovation Potential | 17 | 25 |
| Community/Paper Frontier Match | 14 | 20 |
| ROI | 16 | 20 |
| **Total** | **88** | **120** |

**Decision: INNOVATION** (score >= 85)

---

## 4. Innovation Decision Process

### Step 1: Top 3 Frontier Approaches + 1 Breakthrough

**Approach 1: Chart Factory Pattern with ECharts `dataset`**
Consolidate the 6 horizontal bar charts, 2 calendar heatmaps, 2 Sankey charts, and 3 stacked-bar-with-cumulative-line charts into parameterized factory functions using ECharts' `dataset` component. This decouples data transformation from chart configuration and enables `universalTransition` for seamless morphing between views.

Reference: ECharts 5.x `dataset` specification, Observable Plot's mark-based composition model.

**Approach 2: Interactive Drill-Down Navigation**
Connect calendar heatmaps to daily detail charts via ECharts' `connect` API and click handlers. Clicking a calendar cell filters all connected charts to that specific day. This creates a coordinated multi-view dashboard without additional data fetching (all data is already in the payload).

Reference: Shneiderman's Visual Information-Seeking Mantra ("Overview first, zoom and filter, then details-on-demand"), Crossfilter.js coordinated views.

**Approach 3: Animated Token Flow on Sankey + SSE**
During live mode (SSE), animate particles flowing through Sankey links proportional to real-time token consumption rate. Use ECharts `graphic` component to overlay animated dots along Sankey link paths, creating a "data is flowing" effect that transforms static diagrams into a living system monitor.

Reference: Animated Sankey by Tom Shanley (d3-sankey-timeline), Google Cloud network flow visualization.

**Breakthrough: Horizon Chart Layer**
Replace the multi-line EfficiencyChart with a horizon chart that stacks 3-5 metrics into a single compact row per metric, using color intensity for magnitude and mirroring for negative deltas. This compresses 300px of vertical space into 120px while showing more time-series data at higher density.

Reference: Heer, Kong, and Agrawala (2009) "Sizing the Horizon: The Effects of Chart Size and Layering on the Graphical Perception of Time Series Visualizations" (CHI 2009).

### Step 2: Innovation Value Assessment

```
Innovation Index = (Reference Value x 0.4) + (Innovation Increment x 0.5) + (Risk Controllability x 0.1)
```

| Approach | Reference Value (0-10) | Innovation Increment (0-10) | Risk Controllability (0-10) | Index |
|---|---|---|---|---|
| Chart Factory + dataset | 9 | 5 | 9 | 7.0 |
| Interactive Drill-Down | 8 | 7 | 8 | 7.5 |
| Animated Sankey Flow | 7 | 9 | 6 | 7.9 |
| Horizon Chart | 6 | 10 | 5 | 7.9 |

### Step 3: Final Decision + Innovation Proposal

**Recommended execution order:**

1. **Phase 1 (Stability + Foundation):** Chart Factory Pattern -- extract shared builders for horizontal bar, calendar heatmap, stacked bar+line, and Sankey patterns. Standardize data guards. Create shared color palette array. Estimated: 3 hours, eliminates ~300 lines of duplication.

2. **Phase 2 (High-impact UX):** Interactive Drill-Down -- wire calendar click events to filter connected charts. Add `echarts.connect()` group for Cost and Token chart families. Estimated: 3 hours, transforms passive viewing into active exploration.

3. **Phase 3 (Frontier):** Animated Sankey Flow for live mode -- conditionally activate when SSE stream is active. Estimated: 4 hours, creates visual differentiation from any existing dashboard tool.

---

## 5. Specific Findings

### 5.1 Duplication Hotspots

**Horizontal bar charts (6 files, ~100 lines total):**
- `ToolRanking.js`, `TopCommands.js`, `ProjectRanking.js`, `BranchActivity.js`, `ModelCostChart.js`, `CodegenModel.js`
- All share: horizontal orientation, `barMaxWidth: 22`, `borderRadius: [0,6,6,0]`, right-side labels

**Calendar heatmaps (2 files, ~22 lines):**
- `CostCalendar.js` and `TokenCalendar.js` differ only in: data mapping, color ramp, tooltip formatter

**Stacked bar + cumulative line (3 files, ~90 lines):**
- `DailyCostChart.js`, `DailyTokenChart.js`, `DailyCostTypeChart.js` share 80% of configuration

### 5.2 Stability Risks

1. **Missing data guards in 15+ charts** -- charts that access nested properties like `data.working_patterns.heatmap` without null checks will throw if the data section is absent. Only 6 charts have proper guards (those checking `data.extended`).

2. **Global mutable state** -- `_burnInterval` (TokenBurnCurve.js) is a global `let`. If multiple burn curves were ever rendered, they would share state.

3. **DOM coupling** -- TokenSankey.js and HourlyTempo.js write to DOM elements outside their chart container, creating implicit dependencies on HTML structure.

### 5.3 Accessibility Gaps

- No `decal` patterns for colorblind users.
- No `aria` labels on chart containers.
- Calendar charts use Chinese-only month/day labels (`nameMap: 'ZH'`) regardless of language setting.
- Color-only differentiation in all multi-series charts.

### 5.4 Calendar i18n Bug

Both `CostCalendar.js` and `TokenCalendar.js` hardcode `nameMap: 'ZH'` for month and day labels. When `lang === 'en'`, these should use `'en'` or omit `nameMap` entirely. This is a functional bug in English mode.

---

## 6. Self-Verification (Post-Analysis Rescore)

After completing the full analysis, I re-evaluated each dimension:

| Dimension | Initial | Verified | Delta | Notes |
|---|---|---|---|---|
| Maintainability | 14 | 14 | 0 | Duplication confirmed in detail |
| Performance/Stability | 15 | 14 | -1 | Missing data guards are more widespread than initially assessed |
| Architecture Consistency | 12 | 12 | 0 | Confirmed |
| Innovation Potential | 17 | 18 | +1 | Drill-down opportunity is stronger than initially assessed |
| Community/Frontier Match | 14 | 14 | 0 | Confirmed |
| ROI | 16 | 16 | 0 | Confirmed |
| **Total** | **88** | **88** | **0** | Decision unchanged: INNOVATION |

---

## 7. Actionable Next Steps (Priority Order)

1. **[BUG]** Fix calendar `nameMap` to respect `lang` variable (CostCalendar.js, TokenCalendar.js)
2. **[STABILITY]** Add data existence guards to all 15+ unguarded chart render functions
3. **[REFACTOR]** Extract `makeHorizontalBar()`, `makeCalendarHeatmap()`, `makeStackedBarLine()` factory functions
4. **[REFACTOR]** Extract shared color palette array (`PALETTE_12`, `PALETTE_10`) from hardcoded inline arrays
5. **[REFACTOR]** Move DOM writes out of TokenSankey.js and HourlyTempo.js into section renderers
6. **[INNOVATION]** Implement calendar click-to-filter drill-down using `echarts.connect()`
7. **[INNOVATION]** Add `universalTransition` morphing between RoseChart and CostBreakdownChart
8. **[A11Y]** Add ECharts `decal` patterns and `aria` configuration
