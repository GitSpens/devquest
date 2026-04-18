# DevQuest Quests

Read this file for quest definitions, tracking rules, and display format.

---

## Quest Catalog

| ID | Name | Category | Goal | Tracking Field | Target | XP | Gold |
|----|------|----------|------|----------------|--------|----|------|
| 1 | First Blood | coding | Write 10 lines | stats.lines_written | 10 | 20 | 10 |
| 2 | Centurion | coding | Write 100 lines | stats.lines_written | 100 | 100 | 50 |
| 3 | Thousand Lines | coding | Write 1000 lines | stats.lines_written | 1000 | 500 | 250 |
| 4 | Shopaholic | economy | Purchase 5 items | stats.items_purchased | 5 | 50 | 0 |
| 5 | Code Miser | economy | Have 500 gold balance | character.gold | 500 | 100 | 0 |

---

## Quest State Schema

Each quest in the saved state is keyed by its ID (as a string):

```json
"quests": {
  "1": {"progress": 0, "completed": false, "claimed": false},
  "2": {"progress": 0, "completed": false, "claimed": false},
  "3": {"progress": 0, "completed": false, "claimed": false},
  "4": {"progress": 0, "completed": false, "claimed": false},
  "5": {"progress": 0, "completed": false, "claimed": false}
}
```

Fields:
- `progress` — current numeric progress toward the target
- `completed` — true when the target has been reached
- `claimed` — true after XP and gold rewards have been awarded (always true when completed, since claiming is automatic)

---

## Quest Progress Update Rules

On every tracked action, iterate over all uncompleted quests and update progress according to their tracking field:

1. **Standard quests (IDs 1–4):** Read the value of the quest's tracking field from the character's `stats` object and set `progress` to that value. If `progress >= target`, mark `completed = true` and `claimed = true`, then award XP and gold.

2. **Quest 5 — Code Miser (special):** Check the character's current `gold` balance (not a cumulative counter). Set `progress` to `character.gold`. If the balance is >= 500, mark complete and award rewards. If the balance later drops below 500, the quest remains completed — it is not reverted.

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
  [ 4] Shopaholic       [============] COMPLETE! | Claimed: 50 XP, 0 Gold
```
