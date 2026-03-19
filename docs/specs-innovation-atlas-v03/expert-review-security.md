# Expert Review: Security & Stability

**Reviewer:** Security & Stability Expert
**Date:** 2026-03-19
**Scope:** Full codebase review across all 5 patrol zones
**Release:** 0.3

---

## Executive Summary

The codebase exhibits a solid design philosophy (stdlib-only, local-only data, no user-facing web forms) that inherently limits the attack surface. However, several classes of bugs -- silent error swallowing, unclosed resources, data mutation correctness issues, and missing CDN integrity checks -- reduce the overall security and stability posture. The most critical finding is the UsageEvent mutation bug in hermit.py, which produces silently incorrect cost data. The server has a permissive CORS policy and lacks basic hardening.

**Overall Score: 41/70** (see breakdown below)

---

## Dimension Scores

### 1. Input Validation & Sanitization: 6/10

**Justification:** The parsers read from fixed, well-known filesystem paths (home-directory agent logs). There is no user-controlled path input into file operations, which eliminates classic path traversal. However, validation of data *within* log files is minimal.

**Strengths:**
- All parser roots are hardcoded to `Path.home()` subdirectories -- no user-supplied paths reach `open()` or `sqlite3.connect()`.
- `_si()` in `_base.py:138-139` safely coerces values to int with a fallback of 0.
- `_ts()` in `_base.py:134-135` handles malformed timestamps gracefully.
- `_epoch_ts()` in `hermit.py:19-26` catches `ValueError`, `TypeError`, `OSError`.
- `server.py:30-37` bounds-checks the `days` and `interval` query parameters with min/max clamping.
- `server.py:238-241` validates `since` format before use.

**Weaknesses:**
- JSONL parsing (`_base.py:34-49`) accepts **any** dict from JSON, with no schema validation. A malformed log entry with unexpected types (e.g., a string where an int is expected) propagates silently into aggregation.
- `codex.py:49` passes raw SQLite results directly into `SessionMeta` with `r[1]` (cwd) unchecked -- a malicious or corrupted `codex.db` could inject unexpected data into the dashboard payload.
- `hermit.py:329-330` reads arbitrary JSON files from the sessions directory with `json.load()`. While the directory is fixed, file content is untrusted and only type-checked at the top level (`isinstance(data, dict)`).
- No validation that token counts are non-negative before creating `UsageEvent` objects (a corrupt DB with negative values would produce negative costs).

**Priority Recommendations:**
1. (MEDIUM) Add non-negative assertions for token counts in all parsers before creating UsageEvent.
2. (LOW) Consider a lightweight schema check (expected keys + types) for JSONL rows to catch corruption early.

---

### 2. Error Handling Robustness: 4/10

**Justification:** This is the weakest dimension. The codebase has 8 instances of `except Exception: pass` that silently swallow errors, plus an additional 14 `except Exception` blocks that either `continue` or `return` without logging. This makes debugging production issues extremely difficult.

**Complete `except Exception: pass` inventory:**

| # | File | Line | Scope | Severity |
|---|------|------|-------|----------|
| 1 | `aggregation/insights.py` | 27-28 | Entire insight rule execution | HIGH -- hides bugs in all 10 insight rules |
| 2 | `parsers/codex.py` | 53-54 | SQLite meta query (codex.db) | MEDIUM -- hides DB schema changes |
| 3 | `parsers/codex.py` | 77-78 | Session duration parsing | LOW -- single field |
| 4 | `parsers/codex.py` | 80-81 | Entire state_5.sqlite parsing | HIGH -- hides complete DB failure |
| 5 | `parsers/hermit.py` | 132-133 | `conn.close()` failure | LOW -- cleanup, acceptable |
| 6 | `parsers/cursor.py` | 103-104 | Commit date parsing | LOW -- single field |
| 7 | `parsers/cursor.py` | 122-123 | Entire codegen DB parsing | HIGH -- hides complete DB failure |
| 8 | `server.py` | 140-141 | Background precompute thread | CRITICAL -- silently swallows any pipeline failure in the background thread |

