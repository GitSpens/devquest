#!/usr/bin/env python3
"""
DevQuest Project Setup

Single entry point that runs all project setup: git hook installation
and permission configuration. Called during /devquest-enable.

Usage:
    python setup-project.py --repo <path> --theme <theme>
    python setup-project.py --repo <path> --uninstall

Exit codes:
    0 — all steps succeeded
    1 — one or more steps failed
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run_script(script_name, args):
    """Run a sibling script with the given args. Returns (success, output)."""
    script_path = SCRIPT_DIR / script_name
    cmd = [sys.executable, str(script_path)] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout.strip()
        return result.returncode == 0, output
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="DevQuest project setup")
    parser.add_argument("--repo", required=True, help="Path to git repository")
    parser.add_argument("--theme", default="fantasy", help="Theme name")
    parser.add_argument("--uninstall", action="store_true", help="Remove DevQuest setup")
    args = parser.parse_args()

    all_ok = True

    if args.uninstall:
        ok, msg = run_script("install-hook.py", ["--repo", args.repo, "--uninstall"])
        print(f"Hook: {msg}")
        all_ok = all_ok and ok

        ok, msg = run_script("setup-permissions.py", ["--repo", args.repo, "--uninstall"])
        print(f"Permissions: {msg}")
        all_ok = all_ok and ok
    else:
        ok, msg = run_script("install-hook.py", ["--repo", args.repo, "--theme", args.theme])
        print(f"Hook: {msg}")
        all_ok = all_ok and ok

        ok, msg = run_script("setup-permissions.py", ["--repo", args.repo])
        print(f"Permissions: {msg}")
        all_ok = all_ok and ok

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
