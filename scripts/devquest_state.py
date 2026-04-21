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
