# Technical Spec — devquest-skill

**Date:** 2026-04-17
**Status:** Approved
**Discovery:** [discovery.md](discovery.md)
**Project:** Claude Code Skills Framework (markdown)

---

## 1. Feature Overview

**Name:** devquest-skill
**Purpose:** A Claude Code skill that passively gamifies development work by tracking coding, testing, debugging, and documentation actions to award XP, gold, and level progression. Users earn gold through organic development work and spend it when asking Claude to generate code — creating a natural tension between doing the work yourself and delegating it. The skill supports four visual themes (Fantasy, Sci-Fi, Retro, Minimalist), dual rendering modes (markdown terminal and HTML browser), and includes a shop for stat upgrades/action-based buffs plus a fixed quest system for bonus challenges. One character per project, state persists across sessions.

**Subsystems:** Skill Core, State Management, Rendering (Markdown + HTML), Themes, Commands, Passive Tracking, Progression System, Shop & Economy

---

## 2. Architecture

**File List:**

| File | Action | Purpose |
|------|--------|---------|
| `SKILL.md` | Create | Main skill entry point — frontmatter, command routing, passive tracking logic, core instructions |
| `references/themes.md` | Create | Theme definitions: level titles, icons, emoji sets, ASCII art, progress bar styles per theme |
| `references/progression.md` | Create | XP curves, level thresholds (1-20), achievement definitions, attribute system |
| `references/economy.md` | Create | Shop items catalog, buff definitions, pricing, code generation cost formula |
| `references/quests.md` | Create | Fixed quest set (12 quests), progress tracking rules, reward tables |
| `scripts/render-html.py` | Create | Python script to generate HTML dashboard from state JSON |
| `assets/dashboard.html` | Create | HTML template with theme CSS variables for browser display |
| `assets/styles.css` | Create | Theme-specific CSS: colors, fonts, progress bar animations |

**State file (per-project, created at runtime):** `.devquest/state.json`

---

## 3. Operation Definitions

### Operation: `/devquest-enable`

**Description:** Initialize DevQuest for the current project. Prompts user for environment, theme, and display mode via interactive multiple-choice options. Creates `.devquest/state.json` with initial character state.

**Parameters:**

| Name | Type | Required | Validation | Description |
|------|------|----------|------------|-------------|
| environment | string (enum) | yes | Must be "cli" or "desktop" | Where the user runs Claude |
| theme | string (enum) | yes | Must be "fantasy", "scifi", "retro", or "minimalist" | Visual theme for all output |
| display_mode | string (enum) | yes | Must be "markdown" or "html" | How to render character sheet, shop, quests |

**Return Format (Success):**
Themed welcome message showing:
- Selected theme name and emoji
- Character title (Level 1 name from theme)
- Initial stats: Level 1, 0/100 XP, 0 Gold
- Confirmation that passive tracking is active

**Error Cases:**

| Condition | Error Message |
|-----------|--------------|
| `.devquest/state.json` already exists and `enabled: true` | "DevQuest is already active in this project. Use `/devquest-settings` to change configuration, or `/devquest-disable` first." |
| `.devquest/` directory not writable | "Cannot create DevQuest state directory. Check file permissions." |

---

### Operation: `/devquest-disable`

**Description:** Pause gamification. State freezes — no tracking, no notifications, no code generation gate. State is preserved for re-enabling.

**Parameters:** None

**Return Format (Success):**
Confirmation message: "DevQuest paused. Your progress is saved — use `/devquest-enable` to resume."

**Error Cases:**

| Condition | Error Message |
|-----------|--------------|
| DevQuest not enabled | "DevQuest is not active in this project. Use `/devquest-enable` to start." |

---

### Operation: `/devquest-character`

**Description:** Display full character sheet with level, XP bar, gold, achievements, weekly stats, attributes, and active buffs.

**Parameters:** None

