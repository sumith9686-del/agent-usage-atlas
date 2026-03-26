#!/usr/bin/env python3
"""HTTP service for the live dashboard."""

from __future__ import annotations

import argparse
import atexit
import gzip
import hashlib
import json
import os
import signal
import sys

if sys.platform != "win32":
    import fcntl
import threading
import time
import traceback
import webbrowser
from collections import OrderedDict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__
from .builder import build_html
from .cli import build_dashboard_payload
from .parsers import CLAUDE_ROOT, CODEX_ROOTS, CURSOR_ROOT, HERMIT_ROOTS

_PAYLOAD_CACHE: OrderedDict[
    tuple[int, str | None], tuple[dict, str, bytes, bytes, tuple[int, int, int], dict[int, bytes]]
] = OrderedDict()
_PAYLOAD_LOCK = threading.Lock()
_PAYLOAD_CACHE_MAX = 8
_BUILD_LOCK = threading.Lock()  # serialize parse_all to avoid _ACTIVE_RANGE race

# SSE connection limiting
_SSE_MAX_CONNECTIONS = 10
_SSE_SEMAPHORE = threading.Semaphore(_SSE_MAX_CONNECTIONS)
_SSE_ACTIVE = 0
_SSE_ACTIVE_LOCK = threading.Lock()


def _parse_int(value: str | None, default: int, minimum: int = 1, maximum: int = 3600) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _parse_range(query: str, *, default_days: int) -> tuple[int, str | None]:
    params = parse_qs(query)
    since = params.get("since", [None])[0]
    if since is not None:
        if len(since) > 10:
            since = None
        else:
            try:
                datetime.strptime(since, "%Y-%m-%d")
            except ValueError:
                since = None
    days = _parse_int(params.get("days", [None])[0], default=default_days, minimum=1, maximum=3650)
    return days, since


def _sse_encode(obj: object) -> bytes:
    payload = json.dumps(obj, ensure_ascii=False)
    return f"data: {payload}\n\n".encode("utf-8")


def _json_body(payload: object) -> tuple[bytes, str]:
    body = json.dumps(payload, ensure_ascii=False)
    encoded = body.encode("utf-8")
    return encoded, hashlib.sha256(encoded).hexdigest()


def _build_payload(days: int, since: str | None) -> dict:
    return build_dashboard_payload(days=days, since=since)


def _iter_payload_files():
    for root in CODEX_ROOTS:
        if root.exists():
            for path in root.rglob("*.jsonl"):
                yield path
    if CLAUDE_ROOT.exists():
        for path in CLAUDE_ROOT.rglob("*.jsonl"):
            if path.name == "sessions-index.json":
                continue
            yield path
    if CURSOR_ROOT.exists():
        for path in CURSOR_ROOT.rglob("*.jsonl"):
            if "agent-transcripts" not in str(path):
                continue
            yield path
    for db_path in HERMIT_ROOTS:
        if db_path.exists():
            yield db_path
            wal = db_path.parent / (db_path.name + "-wal")
            if wal.exists():
                yield wal


_SIG_FILE_LIST: list[Path] = []
_SIG_FILE_LIST_TIME: float = 0.0
_SIG_FILE_LIST_LOCK = threading.Lock()
_SIG_RESCAN_INTERVAL: float = 30.0  # seconds between full rglob rescans

# TTL cache for signature result to avoid re-statting files on every call
_SIG_CACHED_RESULT: tuple[int, int, int] = (0, 0, 0)
_SIG_CACHED_TIME: float = 0.0
_SIG_TTL: float = 5.0  # seconds


def _payload_signature() -> tuple[int, int, int]:
    global _SIG_FILE_LIST, _SIG_FILE_LIST_TIME, _SIG_CACHED_RESULT, _SIG_CACHED_TIME

    with _SIG_FILE_LIST_LOCK:
        now = time.monotonic()

        # Return cached signature if within TTL (checked inside lock to
        # prevent multiple threads from computing the signature simultaneously)
        if _SIG_CACHED_TIME and (now - _SIG_CACHED_TIME) < _SIG_TTL:
            return _SIG_CACHED_RESULT

        if not _SIG_FILE_LIST or (now - _SIG_FILE_LIST_TIME) > _SIG_RESCAN_INTERVAL:
            _SIG_FILE_LIST = list(_iter_payload_files())
            _SIG_FILE_LIST_TIME = now
        file_list_snapshot = list(_SIG_FILE_LIST)

    newest_mtime_ns = 0
    total_bytes = 0
    file_count = 0
    for path in file_list_snapshot:
        try:
            st = path.stat()
        except OSError:
            continue
        newest_mtime_ns = max(newest_mtime_ns, int(st.st_mtime_ns))
        total_bytes += int(st.st_size)
        file_count += 1
    result = (newest_mtime_ns, total_bytes, file_count)

    with _SIG_FILE_LIST_LOCK:
        _SIG_CACHED_RESULT = result
        _SIG_CACHED_TIME = time.monotonic()
        return result


