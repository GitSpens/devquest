#!/usr/bin/env python3
"""
DevQuest Enable — Full Project Setup

Creates state.json with defaults, installs git hook, and configures
permissions. Run this FIRST during /devquest-enable, before any
conversation or customization.

Usage:
    python devquest-enable.py --repo <path> [--name <name>] [--theme <theme>] [--env <env>] [--display <mode>]

If state.json already exists with progress, preserves character data
and only updates settings/setup.

Exit codes:
    0 — success
    1 — error
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_STATE = {
    "enabled": True,
    "settings": {
        "environment": "cli",
        "theme": "fantasy",
        "display_mode": "markdown"
    },
    "character": {
        "name": "",
        "level": 1,
        "total_xp_earned": 0,
        "gold": 0,
        "gold_spent": 0,
        "attributes": {
            "code_mastery": 0
        },
        "active_buffs": [],
        "achievements": {}
    },
    "stats": {
        "lines_written": 0,
        "items_purchased": 0
    },
    "weekly_stats": {
        "week_start": "",
        "weekly_xp_earned": 0,
        "weekly_gold_earned": 0,
        "weekly_lines_written": 0,
        "weekly_quests_completed": 0
    },
    "quests": {
        "1": {"progress": 0, "completed": False, "claimed": False},
        "2": {"progress": 0, "completed": False, "claimed": False},
        "3": {"progress": 0, "completed": False, "claimed": False},
        "4": {"progress": 0, "completed": False, "claimed": False},
        "5": {"progress": 0, "completed": False, "claimed": False}
    },
    "tracking": {
        "last_tracked_commit": None,
        "excluded_patterns": [
            "*.lock", "*.min.js", "*.min.css", "package-lock.json", "yarn.lock",
            "*.map", "*.svg", "*.png", "*.jpg", "*.gif", "*.ico",
            "*.woff", "*.woff2", "*.ttf", "*.eot",
            "*.yml", "*.yaml", "*.json", "*.toml", "*.ini", "*.cfg", "*.conf",
            "*.xml", "*.plist", "*.properties", "*.env", "*.env.*",
            "Dockerfile", "docker-compose*", ".dockerignore",
            ".gitignore", ".gitattributes", ".editorconfig", ".prettierrc",
            ".eslintrc", ".stylelintrc", "tsconfig.json", "jest.config.*",
            "Makefile", "Procfile",
            "*.md", "*.txt", "*.rst", "*.csv", "LICENSE*", "CHANGELOG*"
        ]
    }
}


def get_current_monday():
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def get_git_user(repo_path):
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, cwd=repo_path, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def create_state(repo_path, name, theme, env, display_mode):
    """Create or update state.json. Preserves existing progress."""
    state_dir = os.path.join(repo_path, ".devquest")
    state_path = os.path.join(state_dir, "state.json")
    os.makedirs(state_dir, exist_ok=True)

    existing = None
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    if existing and existing.get("character", {}).get("total_xp_earned", 0) > 0:
        existing["enabled"] = True
        existing["settings"]["environment"] = env
        existing["settings"]["theme"] = theme
        existing["settings"]["display_mode"] = display_mode
        if name:
            existing["character"]["name"] = name
        state = existing
    else:
        import copy
        state = copy.deepcopy(DEFAULT_STATE)
        state["settings"]["environment"] = env
        state["settings"]["theme"] = theme
        state["settings"]["display_mode"] = display_mode
        state["character"]["name"] = name or get_git_user(repo_path)
        state["weekly_stats"]["week_start"] = get_current_monday()

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return "created" if existing is None else "updated"


def run_setup(repo_path, theme):
    """Run setup-project.py for hook + permissions."""
    cmd = [sys.executable, str(SCRIPT_DIR / "setup-project.py"),
           "--repo", repo_path, "--theme", theme]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="DevQuest enable")
    parser.add_argument("--repo", required=True, help="Path to project root")
    parser.add_argument("--name", default="", help="Player name")
    parser.add_argument("--theme", default="fantasy", help="Theme (fantasy/scifi/retro/minimalist)")
    parser.add_argument("--env", default="cli", help="Environment (cli/desktop)")
    parser.add_argument("--display", default="markdown", help="Display mode (markdown/html)")
    args = parser.parse_args()

    theme = args.theme.lower().replace("-", "").replace("_", "")

    status = create_state(args.repo, args.name, theme, args.env, args.display)
    print(f"State: {status}")

    ok, msg = run_setup(args.repo, theme)
    print(msg)

    if ok:
        print(f"DevQuest enabled successfully.")
    else:
        print(f"Warning: setup had issues, but state was created.")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
