# Expert Review: Performance & Scalability

**Reviewer:** Performance & Scalability Expert
**Date:** 2026-03-19
**Scope:** Full pipeline (parse -> aggregate -> render -> serve) + frontend rendering
**Input:** 5 patrol reports + source code review of 25+ files

---

## Executive Summary

The agent-usage-atlas pipeline is well-optimized for its current sweet spot (1-50K events, 30-day window, single user). Multi-layer caching (file-signature, per-file incremental, result-level, dashboard-level, payload-level) prevents most redundant work. However, the architecture has a hard scalability ceiling around 100K events due to full-payload SSE broadcasting, O(n log n) sorting in the aggregation context builder, and full re-aggregation on any cache miss. The frontend is well-optimized with IntersectionObserver lazy loading, but the 37-chart full re-render on SSE updates is the primary frontend bottleneck.

**Overall Score: 42/70**

---

## Dimension Scores

### 1. Parse Performance: 7/10

**Justification:**

The parsing layer is the strongest performance story in the codebase. Three levels of caching prevent unnecessary work:

1. **File-signature cache** (`_base.py:13-48`): `_JSONL_CACHE` keyed on `(st_size, st_mtime_ns)` avoids re-reading files whose mtime has not changed. This is O(1) lookup.

2. **Per-file incremental cache** (`claude.py:16-17`): `_PER_FILE_CACHE` stores parsed results per-file with both file signature AND time range key, so only changed files are re-parsed. This is the best optimization in the codebase.

3. **Result-level cache** (`_base.py:59-131`): `result_cache_get/set` with composite file signature (count + total_size + max_mtime_ns) avoids re-running entire parser functions when no files changed. The 10-second `_RESCAN_INTERVAL` avoids rglob overhead.

**Bottlenecks identified:**

- **`_read_json_lines` loads entire files into memory** (`_base.py:34-48`). Each JSONL file is parsed line-by-line into a `list[dict]`, then cached in `_JSONL_CACHE`. For a 100MB file, this means ~100MB of Python dicts in memory. No streaming/generator approach.

- **Concurrent parsing via ThreadPoolExecutor** (`__init__.py:26-48`) is good but the pool is created fresh per call (`with ThreadPoolExecutor() as pool`). Thread creation overhead is ~1ms per thread, negligible for 4 parsers.

- **Claude parser makes two passes** over each file (`claude.py:53-58` for `err_map`, then `claude.py:61-154` for main extraction). The first pass is O(n) to build the `err_map` dict, then the main pass is also O(n). This is unavoidable given the data structure but doubles the per-file CPU cost.

- **`_gp()` model matching** (`models.py:63-74`) does a linear scan through `_P` dict (30 entries) on cache miss. The `lru_cache(128)` mitigates this but the scan itself is O(k) where k=30. Not a bottleneck at current scale.

- **SQLite connection leak in codex.py** (identified in patrol-parsers-report): Leaked connections don't cause performance issues directly but can exhaust file handles on systems with many databases.

**Recommendations:**
- P1: Implement append-only incremental JSONL parsing (byte-offset tracking). Current: O(n) per file on change. Proposed: O(delta).
- P2: Stream JSONL parsing instead of loading entire files into `list[dict]`. This would reduce peak memory by ~50%.
- P3: Fix SQLite connection leak in codex.py with context manager.

---

### 2. Aggregation Performance: 5/10

**Justification:**

The aggregation layer has significant redundant computation. The `build_context` function (`_context.py:88-357`) does a commendable single-pass O(n log n) build (dominated by the two `sorted()` calls at lines 184 and 258), but downstream modules re-iterate `ordered_days` and re-compute identical values.

**Redundant computation inventory:**

