# Git-Based Code Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a git post-commit hook that automatically tracks lines written, awards XP/gold, and prints notifications — enabling manual coding to earn DevQuest rewards without Claude.

**Architecture:** A Python script (`scripts/track-commit.py`) handles all reward logic. A thin bash post-commit hook calls it. SKILL.md is updated to install/remove the hook during enable/disable and to catch up on missed commits at session start.

**Tech Stack:** Python 3 (no external dependencies), Bash (git hooks), JSON (state persistence)

---

### Task 1: Create `scripts/track-commit.py` — Git diff parsing and line counting

**Files:**
- Create: `scripts/track-commit.py`

This task builds the foundation: argument parsing, state loading, git diff analysis, and exclusion pattern filtering. No reward logic yet — just the skeleton that reads a commit and counts lines.

- [ ] **Step 1: Create the script with argument parsing and state loading**

```python
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
```

- [ ] **Step 2: Verify the script runs without errors**

Run: `python scripts/track-commit.py --state .devquest/state.json --theme fantasy`

Expected: exits silently (no state.json exists, so it exits with code 0)

- [ ] **Step 3: Commit**

```bash
git add scripts/track-commit.py
git commit -m "feat: add track-commit.py skeleton with git diff parsing"
```

---

### Task 2: Add the reward pipeline to `track-commit.py`

**Files:**
- Modify: `scripts/track-commit.py`

Add the full reward calculation: base XP/gold, attribute bonuses, buff multipliers, buff decrement, level-up detection, quest progress, achievement checks, and themed notifications.

- [ ] **Step 1: Add constants for XP thresholds, level titles, quest definitions, and theme icons**

Add these constants after the existing `DEFAULT_EXCLUDED_PATTERNS` constant in `scripts/track-commit.py`:

```python
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

THEME_XP_ICONS = {
    "fantasy": "\u2728",   # ✨
    "scifi": "\u26a1",     # ⚡
    "retro": "\U0001f525",  # 🔥
    "minimalist": "XP",
}

THEME_LEVELUP_MESSAGES = {
    "fantasy": "\u2728 The realm trembles with your power! You have risen to **{title}** (Level {level})! \U0001f409",
    "scifi": "\u26a1 Rank update confirmed. You are now designated **{title}** \u2014 Level {level} operative. \U0001f30c",
    "retro": "\U0001f47e LEVEL UP! You've unlocked **{title}** \u2014 Level {level}! \U0001f3c6",
    "minimalist": "Level up. You are now {title} (level {level}). Continue.",
}

QUEST_DEFINITIONS = {
    "1":  {"name": "First Blood",    "field": "lines_written",        "target": 10,   "xp": 20,  "gold": 10},
    "2":  {"name": "Centurion",      "field": "lines_written",        "target": 100,  "xp": 100, "gold": 50},
    "3":  {"name": "Thousand Lines", "field": "lines_written",        "target": 1000, "xp": 500, "gold": 250},
    "4":  {"name": "Test Pilot",     "field": "tests_run",            "target": 5,    "xp": 50,  "gold": 25},
    "5":  {"name": "Test Commander", "field": "tests_passed",         "target": 25,   "xp": 200, "gold": 100},
    "6":  {"name": "Bug Squasher",   "field": "bugs_fixed",           "target": 3,    "xp": 40,  "gold": 20},
    "7":  {"name": "Exterminator",   "field": "bugs_fixed",           "target": 15,   "xp": 200, "gold": 100},
    "8":  {"name": "Scribe",         "field": "functions_documented", "target": 5,    "xp": 30,  "gold": 15},
    "9":  {"name": "Librarian",      "field": "functions_documented", "target": 25,   "xp": 150, "gold": 75},
    "10": {"name": "Well Rounded",   "field": None,                   "target": 4,    "xp": 100, "gold": 50},
    "11": {"name": "Shopaholic",     "field": "items_purchased",      "target": 5,    "xp": 50,  "gold": 0},
    "12": {"name": "Code Miser",     "field": None,                   "target": 500,  "xp": 100, "gold": 0},
}

ACHIEVEMENT_DEFINITIONS = {
    "first_line":  {"name": "First Blood",        "check": lambda s: s["stats"]["lines_written"] >= 1},
    "century":     {"name": "Century",             "check": lambda s: s["stats"]["lines_written"] >= 100},
    "test_pilot":  {"name": "Test Pilot",          "check": lambda s: s["stats"]["tests_run"] >= 10},
    "perfect_run": {"name": "Perfect Run",         "check": lambda s: s["stats"]["consecutive_passing_runs"] >= 5},
    "bug_squasher":{"name": "Bug Squasher",        "check": lambda s: s["stats"]["bugs_fixed"] >= 1},
    "doc_writer":  {"name": "Documentation Hero",  "check": lambda s: s["stats"]["functions_documented"] >= 10},
    "big_spender": {"name": "Big Spender",         "check": lambda s: s["character"]["gold_spent"] >= 100},
    "hoarder":     {"name": "Gold Hoarder",        "check": lambda s: s["character"]["gold"] >= 500},
    "level_5":     {"name": "Rising Star",         "check": lambda s: get_level(s["character"]["total_xp_earned"]) >= 5},
    "level_10":    {"name": "Veteran",             "check": lambda s: get_level(s["character"]["total_xp_earned"]) >= 10},
    "level_20":    {"name": "Ascended",            "check": lambda s: get_level(s["character"]["total_xp_earned"]) >= 20},
    "all_quests":  {"name": "Quest Master",        "check": lambda s: all(q["completed"] for q in s["quests"].values())},
}
```

