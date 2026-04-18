#!/usr/bin/env python3
"""
DevQuest Git Commit Tracker

Called by the post-commit git hook. Analyzes the commit, calculates
rewards, updates state, and prints a notification.

Usage:
    python track-commit.py --state <path-to-state.json> --theme <theme-name>
"""

import argparse
import io
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from fnmatch import fnmatch
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


DEFAULT_EXCLUDED_PATTERNS = [
    "*.lock", "*.min.js", "*.min.css", "package-lock.json", "yarn.lock",
    "*.map", "*.svg", "*.png", "*.jpg", "*.gif", "*.ico",
    "*.woff", "*.woff2", "*.ttf", "*.eot",
]

# ---------------------------------------------------------------------------
# Progression Constants
# ---------------------------------------------------------------------------

XP_THRESHOLDS = [0, 100, 250, 500, 800, 1200, 1800, 2500, 3500, 5000,
                 7000, 9500, 12500, 16000, 20000, 25000, 31000, 38000, 46000, 55000]

LEVEL_TITLES = {
    "fantasy": [
        "Apprentice", "Squire", "Knight", "Paladin", "Wizard",
        "Sorcerer", "Warlock", "Archmage", "Champion", "Legend",
        "Mythic Knight", "Dragon Slayer", "Sage", "Archon", "Demigod",
        "Titan", "Elder God", "Primordial", "Eternal", "Ascended",
    ],
    "scifi": [
        "Cadet", "Ensign", "Engineer", "Lieutenant", "Commander",
        "Captain", "Major", "Colonel", "Admiral", "Fleet Admiral",
        "Commodore Prime", "Star Marshal", "Sector Commander", "Galaxy Admiral", "Fleet Sovereign",
        "Void Walker", "Quantum Lord", "Singularity", "Transcendent", "Ascended",
    ],
    "retro": [
        "Noob", "Rookie", "Pro", "Veteran", "Elite",
        "Master", "Legend", "Mythic", "Godlike", "Transcendent",
        "Pixel Lord", "Bit Crusher", "Glitch King", "ROM Hacker", "Cartridge God",
        "Console Titan", "Arcade Phantom", "8-Bit Deity", "Final Boss", "Game Over",
    ],
    "minimalist": [f"L{i}" for i in range(1, 21)],
}

THEME_XP_ICONS = {"fantasy": "\u2728", "scifi": "\u26a1", "retro": "\U0001f525", "minimalist": "XP"}

THEME_LEVELUP_MESSAGES = {
    "fantasy": "\u2728 The realm trembles with your power! You have risen to **{title}** (Level {level})! \U0001f409",
    "scifi": "\u26a1 Rank update confirmed. You are now designated **{title}** \u2014 Level {level} operative. \U0001f30c",
    "retro": "\U0001f47e LEVEL UP! You've unlocked **{title}** \u2014 Level {level}! \U0001f3c6",
    "minimalist": "Level up. You are now {title} (level {level}). Continue.",
}

QUEST_DEFINITIONS = {
    "1": {"name": "First Blood",    "field": "lines_written", "target": 10,   "xp": 20,  "gold": 10},
    "2": {"name": "Centurion",      "field": "lines_written", "target": 100,  "xp": 100, "gold": 50},
    "3": {"name": "Thousand Lines", "field": "lines_written", "target": 1000, "xp": 500, "gold": 250},
}

ACHIEVEMENT_DEFINITIONS = {
    "first_line": {"name": "First Blood",  "check": lambda s: s.get("stats", {}).get("lines_written", 0) >= 1},
    "century":    {"name": "Century",      "check": lambda s: s.get("stats", {}).get("lines_written", 0) >= 100},
    "hoarder":    {"name": "Gold Hoarder", "check": lambda s: s.get("character", {}).get("gold", 0) >= 500},
    "level_5":    {"name": "Rising Star",  "check": lambda s: get_level(s.get("character", {}).get("total_xp_earned", 0)) >= 5},
    "level_10":   {"name": "Veteran",      "check": lambda s: get_level(s.get("character", {}).get("total_xp_earned", 0)) >= 10},
    "level_20":   {"name": "Ascended",     "check": lambda s: get_level(s.get("character", {}).get("total_xp_earned", 0)) >= 20},
}