**Additional silent swallowing (except Exception + continue/return):**
- `parsers/hermit.py:119-120` -- SQLite connect failure (acceptable: skip corrupt DB)
- `parsers/hermit.py:129` -- entire conversation/receipt/task parsing block (HIGH)
- `parsers/hermit.py:165,233,269` -- individual SQL query failures (MEDIUM)
- `parsers/hermit.py:331` -- session JSON load failure (acceptable: skip corrupt file)
- `parsers/claude.py:237` -- (would need to verify scope)
- `parsers/_base.py:40,44` -- JSON line parse + file read (acceptable: skip corrupt lines/files)

**Priority Recommendations:**
1. (CRITICAL) `server.py:140-141`: Log exceptions in the background precompute thread. A persistent failure here means the dashboard silently serves stale data forever.
   ```python
   except Exception:
       import traceback
       traceback.print_exc()
   ```
2. (HIGH) `insights.py:27-28`: At minimum, collect exceptions and log a warning. Currently, a bug in any insight rule is invisible.
   ```python
   except Exception as exc:
       import warnings
       warnings.warn(f"Insight rule {rule.__name__} failed: {exc}")
   ```
3. (HIGH) Replace all DB-level `except Exception: pass` blocks with `except Exception as exc: warnings.warn(...)`.

---

### 3. Resource Management: 5/10

**Justification:** There are confirmed resource leaks in SQLite connections and unbounded cache growth.

**SQLite Connection Leak -- CONFIRMED (codex.py:49):**
```python
for r in sqlite3.connect(str(db)).execute("SELECT id,cwd,git_branch FROM threads").fetchall():
```
The `sqlite3.connect()` return value is never assigned to a variable and never closed. The connection object is created inline, and while CPython's reference counting *may* close it when the iterator is exhausted, this is an implementation detail -- not guaranteed behavior. On PyPy or under memory pressure, this leaks file descriptors.

**Fix:**
```python
with sqlite3.connect(str(db)) as conn:
    for r in conn.execute("SELECT id,cwd,git_branch FROM threads").fetchall():
        ...
```

**SQLite in hermit.py -- PROPERLY HANDLED:**
Lines 117-133 show explicit `conn.close()` in both success and error paths. This is correct.

**SQLite in cursor.py -- PARTIALLY HANDLED:**
Line 75 opens a connection, line 121 closes it, but the `conn.close()` is inside the `try` block. If an exception occurs between line 75 and line 121, the connection leaks. The outer `except Exception: pass` at line 122 does not close the connection.

**Fix:**
```python
try:
    conn = sqlite3.connect(str(CURSOR_DB))
    # ... queries ...
finally:
    conn.close()
```

**Unbounded Cache Growth -- CONFIRMED:**

1. `_JSONL_CACHE` (`_base.py:13`): Maps file paths to parsed content. No eviction policy. In `--serve` mode with rotating log files, old entries accumulate indefinitely. Each entry stores the full parsed list of dicts.

2. `_RESULT_CACHE` (`_base.py:59`): Stores complete `ParseResult` objects per parser name. Limited to 4 entries (one per parser), so this is bounded.

3. `_PAYLOAD_CACHE` (`server.py:26`): Keyed by `(days, since)` tuples. Different query parameter combinations create new entries that are never evicted. A client cycling through `days=1,2,3,...,365` would create 365 cache entries, each containing the full dashboard payload.

4. `chartCache` (frontend `charts.js`): Stores ECharts instances. Bounded by number of chart containers (fixed ~37).

**Priority Recommendations:**
1. (HIGH) Fix `codex.py:49` SQLite connection leak -- use context manager.
2. (HIGH) Fix `cursor.py:75` -- use `try/finally` to ensure `conn.close()`.
3. (MEDIUM) Add LRU eviction to `_JSONL_CACHE` (e.g., max 200 entries, evict oldest by access time).
4. (MEDIUM) Add max-size to `_PAYLOAD_CACHE` in `server.py` (e.g., max 8 entries).

---

### 4. Concurrency Safety: 6/10

**Justification:** The threading model is adequate for the expected workload but has identifiable race conditions.

**Thread Safety Analysis:**

- `_JSONL_CACHE` (`_base.py:13`): Protected by `_FILE_CACHE_LOCK` for writes (lines 26-27, 47-48) but **read access at line 30-31 is unlocked**. The `_JSONL_CACHE.get(key)` call races with concurrent writes. In CPython, dict operations are atomic due to the GIL, so this is safe in practice but technically a data race under a GIL-free Python (PEP 703).

