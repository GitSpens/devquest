# Discovery — devquest-skill

**Date:** 2026-04-17
**Status:** Approved
**Project:** Claude Code Skills Framework (markdown)

---

## 1. Feature Summary

**Description:** DevQuest is a Claude Code skill that passively gamifies development work — tracking coding, testing, debugging, and documentation actions to award XP, gold, and level progression. It supports themed visual experiences (fantasy/sci-fi/retro/minimalist) with configurable display modes (markdown terminal or HTML browser) and environments (CLI or Desktop). Gold is earned through dev work and spent when asking Claude to generate code. Includes a shop for stat upgrades and action-based buffs, and a quest system for bonus challenges.

**Subsystems:** Skill Core, State Management, Rendering (Markdown + HTML), Themes, Commands, Passive Tracking, Progression System, Shop & Economy

---

## 2. Operations

### Operation: `/devquest-enable`
**Description:** Enable gamification for the current project. Prompts for environment (CLI/Desktop), theme, and display mode (markdown/HTML). Creates initial character state.
**Inputs:** User choices via interactive prompts (environment, theme, display mode)
**Output:** Confirmation with selected theme, initial character info (Level 1, title, 0 XP, 0 gold)

### Operation: `/devquest-disable`
**Description:** Disable gamification. State freezes — no tracking, no notifications. State is preserved for re-enabling later.
**Inputs:** None
**Output:** Confirmation that gamification is paused

### Operation: `/devquest-character`
**Description:** Display full character sheet — level, XP bar, gold, achievements, weekly stats, attributes, active buffs.
**Inputs:** None
**Output:** Themed character sheet in the user's chosen display mode (markdown or HTML)

### Operation: `/devquest-shop`
**Description:** Browse and purchase stat upgrades and action-based buffs with gold.
**Inputs:** User selection of item to purchase
**Output:** Item list with prices, purchase confirmation, updated gold balance. Items include:
- Permanent stat boosts (e.g., Code Mastery +1 level)
- Action-based buffs (e.g., "Test XP Boost — 50% more XP from tests for next 10 actions")
- Unlimited stacking, no cooldowns

### Operation: `/devquest-quests`
**Description:** List active challenges with progress, rewards, and completion status.
**Inputs:** None
**Output:** Quest list with descriptions, progress bars, and reward amounts (XP + gold)

### Operation: `/devquest-theme`
**Description:** Change the visual theme (Fantasy, Sci-Fi, Retro, Minimalist).
**Inputs:** Theme selection
**Output:** Confirmation, all subsequent output uses new theme

### Operation: `/devquest-settings`
**Description:** Single command to view all settings and change any of them (environment, display mode, theme).
**Inputs:** Optional setting to change
**Output:** Current settings table, interactive change flow if requested

### Operation: **Passive Tracking**
**Description:** Automatically detects and rewards development actions with themed notifications.
**Tracking rules:**
- Writing code: +1 XP, +0.5 gold per line
- Running tests (pass): +30 XP, +10 gold
- Running tests (fail): +10 XP
- Implementing features: +50 XP, +20 gold (scaled by complexity)
- Bug fixes: +20 XP, +5 gold
- Documentation: +10 XP, +2 gold per function/module
**Output:** Inline notification after each action with XP/gold earned and current status

### Operation: **Code Generation Gate**
**Description:** When user asks Claude to generate code, calculate gold cost proportional to expected output size. Prompt user with price and balance before proceeding.
**Formula:** `cost = ceil(estimated_lines * 0.5)` — generating code costs roughly what you'd earn writing it yourself.
**Inputs:** Detected code generation request
**Output:** Price prompt showing cost and current balance. If insufficient gold: deny with notification about relevant buffs in inventory. If sufficient: proceed after user confirms.

---

## 3. Success Criteria

- State (XP, gold, level, inventory, settings) persists across sessions
- Passive tracking fires themed notifications with correct XP/gold after coding, testing, debugging, docs
- Code generation gate prompts with price/balance before generating, blocks if insufficient gold
- Buff system: purchasing adds to inventory, active buffs modify rewards, action-based buffs decrement per action and expire at 0
- All output uses selected theme's naming, icons, and visual style consistently
- Character sheet, shop, and quests render correctly in both markdown and HTML display modes
- Settings changes persist and take effect immediately
- Level-up triggers notification with new themed title when XP threshold crossed
- Quests are a fixed set, track progress, and award bonus gold/XP on completion
- Disabling freezes state; re-enabling resumes from frozen state
- One character per project, no cross-project state

---

## 4. Existing Capability Overlap

No existing capabilities overlap with this feature (greenfield project).

---

## 5. Architecture Decision

**Approach:** New skill — full creation from scratch
**Primary files:**
- `SKILL.md` — Main skill entry point with frontmatter, command routing, and core instructions
- `references/themes.md` — Theme definitions (names, icons, level titles, visual styles)
- `references/progression.md` — XP curves, level thresholds, achievement definitions, attribute system
- `references/economy.md` — Shop items, pricing, buff definitions, code generation cost formula
- `references/quests.md` — Quest definitions, progress tracking rules
- `scripts/render-html.py` — HTML dashboard generator for character sheet, shop, quests
- `assets/dashboard.html` — HTML template for browser-based display
- `assets/styles.css` — Theme-specific CSS variables

**State file (per-project):** `.devquest/state.json` stored in the project directory where DevQuest is enabled

---

## 6. Known Gotchas

| Issue | Impact | Mitigation |
|-------|--------|-----------|
| Action-based buff tracking | Must reliably decrement remaining actions on each tracked event | Decrement counter in state on every passive tracking event; remove buff when counter hits 0 |
| Code generation size estimation | Must estimate lines before generation to price it | Use heuristic based on request complexity; can be tuned later if unbalanced |
| State file conflicts | Multiple Claude sessions in same project | Single JSON file with atomic read-modify-write pattern |
| Passive tracking accuracy | Distinguishing user-written code from generated code | Track which actions triggered the generation gate vs. organic work |

---

## 7. Deliverables

- [ ] `SKILL.md` — Skill core with frontmatter, command routing, tracking logic
- [ ] `references/themes.md` — Theme definitions and visual configurations
- [ ] `references/progression.md` — Leveling, achievements, attributes
- [ ] `references/economy.md` — Shop, buffs, pricing, gold cost formula
- [ ] `references/quests.md` — Quest definitions and tracking
- [ ] `scripts/render-html.py` — HTML renderer for browser display mode
- [ ] `assets/dashboard.html` — HTML template
- [ ] `assets/styles.css` — Theme CSS
- [ ] `evals/evals.json` — Test cases for skill evaluation

---

## 8. Gaps & Recommendations

- **Quest content:** Quests are a fixed set (decided). Still need to define the specific 10-15 starter quests across categories (coding, testing, debugging, docs) with escalating difficulty and rewards — to be detailed in the spec phase.
- **Economy balance:** Code generation cost formula is set at `cost = ceil(estimated_lines * 0.5)` (decided). May need tuning after playtesting but formula is locked for initial implementation.
- **No remaining gaps** on buff duration (action-based, decided) or quest type (fixed set, decided).
