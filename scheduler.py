from __future__ import annotations
"""
scheduler.py — Run the fetcher on demand or install a daily macOS launchd job.

Usage:
  python scheduler.py --run-now
  python scheduler.py --install-launchd
  python scheduler.py --uninstall
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PLIST_LABEL = "com.biorxiv.feed.daily"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"
LOG_DIR = SCRIPT_DIR / "logs"

# launchd runs the fetcher silently; open command then surfaces the HTML
PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{script}</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>{log_out}</string>

    <key>StandardErrorPath</key>
    <string>{log_err}</string>

    <key>WorkingDirectory</key>
    <string>{workdir}</string>

    <key>RunAtLoad</key>
    <false/>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
"""


def run_now():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Running bioRxiv fetcher...")
    from biorxiv_fetcher import run_fetch
    papers = run_fetch()
    print(f"\n✓ Done — {len(papers)} preprints fetched.")

    html_file = SCRIPT_DIR / "feed_output" / "index.html"
    if html_file.exists():
        print(f"Opening feed → {html_file}")
        subprocess.run(["open", str(html_file)])
    else:
        print("No HTML file generated — check your config.json keywords and authors.")


def install_launchd():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    plist = PLIST_TEMPLATE.format(
        label=PLIST_LABEL,
        python=sys.executable,
        script=SCRIPT_DIR / "biorxiv_fetcher.py",
        log_out=LOG_DIR / "biorxiv_feed.log",
        log_err=LOG_DIR / "biorxiv_feed.err",
        workdir=SCRIPT_DIR,
    )
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(plist)
    print(f"Wrote plist → {PLIST_PATH}")
    result = subprocess.run(["launchctl", "load", str(PLIST_PATH)], capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Installed — will run daily at 6:00 AM")
        print(f"  Logs: {LOG_DIR}/biorxiv_feed.log")
        print(f"  Feed: {SCRIPT_DIR}/feed_output/index.html")
    else:
        print(f"launchctl error: {result.stderr.strip()}")


def uninstall_launchd():
    if PLIST_PATH.exists():
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
        PLIST_PATH.unlink()
        print(f"✓ Removed {PLIST_PATH}")
    else:
        print("No launchd job found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="bioRxiv Feed Scheduler")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-now", action="store_true")
    group.add_argument("--install-launchd", action="store_true")
    group.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()

    if args.run_now:
        run_now()
    elif args.install_launchd:
        install_launchd()
    elif args.uninstall:
        uninstall_launchd()