**Return Format (Success) — Markdown mode:**
```
+==========================================+
|  DEVQUEST -- CHARACTER SHEET             |
+==========================================+
|  Name: <user>    Class: Knight (Lv. 5)   |
|  XP: [========------] 180/300            |
|  Gold: 245                               |
+------------------------------------------+
|  ACHIEVEMENTS                            |
|  * First Blood -- Write your first line  |
|  * Test Pilot -- Run 10 tests            |
+------------------------------------------+
|  WEEKLY STATS (Apr 10-17)                |
|  Lines Written: 342  | Tests Run: 12     |
|  Features: 3         | Bugs Fixed: 5     |
|  XP Earned: 520      | Gold Earned: 185  |
+------------------------------------------+
|  ATTRIBUTES                              |
|  Code Mastery Lv.2 (3% gold discount)    |
|  Debugging Lv.1 (+10% XP from fixes)     |
+------------------------------------------+
|  ACTIVE BUFFS                            |
|  Test XP Boost +50% (7 actions left)     |
+==========================================+
```

**Return Format (Success) — HTML mode:**
Run `scripts/render-html.py` with the state JSON to produce a themed HTML file, then open it in the browser.

**Error Cases:**

| Condition | Error Message |
|-----------|--------------|
| DevQuest not enabled | "DevQuest is not active. Use `/devquest-enable` to start." |

---

### Operation: `/devquest-shop`

**Description:** Display purchasable items and process purchases. Items are stat upgrades (permanent) and action-based buffs (temporary).

**Parameters:**

| Name | Type | Required | Validation | Description |
|------|------|----------|------------|-------------|
| item_id | integer | no | Must match a valid shop item ID | Item to purchase (if omitted, show catalog) |

**Shop Catalog:**

| ID | Item | Type | Price | Effect |
|----|------|------|-------|--------|
| 1 | Code Mastery +1 | stat_boost | 50 gold | Permanent: +1 level to Code Mastery attribute |
| 2 | Debug Insight +1 | stat_boost | 50 gold | Permanent: +1 level to Debugging attribute |
| 3 | Doc Scholar +1 | stat_boost | 40 gold | Permanent: +1 level to Documentation attribute |
| 4 | Test XP Boost | buff | 30 gold | +50% XP from tests for next 10 tracked actions |
| 5 | Code XP Boost | buff | 30 gold | +50% XP from writing code for next 10 tracked actions |
| 6 | Gold Rush | buff | 25 gold | +25% gold from all sources for next 15 tracked actions |
| 7 | Bug Bounty | buff | 20 gold | +100% XP from bug fixes for next 5 tracked actions |
| 8 | Scholar's Focus | buff | 20 gold | +100% XP from documentation for next 5 tracked actions |

**Return Format (Success) — Browse:**
Themed shop display with item list, prices, and current gold balance.

**Return Format (Success) — Purchase:**
"Purchased <item>! Gold: <old> -> <new>. <effect description>"

**Error Cases:**

| Condition | Error Message |
|-----------|--------------|
| DevQuest not enabled | "DevQuest is not active. Use `/devquest-enable` to start." |
| Invalid item_id | "Item not found. Use `/devquest-shop` to see available items." |
| Insufficient gold | "Not enough gold! You have <balance> gold but <item> costs <price>. Earn more by writing code, running tests, or completing quests." |

---

### Operation: `/devquest-quests`

**Description:** Show the fixed quest set with progress, status, and rewards.

**Parameters:** None

**Fixed Quest Set (12 quests):**

| ID | Quest | Category | Goal | XP Reward | Gold Reward |
|----|-------|----------|------|-----------|-------------|
| 1 | First Blood | coding | Write 10 lines of code | 20 | 10 |
| 2 | Centurion | coding | Write 100 lines of code | 100 | 50 |
| 3 | Thousand Lines | coding | Write 1000 lines of code | 500 | 250 |
| 4 | Test Pilot | testing | Run 5 tests | 50 | 25 |
| 5 | Test Commander | testing | Pass 25 tests | 200 | 100 |
| 6 | Bug Squasher | debugging | Fix 3 bugs | 40 | 20 |
| 7 | Exterminator | debugging | Fix 15 bugs | 200 | 100 |
| 8 | Scribe | docs | Document 5 functions | 30 | 15 |
| 9 | Librarian | docs | Document 25 functions | 150 | 75 |
| 10 | Well Rounded | mixed | Complete 1 quest from each category | 100 | 50 |
| 11 | Shopaholic | economy | Purchase 5 items from the shop | 50 | 0 |
| 12 | Code Miser | economy | Accumulate 500 gold (current balance) | 100 | 0 |

