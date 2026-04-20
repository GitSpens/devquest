#!/usr/bin/env python3
"""
DevQuest Post-Commit Hook Installer

Installs (or updates) the DevQuest post-commit hook in a git repository.
Idempotent — safe to run multiple times.

Usage:
    python install-hook.py --repo <path-to-repo> --theme <theme-name>
    python install-hook.py --repo <path-to-repo> --uninstall

Exit codes:
    0 — success
    1 — error (not a git repo, etc.)
"""

import argparse
import os
import stat
import subprocess
import sys
from pathlib import Path

BEGIN_MARKER = "# --- BEGIN DevQuest hook — do not remove ---"
END_MARKER = "# --- END DevQuest hook ---"
SHEBANG = "#!/bin/bash"

SCRIPT_DIR = Path(__file__).resolve().parent
TRACK_SCRIPT = SCRIPT_DIR / "track-commit.py"


def get_git_hooks_dir(repo_path):
    """Find the hooks directory for a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, cwd=repo_path, timeout=5
        )
        if result.returncode != 0:
            return None
        git_dir = result.stdout.strip()
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(repo_path, git_dir)
        return os.path.join(git_dir, "hooks")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def build_hook_block(theme):
    """Build the DevQuest hook block content."""
    track_path = str(TRACK_SCRIPT).replace("\\", "/")
    return f"""{BEGIN_MARKER}
DEVQUEST_SCRIPT="{track_path}"
if command -v python3 &>/dev/null; then
    python3 "$DEVQUEST_SCRIPT" --state ".devquest/state.json" --theme "{theme}" 2>/dev/null || true
elif command -v python &>/dev/null; then
    python "$DEVQUEST_SCRIPT" --state ".devquest/state.json" --theme "{theme}" 2>/dev/null || true
fi
{END_MARKER}"""


def read_hook_file(hook_path):
    """Read existing hook file, return content or None."""
    try:
        with open(hook_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def remove_devquest_block(content):
    """Remove existing DevQuest block from hook content."""
    if BEGIN_MARKER not in content:
        return content
    lines = content.splitlines(keepends=True)
    result = []
    skipping = False
    for line in lines:
        if BEGIN_MARKER in line:
            skipping = True
            continue
        if END_MARKER in line:
            skipping = False
            continue
        if not skipping:
            result.append(line)
    return "".join(result).rstrip("\n")


def install_hook(repo_path, theme):
    """Install or update the DevQuest post-commit hook. Returns (success, message)."""
    hooks_dir = get_git_hooks_dir(repo_path)
    if hooks_dir is None:
        return False, "Not a git repository"

    os.makedirs(hooks_dir, exist_ok=True)
    hook_path = os.path.join(hooks_dir, "post-commit")
    existing = read_hook_file(hook_path)
    hook_block = build_hook_block(theme)

    if existing is None:
        content = SHEBANG + "\n\n" + hook_block + "\n"
    elif BEGIN_MARKER in existing:
        cleaned = remove_devquest_block(existing)
        content = cleaned + "\n\n" + hook_block + "\n"
    else:
        content = existing.rstrip("\n") + "\n\n" + hook_block + "\n"

    with open(hook_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    try:
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC)
    except OSError:
        pass

    return True, f"Hook installed at {hook_path}"


def uninstall_hook(repo_path):
    """Remove the DevQuest block from post-commit hook. Returns (success, message)."""
    hooks_dir = get_git_hooks_dir(repo_path)
    if hooks_dir is None:
        return False, "Not a git repository"

    hook_path = os.path.join(hooks_dir, "post-commit")
    existing = read_hook_file(hook_path)

    if existing is None or BEGIN_MARKER not in existing:
        return True, "No DevQuest hook found — nothing to remove"

    cleaned = remove_devquest_block(existing)
    stripped = cleaned.strip()

    if not stripped or stripped == SHEBANG:
        os.remove(hook_path)
        return True, "Hook file removed (was DevQuest-only)"
    else:
        with open(hook_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(cleaned.rstrip("\n") + "\n")
        return True, "DevQuest block removed, other hooks preserved"


def main():
    parser = argparse.ArgumentParser(description="DevQuest hook installer")
    parser.add_argument("--repo", required=True, help="Path to git repository")
    parser.add_argument("--theme", default="fantasy", help="Theme name for notifications")
    parser.add_argument("--uninstall", action="store_true", help="Remove the DevQuest hook")
    args = parser.parse_args()

    if args.uninstall:
        success, message = uninstall_hook(args.repo)
    else:
        success, message = install_hook(args.repo, args.theme)

    print(message)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
