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