- `_RESULT_CACHE` (`_base.py:59`): Protected by `_RESULT_CACHE_LOCK` for reads (line 101-102) and writes (line 118-119). Correct.

- `_RESULT_HIT_FLAGS` (`_base.py:91`): Written without any lock at lines 104 and 106. This dict is read by `all_caches_hit()` at line 112. Since `parse_all()` calls parsers in a `ThreadPoolExecutor`, multiple threads write to this dict concurrently. In CPython, this is safe due to GIL atomicity of dict `__setitem__`, but it is fragile.

- `_ACTIVE_RANGE` (`_base.py:64`): Set by `set_active_range()` at line 69-70, which is called from `parse_all()` before launching parser threads. Parsers read it in `result_cache_get()`. No lock, but since it is set before threads start and only read by them, this is safe (happens-before relationship via `ThreadPoolExecutor.submit`).

- `_dashboard_cache` / `_dashboard_cache_key` (`cli.py:17-18`): Module-level globals mutated by `build_dashboard_payload()` at lines 30, 78-79. This function is called from:
  - `server.py:58` via `_build_payload()`, which is called from `_cached_payload()`.
  - `_cached_payload()` is called from the background precompute thread AND from request handler threads.
  - `_PAYLOAD_LOCK` in `server.py` serializes access to `_PAYLOAD_CACHE`, but `build_dashboard_payload()` itself has **no lock** protecting `_dashboard_cache`. If two threads call `build_dashboard_payload()` concurrently (possible if a request arrives while the background thread is computing), they could interleave reads and writes of `_dashboard_cache`.

**Race Condition in cli.py (confirmed):**
Thread A reads `_dashboard_cache_key` at line 54, finds a match, and begins to update `_dashboard_cache["_meta"]` at line 55. Simultaneously, Thread B is in the process of assigning a new dict to `_dashboard_cache` at line 78. Thread A's mutation could be lost or applied to the old dict.

**SSE Thread Accumulation:**
Each SSE client in `_write_stream()` holds a thread in a `while True` loop with `time.sleep(interval)`. There is no limit on concurrent SSE connections. An attacker could open thousands of SSE connections, exhausting the thread pool. `ThreadingHTTPServer` uses `ThreadPoolExecutor` (or spawns threads), so this is a DoS vector.

**Priority Recommendations:**
1. (HIGH) Add a threading lock around `_dashboard_cache` access in `cli.py`, or restructure to use the server-side lock exclusively.
2. (MEDIUM) Limit concurrent SSE connections (e.g., max 10 clients, reject with 503 when full).
3. (LOW) Use explicit locks for `_RESULT_HIT_FLAGS` writes to be GIL-free-ready.

---

### 5. Data Integrity: 4/10

**Justification:** The UsageEvent mutation bug is confirmed and produces silently incorrect cost/total values.

**UsageEvent Mutation Bug -- CONFIRMED and SEVERE:**

**Location 1: `hermit.py:196-200`** (in `_parse_conversations`):
```python
existing.uncached_input = uncached
existing.cache_read = cache_read
existing.cache_write = cache_write
existing.output = out_tok
existing.timestamp = ts
```

**Location 2: `hermit.py:414-416`** (in `_parse_sessions`, cache supplement):
```python
db_evt.cache_read = sup_cr
db_evt.cache_write = sup_cw
db_evt.uncached_input = max(0, total_inp - sup_cr - sup_cw)
```

**Impact:** `UsageEvent.__post_init__` (models.py:90-107) computes `_total`, `_cost`, and `_cost_bd` at construction time and stores them as private attributes. The `cost` and `total` properties (lines 110-119) return these cached values. After mutation, these properties return **stale values** from the original construction.

Example: An event created with `uncached_input=1000, cache_read=0` has `_total=1000` and `_cost` computed accordingly. If `cache_read` is later mutated to 500 and `uncached_input` to 500, `_total` still reports 1000 (correct by coincidence in this case), but `_cost` is wrong because cache_read pricing differs from uncached_input pricing. The `_cost_bd` breakdown dict is also stale.

**Severity: HIGH.** This affects all cost calculations for Hermit events that are updated by either code path. The dashboard will display incorrect cost data for Hermit source.

