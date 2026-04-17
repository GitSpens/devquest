# DevQuest Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete Claude Code skill that gamifies development work with XP, gold, levels, themes, a shop, and quests.

**Architecture:** The skill is a set of markdown instruction files that Claude reads and follows. SKILL.md is the entry point with command routing and core logic. Reference files hold data tables (themes, progression, economy, quests). A Python script generates HTML dashboards. State persists in `.devquest/state.json` per project.

**Tech Stack:** Markdown (SKILL.md + references), Python 3 (HTML renderer), HTML/CSS (dashboard), JSON (state)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `SKILL.md` | Frontmatter, command routing, passive tracking logic, code generation gate, state read/write instructions |
| `references/themes.md` | Theme definitions: 4 themes with level titles (1-20), emoji sets, progress bar styles, welcome messages |
| `references/progression.md` | XP thresholds for 20 levels, achievement definitions and triggers, attribute bonus formulas |
| `references/economy.md` | 8 shop items with prices/effects, buff mechanics, code generation cost formula |
| `references/quests.md` | 12 fixed quests with categories, goals, tracking fields, reward amounts |
| `scripts/render-html.py` | Reads `.devquest/state.json`, loads theme from args, outputs themed HTML dashboard file |
| `assets/dashboard.html` | HTML template with placeholders for state data, theme CSS variable slots |
| `assets/styles.css` | CSS for 4 themes via CSS custom properties, progress bar animations, responsive layout |

---

### Task 1: Reference Files — Themes

**Files:**
- Create: `references/themes.md`

This file is a data reference that SKILL.md reads when it needs theme-specific content. Contains all four themes with level title tables (1-20), emoji sets, and visual styling instructions.

- [ ] **Step 1: Create `references/themes.md`**

Write the full themes reference file containing:
- **Fantasy** theme: emoji set (⚔️🛡️👑📜💎🧪), level titles (Apprentice through Ascended), welcome/level-up messages
- **Sci-Fi** theme: emoji set (🚀🛰️🤖⚛️🌟⚡), level titles (Cadet through Ascended), welcome/level-up messages
- **Retro** theme: emoji set (🕹️👾🎮👽🔥🍄), level titles (Noob through Game Over), welcome/level-up messages
- **Minimalist** theme: no emoji, level titles (L1 through L20), terse messages

Each theme section includes:
- Emoji set, currency icon, XP icon
- Header style description
- Progress bar style: `[========------]` (= filled, - empty)
- Full 20-level title table with XP thresholds
- Welcome message template
- Level-up message template with `{title}` and `{level}` placeholders

The XP thresholds are identical across all themes:

| Level | XP | Level | XP |
|-------|----|-------|----|
| 1 | 0 | 11 | 7000 |
| 2 | 100 | 12 | 9500 |
| 3 | 250 | 13 | 12500 |
| 4 | 500 | 14 | 16000 |
| 5 | 800 | 15 | 20000 |
| 6 | 1200 | 16 | 25000 |
| 7 | 1800 | 17 | 31000 |
| 8 | 2500 | 18 | 38000 |
| 9 | 3500 | 19 | 46000 |
| 10 | 5000 | 20 | 55000 |

Full level titles per theme:

**Fantasy:** Apprentice, Squire, Knight, Paladin, Wizard, Sorcerer, Warlock, Archmage, Champion, Legend, Mythic Knight, Dragon Slayer, Sage, Archon, Demigod, Titan, Elder God, Primordial, Eternal, Ascended

**Sci-Fi:** Cadet, Ensign, Engineer, Lieutenant, Commander, Captain, Major, Colonel, Admiral, Fleet Admiral, Commodore Prime, Star Marshal, Sector Commander, Galaxy Admiral, Fleet Sovereign, Void Walker, Quantum Lord, Singularity, Transcendent, Ascended

**Retro:** Noob, Rookie, Pro, Veteran, Elite, Master, Legend, Mythic, Godlike, Transcendent, Pixel Lord, Bit Crusher, Glitch King, ROM Hacker, Cartridge God, Console Titan, Arcade Phantom, 8-Bit Deity, Final Boss, Game Over

**Minimalist:** L1 through L20

- [ ] **Step 2: Commit**

```bash
git add references/themes.md
git commit -m "feat: add theme definitions for all four themes"
```

---

### Task 2: Reference Files — Progression & Achievements

**Files:**
- Create: `references/progression.md`

- [ ] **Step 1: Create `references/progression.md`**

