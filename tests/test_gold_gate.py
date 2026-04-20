#!/usr/bin/env python3
"""Tests for the DevQuest Code Generation Gold Gate."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from importlib import import_module

gate = import_module("check-gold-gate")


def make_state(gold=100, enabled=True, buffs=None):
    """Create a minimal DevQuest state dict for testing."""
    return {
        "enabled": enabled,
        "character": {
            "gold": gold,
            "gold_spent": 0,
            "active_buffs": buffs or [],
        },
    }


def write_state(tmp_dir, state):
    """Write state to a temp file and return the path."""
    path = os.path.join(tmp_dir, "state.json")
    with open(path, "w") as f:
        json.dump(state, f)
    return path


class TestComputeCost(unittest.TestCase):
    def test_cost_equals_lines(self):
        self.assertEqual(gate.compute_cost(10), 10)
        self.assertEqual(gate.compute_cost(35), 35)
        self.assertEqual(gate.compute_cost(1), 1)

    def test_cost_rounds_up(self):
        self.assertEqual(gate.compute_cost(0), 0)
        self.assertEqual(gate.compute_cost(100), 100)


class TestEstimateLines(unittest.TestCase):
    def test_size_hints(self):
        self.assertEqual(gate.estimate_lines("small"), 10)
        self.assertEqual(gate.estimate_lines("medium"), 35)
        self.assertEqual(gate.estimate_lines("large"), 75)
        self.assertEqual(gate.estimate_lines("xlarge"), 150)

    def test_case_insensitive(self):
        self.assertEqual(gate.estimate_lines("Small"), 10)
        self.assertEqual(gate.estimate_lines("LARGE"), 75)

    def test_unknown_hint_defaults_to_medium(self):
        self.assertEqual(gate.estimate_lines("tiny"), 35)

    def test_integer_passthrough(self):
        self.assertEqual(gate.estimate_lines(42), 42)


class TestHasGoldRushBuff(unittest.TestCase):
    def test_no_buffs(self):
        state = make_state(buffs=[])
        self.assertFalse(gate.has_gold_rush_buff(state))

    def test_with_gold_rush(self):
        state = make_state(buffs=[
            {"id": "gold_rush", "name": "Gold Rush", "actions_remaining": 5,
             "effect": {"target": "all_gold", "multiplier": 1.25}}
        ])
        self.assertTrue(gate.has_gold_rush_buff(state))

    def test_with_other_buff_only(self):
        state = make_state(buffs=[
            {"id": "code_xp_boost", "name": "Code XP Boost", "actions_remaining": 3,
             "effect": {"target": "code_xp", "multiplier": 1.5}}
        ])
        self.assertFalse(gate.has_gold_rush_buff(state))


class TestCheckGate(unittest.TestCase):
    def test_sufficient_gold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=100))
            result, code = gate.check_gate(path, 50)
            self.assertEqual(code, 0)
            self.assertTrue(result["sufficient"])
            self.assertEqual(result["cost"], 50)
            self.assertEqual(result["balance"], 100)

    def test_exact_gold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=35))
            result, code = gate.check_gate(path, 35)
            self.assertEqual(code, 0)
            self.assertTrue(result["sufficient"])

    def test_insufficient_gold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=10))
            result, code = gate.check_gate(path, 50)
            self.assertEqual(code, 1)
            self.assertFalse(result["sufficient"])
            self.assertEqual(result["cost"], 50)
            self.assertEqual(result["balance"], 10)

    def test_zero_gold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=0))
            result, code = gate.check_gate(path, 10)
            self.assertEqual(code, 1)
            self.assertFalse(result["sufficient"])

    def test_disabled_devquest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=999, enabled=False))
            result, code = gate.check_gate(path, 10)
            self.assertEqual(code, 2)
            self.assertTrue(result["skipped"])

    def test_missing_state_file(self):
        result, code = gate.check_gate("/nonexistent/path/state.json", 10)
        self.assertEqual(code, 2)
        self.assertTrue(result["skipped"])

    def test_reports_gold_rush_buff(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = make_state(gold=100, buffs=[
                {"id": "gold_rush", "name": "Gold Rush", "actions_remaining": 5,
                 "effect": {"target": "all_gold", "multiplier": 1.25}}
            ])
            path = write_state(tmp, state)
            result, code = gate.check_gate(path, 10)
            self.assertEqual(code, 0)
            self.assertTrue(result["has_gold_rush"])

    def test_no_gold_rush_buff(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=100))
            result, code = gate.check_gate(path, 10)
            self.assertFalse(result["has_gold_rush"])


class TestDeductGold(unittest.TestCase):
    def test_deducts_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = make_state(gold=100)
            path = write_state(tmp, state)
            new_balance = gate.deduct_gold(path, state, 30)
            self.assertEqual(new_balance, 70)
            self.assertEqual(state["character"]["gold_spent"], 30)

            reloaded = gate.load_state(path)
            self.assertEqual(reloaded["character"]["gold"], 70)
            self.assertEqual(reloaded["character"]["gold_spent"], 30)

    def test_deduct_all_gold(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = make_state(gold=50)
            path = write_state(tmp, state)
            new_balance = gate.deduct_gold(path, state, 50)
            self.assertEqual(new_balance, 0)

    def test_deduct_accumulates_gold_spent(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = make_state(gold=200)
            state["character"]["gold_spent"] = 100
            path = write_state(tmp, state)
            gate.deduct_gold(path, state, 50)
            self.assertEqual(state["character"]["gold_spent"], 150)


class TestCLI(unittest.TestCase):
    """Test the script as a CLI command."""

    def _run(self, state_path, lines, deduct=False):
        cmd = [sys.executable, str(SCRIPT_DIR / "check-gold-gate.py"),
               "--state", state_path, "--lines", str(lines)]
        if deduct:
            cmd.append("--deduct")
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def test_cli_sufficient(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=100))
            result = self._run(path, 50)
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertTrue(data["sufficient"])
            self.assertEqual(data["cost"], 50)

    def test_cli_insufficient(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=10))
            result = self._run(path, 50)
            self.assertEqual(result.returncode, 1)
            data = json.loads(result.stdout)
            self.assertFalse(data["sufficient"])

    def test_cli_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(enabled=False))
            result = self._run(path, 10)
            self.assertEqual(result.returncode, 2)

    def test_cli_missing_file(self):
        result = self._run("/nonexistent/state.json", 10)
        self.assertEqual(result.returncode, 2)

    def test_cli_deduct(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=100))
            result = self._run(path, 30, deduct=True)
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertTrue(data["deducted"])
            self.assertEqual(data["new_balance"], 70)

            reloaded = gate.load_state(path)
            self.assertEqual(reloaded["character"]["gold"], 70)

    def test_cli_deduct_insufficient_does_not_deduct(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=10))
            result = self._run(path, 50, deduct=True)
            self.assertEqual(result.returncode, 1)
            data = json.loads(result.stdout)
            self.assertNotIn("deducted", data)

            reloaded = gate.load_state(path)
            self.assertEqual(reloaded["character"]["gold"], 10)

    def test_cli_size_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_state(tmp, make_state(gold=100))
            result = self._run(path, "medium")
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertEqual(data["cost"], 35)


if __name__ == "__main__":
    unittest.main()