**Fix (create new event):**
```python
# Instead of mutating, create a replacement:
new_evt = UsageEvent(
    source=existing.source,
    timestamp=ts,
    session_id=existing.session_id,
    model=existing.model,
    uncached_input=uncached,
    cache_read=cache_read,
    cache_write=cache_write,
    output=out_tok,
)
# Replace in the output list
idx = out.index(existing)
out[idx] = new_evt
db_conversation_events[cid] = new_evt
```

**Additional mutation in codex.py:170:**
```python
pending_calls[cid].exit_code = int(m.group(1))
```
This mutates `ToolCall.exit_code` after creation. Unlike `UsageEvent`, `ToolCall` has no computed properties, so this mutation is safe -- but it violates immutability principles.

**Stale Cache Risk:**
`_dashboard_cache` in `cli.py:55` mutates the cached dashboard dict in-place:
```python
_dashboard_cache["_meta"]["generated_at"] = now_local.isoformat(timespec="seconds")
```
This modifies the cached dict, meaning any reference to the old dict (e.g., an in-flight SSE response being serialized) sees the mutation. In practice, `json.dumps` serializes atomically, but this is a design smell.

**Priority Recommendations:**
1. (CRITICAL) Fix UsageEvent mutation in hermit.py -- create new events instead of mutating fields.
2. (MEDIUM) Fix ToolCall mutation in codex.py:170,189 for consistency.
3. (LOW) Clone `_dashboard_cache` before mutating `_meta` in cli.py.

---

### 6. Server Security: 7/10

**Justification:** The server binds to localhost by default, which provides strong network-level protection. However, it lacks several hardening measures.

**Strengths:**
- Default bind to `127.0.0.1` (`server.py:384`) -- not exposed to the network unless explicitly changed.
- Only 5 routes are handled (`/`, `/api/dashboard`, `/api/dashboard/stream`, `/health`, `/favicon.ico`). All other paths return 404.
- No static file serving -- eliminates path traversal entirely.
- ETag-based caching with `If-None-Match` support (line 215).
- `no-store` cache control for HTML response (line 231).
- Input validation on query parameters (`_parse_int`, `_parse_range`).

**Weaknesses:**

1. **Permissive CORS (`Access-Control-Allow-Origin: *`)** (line 210): While the server is localhost-only, this header allows any website to make requests to the dashboard API if the user has the server running. A malicious website could read the user's AI agent usage data (token counts, costs, session IDs, project names, file paths) via cross-origin fetch.

   **Risk:** MEDIUM. Requires the server to be running and the user to visit a malicious site. The data exposure includes project names, file paths, and cost data.

   **Fix:** Remove the CORS header or restrict to same-origin.

2. **No rate limiting on SSE connections:** As noted in concurrency section, unbounded SSE connections are a DoS vector.

3. **No Content-Security-Policy:** The HTML loads scripts from `cdn.jsdelivr.net` and `esm.sh` (line 9 of index.html). No CSP meta tag restricts script execution.

4. **No response size limits:** The full dashboard payload is serialized to JSON for each SSE push. A very active user with thousands of sessions could produce multi-megabyte payloads.

5. **Header injection:** Not applicable -- `BaseHTTPRequestHandler.send_header()` does not allow CRLF injection in modern Python.

6. **Path traversal:** Not applicable -- no static file serving, all routes are explicit string matches.

**Priority Recommendations:**
1. (HIGH) Change CORS header to same-origin or remove it entirely. Localhost APIs should not have `Access-Control-Allow-Origin: *`.
2. (MEDIUM) Add a max-connections counter for SSE endpoints.
3. (LOW) Add a `Content-Security-Policy` meta tag to the HTML template.

---

### 7. Dependency Security: 9/10

**Justification:** The stdlib-only constraint is genuinely maintained for the Python backend. The frontend loads 3 external resources from CDNs without integrity verification.

**Python Backend:**
- All imports verified: `json`, `sqlite3`, `threading`, `pathlib`, `collections`, `datetime`, `functools`, `hashlib`, `http.server`, `argparse`, `os`, `signal`, `sys`, `time`, `webbrowser`, `urllib.parse`, `re`, `statistics`, `warnings`, `concurrent.futures`, `atexit`, `fcntl`. All are Python stdlib.
- `tomllib` (Python 3.11+) with `tomli` fallback in `hermit.py:43-53` -- `tomli` is an optional external dependency, but it is only used if `tomllib` is unavailable (Python <3.11) and only for reading config files. Graceful fallback to default model on import failure.