Write the progression reference file containing:

**XP Thresholds section:**
- XP is cumulative (does NOT reset on level-up)
- Table of all 20 levels with total XP required (same thresholds as in themes)
- Level calculation formula: highest level whose threshold <= `total_xp_earned`
- XP bar display formula: `progress = total_xp_earned - current_level_threshold`, `needed = next_level_threshold - current_level_threshold`
- Level-up detection: after adding XP, recalculate level, trigger notification if changed

**Achievements section (12 achievements):**

| ID | Name | Trigger |
|----|------|---------|
| first_line | First Blood | lines_written >= 1 |
| century | Century | lines_written >= 100 |
| test_pilot | Test Pilot | tests_run >= 10 |
| perfect_run | Perfect Run | 5 consecutive passing test runs |
| bug_squasher | Bug Squasher | bugs_fixed >= 1 |
| doc_writer | Documentation Hero | functions_documented >= 10 |
| big_spender | Big Spender | gold_spent >= 100 |
| hoarder | Gold Hoarder | current gold >= 500 |
| level_5 | Rising Star | reach level 5 |
| level_10 | Veteran | reach level 10 |
| level_20 | Ascended | reach level 20 |
| all_quests | Quest Master | complete all 12 quests |

Achievement notification format: `ACHIEVEMENT UNLOCKED: {name}! — {trigger description}`

**Attributes section:**

| Attribute | Bonus Per Level | Applies To |
|-----------|----------------|------------|
| code_mastery | +3% gold | writing code |
| debugging | +10% XP | bug fixes |
| documentation | +5% XP and gold | documentation |

Bonus formula: `modified = base * (1 + attribute_level * bonus_pct / 100)`

**Weekly Stats section:**
- Reset every Monday
- Check: compare `weekly_stats.week_start` to current Monday, reset if different

- [ ] **Step 2: Commit**

```bash
git add references/progression.md
git commit -m "feat: add progression system with achievements and attributes"
```

---

### Task 3: Reference Files — Economy

**Files:**
- Create: `references/economy.md`

- [ ] **Step 1: Create `references/economy.md`**

Write the economy reference file containing:

**Shop Catalog (8 items):**

| ID | Item | Type | Price | Effect |
|----|------|------|-------|--------|
| 1 | Code Mastery +1 | stat_boost | 50 | +1 to code_mastery attribute (permanent) |
| 2 | Debug Insight +1 | stat_boost | 50 | +1 to debugging attribute (permanent) |
| 3 | Doc Scholar +1 | stat_boost | 40 | +1 to documentation attribute (permanent) |
| 4 | Test XP Boost | buff | 30 | +50% XP from tests, 10 actions |
| 5 | Code XP Boost | buff | 30 | +50% XP from writing code, 10 actions |
| 6 | Gold Rush | buff | 25 | +25% gold from all sources, 15 actions |
| 7 | Bug Bounty | buff | 20 | +100% XP from bug fixes, 5 actions |
| 8 | Scholar's Focus | buff | 20 | +100% XP from docs, 5 actions |

**Purchase processing:**
1. Check gold >= price. If not, show error with balance and price.
2. Deduct gold from `character.gold`.
3. Add to `stats.gold_spent`.
4. For stat_boost: increment the corresponding attribute in `character.attributes`.
5. For buff: add buff entry to `buffs` array with `actions_remaining` set.
6. Check quest progress for Shopaholic quest (increment purchase count).
7. Check achievement for Big Spender (gold_spent >= 100).

**Buff entry schema:**
```json
{
  "id": "test_xp_boost",
  "name": "Test XP Boost",
  "effect": { "target": "test_xp", "multiplier": 1.5 },
  "actions_remaining": 10
}
```

**Buff target mapping:**
- `test_xp`: applies multiplier to XP earned from running tests
- `code_xp`: applies multiplier to XP earned from writing code
- `all_gold`: applies multiplier to gold earned from any source
- `bugfix_xp`: applies multiplier to XP earned from bug fixes
- `docs_xp`: applies multiplier to XP earned from documentation

**Buff processing (on every tracked action):**
1. For each active buff, check if its target matches the current action type
2. If match, apply multiplier to the relevant reward (XP or gold)
3. Decrement `actions_remaining` on ALL active buffs (not just matching ones)
4. Remove any buff where `actions_remaining` reaches 0
5. Buffs stack: if multiple buffs apply to the same target, multiply sequentially

