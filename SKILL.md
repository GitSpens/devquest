---
name: devquest
description: "Gamified developer RPG that passively tracks code-writing to award XP, gold, and levels. Use this skill whenever the user mentions devquest, gamification, XP tracking, developer RPG, or wants to enable/disable/view gamified development stats. Also triggers on /devquest-* commands. Triggers on code-writing actions when DevQuest is enabled for passive tracking notifications."
---

# DevQuest — Core Skill Router

DevQuest is a gamified RPG layer for development work. It passively tracks code-writing to award XP, gold, levels, and achievements. State persists in `.devquest/state.json` in the project root. Reference data lives in `references/` — read the specific file indicated for each command rather than duplicating data here.

## Initialization Check

On every invocation, attempt to read `.devquest/state.json` from the project root.

- **File missing or `enabled: false`**: only `/devquest-enable` is functional. All other commands respond: "DevQuest is not enabled. Run /devquest-enable to start." Passive tracking does nothing (no output, no error).
- **File exists and `enabled: true`**: check weekly reset (see `references/progression.md` Section 4) before processing any command or passive action.

### Session Catch-Up

After the weekly reset check, if `tracking.last_tracked_commit` is set and not null, run:

```
git log --author="<git-user>" --oneline <last_tracked_commit>..HEAD
```

If there are unprocessed commits, process each one using the reward pipeline (count lines via `git diff --numstat`). Show a summary:

```
{xp_icon} Catch-up: +{total_xp} XP, +{total_gold} Gold for {count} commits since last session!
```

If `last_tracked_commit` is null or empty, skip catch-up.

## Command Routing

| Command | Read | Action |
|---------|------|--------|
| `/devquest-enable` | `references/themes.md` | Run Enable Flow (below) |
| `/devquest-disable` | — | Set `enabled: false`, remove DevQuest section from `.git/hooks/post-commit` (between BEGIN/END markers), write state, confirm: "DevQuest disabled. Your progress is saved." |
| `/devquest-character` | `references/themes.md`, `references/progression.md` | Render character sheet in configured display mode |
| `/devquest-shop` | `references/economy.md` | Show catalog with prices and gold balance, or process a numbered purchase |
| `/devquest-quests` | `references/quests.md` | Show quest list grouped by active/completed with progress bars |
| `/devquest-theme` | `references/themes.md` | Present 4 numbered theme options, update `settings.theme`, confirm |
| `/devquest-settings` | — | Show current settings table, offer numbered options to change environment, theme, or display mode |

## Enable Flow

Prompt the user with numbered options for each choice:

1. **Environment**: 1. CLI  2. Desktop
2. **Theme**: 1. Fantasy  2. Sci-Fi  3. Retro  4. Minimalist
3. **Display mode**: 1. Markdown  2. HTML

Then create `.devquest/` directory and write `state.json` with the initial state schema (below). Show the themed welcome message from `references/themes.md`.

After writing state.json, install the git post-commit hook:

1. Check if `.git/hooks/post-commit` exists
2. If it exists, check for the `# --- BEGIN DevQuest hook` marker
3. If no existing hook: create `.git/hooks/post-commit` with a shebang and the DevQuest hook block
4. If existing hook without DevQuest marker: append the DevQuest block to the end
5. If DevQuest marker already present: skip (idempotent)
6. Make the hook executable (`chmod +x`)

The hook block content (resolve the path and theme at install time):

```bash
# --- BEGIN DevQuest hook — do not remove ---
DEVQUEST_SCRIPT="<absolute-path-to-skill>/scripts/track-commit.py"
if command -v python3 &>/dev/null; then
    python3 "$DEVQUEST_SCRIPT" --state ".devquest/state.json" --theme "<theme>" 2>/dev/null || true
elif command -v python &>/dev/null; then
    python "$DEVQUEST_SCRIPT" --state ".devquest/state.json" --theme "<theme>" 2>/dev/null || true
fi
# --- END DevQuest hook ---
```

## Character Sheet

**Markdown mode**: Render using this template (read `references/themes.md` for the level title and emoji, `references/progression.md` for XP bar formula):

```
+==============================+
|  {emoji} {NAME} — {Title}   |
|  Level {n}                   |
|  XP: [========------] p/n   |
|  Gold: {g}                   |
|  Buffs: {active_buff_list}   |
+==============================+
```

**HTML mode**: Run `python scripts/render-html.py --state .devquest/state.json --theme {theme} --output .devquest/dashboard.html` — the script renders the dashboard and automatically opens it in the user's default browser. The script prints a `file://` URI — always include this URI in your response so the user can reopen it later.

## Passive Tracking

Triggers after: writing code. Silently skip if DevQuest is disabled.

### Base Rewards

| Action | XP | Gold | Unit |
|--------|-----|------|------|
| Write code | 1 | 0.5 | per line |

### Processing Pipeline

1. Calculate base XP and gold from the table above
2. Apply attribute bonuses — read `references/progression.md` Section 3 for formula
3. Apply active buff multipliers — read `references/economy.md` Buff Processing Rules
4. Round final values to nearest integer
5. Update state: add XP, gold; increment `lines_written` stat counter (lifetime + weekly)
6. Decrement `actions_remaining` on all active buffs; remove expired
7. Check level-up — read `references/progression.md` Section 1 for thresholds
8. Check quest progress — read `references/quests.md` for tracking rules
9. Check achievements — read `references/progression.md` Section 2 for triggers
10. Write state to `.devquest/state.json`
11. Show notification

### Notification Format

```
{xp_icon} +{xp} XP, +{gold} Gold for {action}! Level {n} "{title}" | XP: [{bar}] {p}/{n} | Gold: {g}
```

On level-up, append the themed level-up message from `references/themes.md`. On achievement unlock, append `ACHIEVEMENT UNLOCKED: {name}!`. On quest complete, append `QUEST COMPLETE: {name}! +{xp} XP, +{gold} Gold`.

## Code Generation Gate

Before generating code for the user:

1. Estimate lines; compute cost: `ceil(estimated_lines * 1.0)` gold
2. Show: "This will cost ~{cost} gold. You have {balance} gold. Proceed? (y/n)"
3. If insufficient gold, block and suggest earning more. Mention Gold Rush buff if in inventory (note: it boosts gold earned, not cost)
4. On confirm: deduct gold, generate code. Generated code does NOT earn passive XP/gold

## Settings Handler

Show current settings as a table, then numbered options:

1. Environment (CLI / Desktop)
2. Theme (Fantasy / Sci-Fi / Retro / Minimalist)
3. Display mode (Markdown / HTML)

Update the chosen setting in state and confirm.

## Initial State Schema

```json
{
  "enabled": true,
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
    "1":  {"progress": 0, "completed": false, "claimed": false},
    "2":  {"progress": 0, "completed": false, "claimed": false},
    "3":  {"progress": 0, "completed": false, "claimed": false},
    "4":  {"progress": 0, "completed": false, "claimed": false},
    "5":  {"progress": 0, "completed": false, "claimed": false}
  },
  "tracking": {
    "last_tracked_commit": null,
    "excluded_patterns": ["*.lock", "*.min.js", "*.min.css", "package-lock.json", "yarn.lock", "*.map", "*.svg", "*.png", "*.jpg", "*.gif", "*.ico", "*.woff", "*.woff2", "*.ttf", "*.eot"]
  }
}
```

During enable, set `character.name` to the user's preferred name (ask them), and `weekly_stats.week_start` to the current Monday's date (YYYY-MM-DD).