**Frontend CDN Dependencies (index.html:7-9):**
1. `fontawesome-free@6/css/all.min.css` from `cdn.jsdelivr.net` -- **No SRI hash**
2. `echarts@5/dist/echarts.min.js` from `cdn.jsdelivr.net` -- **No SRI hash**
3. Preact + htm from `esm.sh` (importmap, lines 10-17) -- **No SRI hash, and currently unused**

**Risk:** A CDN compromise or supply-chain attack on jsdelivr.net could inject malicious JavaScript into the dashboard. Since the dashboard displays local file paths, session data, and cost information, a compromised CDN script could exfiltrate this data.

**Mitigating Factor:** The dashboard is primarily used locally (`file://` protocol for static, `http://127.0.0.1` for live). The static HTML file is self-contained after build, so CDN scripts execute in a context with access to all dashboard data.

**Priority Recommendations:**
1. (MEDIUM) Add `integrity` and `crossorigin` attributes to CDN script/link tags (Subresource Integrity).
2. (LOW) Remove unused Preact/htm importmap to eliminate unnecessary CDN requests.

---

## Total Score

| Dimension | Score | Max |
|-----------|-------|-----|
| Input Validation & Sanitization | 6 | 10 |
| Error Handling Robustness | 4 | 10 |
| Resource Management | 5 | 10 |
| Concurrency Safety | 6 | 10 |
| Data Integrity | 4 | 10 |
| Server Security | 7 | 10 |
| Dependency Security | 9 | 10 |
| **Total** | **41** | **70** |

---

## Vulnerability Inventory

### CRITICAL (2)

| ID | Category | File:Line | Description |
|----|----------|-----------|-------------|
| C-1 | Data Integrity | `hermit.py:196-200, 414-416` | UsageEvent mutation bypasses `__post_init__`, producing stale `cost` and `total` values for all Hermit events updated via multi-DB dedup or cache supplementation |
| C-2 | Error Handling | `server.py:140-141` | Background precompute thread swallows all exceptions silently; persistent failures cause indefinitely stale dashboard data with no visible error |

### HIGH (5)

| ID | Category | File:Line | Description |
|----|----------|-----------|-------------|
| H-1 | Resource Management | `codex.py:49` | SQLite connection leak: inline `sqlite3.connect()` never closed |
| H-2 | Error Handling | `insights.py:27-28` | `except Exception: pass` hides bugs in all 10 insight rule functions |
| H-3 | Error Handling | `codex.py:80-81` | `except Exception: pass` hides complete state_5.sqlite parsing failure |
| H-4 | Error Handling | `cursor.py:122-123` | `except Exception: pass` hides complete codegen DB parsing failure |
| H-5 | Server Security | `server.py:210` | `Access-Control-Allow-Origin: *` allows any website to read local agent usage data via cross-origin requests |

### MEDIUM (7)

| ID | Category | File:Line | Description |
|----|----------|-----------|-------------|
| M-1 | Concurrency | `cli.py:17-18, 54-55, 78-79` | `_dashboard_cache` globals have no lock; concurrent access from request threads and background thread creates race condition |
| M-2 | Resource Management | `cursor.py:75-121` | SQLite connection not closed on exception between open and close |
| M-3 | Resource Management | `_base.py:13` | `_JSONL_CACHE` grows unboundedly in long-running serve mode |
| M-4 | Resource Management | `server.py:26` | `_PAYLOAD_CACHE` grows unboundedly with varying query parameters |
| M-5 | Dependency Security | `index.html:8-9` | CDN scripts loaded without Subresource Integrity (SRI) hashes |
| M-6 | Server Security | `server.py:271-280` | No limit on concurrent SSE connections; potential thread exhaustion DoS |
| M-7 | Data Integrity | `cli.py:55` | In-place mutation of cached dashboard dict's `_meta.generated_at` |

### LOW (6)