def _cached_payload(days: int, since: str | None) -> tuple[dict, str, bytes, bytes]:
    key = (days, since)
    signature = _payload_signature()
    with _PAYLOAD_LOCK:
        entry = _PAYLOAD_CACHE.get(key)
        if entry is not None:
            payload, etag, json_bytes, gzip_bytes, payload_sig, _html_cache = entry
            if payload_sig == signature:
                _PAYLOAD_CACHE.move_to_end(key)
                return payload, etag, json_bytes, gzip_bytes

    # Serialize builds so concurrent threads don't stomp on the global
    # _ACTIVE_RANGE inside parse_all, which causes inconsistent event counts.
    with _BUILD_LOCK:
        # Re-check cache — another thread may have just built it.
        signature = _payload_signature()
        with _PAYLOAD_LOCK:
            entry = _PAYLOAD_CACHE.get(key)
            if entry is not None:
                payload, etag, json_bytes, gzip_bytes, payload_sig, _html_cache = entry
                if payload_sig == signature:
                    _PAYLOAD_CACHE.move_to_end(key)
                    return payload, etag, json_bytes, gzip_bytes

        payload = _build_payload(days=days, since=since)
        json_bytes, etag = _json_body(payload)
        gzip_bytes = gzip.compress(json_bytes, compresslevel=6)
        # Re-compute signature AFTER build to capture any file changes during build
        post_build_sig = _payload_signature()
        cache_entry = (payload, etag, json_bytes, gzip_bytes, post_build_sig, {})
        with _PAYLOAD_LOCK:
            _PAYLOAD_CACHE[key] = cache_entry
            _PAYLOAD_CACHE.move_to_end(key)
            while len(_PAYLOAD_CACHE) > _PAYLOAD_CACHE_MAX:
                _PAYLOAD_CACHE.popitem(last=False)
        return payload, etag, json_bytes, gzip_bytes


# ── Background pre-computation thread ──

_BG_THREAD: threading.Thread | None = None
_BG_STOP = threading.Event()


def _bg_precompute(days: int, since: str | None, interval: int) -> None:
    """Daemon thread that periodically refreshes the payload cache."""
    while not _BG_STOP.is_set():
        try:
            _cached_payload(days=days, since=since)
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            print(f"[payload-precompute] Pipeline error: {exc}", file=sys.stderr)
        _BG_STOP.wait(timeout=max(1, interval - 1))


def _start_bg_precompute(days: int, since: str | None, interval: int) -> None:
    global _BG_THREAD
    if _BG_THREAD is not None:
        return
    _BG_STOP.clear()
    _BG_THREAD = threading.Thread(
        target=_bg_precompute,
        args=(days, since, interval),
        daemon=True,
        name="payload-precompute",
    )
    _BG_THREAD.start()


def _log(address: str, fmt: str, *args: object) -> None:
    """Print a log line matching BaseHTTPRequestHandler.log_message format."""
    ts = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
    message = fmt % args if args else fmt
    sys.stderr.write(f"{address} - - [{ts}] {message}\n")


class _ReuseAddrServer(ThreadingHTTPServer):
    allow_reuse_address = True