**Code Generation Cost:**
- Formula: `cost = ceil(estimated_lines * 0.5)`
- Estimation heuristic: small request (1-20 lines) = 10, medium (20-50) = 35, large (50-100) = 75, very large (100+) = estimated lines
- Before generating: show cost and balance, ask user to confirm
- If insufficient: deny and mention relevant buffs in inventory (Gold Rush)
- Generated code is NOT tracked for XP/gold earnings

- [ ] **Step 2: Commit**

```bash
git add references/economy.md
git commit -m "feat: add economy system with shop, buffs, and cost formula"
```

---

### Task 4: Reference Files — Quests

**Files:**
- Create: `references/quests.md`

- [ ] **Step 1: Create `references/quests.md`**

Write the quests reference file containing:

**Quest Catalog (12 fixed quests):**

| ID | Name | Category | Goal | Tracking Field | Target | XP | Gold |
|----|------|----------|------|---------------|--------|-----|------|
| 1 | First Blood | coding | Write 10 lines | stats.lines_written | 10 | 20 | 10 |
| 2 | Centurion | coding | Write 100 lines | stats.lines_written | 100 | 100 | 50 |
| 3 | Thousand Lines | coding | Write 1000 lines | stats.lines_written | 1000 | 500 | 250 |
| 4 | Test Pilot | testing | Run 5 tests | stats.tests_run | 5 | 50 | 25 |
| 5 | Test Commander | testing | Pass 25 tests | stats.tests_passed | 25 | 200 | 100 |
| 6 | Bug Squasher | debugging | Fix 3 bugs | stats.bugs_fixed | 3 | 40 | 20 |
| 7 | Exterminator | debugging | Fix 15 bugs | stats.bugs_fixed | 15 | 200 | 100 |
| 8 | Scribe | docs | Document 5 functions | stats.functions_documented | 5 | 30 | 15 |
| 9 | Librarian | docs | Document 25 functions | stats.functions_documented | 25 | 150 | 75 |
| 10 | Well Rounded | mixed | Complete 1 quest per category | (special) | 4 categories | 100 | 50 |
| 11 | Shopaholic | economy | Purchase 5 items | stats.items_purchased | 5 | 50 | 0 |
| 12 | Code Miser | economy | Have 500 gold balance | character.gold | 500 | 100 | 0 |

**Quest state schema (in `.devquest/state.json`):**
```json
"quests": {
  "1": { "progress": 0, "completed": false, "claimed": false },
  "2": { "progress": 0, "completed": false, "claimed": false }
}
```

**Quest progress update (on every tracked action):**
1. For each uncompleted quest, check if the relevant tracking field has reached the target
2. For quest 10 (Well Rounded): check if at least one quest from each of the 4 main categories (coding, testing, debugging, docs) is completed
3. For quest 12 (Code Miser): check current `character.gold` balance (not cumulative)
4. If progress >= target and not completed: set `completed: true`, `claimed: true`, award XP and gold
5. Auto-claim on completion — no manual claim step needed

**Quest display:**
- Show progress bar: `[======------] 63/100`
- Completed quests show: `[============] COMPLETE! | Claimed: {xp} XP, {gold} Gold`
- Group by: incomplete first, then completed

- [ ] **Step 2: Commit**

```bash
git add references/quests.md
git commit -m "feat: add quest definitions and tracking rules"
```

---

### Task 5: SKILL.md — Core Skill File

**Files:**
- Create: `SKILL.md`

This is the main entry point. It contains the frontmatter (name, description), command routing, passive tracking logic, code generation gate, and state management instructions. It tells Claude how to behave when the skill is active.

- [ ] **Step 1: Create `SKILL.md`**

Write SKILL.md with these sections:

**Frontmatter:**
```yaml
---
name: devquest
description: "Gamified developer RPG that passively tracks coding, testing, debugging, and documentation to award XP, gold, and levels. Use this skill whenever the user mentions devquest, gamification, XP tracking, developer RPG, or wants to enable/disable/view gamified development stats. Also triggers on /devquest-* commands."
---
```

**Section: Overview**
- Brief description of what DevQuest does
- State file location: `.devquest/state.json` in the user's project directory
- Reference files: list each with when to read it

**Section: Initialization Check**
On EVERY invocation (including passive tracking), first:
1. Read `.devquest/state.json` using the Read tool
2. If file doesn't exist or `enabled` is false: only respond to `/devquest-enable`. For all other commands, show "DevQuest is not active" error. For passive tracking, do nothing.
3. If enabled: load current theme from `settings.theme`, read `references/themes.md` for theme data

