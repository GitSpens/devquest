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


if __name__ == "__main__":
    unittest.main()
