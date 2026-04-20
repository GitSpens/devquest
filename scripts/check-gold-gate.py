#!/usr/bin/env python3
"""
DevQuest Code Generation Gold Gate

Checks whether the player can afford to generate code and outputs
the cost, balance, and verdict. Used by the DevQuest skill to enforce
the gold gate before Claude generates code.

Usage:
    python check-gold-gate.py --state <path-to-state.json> --lines <estimated-lines>

Exit codes:
    0 — sufficient gold (proceed after user confirmation)
    1 — insufficient gold (block generation)
    2 — DevQuest not enabled or state missing (skip gate silently)

Output (JSON on stdout):
    {"cost": 35, "balance": 150, "sufficient": true, "has_gold_rush": false}
"""

import argparse
import json
import math
import sys


def load_state(state_path):
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def estimate_lines(size_hint):
    """Map a size hint string to estimated lines, or pass through an int."""
    if isinstance(size_hint, int):
        return size_hint
    hints = {"small": 10, "medium": 35, "large": 75, "xlarge": 150}
    return hints.get(size_hint.lower(), 35)


def compute_cost(lines):
    return math.ceil(lines * 1.0)


def has_gold_rush_buff(state):
    buffs = state.get("character", {}).get("active_buffs", [])
    return any(b.get("id") == "gold_rush" for b in buffs)


def deduct_gold(state_path, state, cost):
    """Deduct gold from state and write back. Returns updated balance."""
    character = state["character"]
    character["gold"] = character.get("gold", 0) - cost
    character["gold_spent"] = character.get("gold_spent", 0) + cost
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return character["gold"]


def check_gate(state_path, lines):
    """Check gold gate. Returns (result_dict, exit_code)."""
    state = load_state(state_path)
    if state is None or not state.get("enabled", False):
        return {"skipped": True, "reason": "DevQuest not enabled"}, 2

    cost = compute_cost(lines)
    balance = state.get("character", {}).get("gold", 0)
    sufficient = balance >= cost
    gold_rush = has_gold_rush_buff(state)

    result = {
        "cost": cost,
        "balance": balance,
        "sufficient": sufficient,
        "has_gold_rush": gold_rush,
    }
    return result, 0 if sufficient else 1


def main():
    parser = argparse.ArgumentParser(description="DevQuest gold gate check")
    parser.add_argument("--state", required=True, help="Path to .devquest/state.json")
    parser.add_argument("--lines", required=True, help="Estimated lines (int or small/medium/large/xlarge)")
    parser.add_argument("--deduct", action="store_true", help="Actually deduct gold (use after user confirms)")
    args = parser.parse_args()

    try:
        lines = int(args.lines)
    except ValueError:
        lines = estimate_lines(args.lines)

    result, exit_code = check_gate(args.state, lines)

    if args.deduct and exit_code == 0:
        state = load_state(args.state)
        cost = compute_cost(lines)
        new_balance = deduct_gold(args.state, state, cost)
        result["deducted"] = True
        result["new_balance"] = new_balance

    print(json.dumps(result))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