- [ ] **Step 2: Add helper functions for level calculation, XP bar, and weekly reset**

Add these functions after the constants block, before `main()`:

```python
def get_level(total_xp):
    for lvl in range(19, -1, -1):
        if total_xp >= XP_THRESHOLDS[lvl]:
            return lvl + 1
    return 1


def get_title(theme, level):
    titles = LEVEL_TITLES.get(theme, LEVEL_TITLES["fantasy"])
    return titles[min(level - 1, 19)]


def make_xp_bar(total_xp):
    level = get_level(total_xp)
    if level >= 20:
        return "[==============] MAX", 0, 0
    current_thresh = XP_THRESHOLDS[level - 1]
    next_thresh = XP_THRESHOLDS[level]
    progress = total_xp - current_thresh
    needed = next_thresh - current_thresh
    filled = round(14 * progress / needed) if needed > 0 else 14
    bar = "[" + "=" * filled + "-" * (14 - filled) + "]"
    return bar, progress, needed


def get_current_monday():
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def check_weekly_reset(state):
    current_monday = get_current_monday()
    if state.get("weekly_stats", {}).get("week_start") != current_monday:
        state["weekly_stats"] = {
            "week_start": current_monday,
            "weekly_xp_earned": 0,
            "weekly_gold_earned": 0,
            "weekly_lines_written": 0,
            "weekly_tests_run": 0,
            "weekly_bugs_fixed": 0,
            "weekly_functions_documented": 0,
            "weekly_quests_completed": 0,
        }
```

- [ ] **Step 3: Add the reward pipeline function**

Add this function after `check_weekly_reset`:

```python
def process_rewards(state, lines_added, bug_fix, theme):
    notifications = []

    # --- Base rewards ---
    xp = lines_added * 1
    gold = lines_added * 0.5

    if bug_fix:
        xp += 20
        gold += 5

    # --- Attribute bonuses ---
    attrs = state["character"].get("attributes", {})
    code_mastery = attrs.get("code_mastery", 0)
    debugging = attrs.get("debugging", 0)

    if lines_added > 0 and code_mastery > 0:
        gold = gold * (1 + code_mastery * 3 / 100)

    if bug_fix and debugging > 0:
        xp = xp * (1 + debugging * 10 / 100)

    # --- Buff multipliers ---
    buffs = state["character"].get("active_buffs", [])
    for buff in buffs:
        target = buff.get("effect", {}).get("target", "")
        multiplier = buff.get("effect", {}).get("multiplier", 1.0)
        if target == "code_xp" and lines_added > 0:
            xp *= multiplier
        if target == "all_gold":
            gold *= multiplier
        if target == "bugfix_xp" and bug_fix:
            xp *= multiplier

    # --- Round ---
    xp = round(xp)
    gold = round(gold)

    # --- Record old level ---
    old_level = get_level(state["character"]["total_xp_earned"])

    # --- Update state ---
    state["character"]["total_xp_earned"] += xp
    state["character"]["gold"] += gold
    state["stats"]["lines_written"] += lines_added
    if bug_fix:
        state["stats"]["bugs_fixed"] += 1

    state["weekly_stats"]["weekly_xp_earned"] += xp
    state["weekly_stats"]["weekly_gold_earned"] += gold
    state["weekly_stats"]["weekly_lines_written"] += lines_added
    if bug_fix:
        state["weekly_stats"]["weekly_bugs_fixed"] += 1

    # --- Decrement buffs ---
    for buff in buffs:
        buff["actions_remaining"] = buff.get("actions_remaining", 0) - 1
    state["character"]["active_buffs"] = [b for b in buffs if b.get("actions_remaining", 0) > 0]

    # --- Level-up check ---
    new_level = get_level(state["character"]["total_xp_earned"])
    state["character"]["level"] = new_level
    if new_level > old_level:
        for lvl in range(old_level + 1, new_level + 1):
            title = get_title(theme, lvl)
            msg_template = THEME_LEVELUP_MESSAGES.get(theme, THEME_LEVELUP_MESSAGES["fantasy"])
            notifications.append(msg_template.format(title=title, level=lvl))

    # --- Quest progress ---
    quest_notifications = update_quests(state)
    notifications.extend(quest_notifications)

    # --- Achievement checks ---
    achievement_notifications = check_achievements(state)
    notifications.extend(achievement_notifications)

    return xp, gold, notifications
```

- [ ] **Step 4: Add quest update and achievement check functions**

Add these before `process_rewards`:

```python
def update_quests(state):
    notifications = []
    quests = state.get("quests", {})
    stats = state.get("stats", {})

    for qid, qdef in QUEST_DEFINITIONS.items():
        quest_state = quests.get(qid, {})
        if quest_state.get("completed", False):
            continue

        if qid == "10":
            categories_done = 0
            coding_done = any(quests.get(str(i), {}).get("completed", False) for i in [1, 2, 3])
            testing_done = any(quests.get(str(i), {}).get("completed", False) for i in [4, 5])
            debugging_done = any(quests.get(str(i), {}).get("completed", False) for i in [6, 7])
            docs_done = any(quests.get(str(i), {}).get("completed", False) for i in [8, 9])
            categories_done = sum([coding_done, testing_done, debugging_done, docs_done])
            quest_state["progress"] = categories_done
        elif qid == "12":
            quest_state["progress"] = state["character"]["gold"]
        elif qdef["field"]:
            quest_state["progress"] = stats.get(qdef["field"], 0)

        if quest_state["progress"] >= qdef["target"] and not quest_state.get("completed", False):
            quest_state["completed"] = True
            quest_state["claimed"] = True
            state["character"]["total_xp_earned"] += qdef["xp"]
            state["character"]["gold"] += qdef["gold"]
            state["weekly_stats"]["weekly_quests_completed"] = state["weekly_stats"].get("weekly_quests_completed", 0) + 1
            notifications.append(f"QUEST COMPLETE: {qdef['name']}! +{qdef['xp']} XP, +{qdef['gold']} Gold")

        quests[qid] = quest_state

    return notifications


def check_achievements(state):
    notifications = []
    achievements = state["character"].get("achievements", {})

    for aid, adef in ACHIEVEMENT_DEFINITIONS.items():
        if achievements.get(aid):
            continue
        try:
            if adef["check"](state):
                achievements[aid] = datetime.now().isoformat()
                notifications.append(f"ACHIEVEMENT UNLOCKED: {adef['name']}!")
        except (KeyError, TypeError):
            continue

    state["character"]["achievements"] = achievements
    return notifications
```

- [ ] **Step 5: Update `main()` to call the reward pipeline and print notifications**

Replace the placeholder section in `main()` (from `if lines_added == 0 and not bug_fix:` onward) with:

```python
    if lines_added == 0 and not bug_fix:
        state.setdefault("tracking", {})["last_tracked_commit"] = commit_sha
        save_state(args.state, state)
        sys.exit(0)

    check_weekly_reset(state)

    xp, gold, notifications = process_rewards(state, lines_added, bug_fix, args.theme)

    # --- Build notification ---
    xp_icon = THEME_XP_ICONS.get(args.theme, THEME_XP_ICONS["fantasy"])
    level = get_level(state["character"]["total_xp_earned"])
    title = get_title(args.theme, level)
    bar, progress, needed = make_xp_bar(state["character"]["total_xp_earned"])
    gold_total = state["character"]["gold"]

    action_desc = f"{lines_added} lines"
    if bug_fix:
        action_desc += " + bug fix"

    print(f"{xp_icon} +{xp} XP, +{gold} Gold for {action_desc}! Level {level} \"{title}\" | XP: {bar} {progress}/{needed} | Gold: {gold_total}")

    for note in notifications:
        print(note)

    state.setdefault("tracking", {})["last_tracked_commit"] = commit_sha
    save_state(args.state, state)
```

- [ ] **Step 6: Commit**

```bash
git add scripts/track-commit.py
git commit -m "feat: add reward pipeline to track-commit.py"
```

---

### Task 3: Update SKILL.md — state schema, enable/disable hooks, session catch-up

**Files:**
- Modify: `SKILL.md`

Update the skill definition to include the `tracking` section in the state schema, hook installation in enable, hook removal in disable, and catch-up on session start.

- [ ] **Step 1: Add `tracking` to the initial state schema in SKILL.md**

In the Initial State Schema JSON block (around line 113), add this new top-level key after the `"quests"` block:

```json
  "tracking": {
    "last_tracked_commit": null,
    "excluded_patterns": ["*.lock", "*.min.js", "*.min.css", "package-lock.json", "yarn.lock", "*.map", "*.svg", "*.png", "*.jpg", "*.gif", "*.ico", "*.woff", "*.woff2", "*.ttf", "*.eot"]
  }
```

- [ ] **Step 2: Update the Enable Flow section to include hook installation**

After the line "Then create `.devquest/` directory and write `state.json` with the initial state schema (below). Show the themed welcome message from `references/themes.md`.", add:

```markdown
After writing state.json, install the git post-commit hook:

1. Check if `.git/hooks/post-commit` exists
2. If it exists, check for `# DevQuest hook` marker comment
3. If no existing hook: create `.git/hooks/post-commit` with the DevQuest hook script
4. If existing hook without DevQuest marker: append the DevQuest section to the end
5. If DevQuest marker already present: skip (idempotent)
6. Make the hook executable (`chmod +x`)

The hook script content:
```bash
# --- BEGIN DevQuest hook — do not remove ---
DEVQUEST_SCRIPT="<resolved-absolute-path-to-skill>/scripts/track-commit.py"
if command -v python3 &>/dev/null; then
    python3 "$DEVQUEST_SCRIPT" --state ".devquest/state.json" --theme "<theme>" 2>/dev/null || true
elif command -v python &>/dev/null; then
    python "$DEVQUEST_SCRIPT" --state ".devquest/state.json" --theme "<theme>" 2>/dev/null || true
fi
# --- END DevQuest hook ---
```

Replace `<resolved-absolute-path-to-skill>` with the actual absolute path to the DevQuest skill directory at install time. Replace `<theme>` with the user's chosen theme.
```

- [ ] **Step 3: Update the Disable section to include hook removal**

Replace the existing `/devquest-disable` line in the Command Routing table action with:

```
Set `enabled: false`, remove DevQuest section from `.git/hooks/post-commit` (between BEGIN/END markers), write state, confirm: "DevQuest disabled. Your progress is saved."
```

- [ ] **Step 4: Add session-start catch-up to the Initialization Check**

After the existing initialization check text, add:

```markdown
### Session Catch-Up

After the weekly reset check, if `tracking.last_tracked_commit` is set and not null, run:

```
git log --author="<git-user>" --oneline <last_tracked_commit>..HEAD
```

If there are unprocessed commits, process each one sequentially using the same reward pipeline as the post-commit hook. This is a fallback for cases where the hook was not installed or was bypassed. Show a summary notification:

```
{xp_icon} Catch-up: +{total_xp} XP, +{total_gold} Gold for {count} commits since last session!
```