**Return Format (Success):**
```
ACTIVE QUESTS
==============================
Centurion -- Write 100 lines of code
   [======------] 63/100 | Reward: 100 XP, 50 Gold

First Blood -- Write 10 lines of code
   [============] COMPLETE! | Claimed: 20 XP, 10 Gold
```

**Error Cases:**

| Condition | Error Message |
|-----------|--------------|
| DevQuest not enabled | "DevQuest is not active. Use `/devquest-enable` to start." |

---

### Operation: `/devquest-theme`

**Description:** Change the visual theme via interactive selection (not manual typing).

**Parameters:**

| Name | Type | Required | Validation | Description |
|------|------|----------|------------|-------------|
| theme | string (enum) | yes | Must be "fantasy", "scifi", "retro", "minimalist" | New theme to apply |

**Return Format (Success):**
Theme-specific welcome in the new style, confirming the change.

**Error Cases:**

| Condition | Error Message |
|-----------|--------------|
| DevQuest not enabled | "DevQuest is not active. Use `/devquest-enable` to start." |
| Same theme selected | "You're already using the <theme> theme." |

---

### Operation: `/devquest-settings`

**Description:** View all settings. When changing a setting, present valid options as interactive choices rather than requiring manual input.

**Parameters:**

| Name | Type | Required | Validation | Description |
|------|------|----------|------------|-------------|
| setting | string | no | Must be "environment", "display", or "theme" | Setting to change (if omitted, show all) |

**Return Format (Success) — View:**
```
DEVQUEST SETTINGS
====================
Environment:  CLI
Display Mode: Markdown
Theme:        Fantasy

Which setting would you like to change? (or "none" to exit)
1. Environment
2. Display Mode
3. Theme
```

**Return Format (Success) — Change:**
Present valid options as numbered choices. Confirm: "Updated <setting> from <old> to <new>."

**Error Cases:**

| Condition | Error Message |
|-----------|--------------|
| DevQuest not enabled | "DevQuest is not active. Use `/devquest-enable` to start." |
| Invalid setting name | "Unknown setting '<name>'. Valid settings: environment, display, theme." |

---

### Operation: **Passive Tracking**

**Description:** After each development action, detect the action type, calculate rewards (applying buff modifiers), decrement active buff counters, check for level-ups and quest progress, and display a themed notification.

**Tracking Rules:**

| Action | Detection Method | Base XP | Base Gold |
|--------|-----------------|---------|-----------|
| Writing code | Lines added in edits (non-generated) | 1 per line | 0.5 per line |
| Tests pass | Test run with passing results | 30 | 10 |
| Tests fail | Test run with failures | 10 | 0 |
| Feature impl | Substantial new functionality added | 50 | 20 |
| Bug fix | Fix applied to resolve an issue | 20 | 5 |
| Documentation | Docstring/comment/doc file added | 10 per function | 2 per function |

**Reward Calculation:**
1. Calculate base XP and gold from tracking rules
2. Apply attribute bonuses (e.g., Code Mastery Lv.2 = +6% gold from coding)
3. Apply active buff multipliers (e.g., Test XP Boost = +50% XP)
4. Round gold to nearest 0.5, XP to nearest integer
5. Add to character state
6. Decrement action counter on all active buffs; remove any that hit 0
7. Check level-up threshold; if crossed, trigger level-up notification
8. Update quest progress counters; if quest completed, trigger quest completion notification

