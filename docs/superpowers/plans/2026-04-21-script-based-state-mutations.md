# Script-based state mutations implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `Edit`/`Write` on `.devquest/state.json` with script calls, add click-to-pick interaction via `AskUserQuestion`, and enforce the flow with a short-lived token so Claude cannot skip the menu step.

**Architecture:** Two new scripts — `menu.py` emits an `AskUserQuestion` payload and writes a token record; `update-state.py` mutates state only when invoked with a valid token. Three interactive commands (`devquest-theme`, `devquest-settings`, `devquest-shop`) become thin routers over these scripts. Menu content lives in one JSON config file.

**Tech Stack:** Python 3 stdlib (argparse, json, secrets, datetime, os.replace), unittest for script tests.

**Spec:** `docs/superpowers/specs/2026-04-21-script-based-state-mutations-design.md`

**Branch:** `feat/script-based-state-mutations` (already created off `main`).

---

## File structure

- **Create** `scripts/config/menus.json` — authoritative data for picker menus (themes, settings options, shop items).
- **Create** `scripts/menu.py` — prints `AskUserQuestion` payload, writes `.devquest/pending-action.json`.
- **Create** `scripts/update-state.py` — applies mutations after validating a token.
- **Create** `tests/test_menu.py` — unit tests for `menu.py`.
- **Create** `tests/test_update_state.py` — unit tests for `update-state.py`.
- **Modify** `scripts/setup-permissions.py:23-31` — add two new permission entries.
- **Modify** `tests/test_setup_permissions.py` — cover new entries.
- **Rewrite** `../devquest-theme/SKILL.md` — thin router.
- **Rewrite** `../devquest-settings/SKILL.md` — thin router.
- **Rewrite** `../devquest-shop/SKILL.md` — thin router.
- **Modify** `SKILL.md` (main router table) — three command rows point at scripts.

`scripts/config/menus.json` is authoritative for script-consumed menu data. `references/themes.md` and `references/economy.md` stay as human-facing narrative documentation; they will no longer be read by these three commands.

---

## Conventions

- Python tests use `unittest` and `import_module("menu")` / `import_module("update-state")` to handle hyphenated script names, matching `tests/test_setup_permissions.py:14-16`.
- Scripts run with `python scripts/<name>.py` from the project root. Paths in scripts use `Path(__file__).resolve().parent.parent` to find the config when needed.
- Tests create a temp directory with a `.devquest/state.json` seeded from a minimal fixture.
- `pending-action.json` schema:
  ```json
  {"token": "<hex>", "action": "<kind>", "allowed_values": ["..."], "expires_at": "<isoformat UTC>"}
  ```
- Token: `secrets.token_hex(16)` (32 hex chars).
- Expiry: 10 minutes.

---

## Task 1: Menu config file and shared state helpers

**Files:**
- Create: `scripts/config/menus.json`
- Create: `scripts/devquest_state.py` (small shared module)
- Create: `tests/test_devquest_state.py`

- [ ] **Step 1: Create `scripts/config/menus.json` with full menu data**

```json
{
  "theme": {
    "question": "Which theme?",
    "header": "Theme",
    "options": [
      {"label": "Fantasy",    "description": "Swords, scrolls, dragons",       "value": "fantasy"},
      {"label": "Sci-Fi",     "description": "Neon, circuits, starships",      "value": "scifi"},
      {"label": "Retro",      "description": "8-bit arcade",                    "value": "retro"},
      {"label": "Minimalist", "description": "Clean monochrome",                 "value": "minimalist"}
    ]
  },
  "settings": {
    "question": "Which setting do you want to change?",
    "header": "Settings",
    "options": [
      {"label": "Environment",  "description": "CLI or Desktop",         "value": "settings-environment"},
      {"label": "Theme",        "description": "Visual style",           "value": "settings-theme"},
      {"label": "Display mode", "description": "Markdown or HTML",       "value": "settings-display-mode"}
    ]
  },
  "settings-environment": {
    "question": "Which environment?",
    "header": "Environment",
    "options": [
      {"label": "CLI",     "description": "Terminal",                "value": "cli"},
      {"label": "Desktop", "description": "Claude Desktop app",      "value": "desktop"}
    ]
  },
  "settings-display-mode": {
    "question": "Which display mode?",
    "header": "Display mode",
    "options": [
      {"label": "Markdown", "description": "Render inline in the chat",       "value": "markdown"},
      {"label": "HTML",     "description": "Open a rendered dashboard in browser", "value": "html"}
    ]
  },
  "shop_items": [
    {
      "id": "code_mastery_plus_1",
      "label": "Code Mastery +1",
      "price": 50,
      "type": "stat_boost",
      "attribute": "code_mastery",
      "one_time": false,
      "description_short": "+1 permanent Code Mastery"
    },
    {
      "id": "code_xp_boost",
      "label": "Code XP Boost",
      "price": 30,
      "type": "buff",
      "buff": {"id": "code_xp_boost", "name": "Code XP Boost", "effect": {"target": "code_xp", "multiplier": 1.5}, "actions_remaining": 10},
      "one_time": false,
      "description_short": "+50% code XP, 10 actions"
    },
    {
      "id": "gold_rush",
      "label": "Gold Rush",
      "price": 25,
      "type": "buff",
      "buff": {"id": "gold_rush", "name": "Gold Rush", "effect": {"target": "all_gold", "multiplier": 1.25}, "actions_remaining": 15},
      "one_time": false,
      "description_short": "+25% gold, 15 actions"
    }
  ]
}
```

- [ ] **Step 2: Create `scripts/devquest_state.py` with load/save helpers**

