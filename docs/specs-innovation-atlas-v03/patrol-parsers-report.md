# Patrol Report: Parsers Zone

**Zone:** `src/agent_usage_atlas/parsers/`
**Date:** 2026-03-19
**Agent:** Patrol (Parsers Zone)
**Status:** Complete

---

## 1. Zone Overview and File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 63 | Parser registry; concurrent dispatch via `ThreadPoolExecutor`; merges `ParseResult` objects |
| `_base.py` | 139 | Shared utilities: JSONL reading with file-signature cache, result-level caching, timestamp/int helpers |
| `claude.py` | 248 | Claude Code JSONL parser; per-file incremental cache; deduplication by `(session_id, message_id)` |
| `codex.py` | 260 | Codex CLI JSONL + SQLite parser; cumulative-delta token counting; session meta from DB |
| `cursor.py` | 124 | Cursor parser; activity message counting from transcripts; SQLite code-gen tracking |
| `hermit.py` | 416 | Hermit agent parser; multi-DB scanning (archives, backups, WAL); session JSON supplementation |
| **Total** | **1250** | |

**Test file:** `tests/test_parsers.py` (54 lines) -- covers only `_ts()` and `_si()` helpers from `_base.py`. No tests for any parser logic.

### Data Flow

```
parse_all() -> ThreadPoolExecutor
  -> codex.parse()  -> ParseResult
  -> claude.parse() -> ParseResult
  -> cursor.parse() -> ParseResult
  -> hermit.parse() -> ParseResult
  -> claude.parse_stats_cache() -> dict
All merged via ParseResult.merge()
```

### Key Architectural Features
- Two-tier caching: file-level signature cache (`_JSONL_CACHE`) and result-level cache with composite file signature
- Thread-safe via `threading.Lock` on all caches
- 30-second timeout on parser futures; 10-second timeout on stats cache
- Each parser produces `ParseResult` dataclasses consumed by `aggregation.py`

---

## 2. Twelve-Dimension Scoring Table

### 2.1 Maintainability (20 pts max): **12/20**

| Factor | Score | Justification |
|--------|-------|---------------|
| Code complexity | 7/10 | Functions are generally well-structured. `claude._parse_single_file` (115 lines) and `codex.parse` (240 lines) are at the upper bound of acceptable. Hermit at 416 lines is the largest single file. Nesting depth stays within 4-5 levels in most cases but hits 6 in some Claude message extraction paths. |
| Dependency freshness | 3/5 | stdlib-only (json, sqlite3, threading, pathlib) -- no dependency rot risk. However, `tomllib` import in hermit has a fallback to `tomli` that may confuse type checkers. |
| Test coverage | 2/5 | Only `_ts()` and `_si()` are tested (~5% of parser code). Zero coverage for actual parsing logic, caching, deduplication, cumulative-delta math, SQLite interactions, or error paths. This is the biggest maintainability gap. |

### 2.2 Performance/Stability Risk (20 pts max): **14/20**

| Factor | Score | Justification |
|--------|-------|---------------|
| Known bottlenecks | 7/10 | `_read_json_lines()` reads entire files into memory (all rows as dicts). For large JSONL files (>100MB), this causes memory spikes. No streaming/generator approach. `rglob("*.jsonl")` on deep directory trees can be slow. The `_RESCAN_INTERVAL=10s` partially mitigates rescan cost. |
| Crash risk | 7/10 | Broad `except Exception` guards prevent crashes but silently swallow errors (e.g., `codex.py:53`, `hermit.py:129`, `cursor.py:122`). SQLite connections in `codex.py:49` are not properly closed on success path (inline `.connect().execute().fetchall()` pattern). `hermit.py` properly closes connections. |

### 2.3 Architecture Consistency (15 pts max): **12/15**

| Factor | Score | Justification |
|--------|-------|---------------|
| Project norms | 7/8 | Follows stdlib-only constraint. Uses dataclasses from `models.py`. Consistent `ParseResult` return type across all parsers. |
| Internal consistency | 5/7 | Parser function signatures differ slightly: `cursor.parse(start_utc, now_utc, local_tz=None)` has an extra param vs others. Hermit uses type annotations (`start_utc: datetime`) while others don't. Variable naming is mostly consistent but `_si`, `_ts`, `_gp` are cryptic single-letter abbreviations. |

### 2.4 Innovation Potential (25 pts max): **16/25**

| Factor | Score | Justification |
|--------|-------|---------------|
| Achievable breakthroughs | 16/25 | **Breakthrough 1: Memory-mapped incremental JSONL parsing.** Current approach reads full files into memory. A line-index approach (tracking byte offsets of previously parsed lines) would allow appending new lines only, reducing re-parse cost from O(n) to O(delta). This is well-documented in structured logging literature (e.g., Uber's CLP -- Compressed Log Processor, OSDI 2019; Splunk's journal indexing). **Breakthrough 2: Schema-aware parser generation.** Each parser hand-codes field extraction from JSON dicts. A declarative schema (defining expected fields, paths, transforms) could auto-generate parsers, reducing boilerplate by ~60% and making new agent support trivial. Related: OpenTelemetry's log data model (OTLP) and the filelog receiver pattern in OpenTelemetry Collector. |