| ID | Category | File:Line | Description |
|----|----------|-----------|-------------|
| L-1 | Error Handling | `codex.py:53-54, 77-78` | Silent exception swallowing in individual field parsing |
| L-2 | Error Handling | `hermit.py:165, 233, 269` | Silent exception swallowing in individual SQL queries |
| L-3 | Data Integrity | `codex.py:170, 189` | ToolCall.exit_code mutated after creation (no computed properties affected, but violates immutability) |
| L-4 | Input Validation | parsers (various) | No validation that token counts are non-negative |
| L-5 | Dependency Security | `index.html:10-17` | Unused Preact/htm importmap adds unnecessary CDN requests |
| L-6 | Server Security | `index.html` | No Content-Security-Policy meta tag |

---

## Fix Recommendations (Priority Order)

### Tier 1: Fix Before Release (1-2 hours)

**C-1: UsageEvent Mutation Bug**

In `hermit.py:_parse_conversations` (around line 195), replace mutation with new event creation:

```python
# Replace lines 196-200 with:
new_evt = UsageEvent(
    source=existing.source,
    timestamp=ts,
    session_id=existing.session_id,
    model=existing.model,
    uncached_input=uncached,
    cache_read=cache_read,
    cache_write=cache_write,
    output=out_tok,
)
idx = out.index(existing)
out[idx] = new_evt
db_conversation_events[cid] = new_evt
```

Apply the same pattern at lines 414-416 for cache supplement.

**C-2: Background Thread Error Logging**

In `server.py:140-141`:
```python
except Exception:
    import sys, traceback
    print("[payload-precompute] Error:", file=sys.stderr)
    traceback.print_exc()
```

**H-1: Codex SQLite Leak**

In `codex.py:47-54`:
```python
if db.exists():
    try:
        with sqlite3.connect(str(db)) as conn:
            for r in conn.execute("SELECT id,cwd,git_branch FROM threads").fetchall():
                ...
    except Exception as exc:
        warnings.warn(f"codex.db meta query failed: {exc}")
```

**H-5: CORS Restriction**

In `server.py:210`, remove or restrict:
```python
# Remove this line:
self.send_header("Access-Control-Allow-Origin", "*")
```

### Tier 2: Fix Soon After Release (2-4 hours)

**H-2/H-3/H-4: Error Swallowing**

Replace all `except Exception: pass` with at minimum `warnings.warn()` calls. This applies to:
- `insights.py:27-28`
- `codex.py:80-81`
- `cursor.py:122-123`

**M-1: Dashboard Cache Lock**

Add a lock to `cli.py`:
```python
_dashboard_lock = threading.Lock()
# ... inside build_dashboard_payload:
with _dashboard_lock:
    if not changed and _dashboard_cache is not None and _dashboard_cache_key == cache_key:
        ...
```

**M-2: Cursor SQLite Resource Safety**

Wrap `cursor.py:75-121` in `try/finally` with `conn.close()`.

**M-3/M-4: Cache Eviction**

Add a max-size check to `_JSONL_CACHE` and `_PAYLOAD_CACHE` (evict oldest entries when exceeding threshold).

### Tier 3: Hardening (4-8 hours)

- M-5: Add SRI hashes to CDN script/link tags
- M-6: Add SSE connection counter with a configurable limit
- L-5: Remove unused Preact importmap
- L-6: Add CSP meta tag

---

## Patrol Report Accuracy Assessment

| Report | Claims Verified | Accuracy |
|--------|----------------|----------|
| Parsers | UsageEvent mutation: confirmed severe. SQLite leak: confirmed. Unbounded cache: confirmed. | High -- all material claims validated |
| Aggregation | Silent exception in insights.py: confirmed. Duplication: confirmed but not a security issue. | High for security-relevant claims |
| Charts | Missing data guards: confirmed but low security impact (frontend crash, not security). | Moderate -- findings are stability, not security |
| Frontend Core | CORS issue not mentioned (gap). Unused importmap: confirmed. Global state: confirmed but is a stability issue. No CSP: correctly identified. | Moderate -- missed the CORS finding |
| Core | Race condition in cli.py globals: confirmed. Thread-per-SSE DoS: confirmed. `_gp()` ordering: confirmed as correctness issue, not security. | High -- accurately identified key issues |

**Gap in Patrol Reports:** None of the 5 patrol reports identified the CORS `Access-Control-Allow-Origin: *` vulnerability (H-5), which allows cross-origin data exfiltration of local agent usage data. This was the most significant finding missed by the patrol phase.
