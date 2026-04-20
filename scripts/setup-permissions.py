#!/usr/bin/env python3
"""
DevQuest Permission Installer

Adds (or removes) DevQuest permission entries in a project's
.claude/settings.local.json so all DevQuest operations run without
per-action approval prompts.

Usage:
    python setup-permissions.py --repo <path-to-project>
    python setup-permissions.py --repo <path-to-project> --uninstall

Exit codes:
    0 — success
    1 — error
"""

import argparse
import json
import os
import sys

DEVQUEST_PERMISSIONS = [
    "Bash(python *scripts/check-gold-gate.py*)",
    "Bash(python *scripts/install-hook.py*)",
    "Bash(python *scripts/track-commit.py*)",
    "Bash(python *scripts/render-html.py*)",
    "Bash(python *scripts/setup-permissions.py*)",
    "Read(.devquest/**)",
    "Edit(.devquest/**)",
]


def load_settings(settings_path):
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save_settings(settings_path, settings):
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")


def install_permissions(repo_path):
    """Add DevQuest permissions to .claude/settings.local.json. Returns (success, message)."""
    settings_path = os.path.join(repo_path, ".claude", "settings.local.json")
    settings = load_settings(settings_path)

    permissions = settings.setdefault("permissions", {})
    allow = permissions.setdefault("allow", [])

    added = 0
    for perm in DEVQUEST_PERMISSIONS:
        if perm not in allow:
            allow.append(perm)
            added += 1

    save_settings(settings_path, settings)
    return True, f"Permissions installed ({added} added, {len(DEVQUEST_PERMISSIONS) - added} already present)"


def uninstall_permissions(repo_path):
    """Remove DevQuest permissions from .claude/settings.local.json. Returns (success, message)."""
    settings_path = os.path.join(repo_path, ".claude", "settings.local.json")
    settings = load_settings(settings_path)

    permissions = settings.get("permissions", {})
    allow = permissions.get("allow", [])

    removed = 0
    for perm in DEVQUEST_PERMISSIONS:
        if perm in allow:
            allow.remove(perm)
            removed += 1

    if not allow:
        permissions.pop("allow", None)
    if not permissions:
        settings.pop("permissions", None)

    save_settings(settings_path, settings)
    return True, f"Permissions removed ({removed} entries)"


def main():
    parser = argparse.ArgumentParser(description="DevQuest permission installer")
    parser.add_argument("--repo", required=True, help="Path to project root")
    parser.add_argument("--uninstall", action="store_true", help="Remove DevQuest permissions")
    args = parser.parse_args()

    if args.uninstall:
        success, message = uninstall_permissions(args.repo)
    else:
        success, message = install_permissions(args.repo)

    print(message)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
