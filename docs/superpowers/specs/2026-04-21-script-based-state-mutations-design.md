# Script-based state mutations with interactive pickers

## Problem

DevQuest currently mutates `.devquest/state.json` via Claude's `Edit` / `Write` tools. Every theme change, settings update, or shop purchase renders a visible JSON diff in the chat transcript, cluttering the conversation. In parallel, deterministic UI (menus, theme lists, shop catalogs) is re-derived by Claude from prose in `SKILL.md` on every invocation, which is slow and wasteful for content that never changes.

## Goals

1. Replace `Edit`/`Write` on `state.json` with script calls so state mutations produce no visible diff.
2. Provide click-to-pick interaction (no typing numbers) for theme, settings, and shop commands, matching the UX of `/frontend-slides`.
3. Enforce the intended flow through scripts rather than prose, consistent with the project rule that skill instructions alone are unreliable.
4. Keep skill files thin — script-first, prose-last.

## Non-goals

- `/devquest-character`, `/devquest-quests` — read-only, no change.
- `/devquest-enable`, `/devquest-disable` — already script-backed; their narration staying with Claude is fine.
- XP/gold award path (`track-commit.py`, `check-gold-gate.py`) — already script-backed.
- HTML dashboard with clickable controls and a local server — deferred to a separate future spec.

## Architecture

Two new scripts in `scripts/`:

- **`menu.py`** — prints a JSON question/options payload for Claude to feed into the native `AskUserQuestion` tool. Stateless with respect to mutation; it reads current state and content definitions to build the payload. Also writes a short-lived `pending-action.json` record to enforce the flow.
- **`update-state.py`** — single generic mutator with one action flag per invocation (`--theme`, `--environment`, `--display-mode`, `--buy`). Requires a valid `--token` issued by `menu.py`. Writes atomically.

Three skill files get rewritten to thin routers: `devquest-theme`, `devquest-settings`, `devquest-shop`. Each tells Claude to run `menu.py`, pass the JSON to `AskUserQuestion`, and run `update-state.py` with the user's choice and the issued token.

Unchanged scripts: `track-commit.py`, `check-gold-gate.py`, `render-html.py`, `install-hook.py`, `setup-permissions.py`, `setup-project.py`, `devquest-enable.py`.

## Interaction flow

Using `/devquest-theme` as the canonical example:

1. User runs `/devquest-theme`.
2. Claude runs `python scripts/menu.py --for theme`. The script writes `.devquest/pending-action.json` with a token, action name, allowed values, and expiry, and prints the `AskUserQuestion` payload (including the token) to stdout.
3. Claude copies `question`, `header`, and `options` into an `AskUserQuestion` tool call. The Claude Code UI renders the picker.
4. User clicks "Sci-Fi". The tool returns the chosen value.
5. Claude runs `python scripts/update-state.py --theme scifi --token <token>`. The script validates, mutates, consumes the token, and prints `Theme changed to Sci-Fi.`
6. Claude echoes the confirmation. No JSON diff appears in the transcript.

Multi-step commands follow the same pattern:

- `/devquest-settings` runs `menu.py --for settings` (picks a field), then `menu.py --for settings-<field>` (picks a value), then `update-state.py`.
- `/devquest-shop` runs `menu.py --for shop` (picks an item), then `update-state.py --buy <item_id>`.

## `menu.py` contract

### CLI

```
python scripts/menu.py --for {theme|settings|settings-environment|settings-theme|settings-display-mode|shop}
```

### Output

Single JSON object on stdout, aligned with `AskUserQuestion` parameters:

```json
{
  "question": "Which theme?",
  "header": "Theme",
  "multiSelect": false,
  "token": "a1b2c3...",
  "options": [
    {"label": "Fantasy", "description": "Swords, scrolls, dragons", "value": "fantasy"},
    {"label": "Sci-Fi",  "description": "Neon, circuits, starships", "value": "scifi"}
  ]
}
```

Claude copies `question`, `header`, `multiSelect`, and `options` directly into the tool call. `token` is not user-visible — Claude passes it to `update-state.py` on the next turn.

### Side effects

Writes `.devquest/pending-action.json`:

```json
{
  "token": "a1b2c3...",
  "action": "theme",
  "allowed_values": ["fantasy", "scifi", "retro", "minimalist"],
  "expires_at": "2026-04-21T14:32:10Z"
}
```

TTL: 10 minutes. The file is overwritten on each `menu.py` call, so only the most recent menu is valid.

### Content sources

