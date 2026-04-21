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