| Computation | Location 1 | Location 2 | Cost |
|---|---|---|---|
| `grand_total = sum(d["total_tokens"] for d in ordered_days)` | `totals.py:15` | `story.py:16` | O(d) x 2 |
| `grand_cost = sum(d["cost"] for d in ordered_days)` | `totals.py:16` | `story.py:17` | O(d) x 2 |
| `grand_cache_read = sum(d["cache_read"] for d in ordered_days)` | `totals.py:17` | `story.py:18` | O(d) x 2 |
| `grand_cache_write = sum(d["cache_write"] for d in ordered_days)` | `totals.py:18` | `story.py:19` | O(d) x 2 |
| `_source_cards(ctx)` call | `totals.py:11` | `story.py:13`, `trends.py:24` via `_get_source_cards` | 3x construction |
| `_active_sessions(ctx)` | `totals.py:12` (called), `sessions.py` (duplicate impl) | Identical 28-line function x 2 |
| `peak_day = max(ordered_days, ...)` | `totals.py:29` | `story.py:35` | O(d) x 2 |
| `cost_peak_day = max(ordered_days, ...)` | `totals.py:30` | `story.py:36` | O(d) x 2 |
| `average_daily_burn` | `totals.py:39-40` | `trends.py:70` | O(7) x 2 |
| Hourly row construction | `patterns.py:12-18` | `story.py:82-88` | O(24*3) x 2 |
| `_combined_tool_counts` | `totals.py:140-146` | `story.py:26-28` | O(k) x 2 |
| Re-sort of `_raw_events` | `prompts.py:65-67` | Already sorted in `_context.py:184` | O(n log n) wasted |

**Quantified waste:** For a typical 30-day window with 10K events and 30 days, the redundant iterations add ~150K unnecessary dict lookups. This is negligible (<1ms) at current scale but becomes the dominant cost at 100K+ events.

**The `token_burn_multi` function** (`trends.py:212-261`) iterates `_raw_events` a third time (after `build_context` already iterated them). Each event gets `astimezone()` called again (expensive datetime operation). For 10K events, this is ~10K redundant timezone conversions.

**The aggregation entry point** (`__init__.py:39-59`) calls 11 `compute()` functions sequentially. None of these are parallelizable because they all read from the shared `AggContext`. However, 6 of them (`daily`, `sessions`, `tooling`, `projects`, `patterns`, `extended`) are independent and could theoretically run in parallel if `AggContext` were immutable (which it effectively is after construction).

**Memory allocation pattern:** `build_context` creates deeply nested `defaultdict` structures with mutable lambdas, then materializes them into plain `dict` at lines 335-346. This double-allocation (defaultdict -> dict) wastes memory for the intermediate structures. At 10K events with 30 days and 100 sessions, this is ~50KB of intermediate dicts -- negligible.

**Recommendations:**
- P0: Precompute `grand_total`, `grand_cost`, `grand_cache_read`, `grand_cache_write`, `peak_day`, `cost_peak_day` in `AggContext` during `build_context`. Eliminates 10+ redundant iterations of `ordered_days`.
- P1: Cache `_source_cards(ctx)` result (called 3 times with identical input). Either compute once in `aggregate()` and pass to consumers, or memoize on AggContext.
- P2: Eliminate the redundant sort in `prompts.py:65-67` -- events are already sorted in `_context.py:184`.
- P3: Cache timezone conversions in `token_burn_multi` by using `ordered_days` date keys rather than re-converting raw events.

---

### 3. Rendering Performance: 6/10

**Justification:**

The `build_html()` function (`builder.py:19-41`) is simple and efficient:

1. Reads ~40 frontend files from disk (one-time I/O).
2. Concatenates JS strings with `"\n".join()`.
3. Does 4 string replacements (`__CSS__`, `__JS__`, `__DATA__`, `__POLL_MS__`).
4. Serializes the data payload via `json.dumps()`.

**The JSON serialization** is the dominant cost. For a typical 30-day dashboard payload with 10K events, the payload JSON is ~50-100KB. `json.dumps()` with `ensure_ascii=False` runs at ~50MB/s in CPython, so a 100KB payload takes ~2ms. Acceptable.

