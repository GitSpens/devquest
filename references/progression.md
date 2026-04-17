# DevQuest Progression System

Read this file when you need XP thresholds, achievement triggers, or attribute bonus formulas.

---

## 1. XP Thresholds

XP is **cumulative** — it does NOT reset on level-up. A player's level is always derived from their total lifetime XP.

### Level Table

| Level | XP Required | XP to Next Level |
|-------|-------------|------------------|
| 1     | 0           | 100              |
| 2     | 100         | 150              |
| 3     | 250         | 250              |
| 4     | 500         | 300              |
| 5     | 800         | 400              |
| 6     | 1,200       | 600              |
| 7     | 1,800       | 700              |
| 8     | 2,500       | 1,000            |
| 9     | 3,500       | 1,500            |
| 10    | 5,000       | 2,000            |
| 11    | 7,000       | 2,500            |
| 12    | 9,500       | 3,000            |
| 13    | 12,500      | 3,500            |
| 14    | 16,000      | 4,000            |
| 15    | 20,000      | 5,000            |
| 16    | 25,000      | 6,000            |
| 17    | 31,000      | 7,000            |
| 18    | 38,000      | 8,000            |
| 19    | 46,000      | 9,000            |
| 20    | 55,000      | — (max level)    |

### Formulas

**Level calculation:**
```
current_level = highest level whose threshold <= total_xp_earned
```
Iterate the level table from level 20 down to level 1 and return the first level where `threshold <= total_xp_earned`.

**XP bar display:**
```
progress = total_xp_earned - current_level_threshold
needed   = next_level_threshold - current_level_threshold
display  = [========------] {progress}/{needed}
```
Fill characters proportionally: `filled = round(14 * progress / needed)`, remainder is dashes. At level 20 (max), display `[==============] MAX`.

**Level-up detection:**
```
old_level = current_level (before adding XP)
total_xp_earned += xp_gained
new_level = recalculate level from total_xp_earned
if new_level > old_level:
    trigger level-up notification for each level crossed
```
Always recompute level from the full XP total; never increment level directly.

---

## 2. Achievements

There are **12 achievements** in total. Each achievement can only be unlocked once per player.

### Achievement Table

| ID            | Name                 | Trigger                                      |
|---------------|----------------------|----------------------------------------------|
| first_line    | First Blood          | `lines_written >= 1`                         |
| century       | Century              | `lines_written >= 100`                       |
| test_pilot    | Test Pilot           | `tests_run >= 10`                            |
| perfect_run   | Perfect Run          | 5 consecutive passing test runs              |
| bug_squasher  | Bug Squasher         | `bugs_fixed >= 1`                            |
| doc_writer    | Documentation Hero   | `functions_documented >= 10`                 |
| big_spender   | Big Spender          | `gold_spent >= 100`                          |
| hoarder       | Gold Hoarder         | current gold `>= 500`                        |
| level_5       | Rising Star          | reach level 5                                |
| level_10      | Veteran              | reach level 10                               |
| level_20      | Ascended             | reach level 20                               |
| all_quests    | Quest Master         | complete all 12 quests                       |

### Achievement Check Instructions

Run achievement checks after any state-changing event (XP gained, gold changed, lines written, tests run, bugs fixed, functions documented, quest completed). For each achievement not yet unlocked:

1. Evaluate the trigger condition against the current player state.
2. If the condition is met, mark the achievement as unlocked and record the timestamp.
3. Emit the notification (see format below).
4. Do not re-check already-unlocked achievements.

For `perfect_run`: maintain a `consecutive_passing_runs` counter. Increment on each passing test run, reset to 0 on any failing run. Trigger when the counter reaches 5.

For `hoarder`: check `player.gold >= 500` (current gold on hand, not lifetime gold earned).

For `level_5`, `level_10`, `level_20`: check immediately after every level-up recalculation.

For `all_quests`: check after every quest completion — trigger when `quests_completed` count equals 12.

### Notification Format

```
ACHIEVEMENT UNLOCKED: {name}! — {trigger description}
```

Examples:
```
ACHIEVEMENT UNLOCKED: First Blood! — wrote your first line of code
ACHIEVEMENT UNLOCKED: Perfect Run! — 5 consecutive passing test runs
ACHIEVEMENT UNLOCKED: Veteran! — reached level 10
```

---

## 3. Attributes

Attributes are permanent bonuses that improve specific reward calculations. Each attribute has a `level` (integer, starts at 0) set by the player's chosen upgrades.

### Attribute Table

| Attribute ID    | Name            | Bonus                                    |
|-----------------|-----------------|------------------------------------------|
| code_mastery    | Code Mastery    | +3% gold per level from writing code    |
| debugging       | Debugging       | +10% XP per level from bug fixes        |
| documentation   | Documentation   | +5% XP and +5% gold per level from docs |

### Bonus Formula

```
modified = base * (1 + attribute_level * bonus_pct / 100)
```

Where:
- `base` is the raw XP or gold amount before the attribute bonus.
- `attribute_level` is the player's current level in that attribute.
- `bonus_pct` is the per-level percentage for the relevant attribute (3, 10, or 5).

**Worked example — Debugging at level 3, base XP reward of 50:**
```
modified = 50 * (1 + 3 * 10 / 100)
         = 50 * (1 + 0.30)
         = 50 * 1.30
         = 65 XP
```

**Worked example — Documentation at level 2, base XP reward of 20 and base gold reward of 10:**
```
xp_modified   = 20 * (1 + 2 * 5 / 100) = 20 * 1.10 = 22 XP
gold_modified = 10 * (1 + 2 * 5 / 100) = 10 * 1.10 = 11 gold
```

Apply attribute bonuses after calculating the base reward and before adding the result to player totals. Round the final value to the nearest integer.

---

## 4. Weekly Stats

Weekly stats track activity within the current Monday-to-Sunday week and reset at the start of each new week.

### Reset Logic

```
current_monday = date of the most recent Monday (today if today is Monday)
if weekly_stats.week_start != current_monday:
    reset weekly_stats counters to 0
    weekly_stats.week_start = current_monday
```

Perform this check at the start of every session (when the skill is invoked) and before recording any stat that feeds into weekly totals.

### Tracked Weekly Stats

The following counters reset each Monday:

- `weekly_xp_earned`
- `weekly_gold_earned`
- `weekly_lines_written`
- `weekly_tests_run`
- `weekly_bugs_fixed`
- `weekly_functions_documented`
- `weekly_quests_completed`

Lifetime counters (`total_xp_earned`, `lines_written`, `bugs_fixed`, etc.) used for achievement triggers are **never** reset.