**Notification Format:**
```
+30 XP, +15 Gold for writing 30 lines of code!
   Level 3 "Knight" | XP: [======--] 150/300 | Gold: 245
```

**Level-up Notification:**
```
LEVEL UP! You are now Level 4: "Wizard"!
   New abilities unlocked. Check /devquest-character for details.
```

**Error Cases:** None — passive tracking fails silently to avoid disrupting workflow.

---

### Operation: **Code Generation Gate**

**Description:** Before Claude generates code, estimate the output size, calculate cost, and prompt the user. Block if insufficient gold.

**Parameters:**

| Name | Type | Required | Validation | Description |
|------|------|----------|------------|-------------|
| estimated_lines | integer | yes (auto-calculated) | Must be > 0 | Estimated lines of code to generate |

**Cost Formula:** `cost = ceil(estimated_lines * 0.5)`

**Flow:**
1. Detect that the user's request will result in code generation
2. Estimate output line count based on request complexity
3. Calculate gold cost
4. Present: "Code generation will cost <cost> gold. Your balance: <balance> gold. Proceed? (yes/no)"
5. If yes and sufficient gold: deduct gold, proceed with generation, mark output as "generated" (not tracked for XP)
6. If insufficient gold: "Not enough gold (<balance>/<cost>). Earn more by coding, testing, or completing quests."
7. If user has relevant buff in inventory (e.g., Gold Rush): "Tip: You have a Gold Rush buff in your inventory that could help you earn gold faster!"

**Error Cases:**

| Condition | Error Message |
|-----------|--------------|
| DevQuest not enabled | Skip gate entirely — no interference when disabled |
| Zero gold balance | "You have no gold. Write some code or run tests to earn gold first!" |

---

## 4. API / Library References

No external API verification needed. The skill uses only:
- Python standard library (`json`, `os`, `datetime`) for `render-html.py`
- Claude Code's built-in tools (Read, Write, Bash, Glob) for state management
- No third-party dependencies

---

## 5. Test Plan

### Tests for `/devquest-enable`

**Happy path:** Enable with Fantasy theme
- Input: User says "enable devquest", selects CLI, Fantasy, Markdown
- Expected: `.devquest/state.json` created with level 1, 0 XP, 0 gold, fantasy theme. Themed welcome displayed.

**Error — already enabled:** Try enabling when already active
- Input: Run `/devquest-enable` when state.json exists with `enabled: true`
- Expected: Error message about already being active

### Tests for `/devquest-character`

**Happy path:** Display character after some activity
- Input: State has level 3, 180/300 XP, 245 gold, 2 achievements, 1 active buff
- Expected: Full character sheet rendered in markdown with all sections populated

**Error — not enabled:** Character when disabled
- Input: No `.devquest/state.json` exists
- Expected: Error about DevQuest not being active

### Tests for `/devquest-shop`

**Happy path:** Purchase a buff
- Input: User has 50 gold, buys "Test XP Boost" (30 gold)
- Expected: Gold deducted to 20, buff added to inventory with 10 actions remaining

**Error — insufficient gold:** Try buying with not enough gold
- Input: User has 10 gold, tries to buy 30 gold item
- Expected: Insufficient gold error with current balance

### Tests for Passive Tracking

**Happy path:** Code writing tracked
- Input: User writes 30 lines of code, has Code XP Boost active (7 actions left)
- Expected: 45 XP (30 base + 50% buff), 15 gold awarded. Buff decremented to 6 actions. Notification displayed.

**Happy path — level up:** XP crosses threshold
- Input: User at 90/100 XP, writes 20 lines (+20 XP)
- Expected: Level up triggered, new level title shown, XP carries over to next level

### Tests for Code Generation Gate

**Happy path:** User can afford generation
- Input: User asks to generate 40 lines, has 50 gold
- Expected: Prompted with cost 20 gold, balance 50. On yes: gold drops to 30, code generated.

