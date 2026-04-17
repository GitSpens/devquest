# DevQuest Economy

Read this file for shop items, buff mechanics, and code generation cost rules.

---

## Shop Catalog

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

---

## Purchase Processing Rules

When a player attempts to purchase an item, follow these steps in order:

1. **Check gold** — Verify the player has enough gold to cover the item price. If not, deny the purchase and inform the player of the shortfall.
2. **Deduct gold** — Subtract the item price from the player's current gold balance.
3. **Add to gold_spent** — Increment the player's `gold_spent` lifetime stat by the item price.
4. **Handle stat_boost** — If the item type is `stat_boost`, permanently increment the corresponding player attribute by 1.
5. **Handle buff** — If the item type is `buff`, add a buff entry to the player's active buffs list using the buff entry schema (see below).
6. **Check quests** — Evaluate whether any active quest objectives were advanced by the purchase (e.g., "buy 3 items from the shop").
7. **Check achievements** — Evaluate whether any achievement conditions were met by the purchase or updated `gold_spent` total.

---

## Buff Entry Schema

When a buff is added to a player's active buffs list, it must follow this structure:

```json
{"id": "test_xp_boost", "name": "Test XP Boost", "effect": {"target": "test_xp", "multiplier": 1.5}, "actions_remaining": 10}
```

Fields:
- `id` — Snake_case identifier for the buff.
- `name` — Display name of the buff.
- `effect.target` — The resource or XP category this buff applies to (see target mapping below).
- `effect.multiplier` — The multiplier applied to the target value (e.g., `1.5` = +50%, `2.0` = +100%).
- `actions_remaining` — Number of player actions remaining before this buff expires.

---

## Buff Target Mapping

| Target | Applies To |
|--------|-----------|
| `test_xp` | XP from tests |
| `code_xp` | XP from writing code |
| `all_gold` | Gold from any source |
| `bugfix_xp` | XP from bug fixes |
| `docs_xp` | XP from documentation |

---

## Buff Processing Rules

When calculating XP or gold rewards for an action, apply active buffs using these steps:

1. **Check target match** — For each active buff, check whether the buff's `effect.target` matches the reward type being calculated (e.g., `test_xp` for a test action).
2. **Apply multiplier** — If the target matches, multiply the base reward value by the buff's `effect.multiplier`.
3. **Decrement ALL buffs** — After any player action that can trigger buffs, decrement `actions_remaining` by 1 on every active buff, regardless of whether a particular buff was triggered.
4. **Remove expired** — After decrementing, remove any buffs where `actions_remaining` has reached 0.
5. **Stacking rule** — If multiple buffs share the same target, apply each multiplier sequentially (multiplicative stacking), not additively.

---

## Code Generation Cost

### Formula

```
cost = ceil(estimated_lines * 0.5)
```

### Line Estimation Heuristic

| Request Size | Estimated Lines | Computed Cost |
|--------------|----------------|---------------|
| Small (1–20 lines) | 10 | 5 gold |
| Medium (20–50 lines) | 35 | 18 gold |
| Large (50–100 lines) | 75 | 38 gold |
| Very Large (100+ lines) | Use actual estimate | ceil(estimate * 0.5) |

### Gate Flow

When a player requests code generation:

1. Show the estimated cost and the player's current gold balance before proceeding.
2. Ask the player to confirm they want to spend the gold.
3. If the player's gold is insufficient, deny the request and explain the shortfall.
4. If the player has a **Gold Rush** buff active in their inventory, mention it — but note that Gold Rush applies to gold earned, not gold spent, so it does not reduce the code generation cost.

### Note

Generated code is **not** tracked for XP or gold rewards. Code generation is a gold-cost service only.