**The `_json_body` function** (`server.py:52-54`) is called on every JSON API response and SSE push. It serializes the payload AND computes a SHA-1 hash, but it encodes the body to UTF-8 twice:

```python
body = json.dumps(payload, ensure_ascii=False)
return body.encode("utf-8"), hashlib.sha1(body.encode("utf-8")).hexdigest()
```

The `body.encode("utf-8")` is called twice -- once for the return value and once for the hash. This doubles the UTF-8 encoding cost (~0.5ms for 100KB payload). Minor but trivially fixable.

**The HTML assembly** in `build_html` reads all files from disk every time it is called. In serve mode, this is called once on `/` index request. Since the frontend files don't change during server runtime, this could be cached, but it is only called per page load (not per SSE update), so the impact is low.

**The `replace("</", r"<\/")`** call at `builder.py:37` is a security measure (preventing `</script>` injection in JSON payloads embedded in HTML). This is an O(n) scan of the entire JSON string. For 100KB, this is ~0.1ms. Negligible.

**Recommendations:**
- P2: Cache the encoded body in `_json_body` to avoid double `encode("utf-8")`.
- P3: Cache the HTML template (CSS + JS concatenation) in serve mode since frontend files are static.

---

### 4. Frontend Performance: 6/10

**Justification:**

**Good patterns:**
- **IntersectionObserver lazy loading** (`charts.js:32-90`): Only 7 charts render eagerly; 30 are deferred until scrolled into view. Root margin of 200px provides preloading buffer.
- **Canvas renderer** is the default for all ECharts instances (good for 37 charts -- SVG would be slower).
- **`isFirstRender` flag** (`charts.js:1`) disables animation on re-render, preventing jank on SSE updates.
- **Debounced resize** (`main.js:152-155`): 150ms debounce prevents resize storm.
- **`requestAnimationFrame` wrapping** for lazy chart renders (`charts.js:48`, `charts.js:81`).

**Performance concerns:**

1. **Full re-render on SSE update** (`sse.js:127-136`): Every SSE message triggers `renderDashboard()` which re-registers all 30 lazy charts and calls `flushLazy()`. For already-rendered charts, `flushLazy` calls `requestAnimationFrame(() => fn())` for each visible chart (`charts.js:46-48`). This means every SSE update triggers up to 37 `chart.setOption()` calls. Each `setOption` call involves ECharts diffing the option tree and re-rendering the canvas. Estimated cost: ~5-15ms per chart x 37 charts = 185-555ms total. This likely causes frame drops on lower-end devices.

2. **`applyI18n()` DOM scan** (referenced in patrol-frontend-core-report): Queries all `[data-i18n]` elements on every render. O(n) DOM scan where n = number of i18n elements (~50-100). Cost: ~1-2ms.

3. **`toggleLang()` full teardown**: Clears 10+ containers via `innerHTML = ''`, disposes all ECharts instances, recreates everything. This causes a full layout thrash. Cost: ~200-500ms.

4. **No chart disposal on data update**: `clearCharts()` is only called on theme toggle, not on SSE data updates. ECharts `setOption` on existing instances is efficient (it diffs), but if series structure changes between updates, old series data may accumulate in memory.

5. **`Math.max(...arr.map(...))` spread pattern** in calendar/heatmap charts: For 168 heatmap points this is fine, but `Math.max(...data.days.map(...))` with 365 days pushes 365 args onto the stack. No stack overflow risk but unnecessary allocation.

6. **37 charts on a single page**: Even with lazy loading, once the user scrolls the full page, all 37 ECharts instances are active. Each instance holds its canvas context, option tree, and animation state. Estimated memory: ~2-5MB per instance = 74-185MB total. This is significant on mobile devices.