**Error — can't afford:** Insufficient gold with buff hint
- Input: User asks to generate 100 lines (cost 50), has 20 gold, has Gold Rush buff in inventory
- Expected: Denied with balance info + hint about Gold Rush buff

### Tests for `/devquest-settings`

**Happy path:** View settings
- Input: DevQuest enabled with CLI, Markdown, Fantasy
- Expected: Settings table showing all three values with change options

**Happy path:** Change display mode via option selection
- Input: User selects "Display Mode" then picks "HTML"
- Expected: Confirmation that display changed from Markdown to HTML

---

## 6. Deliverables Checklist

- [ ] `SKILL.md` — Skill core with frontmatter, command routing, passive tracking logic
- [ ] `references/themes.md` — Theme definitions: 4 themes with level titles, icons, emoji, ASCII art
- [ ] `references/progression.md` — 20 levels with XP thresholds, achievement definitions, attribute system
- [ ] `references/economy.md` — 8 shop items, buff mechanics, code generation cost formula
- [ ] `references/quests.md` — 12 fixed quests with progress tracking rules
- [ ] `scripts/render-html.py` — HTML dashboard generator
- [ ] `assets/dashboard.html` — HTML template with theme support
- [ ] `assets/styles.css` — Theme CSS variables and styling
- [ ] `evals/evals.json` — Test cases for skill evaluation

---

## 7. State File Schema

The `.devquest/state.json` file (created per-project at runtime):

```json
{
  "enabled": true,
  "settings": {
    "environment": "cli",
    "display_mode": "markdown",
    "theme": "fantasy"
  },
  "character": {
    "level": 1,
    "xp": 0,
    "gold": 0,
    "total_xp_earned": 0,
    "total_gold_earned": 0,
    "attributes": {
      "code_mastery": 0,
      "debugging": 0,
      "documentation": 0
    },
    "achievements": [],
    "inventory": []
  },
  "buffs": [],
  "stats": {
    "lines_written": 0,
    "tests_run": 0,
    "tests_passed": 0,
    "features_implemented": 0,
    "bugs_fixed": 0,
    "functions_documented": 0,
    "code_generated_lines": 0,
    "gold_spent": 0
  },
  "weekly_stats": {
    "week_start": "2026-04-14",
    "xp_earned": 0,
    "gold_earned": 0,
    "lines_written": 0,
    "tests_run": 0,
    "features_implemented": 0,
    "bugs_fixed": 0
  },
  "quests": {
    "1": { "progress": 0, "completed": false, "claimed": false },
    "2": { "progress": 0, "completed": false, "claimed": false }
  }
}
```

**Buff entry schema:**
```json
{
  "id": "test_xp_boost",
  "name": "Test XP Boost",
  "effect": { "target": "test_xp", "multiplier": 1.5 },
  "actions_remaining": 10
}
```

**Progression table (XP thresholds):**

| Level | XP Required | Fantasy | Sci-Fi | Retro | Minimalist |
|-------|-------------|---------|--------|-------|------------|
| 1 | 0 | Apprentice | Cadet | Noob | L1 |
| 2 | 100 | Squire | Ensign | Rookie | L2 |
| 3 | 250 | Knight | Engineer | Pro | L3 |
| 4 | 500 | Paladin | Lieutenant | Veteran | L4 |
| 5 | 800 | Wizard | Commander | Elite | L5 |
| 6 | 1200 | Sorcerer | Captain | Master | L6 |
| 7 | 1800 | Warlock | Major | Legend | L7 |
| 8 | 2500 | Archmage | Colonel | Mythic | L8 |
| 9 | 3500 | Champion | Admiral | Godlike | L9 |
| 10 | 5000 | Legend | Fleet Admiral | Transcendent | L10 |

Levels 11-20 follow same pattern with escalating thresholds and increasingly epic titles.

**Attribute bonuses (per level):**

| Attribute | Bonus Per Level |
|-----------|----------------|
| Code Mastery | +3% gold from writing code |
| Debugging | +10% XP from bug fixes |
| Documentation | +5% XP and gold from documentation |