class DashboardHandler(BaseHTTPRequestHandler):
    default_days: int = 30
    default_since: str | None = None
    default_interval: int = 5

    def handle(self) -> None:
        """Suppress ConnectionResetError from browser closing SSE / refreshing."""
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError, TimeoutError):
            pass

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Suppress noisy default logging for SSE reconnects; keep normal request logs
        super().log_message(format, *args)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._write_index()
            return
        if parsed.path == "/api/dashboard":
            self._write_dashboard(parsed.query)
            return
        if parsed.path == "/api/dashboard/stream":
            self._write_stream(parsed.query)
            return
        if parsed.path == "/health":
            self._write_health()
            return
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self._send_security_headers()
            self.end_headers()
            return
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(b"Not Found")

    def _send_security_headers(self) -> None:
        """Add security headers to every response."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")

    def _write_headers(self, status: int = 200, *, content_type: str, cache_control: str = "no-cache") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", cache_control)
        self._send_security_headers()
        self.end_headers()

    def _write_json(
        self, payload: object, status: int = 200, *, etag: str | None = None, gzip_bytes: bytes | None = None
    ) -> None:
        body, computed_etag = _json_body(payload)
        etag = etag or computed_etag
        if status == 200 and self.headers.get("If-None-Match") == f'"{etag}"':
            self.send_response(304)
            self._send_security_headers()
            self.end_headers()
            return
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("ETag", f'"{etag}"')
        self.send_header("Vary", "Accept-Encoding")
        if self._accepts_gzip():
            body = gzip_bytes if gzip_bytes is not None else gzip.compress(body, compresslevel=6)
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _accepts_gzip(self) -> bool:
        return "gzip" in (self.headers.get("Accept-Encoding") or "")

    def _write_index(self) -> None:
        poll_ms = max(2000, self.default_interval * 1000)
        key = (self.default_days, self.default_since)

        # Try to serve cached compressed HTML
        with _PAYLOAD_LOCK:
            entry = _PAYLOAD_CACHE.get(key)
            if entry is not None:
                html_cache = entry[5]
                cached_body = html_cache.get(poll_ms)
                if cached_body is not None:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Vary", "Accept-Encoding")
                    if self._accepts_gzip():
                        self.send_header("Content-Encoding", "gzip")
                    self.send_header("Content-Length", str(len(cached_body)))
                    self._send_security_headers()
                    self.end_headers()
                    self.wfile.write(cached_body)
                    return

        payload, _, __, ___ = _cached_payload(days=self.default_days, since=self.default_since)
        template = build_html(payload, poll_interval_ms=poll_ms, live=True)
        body = template.encode("utf-8")
        body = gzip.compress(body, compresslevel=6)

        # Cache the compressed HTML for future requests
        with _PAYLOAD_LOCK:
            entry = _PAYLOAD_CACHE.get(key)
            if entry is not None:
                entry[5][poll_ms] = body

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Vary", "Accept-Encoding")
        if self._accepts_gzip():
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _write_health(self) -> None:
        self._write_json(
            {
                "status": "ok",
                "version": __version__,
            }
        )

    def _write_dashboard(self, query: str) -> None:
        days, since = _parse_range(query, default_days=self.default_days)
        if since:
            try:
                datetime.strptime(since, "%Y-%m-%d")
            except ValueError:
                self._write_json({"error": "since must be YYYY-MM-DD"}, status=400)
                return
        since = since or self.default_since
        _, etag, json_bytes, gzip_bytes = _cached_payload(days=days, since=since)
        if self.headers.get("If-None-Match") == f'"{etag}"':
            self.send_response(304)
            self._send_security_headers()
            self.end_headers()
            return
        body = json_bytes
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("ETag", f'"{etag}"')
        self.send_header("Vary", "Accept-Encoding")
        if self._accepts_gzip():
            body = gzip_bytes
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _write_stream(self, query: str) -> None:
        parsed = parse_qs(query)
        interval = _parse_int(parsed.get("interval", [None])[0], default=self.default_interval, minimum=2, maximum=60)
        days, since = _parse_range(query, default_days=self.default_days)
        if since:
            try:
                datetime.strptime(since, "%Y-%m-%d")
            except ValueError:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self._send_security_headers()
                self.end_headers()
                self.wfile.write(b"since must be YYYY-MM-DD")
                return
        since = since or self.default_since

        # Enforce SSE connection limit
        if not _SSE_SEMAPHORE.acquire(blocking=False):
            self.send_response(503)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self._send_security_headers()
            self.end_headers()
            self.wfile.write(b"Too many SSE connections")
            return

        try:
            with _SSE_ACTIVE_LOCK:
                global _SSE_ACTIVE
                _SSE_ACTIVE += 1
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self._send_security_headers()
            self.end_headers()
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()

            known_etag = ""
            heartbeat_interval = 15.0  # seconds
            last_write = time.monotonic()
            try:
                while True:
                    _, etag, json_bytes, _gz = _cached_payload(days=days, since=since)
                    now = time.monotonic()
                    if etag != known_etag:
                        known_etag = etag
                        self.wfile.write(b"data: ")
                        self.wfile.write(json_bytes)
                        self.wfile.write(b"\n\n")
                        self.wfile.flush()
                        last_write = now
                    elif (now - last_write) >= heartbeat_interval:
                        # Send heartbeat if idle too long
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
                        last_write = now
                    time.sleep(interval)
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                return
        finally:
            with _SSE_ACTIVE_LOCK:
                _SSE_ACTIVE -= 1
            _SSE_SEMAPHORE.release()


_LOCK_FILE = Path.home() / ".cache" / "agent-usage-atlas" / "server.lock"
_lock_fp = None


def _kill_pid(pid: int) -> bool:
    """Send SIGTERM to *pid* and wait for it to exit. Returns True if killed."""
    if pid == os.getpid():
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    for _ in range(30):
        time.sleep(0.1)
        try:
            os.kill(pid, 0)
        except OSError:
            print(f"Stopped previous server (PID {pid}).", file=sys.stderr)
            return True
    # Still alive — force kill
    try:
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.2)
        print(f"Force-stopped previous server (PID {pid}).", file=sys.stderr)
    except OSError:
        pass
    return True


def _kill_port_holder(port: int) -> None:
    """Find and kill whatever process is listening on *port*."""
    import subprocess

    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f":{port}"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return
    for line in out.splitlines():
        try:
            pid = int(line.strip())
        except ValueError:
            continue
        _kill_pid(pid)


def _acquire_lock(port: int) -> None:
    """Acquire an exclusive file lock; kill any existing server first."""
    if sys.platform == "win32":
        return
    global _lock_fp
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    _lock_fp = open(_LOCK_FILE, "r+") if _LOCK_FILE.exists() else open(_LOCK_FILE, "w")  # noqa: SIM115
    try:
        fcntl.flock(_lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        # Lock held — read PID from file and kill
        _lock_fp.seek(0)
        try:
            old_pid = int(_lock_fp.read().strip())
            _kill_pid(old_pid)
        except (ValueError, OSError):
            pass
        _lock_fp.close()
        _lock_fp = None
        time.sleep(0.3)
        _lock_fp = open(_LOCK_FILE, "w")  # noqa: SIM115
        try:
            fcntl.flock(_lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            _lock_fp.close()
            _lock_fp = None
            print("Error: could not stop the previous server.", file=sys.stderr)
            sys.exit(1)

    # Even with the lock, the port might be held by a stale process
    _kill_port_holder(port)
    time.sleep(0.2)

    _lock_fp.seek(0)
    _lock_fp.truncate()
    _lock_fp.write(str(os.getpid()))
    _lock_fp.flush()
    atexit.register(_release_lock)


def _release_lock() -> None:
    if sys.platform == "win32":
        return
    global _lock_fp
    if _lock_fp is not None:
        try:
            fcntl.flock(_lock_fp, fcntl.LOCK_UN)
            _lock_fp.close()
        except OSError:
            pass
        _lock_fp = None


def _make_handler(days: int, since: str | None, interval: int) -> type:
    """Return a DashboardHandler subclass with the given defaults baked in."""

    class _Handler(DashboardHandler):
        default_days = days
        default_since = since
        default_interval = interval

    return _Handler


def run_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    days: int = 30,
    since: str | None = None,
    interval: int = 5,
    open_browser: bool = False,
) -> None:
    _acquire_lock(port)

    if since:
        datetime.strptime(since, "%Y-%m-%d")

    _cached_payload(days=days, since=since)
    _start_bg_precompute(days=days, since=since, interval=interval)

    server = _ReuseAddrServer((host, port), _make_handler(days, since, interval))
    url = f"http://{host}:{port}"
    _log(host, "Agent Usage Atlas dashboard server running at %s", url)
    _log(host, "JSON: %s/api/dashboard", url)
    _log(host, "SSE:  %s/api/dashboard/stream?interval=%d", url, interval)

    if open_browser:
        webbrowser.open(url)

    def _on_signal(signum, frame):
        _BG_STOP.set()
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _on_signal)

    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        _BG_STOP.set()
        server.server_close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-usage-atlas-server",
        description="Serve a local dashboard from agent logs.",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--since", type=str, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--interval", type=int, default=5)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    run_server(
        host=args.host,
        port=args.port,
        days=args.days,
        since=args.since,
        interval=args.interval,
    )


if __name__ == "__main__":
    main()