# ---------------------------------------------------------------------------
# Progression Helpers
# ---------------------------------------------------------------------------

def get_level(total_xp):
    """Return the current level (1-20) for the given total XP."""
    for i in range(19, -1, -1):
        if total_xp >= XP_THRESHOLDS[i]:
            return i + 1
    return 1


def get_title(theme, level):
    """Return the display title for a given theme and level."""
    titles = LEVEL_TITLES.get(theme, LEVEL_TITLES["fantasy"])
    idx = max(0, min(level - 1, len(titles) - 1))
    return titles[idx]


def make_xp_bar(total_xp):
    """Return (bar_string, progress, needed). 14-char bar with = and -."""
    level = get_level(total_xp)
    if level >= 20:
        return "[==============] MAX", 0, 0
    current_threshold = XP_THRESHOLDS[level - 1]
    next_threshold = XP_THRESHOLDS[level]
    progress = total_xp - current_threshold
    needed = next_threshold - current_threshold
    filled = round(14 * progress / needed) if needed > 0 else 14
    empty = 14 - filled
    bar = "[" + "=" * filled + "-" * empty + "]"
    return bar, progress, needed


def get_current_monday():
    """Return ISO date string of most recent Monday."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def check_weekly_reset(state):
    """If week_start != current monday, reset all weekly counters."""
    weekly = state.setdefault("weekly_stats", {})
    current_monday = get_current_monday()
    if weekly.get("week_start") != current_monday:
        weekly["week_start"] = current_monday
        weekly["weekly_xp_earned"] = 0
        weekly["weekly_gold_earned"] = 0
        weekly["weekly_lines_written"] = 0
        weekly["weekly_tests_run"] = 0
        weekly["weekly_bugs_fixed"] = 0
        weekly["weekly_functions_documented"] = 0
        weekly["weekly_quests_completed"] = 0


# ---------------------------------------------------------------------------
# Quest and Achievement Functions
# ---------------------------------------------------------------------------

def update_quests(state):
    """Update quest progress and auto-claim completed quests. Return notifications."""
    quests = state.setdefault("quests", {})
    stats = state.get("stats", {})
    character = state.get("character", {})
    weekly = state.setdefault("weekly_stats", {})
    notifications = []

    for qid, qdef in QUEST_DEFINITIONS.items():
        quest = quests.setdefault(qid, {"progress": 0, "completed": False, "claimed": False})
        if quest.get("completed", False):
            continue

        # Update progress from stats
        quest["progress"] = stats.get(qdef["field"], 0)

        # Check completion
        if quest["progress"] >= qdef["target"]:
            quest["completed"] = True
            quest["claimed"] = True
            # Award rewards
            character["total_xp_earned"] = character.get("total_xp_earned", 0) + qdef["xp"]
            character["gold"] = character.get("gold", 0) + qdef["gold"]
            weekly["weekly_xp_earned"] = weekly.get("weekly_xp_earned", 0) + qdef["xp"]
            weekly["weekly_gold_earned"] = weekly.get("weekly_gold_earned", 0) + qdef["gold"]
            weekly["weekly_quests_completed"] = weekly.get("weekly_quests_completed", 0) + 1
            notifications.append(
                f"QUEST COMPLETE: {qdef['name']}! +{qdef['xp']} XP, +{qdef['gold']} Gold"
            )

    return notifications


def check_achievements(state):
    """Check all uncompleted achievements and unlock any that are met. Return notifications."""
    achievements = state.setdefault("character", {}).setdefault("achievements", {})
    notifications = []

    for aid, adef in ACHIEVEMENT_DEFINITIONS.items():
        if achievements.get(aid, {}).get("unlocked", False) if isinstance(achievements.get(aid), dict) else bool(achievements.get(aid)):
            continue
        if adef["check"](state):
            achievements[aid] = {
                "name": adef["name"],
                "unlocked": True,
                "unlocked_at": datetime.now().isoformat(),
            }
            notifications.append(f"ACHIEVEMENT UNLOCKED: {adef['name']}!")

    return notifications


# ---------------------------------------------------------------------------
# Core Reward Function
# ---------------------------------------------------------------------------

def process_rewards(state, lines_added, theme):
    """Calculate and apply rewards. Return (xp_earned, gold_earned, notifications)."""
    character = state.setdefault("character", {})
    stats = state.setdefault("stats", {})
    weekly = state.setdefault("weekly_stats", {})
    notifications = []

    # --- Base rewards ---
    base_xp = lines_added  # 1 XP per line
    base_gold = lines_added * 0.5  # 0.5 gold per line

    # --- Attribute bonuses ---
    attributes = character.get("attributes", {})
    # code_mastery: +3% gold per level from writing code
    cm_level = attributes.get("code_mastery", 0)
    if cm_level > 0:
        base_gold = base_gold * (1 + cm_level * 3 / 100)

    # --- Buff multipliers ---
    active_buffs = character.get("active_buffs", [])
    for buff in active_buffs:
        target = buff.get("effect", {}).get("target", "")
        multiplier = buff.get("effect", {}).get("multiplier", 1.0)
        if target == "code_xp":
            base_xp *= multiplier
        elif target == "all_gold":
            base_gold *= multiplier

    # --- Round ---
    xp_earned = round(base_xp)
    gold_earned = round(base_gold)

    # --- Record old level for level-up detection ---
    old_xp = character.get("total_xp_earned", 0)
    old_level = get_level(old_xp)

    # --- Update state ---
    character["total_xp_earned"] = old_xp + xp_earned
    character["gold"] = character.get("gold", 0) + gold_earned
    stats["lines_written"] = stats.get("lines_written", 0) + lines_added
    weekly["weekly_xp_earned"] = weekly.get("weekly_xp_earned", 0) + xp_earned
    weekly["weekly_gold_earned"] = weekly.get("weekly_gold_earned", 0) + gold_earned
    weekly["weekly_lines_written"] = weekly.get("weekly_lines_written", 0) + lines_added

    # --- Decrement ALL buffs ---
    for buff in active_buffs:
        buff["actions_remaining"] = buff.get("actions_remaining", 0) - 1
    character["active_buffs"] = [b for b in active_buffs if b.get("actions_remaining", 0) > 0]

    # --- Level-up detection ---
    new_level = get_level(character["total_xp_earned"])
    if new_level > old_level:
        for lvl in range(old_level + 1, new_level + 1):
            title = get_title(theme, lvl)
            msg = THEME_LEVELUP_MESSAGES.get(theme, THEME_LEVELUP_MESSAGES["fantasy"])
            notifications.append(msg.format(title=title, level=lvl))

    # --- Quest progress ---
    quest_notifications = update_quests(state)
    notifications.extend(quest_notifications)

    # --- Achievement checks ---
    achievement_notifications = check_achievements(state)
    notifications.extend(achievement_notifications)

    return xp_earned, gold_earned, notifications


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
    commit_sha = get_commit_sha()

    if lines_added == 0:
        state.setdefault("tracking", {})["last_tracked_commit"] = commit_sha
        save_state(args.state, state)
        sys.exit(0)

    theme = args.theme.lower()
    if theme not in LEVEL_TITLES:
        theme = "minimalist"

    # --- Reward pipeline ---
    check_weekly_reset(state)
    xp_earned, gold_earned, notifications = process_rewards(state, lines_added, theme)

    # Build themed notification
    xp_icon = THEME_XP_ICONS.get(theme, "XP")
    level = get_level(state["character"]["total_xp_earned"])
    title = get_title(theme, level)
    bar, progress, needed = make_xp_bar(state["character"]["total_xp_earned"])
    gold_total = state["character"]["gold"]

    if needed > 0:
        main_line = (
            f"{xp_icon} +{xp_earned} XP, +{gold_earned} Gold for {lines_added} lines! "
            f"Level {level} \"{title}\" | XP: {bar} {progress}/{needed} | Gold: {gold_total}"
        )
    else:
        main_line = (
            f"{xp_icon} +{xp_earned} XP, +{gold_earned} Gold for {lines_added} lines! "
            f"Level {level} \"{title}\" | XP: {bar} | Gold: {gold_total}"
        )

    print(main_line)
    for note in notifications:
        print(note)

    state.setdefault("tracking", {})["last_tracked_commit"] = commit_sha
    save_state(args.state, state)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[DevQuest] Warning: tracking failed ({e})", file=sys.stderr)
        sys.exit(0)
