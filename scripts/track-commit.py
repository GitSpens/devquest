#!/usr/bin/env python3
"""
DevQuest Git Commit Tracker

Called by the post-commit git hook. Analyzes the commit, calculates
rewards, updates state, and prints a notification.

Usage:
    python track-commit.py --state <path-to-state.json> --theme <theme-name>
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from fnmatch import fnmatch
from pathlib import Path


DEFAULT_EXCLUDED_PATTERNS = [
    "*.lock", "*.min.js", "*.min.css", "package-lock.json", "yarn.lock",
    "*.map", "*.svg", "*.png", "*.jpg", "*.gif", "*.ico",
    "*.woff", "*.woff2", "*.ttf", "*.eot",
]


def parse_args():
    parser = argparse.ArgumentParser(description="DevQuest commit tracker")
    parser.add_argument("--state", required=True, help="Path to .devquest/state.json")
    parser.add_argument("--theme", default="fantasy", help="Theme name for notifications")
    return parser.parse_args()


def load_state(state_path):
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_state(state_path, state):
    os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_excluded_patterns(state, state_path):
    config_path = os.path.join(os.path.dirname(state_path), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            patterns = config.get("tracking", {}).get("excluded_patterns")
            if patterns is not None:
                return patterns
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return state.get("tracking", {}).get("excluded_patterns", DEFAULT_EXCLUDED_PATTERNS)


def is_excluded(filepath, patterns):
    basename = os.path.basename(filepath)
    for pattern in patterns:
        if fnmatch(basename, pattern) or fnmatch(filepath, pattern):
            return True
    return False


def git_cmd(*args):
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def count_lines_added(excluded_patterns):
    output = git_cmd("diff", "--numstat", "HEAD~1", "HEAD")
    if not output:
        return 0
    total = 0
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, _, filepath = parts
        if added == "-":
            continue
        if is_excluded(filepath, excluded_patterns):
            continue
        total += int(added)
    return total


def get_commit_message():
    return git_cmd("log", "-1", "--format=%s")


def get_commit_sha():
    return git_cmd("rev-parse", "HEAD")


def get_git_user():
    return git_cmd("config", "user.name")


def get_commit_author():
    return git_cmd("log", "-1", "--format=%an")


def is_bug_fix(message):
    return bool(re.match(r"^fix(\(.*\))?:", message, re.IGNORECASE))


def main():
    args = parse_args()
    state = load_state(args.state)
    if state is None or not state.get("enabled", False):
        sys.exit(0)

    git_user = get_git_user()
    commit_author = get_commit_author()
    if git_user and commit_author and git_user != commit_author:
        sys.exit(0)

    excluded = get_excluded_patterns(state, args.state)
    lines_added = count_lines_added(excluded)
    commit_msg = get_commit_message()
    commit_sha = get_commit_sha()
    bug_fix = is_bug_fix(commit_msg)

    if lines_added == 0 and not bug_fix:
        state.setdefault("tracking", {})["last_tracked_commit"] = commit_sha
        save_state(args.state, state)
        sys.exit(0)

    # Reward pipeline will be added in Task 2
    print(f"[DevQuest] Tracked {lines_added} lines (bug_fix={bug_fix})")

    state.setdefault("tracking", {})["last_tracked_commit"] = commit_sha
    save_state(args.state, state)


if __name__ == "__main__":
    main()
