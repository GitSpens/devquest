# DevQuest Quests

Read this file for quest definitions, tracking rules, and display format.

---

## Quest Catalog

| ID | Name | Category | Goal | Tracking Field | Target | XP | Gold |
|----|------|----------|------|----------------|--------|----|------|
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

---

## Quest State Schema

Each quest in the saved state is keyed by its ID (as a string):

```json
"quests": {
  "1": {"progress": 0, "completed": false, "claimed": false},
  "2": {"progress": 0, "completed": false, "claimed": false},
  "3": {"progress": 0, "completed": false, "claimed": false},
  "4": {"progress": 0, "completed": false, "claimed": false},
  "5": {"progress": 0, "completed": false, "claimed": false},
  "6": {"progress": 0, "completed": false, "claimed": false},
  "7": {"progress": 0, "completed": false, "claimed": false},
  "8": {"progress": 0, "completed": false, "claimed": false},
  "9": {"progress": 0, "completed": false, "claimed": false},
  "10": {"progress": 0, "completed": false, "claimed": false},
  "11": {"progress": 0, "completed": false, "claimed": false},
  "12": {"progress": 0, "completed": false, "claimed": false}
}
```

Fields:
- `progress` — current numeric progress toward the target
- `completed` — true when the target has been reached
- `claimed` — true after XP and gold rewards have been awarded (always true when completed, since claiming is automatic)

---

## Quest Progress Update Rules

On every tracked action, iterate over all uncompleted quests and update progress according to their tracking field:

1. **Standard quests (IDs 1–9, 11):** Read the value of the quest's tracking field from the character's `stats` object and set `progress` to that value. If `progress >= target`, mark `completed = true` and `claimed = true`, then award XP and gold.

2. **Quest 10 — Well Rounded (special):** Check whether at least one quest from each of the four categories has been completed:
   - `coding` (IDs 1, 2, 3)
   - `testing` (IDs 4, 5)
   - `debugging` (IDs 6, 7)
   - `docs` (IDs 8, 9)

   Set `progress` to the count of categories that have at least one completed quest (0–4). If `progress >= 4`, mark complete and award rewards.

3. **Quest 12 — Code Miser (special):** Check the character's current `gold` balance (not a cumulative counter). Set `progress` to `character.gold`. If the balance is >= 500, mark complete and award rewards. If the balance later drops below 500, the quest remains completed — it is not reverted.

4. **Auto-claim:** There is no manual claim step. Rewards are granted immediately when a quest transitions to `completed = true`.

---

## Quest Display Format

### Progress Bar

A 12-character bar where `=` marks filled progress and `-` marks remaining:

```
[======------] 63/100
```

- Filled characters: `floor(progress / target * 12)`
- Empty characters: `12 - filled`

### Completed Quest

```
[============] COMPLETE! | Claimed: {xp} XP, {gold} Gold
```

### Quest List Grouping

Display incomplete quests first (sorted by ID), followed by completed quests (sorted by ID):

```
ACTIVE QUESTS
  [ 1] First Blood      [======------]  6/10
  [ 2] Centurion        [=-----------]  8/100

COMPLETED QUESTS
  [ 6] Bug Squasher     [============] COMPLETE! | Claimed: 40 XP, 20 Gold
```
