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