7. **No `content-visibility: auto`**: Collapsed sections still participate in layout calculations. Adding CSS `content-visibility: auto` to `.section-wrap.collapsed` would eliminate paint cost for hidden sections.

**Recommendations:**
- P0: On SSE updates, only re-render charts whose data actually changed (compare data subsections by reference or hash, not re-render everything).
- P1: Add `content-visibility: auto` to collapsed sections and `.section-more` elements.
- P2: Batch chart updates using `requestIdleCallback` instead of `requestAnimationFrame` for non-visible charts.
- P3: Consider disposing charts in collapsed/hidden sections and re-creating on expand.

---

### 5. Server Performance: 5/10

**Justification:**

**Architecture:** `ThreadingHTTPServer` with `BaseHTTPRequestHandler` creates one OS thread per connection. SSE connections are long-lived, so each connected client holds a thread indefinitely.

**Thread-per-SSE-connection cost** (`server.py:247-280`):
- Each SSE connection runs a blocking `while True` loop with `time.sleep(interval)`.
- Python threads have ~8MB default stack size (configurable).
- At 10 concurrent SSE clients: 10 threads, ~80MB stack reservation (though virtual, not RSS).
- At 50 clients: 50 threads. Python's GIL means only one thread runs Python code at a time, but I/O (socket writes, file stat) releases the GIL. This architecture tops out around ~100 concurrent SSE clients before thread creation overhead and GIL contention become problematic.

**SSE payload cost:**
- Every SSE push sends the **full dashboard payload** (~50-100KB JSON).
- The `_cached_payload` function (`server.py:109-126`) avoids re-computation when the file signature hasn't changed (good), but the full payload is still serialized and sent to every client.
- For 10 clients with 5-second interval: 10 x 100KB / 5s = 200KB/s outbound bandwidth. Manageable for localhost but inefficient on remote connections.
- A JSON Patch (RFC 6902) differential approach would reduce payload to ~1-5KB per update (only daily counters change in steady state), a 95% reduction.

**ETag-based deduplication** (`server.py:270-276`):
- SSE only sends data when `etag != known_etag`. This prevents redundant sends when nothing changed. Good optimization.
- However, `_cached_payload` still calls `_payload_signature()` on every check, which stats all monitored files. For 100 log files, this is 100 `stat()` syscalls per SSE client per interval. At 10 clients with 5s interval: 200 stat() calls/second. Negligible on modern filesystems but wasteful.

**Background precomputation** (`server.py:135-156`):
- A daemon thread runs `_cached_payload` periodically, warming the cache so SSE clients read pre-computed data. This is a good pattern -- SSE threads don't block on computation.
- However, the precompute thread and SSE threads can race on `_PAYLOAD_LOCK`. Since the lock protects only the cache dict read/write (not the computation itself), the actual computation can run in parallel in multiple threads if multiple SSE clients trigger cache misses simultaneously.

**No SSE heartbeat** (`server.py:267`):
- Only `": connected\n\n"` is sent on initial connection. No periodic heartbeat.
- Proxies (nginx, CloudFlare) may kill idle SSE connections after 60-120 seconds of inactivity.
- Recommendation: Send `":\n\n"` comment every 15 seconds.

**Recommendations:**
- P0: Add SSE heartbeat (15-second `":\n\n"` comments).
- P1: Share file-signature computation across SSE clients (currently each SSE thread independently stats all files). The background precompute thread already does this, but SSE threads re-check.
- P2: Implement JSON Patch differential updates to reduce SSE payload by ~95%.
- P3: Migrate to asyncio server to eliminate thread-per-connection overhead. This is a significant refactor but would improve scalability from ~100 to ~10,000 concurrent SSE clients.

---

### 6. Memory Efficiency: 6/10

**Justification:**

**Cache inventory and memory impact:**

