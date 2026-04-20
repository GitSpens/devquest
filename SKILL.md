---
name: devquest
description: "Gamified developer RPG that passively tracks code-writing to award XP, gold, and levels. Use this skill whenever the user mentions devquest, gamification, XP tracking, developer RPG, or wants to enable/disable/view gamified development stats. Also triggers on /devquest-* commands. IMPORTANT: You MUST invoke this skill BEFORE generating, writing, creating, or implementing any code when a .devquest/state.json file exists in the project root — the skill enforces a gold-cost gate that requires user confirmation before code generation."
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
| `/devquest-disable` | — | Set `enabled: false`, run `python <skill-path>/scripts/install-hook.py --repo <project-root> --uninstall`, run `python <skill-path>/scripts/setup-permissions.py --repo <project-root> --uninstall`, write state, confirm: "DevQuest disabled. Your progress is saved." |
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

After writing state.json:

1. **Install the git post-commit hook** by running:
   ```
   python <skill-path>/scripts/install-hook.py --repo <project-root> --theme <theme>
   ```
   The script is idempotent. **You MUST run this script** — do not attempt to write the hook file manually.

2. **Install permissions** for seamless operation by running:
   ```
   python <skill-path>/scripts/setup-permissions.py --repo <project-root>
   ```
   This adds DevQuest entries to `.claude/settings.json` so all operations run without per-action permission prompts. **You MUST run this script** — do not write permissions manually.

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

## Code Generation Gate — MANDATORY

**This gate MUST fire before ANY code generation.** If the user asks you to write, create, generate, implement, or scaffold code and DevQuest is enabled, you MUST run the gate before producing any code. No exceptions.

### How to run the gate

1. **Estimate lines** the request will produce (use your judgment):
   - Small (1–20 lines): ~10
   - Medium (20–50 lines): ~35
   - Large (50–100 lines): ~75
   - Very Large (100+): use your best estimate
2. **Check gold balance** by running:
   ```
   python <skill-path>/scripts/check-gold-gate.py --state .devquest/state.json --lines <estimated_lines>
   ```
   The script outputs JSON: `{"cost": N, "balance": N, "sufficient": true/false, "has_gold_rush": true/false}`
3. **If sufficient** — Show the user:
   > ⚔️ This will cost ~{cost} gold. You have {balance} gold. Proceed? (y/n)
   
   If the user has a Gold Rush buff, mention it but clarify it boosts gold *earned*, not gold *spent*.
   
   Wait for the user to confirm before generating any code.
4. **If insufficient** — Block generation and show:
   > 🚫 Not enough gold! This would cost ~{cost} gold but you only have {balance}. Write more code manually and commit to earn gold!
   
   Do NOT generate any code.
5. **On user confirmation** — Deduct gold:
   ```
   python <skill-path>/scripts/check-gold-gate.py --state .devquest/state.json --lines <estimated_lines> --deduct
   ```
   Then generate the code. Generated code does NOT earn passive XP/gold.

### What counts as code generation

Any request where Claude writes code that will end up in the project's source files:
- "Write a function that..."
- "Create a component for..."
- "Implement the API endpoint..."
- "Add error handling to..."
- "Refactor this to..."
- Using Edit or Write tools to add new code

Does NOT count (no gate needed):
- Explaining code
- Answering questions
- Writing shell commands for the user to run
- Editing DevQuest's own files

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
    "excluded_patterns": ["*.lock", "*.min.js", "*.min.css", "package-lock.json", "yarn.lock", "*.map", "*.svg", "*.png", "*.jpg", "*.gif", "*.ico", "*.woff", "*.woff2", "*.ttf", "*.eot", "*.yml", "*.yaml", "*.json", "*.toml", "*.ini", "*.cfg", "*.conf", "*.xml", "*.plist", "*.properties", "*.env", "*.env.*", "Dockerfile", "docker-compose*", ".dockerignore", ".gitignore", ".gitattributes", ".editorconfig", ".prettierrc", ".eslintrc", ".stylelintrc", "tsconfig.json", "jest.config.*", "Makefile", "Procfile", "*.md", "*.txt", "*.rst", "*.csv", "LICENSE*", "CHANGELOG*"]
  }
}
```

During enable, set `character.name` to the user's preferred name (ask them), and `weekly_stats.week_start` to the current Monday's date (YYYY-MM-DD).