**Section: Command Routing**
When the user invokes a `/devquest-*` command, route to the appropriate handler:

| Command | Handler |
|---------|---------|
| `/devquest-enable` | Run Enable flow |
| `/devquest-disable` | Set `enabled: false`, write state, confirm |
| `/devquest-character` | Read state, read themes, render character sheet |
| `/devquest-shop` | Read state, read `references/economy.md`, show shop or process purchase |
| `/devquest-quests` | Read state, read `references/quests.md`, show quest progress |
| `/devquest-theme` | Present theme options, update `settings.theme`, write state |
| `/devquest-settings` | Show settings table, handle changes via numbered options |

**Section: Enable Flow**
1. Check if `.devquest/state.json` already exists with `enabled: true` — if so, error
2. Ask user to choose environment: "1. CLI  2. Desktop"
3. Ask user to choose theme: "1. Fantasy  2. Sci-Fi  3. Retro  4. Minimalist"
4. Ask user to choose display mode: "1. Markdown  2. HTML"
5. Create `.devquest/` directory
6. Write initial `state.json` with all defaults (level 1, 0 XP, 0 gold, all quests initialized)
7. Read theme's welcome message from `references/themes.md`
8. Display themed welcome

**Section: Character Sheet Rendering**

*Markdown mode:*
Read state and theme. Build character sheet using this template:
```
+==========================================+
|  {theme_accent} DEVQUEST -- CHARACTER SHEET
+==========================================+
|  Class: {title} (Lv. {level})
|  XP: [{progress_bar}] {progress}/{needed}
|  {currency_icon} Gold: {gold}
+------------------------------------------+
|  ACHIEVEMENTS
|  {for each achievement: * {name} -- {description}}
+------------------------------------------+
|  WEEKLY STATS ({week_range})
|  Lines Written: {n}  | Tests Run: {n}
|  Features: {n}       | Bugs Fixed: {n}
|  XP Earned: {n}      | Gold Earned: {n}
+------------------------------------------+
|  ATTRIBUTES
|  {for each attribute with level > 0: {name} Lv.{level} ({bonus_description})}
+------------------------------------------+
|  ACTIVE BUFFS
|  {for each buff: {name} +{pct}% ({actions_remaining} actions left)}
+==========================================+
```

*HTML mode:*
Run: `python scripts/render-html.py --state .devquest/state.json --theme {theme} --output .devquest/dashboard.html`
Then open the file in the browser.

**Section: Shop Handler**
1. Read `references/economy.md` for item catalog
2. If no item selected: display themed shop with items, prices, current gold
3. If item selected: validate item ID, check gold >= price, process purchase per economy rules
4. Write updated state
5. Display confirmation

**Section: Passive Tracking**

After EVERY development action (writing code, running tests, fixing bugs, documenting), if DevQuest is enabled:

1. Read `.devquest/state.json`
2. Determine action type and magnitude:
   - Wrote N lines of code → type: `code`, magnitude: N
   - Ran tests (M passed, F failed) → type: `test_pass` (M times) + `test_fail` (F times)
   - Fixed a bug → type: `bugfix`, magnitude: 1
   - Documented functions → type: `docs`, magnitude: count
   - Implemented a feature → type: `feature`, magnitude: 1
3. Read `references/progression.md` for bonus formulas
4. Calculate base XP and gold per tracking rules
5. Apply attribute bonuses
6. Apply buff multipliers (read from `buffs` array)
7. Add XP to `total_xp_earned` and `character.xp`, gold to `character.gold`
8. Update `stats` counters and `weekly_stats` counters
9. Decrement all buff action counters; remove expired buffs
10. Check for weekly stats reset
11. Check level-up (read progression thresholds)
12. Check quest progress (read `references/quests.md`)
13. Check achievements (read `references/progression.md`)
14. Write updated state
15. Display themed notification with XP/gold earned and current status bar
16. If level-up: display level-up notification
17. If quest completed: display quest completion notification
18. If achievement unlocked: display achievement notification

**Section: Code Generation Gate**

Before generating code for the user:
1. If DevQuest is not enabled, skip entirely
2. Estimate the number of lines that will be generated
3. Calculate cost: `ceil(estimated_lines * 0.5)`
4. Read current gold balance from state
5. Display: "Code generation will cost {cost} gold. Your balance: {balance} gold. Proceed?"
6. If user says yes and gold >= cost: deduct gold, write state, proceed with generation
7. If gold < cost: "Not enough gold ({balance}/{cost})."
   - Check if user has Gold Rush buff in inventory, mention it if so