### 2.5 Community/Paper Frontier Match (20 pts max): **12/20**

| Factor | Score | Justification |
|--------|-------|---------------|
| Tech evolution match | 12/20 | The log parsing domain has seen significant activity: (1) OpenTelemetry's universal logging protocol has matured with OTLP logs GA. (2) ClickHouse/DuckDB embedded analytics for local log querying. (3) CLP (Compressed Log Processor) from U of T/Uber for compressed log search. However, the project's niche (local AI agent log aggregation) is still underserved -- most tools target server-side observability. The stdlib-only constraint limits adoption of these frameworks but the patterns are applicable. |

### 2.6 ROI (20 pts max): **15/20**

| Factor | Score | Justification |
|--------|-------|---------------|
| Effort vs benefit | 15/20 | **High ROI items:** (1) Adding tests for parser logic (~2-3 hours, massive stability benefit). (2) Fixing SQLite connection leak in codex.py (~10 min fix). (3) Standardizing parser signatures (~30 min). **Medium ROI:** Incremental JSONL parsing (~4-6 hours, significant perf improvement for heavy users). **Lower ROI:** Schema-based parser generation (~1-2 days, valuable for extensibility but current 4-parser count doesn't urgently need it). |

---

## 3. Total Score and Decision Category

| Dimension | Score | Max |
|-----------|-------|-----|
| Maintainability | 12 | 20 |
| Performance/Stability Risk | 14 | 20 |
| Architecture Consistency | 12 | 15 |
| Innovation Potential | 16 | 25 |
| Community/Paper Frontier Match | 12 | 20 |
| ROI | 15 | 20 |
| **Total** | **81** | **120** |

**Decision Category: Stability Bug/Refactor** (60-84 range)

---

## 4. Innovation Search Results

Hermit task submission failed (`Session not found`), and web search was unavailable. Analysis based on domain knowledge (cutoff: May 2025).

### Top 3 Frontier Approaches

1. **Append-only Incremental JSONL Parsing with Line Index**
   - Technique: Maintain a byte-offset index per file. On re-parse, seek to last-known offset and parse only new lines. Combined with the existing `_file_signature` mtime check.
   - Reference: Filebeat's harvester pattern (Elastic); Fluent Bit's tail input plugin; CLP (Compressed Log Processor, OSDI 2019).
   - Applicability: Direct fit. The current `_read_json_lines()` re-reads entire files every time the mtime changes (even if 1 line was appended).

2. **OpenTelemetry Log Data Model for Agent Telemetry**
   - Technique: Normalize all parser outputs to OTLP LogRecord schema, enabling interop with any OTEL-compatible backend.
   - Reference: OpenTelemetry Logs specification (GA since Nov 2024); opentelemetry-python-contrib filelog receiver.
   - Applicability: Would standardize the `ParseResult` model and enable export to Grafana/Jaeger, but conflicts with the "zero external dependencies" constraint. Best adopted as an optional export path.

3. **DuckDB In-Process Analytics for Aggregation**
   - Technique: Replace Python-side aggregation with SQL queries over structured data, using DuckDB's zero-copy Parquet/JSON reading.
   - Reference: DuckDB project; MotherDuck's embedded analytics pattern.
   - Applicability: Would dramatically simplify `aggregation.py` but introduces an external dependency (violates project constraint). Could be an optional "turbo mode."

### 1 Not-Yet-Widely-Adopted Breakthrough

**Adaptive Parser Fingerprinting:** Automatically detect log format (Claude vs Codex vs Cursor vs unknown) by sampling the first N lines and matching against known field-signature patterns (similar to MIME type detection). This would enable a single entry point `parse_auto(path)` that routes to the correct parser without requiring directory-based heuristics. Related work: LogPAI's Drain3 algorithm for automated log template extraction (ICSE 2019), adapted for structured JSON rather than unstructured text.

---

## 5. Innovation Index Calculation

| Criterion | Score (0-10) | Weight | Weighted |
|-----------|-------------|--------|----------|
| Reference Value (maturity + fit) | 7.5 | 0.4 | 3.00 |
| Innovation Increment (generational gap) | 5.0 | 0.5 | 2.50 |
| Risk Controllability | 8.5 | 0.1 | 0.85 |
| **Innovation Index** | | | **6.35** |

**Innovation Increment justification:** The current caching system already provides a reasonable optimization layer. Incremental JSONL parsing is an evolutionary improvement (~1.0 generation gap), not a paradigm shift (which would require >= 1.5 generations). The adaptive parser fingerprinting is novel but the current 4-parser architecture doesn't create enough pain to justify the complexity.

**Decision: Innovation Index 6.35 < 7.5 threshold. Downgrade to stability optimization.**

---

## 6. Final Decision and Rationale

**Decision: Stability Bug/Refactor**

**Rationale:**
- Total score of 81/120 places this zone firmly in the "Stability Bug/Refactor" category (60-84).
- Innovation Index of 6.35 is below the 7.5 threshold for innovation features.
- The most impactful work is addressing the near-zero test coverage and fixing identified bugs.
- The caching architecture is already well-designed; incremental improvements are evolutionary, not breakthrough.

---

## 7. Identified Issues and Proposed Changes

### Issue 1: SQLite Connection Leak in codex.py (CRITICAL)

**Location:** `codex.py:49`

```python
# CURRENT (leaked connection):
for r in sqlite3.connect(str(db)).execute("SELECT id,cwd,git_branch FROM threads").fetchall():
```

The `sqlite3.connect()` return value is never closed. This leaks file handles.

**Fix:** Use context manager or explicit close.

### Issue 2: Silent Error Swallowing (MEDIUM)

Multiple locations use bare `except Exception: pass` patterns:
- `codex.py:53` (SQLite meta query)
- `codex.py:81` (state_5.sqlite session durations)
- `cursor.py:122` (entire codegen DB parsing)
- `hermit.py:129` (DB connection/query errors)

These hide real bugs. At minimum, these should use `warnings.warn()` like `__init__.py:41` does.

### Issue 3: Inconsistent Parser Signatures (LOW)

- `cursor.parse(start_utc, now_utc, local_tz=None)` -- extra `local_tz` param (not used in the function body for token parsing, only implicitly via file timestamps)
- Type annotations present in `hermit.py` but absent in other parsers
- No consistent docstring format

### Issue 4: Mutation of UsageEvent in hermit.py (MEDIUM)

**Location:** `hermit.py:190-200` and `hermit.py:410-416`

The hermit parser mutates `UsageEvent` objects after creation:
```python
existing.uncached_input = uncached
existing.cache_read = cache_read
...
```

This bypasses `__post_init__`, so the cached `_total`, `_cost`, and `_cost_bd` properties become stale. Any downstream code using `.cost` or `.total` on these events gets incorrect values.

**This is a correctness bug.** After mutation, a new `UsageEvent` should be created, or `__post_init__` should be re-called.

### Issue 5: `_read_json_lines` Caches Grow Unboundedly (LOW)

`_JSONL_CACHE` in `_base.py` stores all parsed file contents forever. For long-running `--serve` mode with many log files, this can consume significant memory. No eviction policy exists.

---

## 8. Code Changes Implemented

**No code changes were made.** Per constraints, the patrol agent does not commit code. The identified issues are documented above for the main controller to action.

---

## 9. Self-Verification Re-Scoring

Re-running the scoring table after analysis:

| Dimension | Initial | Re-score | Delta |
|-----------|---------|----------|-------|
| Maintainability | 12 | 11 | -1 (Issue 4 -- mutation bug is worse than initially assessed) |
| Performance/Stability Risk | 14 | 13 | -1 (Issue 1 -- connection leak confirmed) |
| Architecture Consistency | 12 | 12 | 0 |
| Innovation Potential | 16 | 16 | 0 |
| Community/Paper Frontier Match | 12 | 12 | 0 |
| ROI | 15 | 15 | 0 |
| **Total** | **81** | **79** | **-2** |

Delta of -2 is within the 8-point stability threshold. No forced redo required.

**Final score: 79/120 -- Stability Bug/Refactor confirmed.**

---

## 10. Hermit Tasks Submitted and Outcomes

| Task | Query | Status |
|------|-------|--------|
| 1 | JSONL parsing optimization, multi-format log unification, incremental parsers, token counting (arXiv/GitHub/Reddit) | **FAILED** -- Hermit session not found |
| 2 | GitHub search for multi-agent log aggregation projects, JSONL incremental parsers, unified AI telemetry | **FAILED** -- Hermit session not found |

**Fallback:** Analysis conducted using domain knowledge and code review only. No DAG tasks were launched due to hermit unavailability.

---

## 11. Priority Action Items (Recommended Order)

1. **[BUG] Fix UsageEvent mutation in hermit.py** -- Stale cost/total after field mutation. Create new events or re-invoke `__post_init__`. Estimated effort: 30 min.
2. **[BUG] Fix SQLite connection leak in codex.py:49** -- Use `with` context manager. Estimated effort: 10 min.
3. **[QUALITY] Add parser unit tests** -- Target: test each parser's `parse()` function with synthetic JSONL/SQLite fixtures. Current coverage ~5%, target 80%+. Estimated effort: 3-4 hours.
4. **[QUALITY] Replace bare `except Exception: pass` with `warnings.warn()`** -- 4 locations. Estimated effort: 15 min.
5. **[REFACTOR] Standardize parser signatures and add type annotations** -- Align all parsers to `(start_utc: datetime, now_utc: datetime) -> ParseResult`. Estimated effort: 30 min.
6. **[PERF] Add LRU eviction to `_JSONL_CACHE`** -- Prevent unbounded memory growth in serve mode. Estimated effort: 1 hour.