| Cache | Location | Eviction | Growth Pattern |
|---|---|---|---|
| `_JSONL_CACHE` | `_base.py:13` | None | Grows with every new/changed JSONL file. Each entry stores the full parsed `list[dict]`. |
| `_PER_FILE_CACHE` | `claude.py:16` | None | Grows with every Claude log file. Stores parsed events, calls, metas per file. |
| `_RESULT_CACHE` | `_base.py:59` | None | Grows per parser name (max 4 entries). Bounded. |
| `_dashboard_cache` | `cli.py:17` | Replaced on new data | Single entry. Bounded. |
| `_PAYLOAD_CACHE` | `server.py:26` | None | Grows per unique `(days, since)` query combination. Unbounded. |
| `_gp` LRU cache | `models.py:63` | LRU, maxsize=128 | Bounded at 128 entries. |
| `chartCache` | `charts.js:17-23` | Only on theme toggle (`clearCharts`) | Grows with chart count (max 37). Bounded. |

**Memory concerns:**

1. **`_JSONL_CACHE` stores all parsed JSONL content forever** (`_base.py:13`). For a user with 30 days of Claude logs (say 500 files x 5000 lines average), this stores ~2.5M dict objects. At ~500 bytes per dict (rough estimate for usage events with string fields), this is ~1.25GB. This is the single biggest memory concern. The cache signature check prevents re-parsing but never evicts old data.

2. **`_raw_events` stored in AggContext** (`_context.py:77`): The full list of unsorted events is stored on the context so that `token_burn_multi` and `prompts.py` can iterate them. This doubles the memory for events (once in the sorted order within rollups, once as the raw list).

3. **`_PAYLOAD_CACHE` is unbounded** (`server.py:26`): Each unique `(days, since)` combination creates a new cache entry containing the full payload dict AND the JSON-encoded body. If users experiment with different date ranges, this grows without bound.

4. **`ParseResult.merge()` uses `list.extend()`** (`models.py:202-210`): This is efficient (amortized O(1) per append) but the merged result holds all events from all parsers in memory simultaneously.

5. **Data structure choice**: `UsageEvent` is a dataclass with 10 fields + 3 computed properties. Each instance is a full Python object (~500 bytes with `__dict__`). For 50K events, this is ~25MB. Using `__slots__` would reduce to ~200 bytes per instance, saving ~15MB. Using `NamedTuple` would be even more compact.

**GC pressure:**
- The aggregation pipeline creates many short-lived dicts (defaultdict entries, list comprehensions, sorted() results). For 10K events, `build_context` creates ~10K dict lookups/updates but few new allocations (it accumulates into existing dicts). GC pressure is moderate.
- The worst GC pattern is in `build_html()` which creates a large string (~500KB+) from concatenation, then does 4 string replacements creating 4 intermediate copies. Python strings are immutable, so each `replace()` allocates a new string. Total: ~2MB of temporary strings for a 500KB HTML output.

**Recommendations:**
- P0: Add LRU eviction to `_JSONL_CACHE` (keep last 200 files, evict by access time). This bounds memory in serve mode.
- P0: Add size limit to `_PAYLOAD_CACHE` (max 8 entries, LRU eviction).
- P1: Add `__slots__` to `UsageEvent`, `ToolCall`, and other high-volume dataclasses. ~40% memory reduction per instance.
- P2: Eliminate `_raw_events` storage on AggContext by computing `token_burn_multi` data during the context build pass.
- P3: Use `str.join()` instead of chained `str.replace()` in `build_html` to reduce intermediate string copies.

---

### 7. Scalability Ceiling: 7/10

**What breaks at each scale:**

#### 10x current load (~100K events, 300 days)

| Component | Impact | Severity |
|---|---|---|
| `_read_json_lines` memory | ~500MB cached JSONL dicts | High |
| `build_context` sort | O(100K log 100K) = ~1.7M comparisons, ~200ms | Medium |
| `token_burn_multi` | 100K timezone conversions, ~500ms | Medium |
| SSE payload size | ~500KB per push | Medium |
| Frontend: 37 charts with 300 daily datapoints | Some charts visually crowded but functional | Low |