If `last_tracked_commit` is null or empty, skip catch-up (do not retroactively process history).
```

- [ ] **Step 5: Commit**

```bash
git add SKILL.md
git commit -m "feat: update SKILL.md with hook install/remove and session catch-up"
```

---

### Task 4: Test the full flow end-to-end

**Files:**
- No new files — manual verification

This task verifies the complete flow: enabling DevQuest installs the hook, a manual commit triggers the hook, rewards are calculated correctly, and the notification appears.

- [ ] **Step 1: Create a test project to verify the hook**

```bash
mkdir -p /tmp/devquest-test && cd /tmp/devquest-test
git init
git config user.name "Test User"
git config user.email "test@test.com"
```

- [ ] **Step 2: Create a `.devquest/state.json` with test state**

Create `/tmp/devquest-test/.devquest/state.json` with the initial state schema from SKILL.md, setting `enabled: true`, `character.name: "Tester"`, and `weekly_stats.week_start` to the current Monday.

- [ ] **Step 3: Install the post-commit hook manually**

Create `/tmp/devquest-test/.git/hooks/post-commit`:

```bash
#!/bin/bash
# --- BEGIN DevQuest hook — do not remove ---
DEVQUEST_SCRIPT="C:/Users/jacob_n3tltpd/.claude/skills/devquest/scripts/track-commit.py"
if command -v python3 &>/dev/null; then
    python3 "$DEVQUEST_SCRIPT" --state ".devquest/state.json" --theme "fantasy" 2>/dev/null || true
elif command -v python &>/dev/null; then
    python "$DEVQUEST_SCRIPT" --state ".devquest/state.json" --theme "fantasy" 2>/dev/null || true
fi
# --- END DevQuest hook ---
```

Make it executable: `chmod +x /tmp/devquest-test/.git/hooks/post-commit`

- [ ] **Step 4: Create a test file and commit**

```bash
cd /tmp/devquest-test
cat > hello.py << 'PYEOF'
def greet(name):
    return f"Hello, {name}!"

def farewell(name):
    return f"Goodbye, {name}!"

if __name__ == "__main__":
    print(greet("World"))
    print(farewell("World"))
PYEOF
git add hello.py
git commit -m "feat: add greeting functions"
```

Expected output after commit:
```
✨ +10 XP, +5 Gold for 10 lines! Level 1 "Apprentice" | XP: [=-------------] 10/100 | Gold: 5
QUEST COMPLETE: First Blood! +20 XP, +10 Gold
ACHIEVEMENT UNLOCKED: First Blood!
```

- [ ] **Step 5: Verify state.json was updated**

Read `/tmp/devquest-test/.devquest/state.json` and confirm:
- `character.total_xp_earned` is 30 (10 base + 20 quest)
- `character.gold` is 15 (5 base + 10 quest)
- `stats.lines_written` is 10
- `tracking.last_tracked_commit` is the commit SHA
- `quests.1.completed` is true

- [ ] **Step 6: Test a bug fix commit**

```bash
cd /tmp/devquest-test
cat >> hello.py << 'PYEOF'

def add(a, b):
    return a + b
PYEOF
git add hello.py
git commit -m "fix: correct arithmetic function"
```

Expected: notification should include "+ bug fix" and award the bug fix bonus (20 XP + 5 gold on top of the 3 lines).

- [ ] **Step 7: Test excluded files**

```bash
cd /tmp/devquest-test
echo '{"dependencies": {}}' > package-lock.json
git add package-lock.json
git commit -m "chore: add lockfile"
```

Expected: hook exits silently (0 lines after exclusion, no notification).

- [ ] **Step 8: Clean up test project**

```bash
rm -rf /tmp/devquest-test
```

- [ ] **Step 9: Commit any fixes found during testing**

```bash
cd "C:/Users/jacob_n3tltpd/.claude/skills/devquest"
git add -A
git commit -m "fix: address issues found during end-to-end testing"
```

(Skip this step if no fixes were needed.)

---

### Task 5: Wrap up — error handling hardening and final commit

**Files:**
- Modify: `scripts/track-commit.py`

Ensure the script never blocks a commit, even on unexpected errors.

- [ ] **Step 1: Wrap `main()` in a top-level try/except**

At the bottom of `track-commit.py`, replace the `if __name__` block:

```python
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[DevQuest] Warning: tracking failed ({e})", file=sys.stderr)
        sys.exit(0)
```

- [ ] **Step 2: Commit**

```bash
git add scripts/track-commit.py
git commit -m "fix: ensure track-commit.py never blocks a commit on errors"
```