- `--for theme` reads theme definitions from `references/themes.md` (or a JSON sibling).
- `--for shop` reads the catalog from `references/economy.md`, filters out already-owned one-time items, and marks unaffordable items with a `"— locked (need X gold)"` suffix in `description`. Affordability is informational; `update-state.py` is the actual gatekeeper.
- `--for settings` returns a fixed three-option menu (Environment, Theme, Display Mode). Each `value` is the next `--for` kind Claude should request.
- `--for settings-environment` and `--for settings-display-mode` return fixed two-option menus. Current value is marked in the `description`.

### Errors

Non-zero exit with a plain message to stderr: missing `state.json`, unknown `--for` kind, malformed content source.

## `update-state.py` contract

### CLI

Exactly one action flag per call, plus a required `--token`:

- `--theme {fantasy|scifi|retro|minimalist}`
- `--environment {cli|desktop}`
- `--display-mode {markdown|html}`
- `--buy <item_id>`

### Token validation

Before any mutation:

- `.devquest/pending-action.json` exists and is readable.
- `token` matches exactly.
- `action` matches the flag family (e.g., `--theme` requires `action: "theme"`).
- The chosen value is in `allowed_values`.
- `expires_at` has not passed.

On success, delete `pending-action.json` so the token cannot be replayed.

### Success output

One short line to stdout:

- `Theme changed to Sci-Fi.`
- `Environment set to Desktop.`
- `Display mode set to HTML.`
- `Purchased Focus Potion. -50 gold (150 remaining).`

### Error output

Plain message to stderr, non-zero exit. Representative cases:

- `Not enough gold (need 50, have 30).`
- `Unknown item: xyz.`
- `Item already owned.`
- `Invalid or expired selection. Run the command again.` (token mismatch / expired)
- `.devquest/state.json not found. Run /devquest-enable first.`

### Atomicity

Read current state, compute full new state in memory, write to `.devquest/state.json.tmp`, `os.replace` to `state.json`. A crash mid-write cannot corrupt state.

## Enforcement model

The token flow is what enforces skill steps. Claude cannot:

- Skip `menu.py` — without the token, `update-state.py` refuses.
- Fabricate a value — values outside `allowed_values` are rejected.
- Replay a prior pick — tokens are single-use and time-limited.
- Cross-apply a token — theme token on `--buy` fails the `action` check.

This matches the gold-gate pattern: enforcement sits in the script, not in SKILL prose.

## Skill file changes

Each interactive command's SKILL.md becomes a short instruction list referencing scripts, with no hardcoded option content. Example shape:

```markdown
1. Run: python scripts/menu.py --for theme
2. Parse the JSON. Pass question, header, multiSelect, and options to AskUserQuestion. Remember the token.
3. Run: python scripts/update-state.py --theme <value> --token <token>
4. Print the script's stdout verbatim on success, or stderr verbatim on non-zero exit.
```

The main `SKILL.md` router table is updated so the three interactive commands point at the scripts rather than at reference files.

## Permissions

`setup-permissions.py` is updated to install two additional entries alongside the existing `track-commit.py` allowance:

- `Bash(python scripts/menu.py:*)`
- `Bash(python scripts/update-state.py:*)`

`AskUserQuestion` does not require a permission entry.

## Testing

Following the project rules: unit tests prove script logic, manual testing proves integration.

### Unit tests (`tests/`)

- `menu.py` emits valid JSON for each `--for` kind. Shape conforms to `AskUserQuestion`'s expected fields.
- `menu.py` writes `pending-action.json` with correct fields and TTL.
- `menu.py` for shop filters owned items and marks unaffordable items.
- `update-state.py` mutates state correctly for each flag.
- `update-state.py` rejects: missing token file, wrong token, mismatched action, out-of-range value, expired token, replayed (deleted) token.
- `update-state.py` writes atomically (simulate mid-write failure).
- Permission installer includes the two new entries.

### Manual test checklist (must pass before push)

1. `/devquest-theme` → picker appears in chat → click an option → confirmation printed → `state.json` theme changed → no diff visible in the transcript.
2. `/devquest-settings` → first picker (Environment/Theme/Display) → second picker → confirmation → state updated.
3. `/devquest-shop` with enough gold → purchase succeeds, gold drops, item added to state.
4. `/devquest-shop` with insufficient gold → error message printed, no state change.
5. Run `/devquest-theme` twice in quick succession — tokens don't leak between invocations; only the most recent menu's choice applies.
6. Interrupt mid-flow (Esc after picker) — next `/devquest-theme` still works (TTL expiry or overwrite clears stale state).

### Report rules

When reporting completion, state explicitly which items are script-tested vs manual-only. Do not claim the feature works on the basis of passing unit tests alone.

## Rollout

- New branch: `feat/script-based-state-mutations` off `main`.
- No push to remote until the manual checklist passes and the user confirms.