**First failure:** Memory exhaustion from `_JSONL_CACHE` storing all parsed file contents without eviction. A user with 300 days of Claude logs could have 5,000+ JSONL files cached in memory.

#### 100x current load (~1M events, 3 years)

| Component | Impact | Severity |
|---|---|---|
| `_read_json_lines` memory | ~5GB cached dicts | Critical -- OOM |
| `build_context` sort | O(1M log 1M) = ~20M comparisons, ~2-5s | High |
| `aggregate()` pipeline | ~10s total (sort + 11 compute modules) | High |
| SSE full-payload-per-push | ~5MB per push, 50MB/s for 10 clients | Critical |
| `json.dumps` serialization | ~100ms for 5MB payload | High |
| Frontend: 37 charts | ECharts `setOption` with 1000+ daily points: ~1-2s per chart | Critical |

**First failure:** OOM from `_JSONL_CACHE`. Secondary: SSE bandwidth explosion.

#### 1000x current load (~10M events, multi-user)

Not feasible with current architecture. Every component fails:
- Memory: 50GB+ cache requirement
- CPU: 30+ second aggregation time
- Network: 50MB+ SSE payloads
- Frontend: Browser tab crash from 37 charts with 10K+ datapoints each

**Recommendations for scalability:**
- P0: Bounded caching with eviction (addresses 10x)
- P1: Incremental aggregation (addresses 100x CPU)
- P2: JSON Patch SSE (addresses 100x bandwidth)
- P3: Data windowing/sampling for charts (addresses 100x frontend)
- P4: SQLite/DuckDB backend for aggregation (addresses 1000x -- breaks zero-dep constraint)

---

## Performance Bottleneck Inventory (Priority-Ordered)

| # | Bottleneck | Location | Current Cost | At 10x Scale | Fix Effort |
|---|---|---|---|---|---|
| 1 | Unbounded `_JSONL_CACHE` memory | `_base.py:13` | ~50MB | ~500MB | 1h (LRU wrapper) |
| 2 | Full SSE payload per push | `server.py:276` | 100KB/push | 500KB/push | 2d (JSON Patch) |
| 3 | Full re-render on SSE update | `sse.js:127` + `main.js:1-76` | 37 charts re-set | 37 charts re-set | 4h (diff detection) |
| 4 | Redundant aggregation passes | `totals.py`, `story.py` | ~5 redundant O(d) passes | ~5 x O(300) | 2h (precompute in context) |
| 5 | `token_burn_multi` re-iterates raw events | `trends.py:225-229` | O(n) TZ conversions | O(100K) TZ | 2h (use daily bins) |
| 6 | Thread-per-SSE-connection | `server.py:247-280` | 4 threads | 40 threads | 2d (asyncio) |
| 7 | No SSE heartbeat | `server.py:267` | Proxy timeout risk | Same | 30m |
| 8 | `_PAYLOAD_CACHE` unbounded | `server.py:26` | ~3 entries | Grows with query variety | 1h (LRU) |
| 9 | `_source_cards` computed 3x | `totals.py:11`, `story.py:13`, `trends.py:24` | 3x O(k) | Same | 30m (memoize) |
| 10 | `prompts.py` re-sorts events | `prompts.py:65-67` | O(n log n) | O(100K log 100K) | 15m (remove sort) |

---

## Feasibility Assessment: Incremental Aggregation

The patrol reports propose incremental aggregation (t-digest, online accumulators) to avoid full re-computation on SSE ticks. Assessment:

**Current data structures hinder incrementality:**
- `AggContext.ordered_days` is a flat list of dicts built by iterating ALL daily rollups in date order. Appending a new event requires re-computing cumulative totals for all subsequent days.
- `AggContext.session_rollups` uses mutable dicts with running counters. These ARE incrementally updateable.
- `AggContext.source_rollups` similarly incrementally updateable.
- `ordered_days` cumulative fields (`cumulative_tokens`, `cost_cumulative`) require re-walking from the insertion point. This is O(d) where d = days in window.

**Verdict:** Incremental aggregation is feasible for source/session/model rollups (the counters are already structured as accumulators). It is NOT feasible for `ordered_days` cumulative fields without restructuring to use a separate running-total pass. The `build_context` function would need to be split into an `update(new_events)` method that merges deltas into existing rollups and a `finalize()` method that builds `ordered_days` from the rollups.

**Estimated effort:** 3-5 days for full incremental aggregation. 1 day for the easy wins (skip aggregation entirely when `all_caches_hit()` returns True -- which `cli.py:54` already does).

---

## Benchmark Recommendations

To establish a performance baseline and detect regressions:

1. **Parse benchmark**: Time `parse_all()` with synthetic JSONL fixtures of known sizes (1K, 10K, 100K events). Measure wall-clock time and peak RSS.

2. **Aggregation benchmark**: Time `aggregate()` with pre-parsed `ParseResult` fixtures. Measure per-module breakdown using `time.perf_counter()` around each `compute()` call in `__init__.py`.

3. **Render benchmark**: Time `build_html()` with varying payload sizes. Measure JSON serialization time separately.

4. **SSE throughput benchmark**: Measure end-to-end latency from file modification to SSE push receipt using a test client. Measure at 1, 10, 50 concurrent clients.

5. **Frontend benchmark**: Use Lighthouse Performance audit on the generated HTML with varying data sizes. Measure Time to Interactive, Largest Contentful Paint, and Total Blocking Time.

6. **Memory benchmark**: Track peak RSS during serve mode over 1 hour with periodic log file updates. Detect memory leaks from unbounded caches.

Suggested harness: `pytest-benchmark` for Python-side measurements, Lighthouse CI for frontend measurements.

---

## Score Summary

| Dimension | Score | Max | Key Issue |
|---|---|---|---|
| Parse Performance | 7 | 10 | Unbounded `_JSONL_CACHE` memory |
| Aggregation Performance | 5 | 10 | 10+ redundant iterations of `ordered_days` |
| Rendering Performance | 6 | 10 | Double UTF-8 encoding in `_json_body` |
| Frontend Performance | 6 | 10 | Full 37-chart re-render on SSE update |
| Server Performance | 5 | 10 | Thread-per-SSE, no heartbeat, full payload per push |
| Memory Efficiency | 6 | 10 | 3 unbounded caches, no `__slots__` on dataclasses |
| Scalability Ceiling | 7 | 10 | Breaks at 100K events (memory); 1M events (CPU + network) |
| **Total** | **42** | **70** | |

**Grade: B- (60%)** -- Adequate for current scale, architectural changes needed for 10x+ growth.

---

## Top 5 Performance Actions (Priority Order)

1. **Add LRU eviction to `_JSONL_CACHE` and `_PAYLOAD_CACHE`** -- Prevents OOM in serve mode. Effort: 2h. Impact: Removes the #1 scalability blocker.

2. **Precompute shared aggregation values in `AggContext`** -- Eliminate redundant `sum()` / `max()` across `totals.py`, `story.py`, `trends.py`. Effort: 2h. Impact: ~40% reduction in aggregation CPU.

3. **Differential SSE updates** -- Send only changed data subsections (or JSON Patch). Effort: 2d. Impact: 95% reduction in SSE bandwidth.

4. **Selective chart re-rendering** -- On SSE update, compare data subsections and only re-render charts whose data changed. Effort: 4h. Impact: ~80% reduction in frontend re-render cost.

5. **Add SSE heartbeat** -- Prevent proxy timeouts. Effort: 30m. Impact: Reliability improvement for reverse-proxy deployments.