```python
"""Shared helpers for loading and saving DevQuest state atomically."""

import json
import os
from pathlib import Path


def state_path(repo_path: str) -> Path:
    return Path(repo_path) / ".devquest" / "state.json"


def load_state(repo_path: str) -> dict:
    """Load state.json. Raises FileNotFoundError if missing, ValueError if malformed."""
    path = state_path(repo_path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(repo_path: str, state: dict) -> None:
    """Write state.json atomically via temp file + os.replace."""
    path = state_path(repo_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def load_menus_config() -> dict:
    """Load scripts/config/menus.json."""
    cfg_path = Path(__file__).resolve().parent / "config" / "menus.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **Step 3: Write failing test `tests/test_devquest_state.py`**

```python
#!/usr/bin/env python3
"""Tests for shared DevQuest state helpers."""

import json
import os
import sys
import tempfile
import unittest
from importlib import import_module
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

state_mod = import_module("devquest_state")


class TestSaveStateAtomic(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = {"foo": "bar", "n": 1}
            state_mod.save_state(tmp, data)
            loaded = state_mod.load_state(tmp)
            self.assertEqual(loaded, data)

    def test_no_tmp_file_left_behind(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_mod.save_state(tmp, {"ok": True})
            tmp_path = Path(tmp) / ".devquest" / "state.json.tmp"
            self.assertFalse(tmp_path.exists())


class TestLoadMenusConfig(unittest.TestCase):
    def test_loads_shop_items(self):
        cfg = state_mod.load_menus_config()
        self.assertIn("shop_items", cfg)
        self.assertTrue(len(cfg["shop_items"]) >= 3)

    def test_loads_theme_options(self):
        cfg = state_mod.load_menus_config()
        self.assertEqual(len(cfg["theme"]["options"]), 4)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run test to verify passes**

Run: `python -m pytest tests/test_devquest_state.py -v`
Expected: all 4 tests PASS (helpers and config already exist from steps 1-2).

- [ ] **Step 5: Commit**

```bash
git add scripts/config/menus.json scripts/devquest_state.py tests/test_devquest_state.py
git commit -m "feat: add menu config and shared state helpers"
```

---

## Task 2: `menu.py` with `--for theme`

**Files:**
- Create: `scripts/menu.py`
- Create: `tests/test_menu.py`

- [ ] **Step 1: Write failing test for `--for theme` payload**

```python
#!/usr/bin/env python3
"""Tests for menu.py."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

menu = import_module("menu")
state_mod = import_module("devquest_state")


def seed_state(repo_path, **overrides):
    """Seed a minimal .devquest/state.json."""
    state = {
        "settings": {"environment": "cli", "theme": "fantasy", "display_mode": "markdown"},
        "character": {"gold": 100, "gold_spent": 0, "attributes": {"code_mastery": 0}, "active_buffs": []},
        "stats": {"items_purchased": 0},
    }
    for k, v in overrides.items():
        state[k] = v
    state_mod.save_state(repo_path, state)


class TestThemeMenu(unittest.TestCase):
    def test_payload_has_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            payload = menu.build_payload(tmp, "theme")
            self.assertIn("question", payload)
            self.assertEqual(payload["header"], "Theme")
            self.assertFalse(payload["multiSelect"])
            self.assertEqual(len(payload["options"]), 4)
            self.assertIn("token", payload)
            self.assertEqual(len(payload["token"]), 32)

    def test_writes_pending_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            payload = menu.build_payload(tmp, "theme")
            pending_path = Path(tmp) / ".devquest" / "pending-action.json"
            self.assertTrue(pending_path.exists())
            with open(pending_path) as f:
                pending = json.load(f)
            self.assertEqual(pending["token"], payload["token"])
            self.assertEqual(pending["action"], "theme")
            self.assertEqual(
                set(pending["allowed_values"]),
                {"fantasy", "scifi", "retro", "minimalist"},
            )
            # expires_at is 10 minutes in the future
            expires = datetime.fromisoformat(pending["expires_at"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = (expires - now).total_seconds()
            self.assertTrue(540 < delta < 660)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_menu.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'menu'` or similar.

- [ ] **Step 3: Create `scripts/menu.py` handling `--for theme`**

```python
#!/usr/bin/env python3
"""
DevQuest interactive menu generator.

Prints a JSON payload for the AskUserQuestion tool and writes a short-lived
pending-action token to .devquest/pending-action.json.

Usage:
    python menu.py --for theme [--repo <path>]
    python menu.py --for settings [--repo <path>]
    python menu.py --for settings-environment [--repo <path>]
    python menu.py --for settings-theme [--repo <path>]
    python menu.py --for settings-display-mode [--repo <path>]
    python menu.py --for shop [--repo <path>]
"""

import argparse
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import devquest_state

TOKEN_TTL_SECONDS = 600

ACTION_NAMES = {
    "theme": "theme",
    "settings-theme": "theme",
    "settings-environment": "environment",
    "settings-display-mode": "display-mode",
    "shop": "buy",
}


def _options_for(kind: str, state: dict, cfg: dict) -> list:
    if kind in ("theme", "settings-theme"):
        return cfg["theme"]["options"]
    if kind == "settings":
        return cfg["settings"]["options"]
    if kind == "settings-environment":
        return cfg["settings-environment"]["options"]
    if kind == "settings-display-mode":
        return cfg["settings-display-mode"]["options"]
    if kind == "shop":
        return _shop_options(state, cfg)
    raise ValueError(f"Unknown menu kind: {kind}")


def _shop_options(state: dict, cfg: dict) -> list:
    # Filled in in Task 8.
    raise NotImplementedError("Shop menu not yet implemented.")


def _question_and_header(kind: str, cfg: dict) -> tuple[str, str]:
    if kind in ("theme", "settings-theme"):
        return cfg["theme"]["question"], cfg["theme"]["header"]
    if kind == "settings":
        return cfg["settings"]["question"], cfg["settings"]["header"]
    if kind == "settings-environment":
        return cfg["settings-environment"]["question"], cfg["settings-environment"]["header"]
    if kind == "settings-display-mode":
        return cfg["settings-display-mode"]["question"], cfg["settings-display-mode"]["header"]
    if kind == "shop":
        return "Which item do you want to buy?", "Shop"
    raise ValueError(f"Unknown menu kind: {kind}")


def build_payload(repo_path: str, kind: str) -> dict:
    cfg = devquest_state.load_menus_config()
    state = devquest_state.load_state(repo_path)

    options = _options_for(kind, state, cfg)
    question, header = _question_and_header(kind, cfg)

    token = secrets.token_hex(16)
    action = ACTION_NAMES.get(kind)
    if action is None and kind != "settings":
        raise ValueError(f"Unknown menu kind: {kind}")

    payload = {
        "question": question,
        "header": header,
        "multiSelect": False,
        "options": options,
        "token": token,
    }

    # Settings is a router menu — no mutation follows, so no pending action file.
    if kind != "settings":
        expires = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS)
        pending = {
            "token": token,
            "action": action,
            "allowed_values": [opt["value"] for opt in options],
            "expires_at": expires.isoformat().replace("+00:00", "Z"),
        }
        pending_path = Path(repo_path) / ".devquest" / "pending-action.json"
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pending_path, "w", encoding="utf-8") as f:
            json.dump(pending, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return payload


def main():
    parser = argparse.ArgumentParser(description="DevQuest menu generator")
    parser.add_argument(
        "--for",
        dest="kind",
        required=True,
        choices=["theme", "settings", "settings-theme", "settings-environment", "settings-display-mode", "shop"],
    )
    parser.add_argument("--repo", default=".", help="Project root (default: cwd)")
    args = parser.parse_args()

    try:
        payload = build_payload(args.repo, args.kind)
    except FileNotFoundError:
        print(".devquest/state.json not found. Run /devquest-enable first.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(payload, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_menu.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/menu.py tests/test_menu.py
git commit -m "feat: add menu.py with theme picker"
```

---

## Task 3: `update-state.py` with `--theme` + token validation

**Files:**
- Create: `scripts/update-state.py`
- Create: `tests/test_update_state.py`

- [ ] **Step 1: Write failing tests covering theme mutation and token validation**

```python
#!/usr/bin/env python3
"""Tests for update-state.py."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

update = import_module("update-state")
state_mod = import_module("devquest_state")


def seed_state(repo_path, **overrides):
    state = {
        "settings": {"environment": "cli", "theme": "fantasy", "display_mode": "markdown"},
        "character": {"gold": 100, "gold_spent": 0, "attributes": {"code_mastery": 0}, "active_buffs": []},
        "stats": {"items_purchased": 0},
    }
    for k, v in overrides.items():
        state[k] = v
    state_mod.save_state(repo_path, state)


def seed_pending(repo_path, action, allowed_values, token="abc123", expires_in_seconds=600):
    expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    pending = {
        "token": token,
        "action": action,
        "allowed_values": allowed_values,
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
    }
    path = Path(repo_path) / ".devquest" / "pending-action.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pending, f)


class TestThemeUpdate(unittest.TestCase):
    def test_valid_theme_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            seed_pending(tmp, "theme", ["fantasy", "scifi", "retro", "minimalist"])
            msg = update.apply(tmp, action="theme", value="scifi", token="abc123")
            self.assertEqual(msg, "Theme changed to Sci-Fi.")
            state = state_mod.load_state(tmp)
            self.assertEqual(state["settings"]["theme"], "scifi")

    def test_token_consumed_after_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            seed_pending(tmp, "theme", ["fantasy", "scifi", "retro", "minimalist"])
            update.apply(tmp, action="theme", value="scifi", token="abc123")
            pending_path = Path(tmp) / ".devquest" / "pending-action.json"
            self.assertFalse(pending_path.exists())

    def test_wrong_token_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            seed_pending(tmp, "theme", ["fantasy", "scifi", "retro", "minimalist"], token="good")
            with self.assertRaises(update.TokenError):
                update.apply(tmp, action="theme", value="scifi", token="bad")
            # state unchanged
            state = state_mod.load_state(tmp)
            self.assertEqual(state["settings"]["theme"], "fantasy")

    def test_missing_pending_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            with self.assertRaises(update.TokenError):
                update.apply(tmp, action="theme", value="scifi", token="abc123")

    def test_wrong_action_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            seed_pending(tmp, "buy", ["code_mastery_plus_1"])
            with self.assertRaises(update.TokenError):
                update.apply(tmp, action="theme", value="scifi", token="abc123")

    def test_value_not_in_allowed_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            seed_pending(tmp, "theme", ["fantasy", "scifi"])
            with self.assertRaises(update.TokenError):
                update.apply(tmp, action="theme", value="gothic", token="abc123")

    def test_expired_token_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            seed_pending(tmp, "theme", ["fantasy", "scifi"], expires_in_seconds=-1)
            with self.assertRaises(update.TokenError):
                update.apply(tmp, action="theme", value="scifi", token="abc123")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_update_state.py -v`
Expected: all FAIL with ModuleNotFoundError.

- [ ] **Step 3: Create `scripts/update-state.py`**

```python
#!/usr/bin/env python3
"""
DevQuest state mutator.

Applies a single state mutation only when called with a valid token that was
issued by a recent menu.py run. On success, consumes the token (deletes
.devquest/pending-action.json).

Usage:
    python update-state.py --theme <fantasy|scifi|retro|minimalist> --token <token> [--repo <path>]
    python update-state.py --environment <cli|desktop> --token <token> [--repo <path>]
    python update-state.py --display-mode <markdown|html> --token <token> [--repo <path>]
    python update-state.py --buy <item_id> --token <token> [--repo <path>]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import devquest_state


class TokenError(Exception):
    pass


class MutationError(Exception):
    pass


THEME_LABELS = {
    "fantasy": "Fantasy",
    "scifi": "Sci-Fi",
    "retro": "Retro",
    "minimalist": "Minimalist",
}

ENVIRONMENT_LABELS = {"cli": "CLI", "desktop": "Desktop"}
DISPLAY_MODE_LABELS = {"markdown": "Markdown", "html": "HTML"}


def _validate_token(repo_path: str, action: str, value: str, token: str) -> None:
    pending_path = Path(repo_path) / ".devquest" / "pending-action.json"
    if not pending_path.exists():
        raise TokenError("Invalid or expired selection. Run the command again.")
    with open(pending_path, "r", encoding="utf-8") as f:
        pending = json.load(f)

    if pending.get("token") != token:
        raise TokenError("Invalid or expired selection. Run the command again.")
    if pending.get("action") != action:
        raise TokenError("Invalid or expired selection. Run the command again.")
    if value not in pending.get("allowed_values", []):
        raise TokenError("Invalid or expired selection. Run the command again.")

    expires = pending.get("expires_at", "")
    try:
        exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
    except ValueError:
        raise TokenError("Invalid or expired selection. Run the command again.")
    if datetime.now(timezone.utc) > exp_dt:
        raise TokenError("Invalid or expired selection. Run the command again.")


def _consume_token(repo_path: str) -> None:
    pending_path = Path(repo_path) / ".devquest" / "pending-action.json"
    try:
        pending_path.unlink()
    except FileNotFoundError:
        pass


def apply(repo_path: str, action: str, value: str, token: str) -> str:
    """Validate token and apply mutation. Returns success message."""
    _validate_token(repo_path, action, value, token)

    state = devquest_state.load_state(repo_path)

    if action == "theme":
        state["settings"]["theme"] = value
        msg = f"Theme changed to {THEME_LABELS[value]}."
    elif action == "environment":
        state["settings"]["environment"] = value
        msg = f"Environment set to {ENVIRONMENT_LABELS[value]}."
    elif action == "display-mode":
        state["settings"]["display_mode"] = value
        msg = f"Display mode set to {DISPLAY_MODE_LABELS[value]}."
    elif action == "buy":
        msg = _apply_purchase(state, value)
    else:
        raise MutationError(f"Unknown action: {action}")

    devquest_state.save_state(repo_path, state)
    _consume_token(repo_path)
    return msg


def _apply_purchase(state: dict, item_id: str) -> str:
    # Filled in in Task 9.
    raise NotImplementedError("Shop purchase not yet implemented.")


def main():
    parser = argparse.ArgumentParser(description="DevQuest state mutator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--theme")
    group.add_argument("--environment")
    group.add_argument("--display-mode", dest="display_mode")
    group.add_argument("--buy")
    parser.add_argument("--token", required=True)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()

    if args.theme is not None:
        action, value = "theme", args.theme
    elif args.environment is not None:
        action, value = "environment", args.environment
    elif args.display_mode is not None:
        action, value = "display-mode", args.display_mode
    else:
        action, value = "buy", args.buy

    try:
        msg = apply(args.repo, action, value, args.token)
    except TokenError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except MutationError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(".devquest/state.json not found. Run /devquest-enable first.", file=sys.stderr)
        sys.exit(1)

    print(msg)
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_update_state.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/update-state.py tests/test_update_state.py
git commit -m "feat: add update-state.py with theme mutation and token validation"
```

---

## Task 4: Wire up `devquest-theme` skill

**Files:**
- Modify: `../devquest-theme/SKILL.md` (fully rewritten)

Note: this skill lives in a sibling directory, at `C:/Users/jacob_n3tltpd/.claude/skills/devquest-theme/SKILL.md`. From the `devquest` skill repo root this is `../devquest-theme/SKILL.md`.

- [ ] **Step 1: Read the current file to preserve the frontmatter description**

Run: `cat ../devquest-theme/SKILL.md` (or use the Read tool) and copy the frontmatter `name` and `description` fields.

- [ ] **Step 2: Rewrite the skill file to be a thin router**

Overwrite `../devquest-theme/SKILL.md` with (replace `<existing description>` with the current description verbatim):

```markdown
---
name: devquest-theme
description: <existing description>
---

# /devquest-theme

Change the DevQuest visual theme. The script layer owns all mutation and option content — this skill is a router only.

## Steps

1. Run: `python scripts/menu.py --for theme`.
2. Parse the JSON printed on stdout. Note the `token` field.
3. Call `AskUserQuestion` with the payload's `question`, `header`, `multiSelect`, and `options` fields passed through verbatim.
4. When the user answers, take the selected option's `value` and run:
   `python scripts/update-state.py --theme <value> --token <token>`
5. Print the script's stdout verbatim on success, or stderr verbatim on non-zero exit. Do not embellish or re-phrase.
6. Do not call `Edit` or `Write` on `.devquest/state.json`. All mutation flows through `update-state.py`.
```

- [ ] **Step 3: Commit**

```bash
git add ../devquest-theme/SKILL.md
git commit -m "refactor: make devquest-theme a thin script router"
```

---

## Task 5: Extend `menu.py` — settings router and sub-menus

**Files:**
- Modify: `scripts/menu.py`
- Modify: `tests/test_menu.py`

Note: the settings router (`--for settings`) must NOT write a pending-action file — it's a navigation step, not a mutation. The sub-menus (`--for settings-environment`, etc.) do write pending-action files, mapped to actions `environment`, `theme`, and `display-mode`.

- [ ] **Step 1: Add tests for settings router and sub-menus**

Append to `tests/test_menu.py`:

```python
class TestSettingsMenus(unittest.TestCase):
    def test_settings_router_no_pending_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            payload = menu.build_payload(tmp, "settings")
            self.assertEqual(len(payload["options"]), 3)
            self.assertEqual(payload["header"], "Settings")
            pending = Path(tmp) / ".devquest" / "pending-action.json"
            self.assertFalse(pending.exists())

    def test_settings_environment_writes_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            menu.build_payload(tmp, "settings-environment")
            pending_path = Path(tmp) / ".devquest" / "pending-action.json"
            self.assertTrue(pending_path.exists())
            with open(pending_path) as f:
                pending = json.load(f)
            self.assertEqual(pending["action"], "environment")
            self.assertEqual(set(pending["allowed_values"]), {"cli", "desktop"})

    def test_settings_display_mode_action_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            menu.build_payload(tmp, "settings-display-mode")
            with open(Path(tmp) / ".devquest" / "pending-action.json") as f:
                pending = json.load(f)
            self.assertEqual(pending["action"], "display-mode")

    def test_settings_theme_action_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            menu.build_payload(tmp, "settings-theme")
            with open(Path(tmp) / ".devquest" / "pending-action.json") as f:
                pending = json.load(f)
            self.assertEqual(pending["action"], "theme")
```

- [ ] **Step 2: Run new tests to verify they pass**

Existing `menu.py` (from Task 2) already has the `settings`, `settings-environment`, `settings-theme`, and `settings-display-mode` branches wired in. The pending-action write is skipped for bare `settings` because of the `if kind != "settings":` guard at the bottom of `build_payload`.

Run: `python -m pytest tests/test_menu.py -v`
Expected: all tests PASS (4 new + previous 2 = 6 total).

- [ ] **Step 3: Commit**

```bash
git add tests/test_menu.py
git commit -m "test: cover settings menus in menu.py"
```

---

## Task 6: `update-state.py` — environment and display-mode

**Files:**
- Modify: `tests/test_update_state.py`

The Task-3 `apply()` already implements `environment` and `display-mode`, so this task just confirms with tests.

- [ ] **Step 1: Add tests for environment and display-mode**

Append to `tests/test_update_state.py`:

```python
class TestEnvironmentUpdate(unittest.TestCase):
    def test_valid_environment_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            seed_pending(tmp, "environment", ["cli", "desktop"])
            msg = update.apply(tmp, action="environment", value="desktop", token="abc123")
            self.assertEqual(msg, "Environment set to Desktop.")
            state = state_mod.load_state(tmp)
            self.assertEqual(state["settings"]["environment"], "desktop")

    def test_environment_token_cross_action_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            seed_pending(tmp, "theme", ["fantasy", "scifi"])
            with self.assertRaises(update.TokenError):
                update.apply(tmp, action="environment", value="desktop", token="abc123")


class TestDisplayModeUpdate(unittest.TestCase):
    def test_valid_display_mode_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp)
            seed_pending(tmp, "display-mode", ["markdown", "html"])
            msg = update.apply(tmp, action="display-mode", value="html", token="abc123")
            self.assertEqual(msg, "Display mode set to HTML.")
            state = state_mod.load_state(tmp)
            self.assertEqual(state["settings"]["display_mode"], "html")
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_update_state.py -v`
Expected: all tests PASS (3 new + 7 previous = 10 total).

- [ ] **Step 3: Commit**

```bash
git add tests/test_update_state.py
git commit -m "test: cover environment and display-mode mutations"
```

---

## Task 7: Wire up `devquest-settings` skill

**Files:**
- Modify: `../devquest-settings/SKILL.md`

- [ ] **Step 1: Read current file for frontmatter description**

Use the Read tool on `../devquest-settings/SKILL.md`.

- [ ] **Step 2: Rewrite to a two-step thin router**

Overwrite `../devquest-settings/SKILL.md` with:

```markdown
---
name: devquest-settings
description: <existing description>
---

# /devquest-settings

View and change DevQuest settings. Two-step interaction: pick which setting, then pick the new value. All mutation goes through `update-state.py`.

## Steps

1. Run: `python scripts/menu.py --for settings`.
2. Parse the JSON. Call `AskUserQuestion` with `question`, `header`, `multiSelect`, `options`. The `settings` router does not issue a token — ignore the `token` field here.
3. The selected option's `value` is one of: `settings-environment`, `settings-theme`, `settings-display-mode`.
4. Run: `python scripts/menu.py --for <selected-value>`. Parse the JSON. Note the `token`.
5. Call `AskUserQuestion` again with the new payload.
6. When the user answers, run `update-state.py` with the flag that matches the sub-menu:
   - `settings-environment` → `python scripts/update-state.py --environment <value> --token <token>`
   - `settings-theme`       → `python scripts/update-state.py --theme <value> --token <token>`
   - `settings-display-mode`→ `python scripts/update-state.py --display-mode <value> --token <token>`
7. Print the script's stdout verbatim on success, or stderr verbatim on non-zero exit.
8. Do not call `Edit` or `Write` on `.devquest/state.json`.
```

- [ ] **Step 3: Commit**

```bash
git add ../devquest-settings/SKILL.md
git commit -m "refactor: make devquest-settings a thin script router"
```

---

## Task 8: `menu.py` — shop menu

**Files:**
- Modify: `scripts/menu.py`
- Modify: `tests/test_menu.py`

Owned one-time items are hidden from the shop menu (none currently flagged `one_time: true`, but the logic must exist). Unaffordable items stay visible with a `"— locked (need N gold)"` suffix appended to `description`. The `value` is the item `id`. The `allowed_values` in the pending token include ALL visible options (including unaffordable) — the gate on affordability happens in `update-state.py` so a stale token that used to be affordable still fails cleanly if gold dropped.

- [ ] **Step 1: Write failing tests for shop menu**

Append to `tests/test_menu.py`:

```python
class TestShopMenu(unittest.TestCase):
    def test_payload_has_all_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp, character={"gold": 100, "gold_spent": 0, "attributes": {"code_mastery": 0}, "active_buffs": [], "purchased_one_time_items": []})
            payload = menu.build_payload(tmp, "shop")
            self.assertEqual(payload["header"], "Shop")
            self.assertEqual(len(payload["options"]), 3)
            with open(Path(tmp) / ".devquest" / "pending-action.json") as f:
                pending = json.load(f)
            self.assertEqual(pending["action"], "buy")
            self.assertEqual(
                set(pending["allowed_values"]),
                {"code_mastery_plus_1", "code_xp_boost", "gold_rush"},
            )

    def test_unaffordable_items_marked(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp, character={"gold": 10, "gold_spent": 0, "attributes": {"code_mastery": 0}, "active_buffs": [], "purchased_one_time_items": []})
            payload = menu.build_payload(tmp, "shop")
            descriptions = {o["value"]: o["description"] for o in payload["options"]}
            self.assertIn("locked", descriptions["code_mastery_plus_1"])
            self.assertIn("locked", descriptions["code_xp_boost"])
            self.assertIn("locked", descriptions["gold_rush"])

    def test_description_includes_price(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_state(tmp, character={"gold": 100, "gold_spent": 0, "attributes": {"code_mastery": 0}, "active_buffs": [], "purchased_one_time_items": []})
            payload = menu.build_payload(tmp, "shop")
            desc = next(o["description"] for o in payload["options"] if o["value"] == "code_mastery_plus_1")
            self.assertIn("50", desc)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_menu.py::TestShopMenu -v`
Expected: FAIL with `NotImplementedError: Shop menu not yet implemented.`

- [ ] **Step 3: Replace `_shop_options` in `scripts/menu.py`**

Replace the existing stub:

```python
def _shop_options(state: dict, cfg: dict) -> list:
    raise NotImplementedError("Shop menu not yet implemented.")
```

with:

```python
def _shop_options(state: dict, cfg: dict) -> list:
    gold = state.get("character", {}).get("gold", 0)
    owned_one_time = set(state.get("character", {}).get("purchased_one_time_items", []))
    options = []
    for item in cfg["shop_items"]:
        if item.get("one_time") and item["id"] in owned_one_time:
            continue
        price = item["price"]
        base_desc = f"{price} gold — {item['description_short']}"
        if gold < price:
            desc = f"{base_desc} — locked (need {price - gold} more gold)"
        else:
            desc = base_desc
        options.append({"label": item["label"], "description": desc, "value": item["id"]})
    return options
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_menu.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/menu.py tests/test_menu.py
git commit -m "feat: add shop menu generation"
```

---

## Task 9: `update-state.py` — shop purchase

**Files:**
- Modify: `scripts/update-state.py`
- Modify: `tests/test_update_state.py`

The purchase logic follows `references/economy.md` rules 1-5 (the quest/achievement steps 6-7 are out of scope for this change — they stay in Claude's hands for now since they're not state mutations triggered by the purchase button directly; `track-commit.py` and quest claims handle those).

Required mutations on a successful purchase:

- `character.gold` -= price
- `character.gold_spent` += price
- `stats.items_purchased` += 1
- For `stat_boost`: `character.attributes[<attribute>]` += 1
- For `buff`: append `item["buff"]` dict (deep copy) to `character.active_buffs`
- For `one_time` items: append item id to `character.purchased_one_time_items` (create list if missing)

- [ ] **Step 1: Write failing tests for shop purchase**

Append to `tests/test_update_state.py`:

```python
class TestPurchase(unittest.TestCase):
    def _seed_shop_state(self, tmp, gold=200):
        state = {
            "settings": {"environment": "cli", "theme": "fantasy", "display_mode": "markdown"},
            "character": {
                "gold": gold,
                "gold_spent": 0,
                "attributes": {"code_mastery": 0},
                "active_buffs": [],
                "purchased_one_time_items": [],
            },
            "stats": {"items_purchased": 0},
        }
        state_mod.save_state(tmp, state)

    def test_stat_boost_purchase(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_shop_state(tmp, gold=100)
            seed_pending(tmp, "buy", ["code_mastery_plus_1", "code_xp_boost", "gold_rush"])
            msg = update.apply(tmp, action="buy", value="code_mastery_plus_1", token="abc123")
            self.assertEqual(msg, "Purchased Code Mastery +1. -50 gold (50 remaining).")
            state = state_mod.load_state(tmp)
            self.assertEqual(state["character"]["gold"], 50)
            self.assertEqual(state["character"]["gold_spent"], 50)
            self.assertEqual(state["character"]["attributes"]["code_mastery"], 1)
            self.assertEqual(state["stats"]["items_purchased"], 1)

    def test_buff_purchase(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_shop_state(tmp, gold=100)
            seed_pending(tmp, "buy", ["code_mastery_plus_1", "code_xp_boost", "gold_rush"])
            msg = update.apply(tmp, action="buy", value="code_xp_boost", token="abc123")
            self.assertEqual(msg, "Purchased Code XP Boost. -30 gold (70 remaining).")
            state = state_mod.load_state(tmp)
            self.assertEqual(len(state["character"]["active_buffs"]), 1)
            self.assertEqual(state["character"]["active_buffs"][0]["id"], "code_xp_boost")
            self.assertEqual(state["character"]["active_buffs"][0]["actions_remaining"], 10)

    def test_insufficient_gold_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_shop_state(tmp, gold=10)
            seed_pending(tmp, "buy", ["code_mastery_plus_1", "code_xp_boost", "gold_rush"])
            with self.assertRaises(update.MutationError) as ctx:
                update.apply(tmp, action="buy", value="code_mastery_plus_1", token="abc123")
            self.assertIn("Not enough gold", str(ctx.exception))
            state = state_mod.load_state(tmp)
            self.assertEqual(state["character"]["gold"], 10)
            # Token should NOT be consumed on failure — user can retry the pick
            pending_path = Path(tmp) / ".devquest" / "pending-action.json"
            self.assertTrue(pending_path.exists())

    def test_unknown_item_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_shop_state(tmp, gold=100)
            seed_pending(tmp, "buy", ["bogus"])
            with self.assertRaises(update.MutationError) as ctx:
                update.apply(tmp, action="buy", value="bogus", token="abc123")
            self.assertIn("Unknown item", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
```

Note: the insufficient-gold case deliberately does NOT consume the token. Rationale: the user picked a real option that passed the token gate, but failed the affordability gate. Letting them re-try without re-running the menu is friendlier. To implement this, `apply()` must only call `_consume_token` after a successful mutation, which requires restructuring slightly.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_update_state.py::TestPurchase -v`
Expected: 4 FAIL with `NotImplementedError: Shop purchase not yet implemented.`

- [ ] **Step 3: Replace `_apply_purchase` and restructure `apply` for failed-purchase token retention**

Replace the `_apply_purchase` stub:

```python
def _apply_purchase(state: dict, item_id: str) -> str:
    raise NotImplementedError("Shop purchase not yet implemented.")
```

with:

```python
def _apply_purchase(state: dict, item_id: str) -> str:
    import copy
    cfg = devquest_state.load_menus_config()
    item = next((i for i in cfg["shop_items"] if i["id"] == item_id), None)
    if item is None:
        raise MutationError(f"Unknown item: {item_id}.")

    price = item["price"]
    char = state.setdefault("character", {})
    gold = char.get("gold", 0)
    if gold < price:
        raise MutationError(f"Not enough gold (need {price}, have {gold}).")

    if item.get("one_time"):
        owned = char.setdefault("purchased_one_time_items", [])
        if item_id in owned:
            raise MutationError("Item already owned.")
        owned.append(item_id)

    char["gold"] = gold - price
    char["gold_spent"] = char.get("gold_spent", 0) + price
    state.setdefault("stats", {})["items_purchased"] = state["stats"].get("items_purchased", 0) + 1

    if item["type"] == "stat_boost":
        attr = item["attribute"]
        attrs = char.setdefault("attributes", {})
        attrs[attr] = attrs.get(attr, 0) + 1
    elif item["type"] == "buff":
        buffs = char.setdefault("active_buffs", [])
        buffs.append(copy.deepcopy(item["buff"]))
    else:
        raise MutationError(f"Unknown item type: {item['type']}")

    return f"Purchased {item['label']}. -{price} gold ({char['gold']} remaining)."
```

Update `apply()` to defer token consumption until after a successful mutation. Replace the body of `apply` in `scripts/update-state.py` with:

```python
def apply(repo_path: str, action: str, value: str, token: str) -> str:
    """Validate token and apply mutation. Returns success message."""
    _validate_token(repo_path, action, value, token)

    state = devquest_state.load_state(repo_path)

    if action == "theme":
        state["settings"]["theme"] = value
        msg = f"Theme changed to {THEME_LABELS[value]}."
    elif action == "environment":
        state["settings"]["environment"] = value
        msg = f"Environment set to {ENVIRONMENT_LABELS[value]}."
    elif action == "display-mode":
        state["settings"]["display_mode"] = value
        msg = f"Display mode set to {DISPLAY_MODE_LABELS[value]}."
    elif action == "buy":
        msg = _apply_purchase(state, value)  # raises MutationError on failure, before save
    else:
        raise MutationError(f"Unknown action: {action}")

    devquest_state.save_state(repo_path, state)
    _consume_token(repo_path)
    return msg
```

(The existing Task-3 body is already this shape; verify `_apply_purchase` is called BEFORE `save_state` and `_consume_token` — so a MutationError from `_apply_purchase` leaves state unchanged AND the token intact.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_update_state.py -v`
Expected: all tests PASS (4 new + 10 previous = 14 total).

- [ ] **Step 5: Commit**

```bash
git add scripts/update-state.py tests/test_update_state.py
git commit -m "feat: add shop purchase handling with gold check"
```

---

## Task 10: Wire up `devquest-shop` skill

**Files:**
- Modify: `../devquest-shop/SKILL.md`

- [ ] **Step 1: Read current file for frontmatter description**

Use the Read tool on `../devquest-shop/SKILL.md`.

- [ ] **Step 2: Rewrite as a thin router**

Overwrite `../devquest-shop/SKILL.md` with:

```markdown
---
name: devquest-shop
description: <existing description>
---

# /devquest-shop

Browse and buy items from the DevQuest shop. The script determines catalog, pricing, affordability, and purchase rules.

## Steps

1. Run: `python scripts/menu.py --for shop`.
2. Parse the JSON. Note the `token`.
3. Call `AskUserQuestion` with the payload's `question`, `header`, `multiSelect`, and `options`. Unaffordable items are shown with "— locked (need N gold)" in their description; the user can still select them, but the purchase will be rejected by the script.
4. When the user picks, run: `python scripts/update-state.py --buy <value> --token <token>`.
5. Print the script's stdout verbatim on success, or stderr verbatim on non-zero exit. Examples of expected failure messages:
   - `Not enough gold (need 50, have 30).`
   - `Item already owned.`
   In these cases, do not retry automatically — let the user decide whether to run `/devquest-shop` again.
6. Do not call `Edit` or `Write` on `.devquest/state.json`.
```

- [ ] **Step 3: Commit**

```bash
git add ../devquest-shop/SKILL.md
git commit -m "refactor: make devquest-shop a thin script router"
```

---

## Task 11: Update `setup-permissions.py`

**Files:**
- Modify: `scripts/setup-permissions.py:23-31`
- Modify: `tests/test_setup_permissions.py`

- [ ] **Step 1: Update test to expect the two new entries**

Read `tests/test_setup_permissions.py` and add this test case at the end of `TestInstallPermissions` class (right after the existing tests):

```python
    def test_includes_new_mutation_permissions(self):
        self.assertIn("Bash(python *scripts/menu.py*)", perms.DEVQUEST_PERMISSIONS)
        self.assertIn("Bash(python *scripts/update-state.py*)", perms.DEVQUEST_PERMISSIONS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_setup_permissions.py::TestInstallPermissions::test_includes_new_mutation_permissions -v`
Expected: FAIL with AssertionError.

- [ ] **Step 3: Add the two entries in `scripts/setup-permissions.py`**

In `scripts/setup-permissions.py`, change lines 23-31:

```python
DEVQUEST_PERMISSIONS = [
    "Bash(python *scripts/check-gold-gate.py*)",
    "Bash(python *scripts/install-hook.py*)",
    "Bash(python *scripts/track-commit.py*)",
    "Bash(python *scripts/render-html.py*)",
    "Bash(python *scripts/setup-permissions.py*)",
    "Read(.devquest/**)",
    "Edit(.devquest/**)",
]
```

to:

```python
DEVQUEST_PERMISSIONS = [
    "Bash(python *scripts/check-gold-gate.py*)",
    "Bash(python *scripts/install-hook.py*)",
    "Bash(python *scripts/track-commit.py*)",
    "Bash(python *scripts/render-html.py*)",
    "Bash(python *scripts/setup-permissions.py*)",
    "Bash(python *scripts/menu.py*)",
    "Bash(python *scripts/update-state.py*)",
    "Read(.devquest/**)",
    "Edit(.devquest/**)",
]
```

- [ ] **Step 4: Run all permission tests to verify they pass**

Run: `python -m pytest tests/test_setup_permissions.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/setup-permissions.py tests/test_setup_permissions.py
git commit -m "feat: allow menu.py and update-state.py in installed permissions"
```

---

## Task 12: Update main `SKILL.md` router table

**Files:**
- Modify: `SKILL.md:37-43` (the slash-command table)

- [ ] **Step 1: Read the current router table**

Use the Read tool on `SKILL.md` at lines 30-55 to see the current table.

- [ ] **Step 2: Update three rows**

Replace the rows for `/devquest-theme`, `/devquest-settings`, and `/devquest-shop` so their "content source" column points at the scripts instead of references.

Original rows (for reference):

```
| `/devquest-shop` | `references/economy.md` | Show catalog with prices and gold balance, or process a numbered purchase |
| `/devquest-theme` | `references/themes.md` | Present 4 numbered theme options, update `settings.theme`, confirm |
| `/devquest-settings` | — | Show current settings table, offer numbered options to change environment, theme, or display mode |
```

Replace with:

```
| `/devquest-shop` | `scripts/menu.py`, `scripts/update-state.py` | Run menu.py --for shop, AskUserQuestion, update-state.py --buy |
| `/devquest-theme` | `scripts/menu.py`, `scripts/update-state.py` | Run menu.py --for theme, AskUserQuestion, update-state.py --theme |
| `/devquest-settings` | `scripts/menu.py`, `scripts/update-state.py` | Two-step: menu.py --for settings, then --for settings-<field>, update-state.py --<field> |
```

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "docs: update router table to point at mutation scripts"
```

---

## Task 13: Full test-suite run and lint

**Files:** (none modified)

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: all tests PASS.

- [ ] **Step 2: Spot-check the scripts run from the CLI end-to-end**

These are **sanity checks, not manual acceptance tests** — the real manual checklist (below) must be run in a real project by the user.

In a throwaway directory:

```bash
mkdir -p /tmp/devquest-sanity/.devquest
cp /path/to/devquest/tests/fixtures/minimal_state.json /tmp/devquest-sanity/.devquest/state.json  # or write one inline
cd /tmp/devquest-sanity
python /path/to/devquest/scripts/menu.py --for theme
# Expect JSON with 4 options on stdout
python /path/to/devquest/scripts/update-state.py --theme scifi --token <token-from-payload>
# Expect "Theme changed to Sci-Fi."
cat .devquest/state.json
# Expect "theme": "scifi"
```

If the sanity check fails, fix the underlying script and re-run the test suite.

---

## Manual acceptance checklist (user runs in a real project)

This MUST pass before any push to remote. Per the project's memory rule: unit tests don't prove e2e; manual testing does.

1. Enable DevQuest in a scratch project: `/devquest-enable`.
2. Run `/devquest-theme` → a clickable picker appears in the chat → pick "Sci-Fi" → confirmation printed → `.devquest/state.json` has `"theme": "scifi"` → no JSON diff visible in transcript.
3. Run `/devquest-settings` → first picker with Environment/Theme/Display → pick Display → second picker with Markdown/HTML → pick HTML → confirmation → state updated.
4. Run `/devquest-shop` with enough gold → pick Code XP Boost → confirmation → gold drops by 30 → `active_buffs` contains the buff.
5. Spend down to <25 gold, run `/devquest-shop` → pick an item → error message printed, state unchanged, Claude does not retry.
6. Run `/devquest-theme` twice in quick succession, picking on the second invocation → second menu's choice applies, first token is overwritten and does not cause leaks.
7. Run `/devquest-theme`, dismiss the picker (Esc), run `/devquest-theme` again → second run succeeds (stale token is overwritten by the new menu call).

After each step, open `.devquest/state.json` and visually confirm the expected field changed — and no other fields were mutated.

Only after all 7 pass: `git push -u origin feat/script-based-state-mutations` and open a PR.

---

## Self-review notes

- **Spec coverage:** Scope (theme/settings/shop) → Tasks 2-10. `menu.py` contract → Tasks 2, 5, 8. `update-state.py` contract → Tasks 3, 6, 9. Enforcement/tokens → Tasks 2-3 (baseline), 9 (failed-mutation retention). Permissions → Task 11. Skill file changes → Tasks 4, 7, 10, 12. Testing strategy → tests scattered through each implementation task, plus Task 13 and the manual checklist. All spec sections covered.
- **Placeholder scan:** None. `<existing description>` in skill-file rewrites is explicit about what to copy from the current file (first step of each wiring task).
- **Type consistency:** `devquest_state` (helper module, no hyphen) vs `update-state` / `menu` (script names with hyphens). `apply(repo_path, action, value, token)` signature consistent between Task 3 and Task 9 rework. Action names (`theme`, `environment`, `display-mode`, `buy`) consistent between `menu.py` `ACTION_NAMES` (Task 2) and `update-state.py` `apply()` (Task 3).
