#!/usr/bin/env python3
"""
Capture dashboard screenshots for README / docs.

Strategy:
  1. Generate a static HTML dashboard (data embedded, no SSE delay).
  2. For each section, build a tiny wrapper HTML that iframe-embeds the
     dashboard and offsets it by a known scroll-Y value.
  3. Use Chrome headless (--screenshot) to capture each wrapper.
  4. Auto-crop trailing background rows with macOS `sips` or Pillow.

Usage:
  python scripts/screenshots.py                 # default: 30 days
  python scripts/screenshots.py --days 7
  python scripts/screenshots.py --since 2026-03-01
  python scripts/screenshots.py --chrome /path/to/chrome
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

WIDTH = 1440

# Each entry: (filename, scroll_y, viewport_height)
# Tune scroll_y to frame each dashboard section.
SECTIONS = [
    ("hero-overview",    0,    1050),
    ("cost-charts",      920,  950),
    ("token-charts",     2700, 950),
    ("heatmap-sessions", 3550, 950),
    ("tool-charts",      4550, 950),
    ("tools-efficiency", 5450, 950),
]

# Must match the dashboard's CSS `--bg` variable.
PAGE_BG = "#0d1016"

# ── Helpers ──────────────────────────────────────────────────────────────────

def find_chrome() -> str | None:
    """Locate Chrome / Chromium binary."""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    return None


def generate_dashboard_html(days: int, since: str | None) -> Path:
    """Run the dashboard generator and return the path to the HTML file."""
    out = Path(tempfile.mkdtemp()) / "dashboard.html"
    cmd = [sys.executable, "-m", "agent_usage_atlas", "--output", str(out)]
    if since:
        cmd += ["--since", since]
    else:
        cmd += ["--days", str(days)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[error] Dashboard generation failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"[ok] Generated dashboard: {out}")
    return out


def build_wrapper_html(dashboard_uri: str, scroll_y: int, lang: str = "zh") -> Path:
    """Create a wrapper HTML that iframes the dashboard at a given scroll offset."""
    html = f"""\
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;background:{PAGE_BG};overflow:hidden}}</style>
</head><body><script>
(function(){{
  localStorage.setItem('atlas-lang','{lang}');
  var f=document.createElement('iframe');
  f.src='{dashboard_uri}';
  f.style.cssText='width:{WIDTH}px;height:15000px;border:none;position:absolute;top:-{scroll_y}px;left:0';
  document.body.appendChild(f);
}})();
</script></body></html>"""
    path = Path(tempfile.mktemp(suffix=".html"))
    path.write_text(html, encoding="utf-8")
    return path


def capture(chrome: str, wrapper: Path, out: Path, width: int, height: int) -> bool:
    """Run Chrome headless screenshot and return True on success."""
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--screenshot={out}",
        f"file://{wrapper}",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=20)
    return out.exists() and out.stat().st_size > 1000


def auto_crop(path: Path, target_height: int) -> None:
    """Trim trailing background rows.

    Tries Pillow first (pixel-accurate), falls back to macOS sips (fixed trim).
    """
    try:
        from PIL import Image  # type: ignore

        img = Image.open(path).convert("RGB")
        w, h = img.size
        # Parse the expected background color
        bg_hex = PAGE_BG.lstrip("#")
        bg_rgb = tuple(int(bg_hex[i : i + 2], 16) for i in (0, 2, 4))

        # Scan from bottom to find last non-background row
        bottom = h
        for y in range(h - 1, -1, -1):
            row = img.crop((0, y, w, y + 1)).getdata()
            # Allow tolerance of ±3 per channel for anti-aliasing
            if any(abs(p[0] - bg_rgb[0]) > 3 or abs(p[1] - bg_rgb[1]) > 3 or abs(p[2] - bg_rgb[2]) > 3 for p in row):
                bottom = y + 1
                break

        if bottom < h:
            img.crop((0, 0, w, bottom)).save(path)
            print(f"       Pillow crop: {h} -> {bottom}px")
        return
    except ImportError:
        pass

    # Fallback: sips (macOS only) — trim 10px from bottom as a safe margin
    trim = 10
    cropped_h = target_height - trim
    subprocess.run(
        ["sips", "--cropToHeightWidth", str(cropped_h), str(WIDTH), str(path)],
        capture_output=True,
    )
    print(f"       sips crop: {target_height} -> {cropped_h}px")


# ── Main ─────────────────────────────────────────────────────────────────────

def capture_lang(chrome: str, dashboard_uri: str, outdir: Path, lang: str) -> int:
    """Capture all sections for a given language. Returns success count."""
    print(f"\n[lang] Capturing {lang.upper()} screenshots → {outdir}")
    outdir.mkdir(parents=True, exist_ok=True)
    ok_count = 0
    for name, scroll_y, vh in SECTIONS:
        out = outdir / f"{name}.png"
        wrapper = build_wrapper_html(dashboard_uri, scroll_y, lang=lang)
        try:
            if capture(chrome, wrapper, out, WIDTH, vh):
                auto_crop(out, vh)
                size_kb = out.stat().st_size / 1024
                print(f"  [ok] {name}.png ({size_kb:.0f} KB)")
                ok_count += 1
            else:
                print(f"  [fail] {name}.png")
        finally:
            wrapper.unlink(missing_ok=True)
    return ok_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture dashboard screenshots.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--since", type=str, default=None)
    parser.add_argument("--chrome", type=str, default=None, help="Path to Chrome/Chromium binary")
    parser.add_argument("--outdir", type=str, default=None, help="Output directory (default: docs/screenshots)")
    parser.add_argument("--lang", type=str, default=None, choices=["zh", "en"],
                        help="Capture only one language (default: both zh and en)")
    args = parser.parse_args()

    # Find Chrome
    chrome = args.chrome or find_chrome()
    if not chrome:
        print("[error] Chrome/Chromium not found. Install it or pass --chrome /path/to/chrome", file=sys.stderr)
        sys.exit(1)
    print(f"[ok] Chrome: {chrome}")

    # Output directory
    repo_root = Path(__file__).resolve().parent.parent
    base_outdir = Path(args.outdir) if args.outdir else repo_root / "docs" / "screenshots"
    print(f"[ok] Output base: {base_outdir}")

    # Generate static dashboard
    dashboard = generate_dashboard_html(days=args.days, since=args.since)
    dashboard_uri = dashboard.as_uri()

    # Determine languages to capture
    langs = [args.lang] if args.lang else ["zh", "en"]

    total_ok = 0
    total_sections = 0
    for lang in langs:
        outdir = base_outdir / lang
        total_ok += capture_lang(chrome, dashboard_uri, outdir, lang)
        total_sections += len(SECTIONS)

    # Cleanup
    dashboard.unlink(missing_ok=True)
    dashboard.parent.rmdir()

    print(f"\nDone: {total_ok}/{total_sections} screenshots saved")


if __name__ == "__main__":
    main()