8. Mark generated code so it is NOT tracked for passive XP/gold

**Section: Settings Handler**
1. Display current settings as table
2. Ask which to change (numbered options)
3. Present valid values as numbered options
4. Update state, write, confirm

- [ ] **Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat: add core skill file with command routing and tracking logic"
```

---

### Task 6: HTML Rendering — Python Script

**Files:**
- Create: `scripts/render-html.py`

- [ ] **Step 1: Create `scripts/render-html.py`**

Write a Python script that:
1. Accepts command-line args: `--state <path>`, `--theme <name>`, `--output <path>`
2. Reads and parses the state JSON file
3. Reads `assets/dashboard.html` template
4. Calculates derived values: level title (from theme), XP progress/needed, progress bar percentage
5. Replaces template placeholders with actual values
6. Sets CSS theme class on the body element based on theme name
7. Writes the output HTML file

Use only Python standard library: `json`, `os`, `sys`, `argparse`, `math`.

Script structure:
```python
import argparse
import json
import math
import os
import sys

# XP thresholds (same as in references/progression.md)
XP_THRESHOLDS = [0, 100, 250, 500, 800, 1200, 1800, 2500, 3500, 5000,
                 7000, 9500, 12500, 16000, 20000, 25000, 31000, 38000, 46000, 55000]

# Level titles per theme
TITLES = {
    "fantasy": ["Apprentice", "Squire", "Knight", ...all 20...],
    "scifi": ["Cadet", "Ensign", "Engineer", ...all 20...],
    "retro": ["Noob", "Rookie", "Pro", ...all 20...],
    "minimalist": ["L1", "L2", "L3", ...all 20...]
}

def get_level(total_xp):
    # find highest level whose threshold <= total_xp

def get_xp_progress(total_xp, level):
    # return (progress, needed) for XP bar

def render_dashboard(state, theme):
    # read template, replace placeholders, return HTML string

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--theme", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    # read state, render, write output

if __name__ == "__main__":
    main()
```

Write the full implementation with all 20 level titles, placeholder replacement, and theme class injection.

- [ ] **Step 2: Commit**

```bash
git add scripts/render-html.py
git commit -m "feat: add HTML dashboard renderer script"
```

---

### Task 7: HTML Rendering — Template and CSS

**Files:**
- Create: `assets/dashboard.html`
- Create: `assets/styles.css`

- [ ] **Step 1: Create `assets/dashboard.html`**

Write an HTML template that `render-html.py` will populate. Use these placeholders (the Python script replaces them):
- `{{THEME_CLASS}}` — CSS class on body: `theme-fantasy`, `theme-scifi`, `theme-retro`, `theme-minimalist`
- `{{TITLE}}` — current level title
- `{{LEVEL}}` — current level number
- `{{XP_PROGRESS}}` — current XP progress within level
- `{{XP_NEEDED}}` — XP needed for next level
- `{{XP_PERCENT}}` — percentage for progress bar width
- `{{GOLD}}` — current gold
- `{{ACHIEVEMENTS_HTML}}` — rendered achievement list items
- `{{WEEKLY_STATS_HTML}}` — rendered weekly stats
- `{{ATTRIBUTES_HTML}}` — rendered attributes
- `{{BUFFS_HTML}}` — rendered active buffs
- `{{QUESTS_HTML}}` — rendered quest progress

Template structure:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>DevQuest — Character Dashboard</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body class="{{THEME_CLASS}}">
    <div class="dashboard">
        <header>
            <h1>DevQuest</h1>
            <div class="class-info">{{TITLE}} (Level {{LEVEL}})</div>
        </header>
        <section class="stats-bar">
            <div class="xp-section">
                <label>XP</label>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {{XP_PERCENT}}%"></div>
                </div>
                <span>{{XP_PROGRESS}} / {{XP_NEEDED}}</span>
            </div>
            <div class="gold-section">
                <span class="gold-amount">{{GOLD}} Gold</span>
            </div>
        </section>
        <section class="achievements">
            <h2>Achievements</h2>
            <ul>{{ACHIEVEMENTS_HTML}}</ul>
        </section>
        <section class="weekly-stats">
            <h2>Weekly Stats</h2>
            {{WEEKLY_STATS_HTML}}
        </section>
        <section class="attributes">
            <h2>Attributes</h2>
            {{ATTRIBUTES_HTML}}
        </section>
        <section class="buffs">
            <h2>Active Buffs</h2>
            {{BUFFS_HTML}}
        </section>
        <section class="quests">
            <h2>Quests</h2>
            {{QUESTS_HTML}}
        </section>
    </div>
</body>
</html>
```

