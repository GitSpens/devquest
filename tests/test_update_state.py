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
