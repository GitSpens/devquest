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
| `/devquest-disable` | — | Set `enabled: false`, run `python <skill-path>/scripts/setup-project.py --repo <project-root> --uninstall`, write state, confirm: "DevQuest disabled. Your progress is saved." |
| `/devquest-character` | `references/themes.md`, `references/progression.md` | Render character sheet in configured display mode |
| `/devquest-shop` | `references/economy.md` | Show catalog with prices and gold balance, or process a numbered purchase |
| `/devquest-quests` | `references/quests.md` | Show quest list grouped by active/completed with progress bars |
| `/devquest-theme` | `references/themes.md` | Present 4 numbered theme options, update `settings.theme`, confirm |
| `/devquest-settings` | — | Show current settings table, offer numbered options to change environment, theme, or display mode |

## Enable Flow

**Step 1 — IMMEDIATELY run the enable script.** This is the FIRST thing you do, before any conversation:

```
python <skill-path>/scripts/devquest-enable.py --repo <project-root>
```

This creates state.json with sensible defaults (fantasy theme, CLI, markdown) AND installs the git hook AND configures permissions. Everything is set up after this one command.

**Step 2 — Show the themed welcome message** from `references/themes.md` and offer customization:

> Want to customize your setup? You can change:
> 1. Theme (currently Fantasy) — run /devquest-theme
> 2. Display mode (currently Markdown) — run /devquest-settings
>
> Or just start coding to earn XP!
>
> 💡 **Tip:** Start a new Claude Code session for the smoothest experience — this lets the newly installed permissions take effect so DevQuest commands run seamlessly without approval prompts.

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

The state schema is defined in `scripts/devquest-enable.py`. The enable script creates state.json with sensible defaults, sets the player name from git config, and initializes weekly stats. Do not create state.json manually — always use the enable script.