- [ ] **Step 2: Create `assets/styles.css`**

Write CSS with:
- CSS custom properties per theme (set on `body.theme-*` classes)
- Properties: `--bg`, `--text`, `--accent`, `--accent-secondary`, `--card-bg`, `--border`, `--progress-fill`, `--progress-bg`, `--gold-color`
- Theme values:
  - **Fantasy:** dark parchment tones, gold accents, warm colors
  - **Sci-Fi:** dark blue/black, neon cyan/green accents
  - **Retro:** dark background, pixel-green/magenta accents
  - **Minimalist:** white background, gray/black, no decorative elements
- Base layout: centered dashboard, max-width 800px, card-based sections
- Progress bar: rounded, animated fill with transition
- Achievement list: inline badges
- Responsive: stack on mobile
- No external fonts (use system font stack)

- [ ] **Step 3: Commit**

```bash
git add assets/dashboard.html assets/styles.css
git commit -m "feat: add HTML dashboard template and theme CSS"
```

---

### Task 8: Integration — Verify All Files Work Together

**Files:**
- All files from Tasks 1-7

- [ ] **Step 1: Create a test state file**

Write a sample `.devquest/state.json` in the project directory with realistic test data:
- Level 5, 900 total XP, 245 gold
- 2 achievements earned
- 1 active buff (Test XP Boost, 7 actions remaining)
- Some weekly stats populated
- A few quests with progress

- [ ] **Step 2: Run the HTML renderer**

```bash
python scripts/render-html.py --state .devquest/state.json --theme fantasy --output .devquest/dashboard.html
```

Expected: `dashboard.html` is created with Fantasy theme styling and all data populated.

- [ ] **Step 3: Open and visually verify the dashboard**

Open `.devquest/dashboard.html` in a browser. Verify:
- Theme colors are correct (Fantasy = warm/parchment)
- XP progress bar shows correct fill percentage
- Achievements, stats, attributes, and buffs all render
- Layout is clean and readable

- [ ] **Step 4: Test with each theme**

Run the renderer with `--theme scifi`, `--theme retro`, `--theme minimalist` and verify each produces correctly themed output.

- [ ] **Step 5: Clean up test state**

Remove the test `.devquest/` directory — it shouldn't be committed.

```bash
rm -rf .devquest/
```

- [ ] **Step 6: Commit any fixes**

If any files needed adjustment during verification:
```bash
git add -A
git commit -m "fix: adjustments from integration testing"
```

---

### Task 9: Final Review and Documentation

**Files:**
- Review: all files
- Create: `evals/evals.json`

- [ ] **Step 1: Read through SKILL.md end to end**

Verify:
- All command handlers reference the correct reference files
- State schema matches what the reference files expect
- Passive tracking covers all action types
- Code generation gate flow is complete
- Settings handler uses numbered option selection (not manual typing)

- [ ] **Step 2: Cross-reference consistency**

Check that:
- Quest tracking fields in `references/quests.md` match the `stats` fields in the state schema
- Achievement triggers in `references/progression.md` match the stat fields
- Shop items in `references/economy.md` match the attribute names in state
- Buff targets in economy match the action types in SKILL.md tracking

- [ ] **Step 3: Create `evals/evals.json`**

```json
{
  "skill_name": "devquest",
  "evals": [
    {
      "id": 1,
      "prompt": "I want to enable devquest for my project with a fantasy theme",
      "expected_output": "Prompts for environment, theme, display mode. Creates state file. Shows fantasy welcome message.",
      "files": []
    },
    {
      "id": 2,
      "prompt": "Show me my devquest character sheet",
      "expected_output": "Reads state, displays full character sheet with level, XP bar, gold, achievements, weekly stats, attributes, buffs in markdown format.",
      "files": []
    },
    {
      "id": 3,
      "prompt": "I want to buy a Test XP Boost from the devquest shop",
      "expected_output": "Shows shop catalog, processes purchase if enough gold, adds buff to inventory, updates gold balance.",
      "files": []
    }
  ]
}
```

- [ ] **Step 4: Commit**

```bash
git add evals/evals.json
git commit -m "feat: add eval test cases for skill verification"
```
