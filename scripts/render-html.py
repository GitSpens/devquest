#!/usr/bin/env python3
"""
DevQuest HTML Dashboard Renderer

Usage:
    python render-html.py --state <path> --theme <name> --output <path>

Reads a DevQuest state.json file and renders an HTML dashboard using the
assets/dashboard.html template.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XP_THRESHOLDS = [0, 100, 250, 500, 800, 1200, 1800, 2500, 3500, 5000,
                 7000, 9500, 12500, 16000, 20000, 25000, 31000, 38000, 46000, 55000]

LEVEL_TITLES = {
    "fantasy": [
        "Apprentice", "Squire", "Knight", "Paladin", "Wizard",
        "Sorcerer", "Warlock", "Archmage", "Champion", "Legend",
        "Mythic Knight", "Dragon Slayer", "Sage", "Archon", "Demigod",
        "Titan", "Elder God", "Primordial", "Eternal", "Ascended",
    ],
    "scifi": [
        "Cadet", "Ensign", "Engineer", "Lieutenant", "Commander",
        "Captain", "Major", "Colonel", "Admiral", "Fleet Admiral",
        "Commodore Prime", "Star Marshal", "Sector Commander", "Galaxy Admiral", "Fleet Sovereign",
        "Void Walker", "Quantum Lord", "Singularity", "Transcendent", "Ascended",
    ],
    "retro": [
        "Noob", "Rookie", "Pro", "Veteran", "Elite",
        "Master", "Legend", "Mythic", "Godlike", "Transcendent",
        "Pixel Lord", "Bit Crusher", "Glitch King", "ROM Hacker", "Cartridge God",
        "Console Titan", "Arcade Phantom", "8-Bit Deity", "Final Boss", "Game Over",
    ],
    "minimalist": [f"L{i}" for i in range(1, 21)],
}

QUEST_NAMES = {
    "1":  "First Blood",
    "2":  "Centurion",
    "3":  "Thousand Lines",
    "4":  "Test Pilot",
    "5":  "Test Commander",
    "6":  "Bug Squasher",
    "7":  "Exterminator",
    "8":  "Scribe",
    "9":  "Librarian",
    "10": "Well Rounded",
    "11": "Shopaholic",
    "12": "Code Miser",
}

QUEST_TARGETS = {
    "1":  10,
    "2":  100,
    "3":  1000,
    "4":  5,
    "5":  25,
    "6":  3,
    "7":  15,
    "8":  5,
    "9":  25,
    "10": 4,
    "11": 5,
    "12": 500,
}


# ---------------------------------------------------------------------------
# Progression helpers
# ---------------------------------------------------------------------------

def calculate_level(total_xp: int) -> int:
    """Return the current level (1-20) for the given total XP."""
    level = 1
    for i, threshold in enumerate(XP_THRESHOLDS):
        if total_xp >= threshold:
            level = i + 1
    return level


def xp_progress(total_xp: int) -> tuple[int, int, float]:
    """Return (progress_in_level, xp_needed_for_level, percent)."""
    level = calculate_level(total_xp)
    if level >= len(XP_THRESHOLDS):
        # Max level
        return total_xp - XP_THRESHOLDS[-1], 0, 100.0

    current_threshold = XP_THRESHOLDS[level - 1]
    next_threshold = XP_THRESHOLDS[level]
    level_span = next_threshold - current_threshold
    progress = total_xp - current_threshold
    percent = round((progress / level_span) * 100, 1) if level_span > 0 else 100.0
    return progress, level_span, percent


def get_level_title(theme: str, level: int) -> str:
    """Return the display title for a given theme and level."""
    titles = LEVEL_TITLES.get(theme, LEVEL_TITLES["minimalist"])
    idx = max(0, min(level - 1, len(titles) - 1))
    return titles[idx]


# ---------------------------------------------------------------------------
# HTML fragment builders
# ---------------------------------------------------------------------------

def _escape(text: str) -> str:
    """Minimal HTML escaping."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def build_achievements_html(achievements: dict) -> str:
    """Build <li> items for the achievements section."""
    if not achievements:
        return '<li class="achievement empty">No achievements yet</li>'

    items = []
    for key, value in achievements.items():
        # value may be a bool, a timestamp string, or a dict with an 'unlocked_at' key
        if isinstance(value, dict):
            unlocked = value.get("unlocked", True)
            label = value.get("name", key.replace("_", " ").title())
        else:
            unlocked = bool(value)
            label = key.replace("_", " ").title()

        if unlocked:
            items.append(
                f'<li class="achievement unlocked">'
                f'<span class="achievement-icon">&#9733;</span>'
                f'<span class="achievement-name">{_escape(label)}</span>'
                f'</li>'
            )

    if not items:
        return '<li class="achievement empty">No achievements yet</li>'
    return "\n".join(items)


def build_weekly_stats_html(weekly_stats: dict) -> str:
    """Build the weekly stats grid."""
    labels = {
        "weekly_xp_earned":            "XP Earned",
        "weekly_gold_earned":          "Gold Earned",
        "weekly_lines_written":        "Lines Written",
        "weekly_tests_run":            "Tests Run",
        "weekly_bugs_fixed":           "Bugs Fixed",
        "weekly_functions_documented": "Functions Documented",
        "weekly_quests_completed":     "Quests Completed",
    }

    items = []
    for key, label in labels.items():
        value = weekly_stats.get(key, 0)
        items.append(
            f'<div class="stat-card">'
            f'<span class="stat-value">{_escape(value)}</span>'
            f'<span class="stat-label">{_escape(label)}</span>'
            f'</div>'
        )

    week_start = weekly_stats.get("week_start", "")
    header = f'<p class="week-label">Week of {_escape(week_start)}</p>' if week_start else ""
    return header + '<div class="stats-grid">' + "\n".join(items) + "</div>"


def build_attributes_html(attributes: dict) -> str:
    """Build the attributes list."""
    display_names = {
        "code_mastery":  "Code Mastery",
        "debugging":     "Debugging",
        "documentation": "Documentation",
    }
    descriptions = {
        "code_mastery":  "+3% gold per level from writing code",
        "debugging":     "+10% XP per level from bug fixes",
        "documentation": "+5% XP and +5% gold per level from docs",
    }

    items = []
    for key, display in display_names.items():
        level = attributes.get(key, 0)
        desc = descriptions.get(key, "")
        items.append(
            f'<li class="attribute">'
            f'<span class="attribute-name">{_escape(display)}</span>'
            f'<span class="attribute-level">Lv. {_escape(level)}</span>'
            f'<span class="attribute-desc">{_escape(desc)}</span>'
            f'</li>'
        )
    return "\n".join(items)


def build_buffs_html(active_buffs: list) -> str:
    """Build the buffs list or a 'no buffs' notice."""
    if not active_buffs:
        return '<p class="no-buffs">No active buffs</p>'

    items = []
    for buff in active_buffs:
        name = buff.get("name", "Unknown Buff")
        remaining = buff.get("actions_remaining", 0)
        items.append(
            f'<li class="buff">'
            f'<span class="buff-name">{_escape(name)}</span>'
            f'<span class="buff-remaining">{_escape(remaining)} action{"s" if remaining != 1 else ""} remaining</span>'
            f'</li>'
        )
    return "<ul class=\"buff-list\">" + "\n".join(items) + "</ul>"


def _quest_bar(progress: int, target: int, width: int = 12) -> str:
    """Return an HTML progress bar for a quest."""
    if target <= 0:
        filled = width
    else:
        filled = min(width, math.floor(progress / target * width))
    empty = width - filled
    bar_inner = "=" * filled + "-" * empty
    pct = min(100, round(progress / target * 100)) if target > 0 else 100
    return (
        f'<div class="quest-bar" title="{_escape(progress)}/{_escape(target)}">'
        f'<div class="quest-bar-fill" style="width:{pct}%"></div>'
        f'</div>'
        f'<span class="quest-progress-text">[{_escape(bar_inner)}] {_escape(progress)}/{_escape(target)}</span>'
    )


def build_quests_html(quests: dict) -> str:
    """Build the quest progress section."""
    if not quests:
        return '<p class="no-quests">No quest data available</p>'

    active = []
    completed = []

    for quest_id in sorted(quests.keys(), key=lambda x: int(x)):
        q = quests[quest_id]
        name = QUEST_NAMES.get(quest_id, f"Quest {quest_id}")
        target = QUEST_TARGETS.get(quest_id, 1)
        progress = q.get("progress", 0)
        is_completed = q.get("completed", False)
        is_claimed = q.get("claimed", False)

        if is_completed:
            completed.append((quest_id, name, progress, target, is_claimed))
        else:
            active.append((quest_id, name, progress, target))

    parts = []

    if active:
        parts.append('<h3 class="quest-section-header">Active Quests</h3>')
        parts.append('<ul class="quest-list">')
        for quest_id, name, progress, target in active:
            bar = _quest_bar(progress, target)
            parts.append(
                f'<li class="quest active">'
                f'<span class="quest-id">[{_escape(quest_id):>2}]</span>'
                f'<span class="quest-name">{_escape(name)}</span>'
                f'{bar}'
                f'</li>'
            )
        parts.append('</ul>')
    else:
        parts.append('<p class="no-active-quests">All quests completed!</p>')

    if completed:
        parts.append('<h3 class="quest-section-header">Completed Quests</h3>')
        parts.append('<ul class="quest-list">')
        for quest_id, name, progress, target, claimed in completed:
            claimed_text = "Claimed" if claimed else "Unclaimed"
            parts.append(
                f'<li class="quest completed">'
                f'<span class="quest-id">[{_escape(quest_id):>2}]</span>'
                f'<span class="quest-name">{_escape(name)}</span>'
                f'<span class="quest-complete-badge">&#10003; COMPLETE</span>'
                f'<span class="quest-claimed">{_escape(claimed_text)}</span>'
                f'</li>'
            )
        parts.append('</ul>')

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def render_template(template: str, replacements: dict) -> str:
    """Replace all {{PLACEHOLDER}} tokens in template."""
    result = template
    for key, value in replacements.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


# ---------------------------------------------------------------------------
# CSS inlining
# ---------------------------------------------------------------------------

def load_css(script_dir: Path) -> str:
    """Load CSS from assets/styles.css relative to script location, or return empty string."""
    css_path = script_dir.parent / "assets" / "styles.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


def inline_css(html: str, css: str) -> str:
    """
    If the template has a <link rel="stylesheet" ...> tag pointing to styles.css,
    replace it with an inline <style> block. Otherwise append <style> to <head>.
    """
    if not css:
        return html

    style_block = f"<style>\n{css}\n</style>"

    import re
    # Replace <link rel="stylesheet" href="...styles.css..."> with inline style
    link_pattern = re.compile(
        r'<link\s[^>]*rel=["\']stylesheet["\'][^>]*href=["\'][^"\']*styles\.css["\'][^>]*>',
        re.IGNORECASE,
    )
    if link_pattern.search(html):
        return link_pattern.sub(style_block, html)

    # Alternatively, insert before </head>
    if "</head>" in html:
        return html.replace("</head>", style_block + "\n</head>", 1)

    # Fallback: prepend
    return style_block + "\n" + html


# ---------------------------------------------------------------------------
# Fallback template (used when assets/dashboard.html is absent)
# ---------------------------------------------------------------------------

FALLBACK_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en" class="{{THEME_CLASS}}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{TITLE}} — DevQuest Dashboard</title>
  <link rel="stylesheet" href="../assets/styles.css">
</head>
<body>
  <div class="dashboard">

    <header class="character-header">
      <h1 class="character-title">{{TITLE}}</h1>
      <div class="level-badge">Level {{LEVEL}}</div>
    </header>

    <section class="xp-section">
      <div class="xp-bar-container">
        <div class="xp-bar-fill" style="width: {{XP_PERCENT}}%"></div>
      </div>
      <p class="xp-text">{{XP_PROGRESS}} / {{XP_NEEDED}} XP ({{XP_PERCENT}}%)</p>
    </section>

    <section class="gold-section">
      <span class="gold-icon">&#9733;</span>
      <span class="gold-amount">{{GOLD}} Gold</span>
    </section>

    <section class="achievements-section">
      <h2>Achievements</h2>
      <ul class="achievements-list">
        {{ACHIEVEMENTS_HTML}}
      </ul>
    </section>

    <section class="weekly-stats-section">
      <h2>Weekly Stats</h2>
      {{WEEKLY_STATS_HTML}}
    </section>

    <section class="attributes-section">
      <h2>Attributes</h2>
      <ul class="attributes-list">
        {{ATTRIBUTES_HTML}}
      </ul>
    </section>

    <section class="buffs-section">
      <h2>Active Buffs</h2>
      {{BUFFS_HTML}}
    </section>

    <section class="quests-section">
      <h2>Quests</h2>
      {{QUESTS_HTML}}
    </section>

  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Render a DevQuest HTML dashboard from state.json"
    )
    parser.add_argument("--state",  required=True, help="Path to .devquest/state.json")
    parser.add_argument("--theme",  required=True, help="Theme name (fantasy, scifi, retro, minimalist)")
    parser.add_argument("--output", required=True, help="Path to write the output HTML file")
    parser.add_argument("--no-open", action="store_true", help="Skip opening the dashboard in the default browser")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    # 1. Read state JSON
    state_path = Path(args.state)
    if not state_path.exists():
        print(f"Error: state file not found: {state_path}", file=sys.stderr)
        sys.exit(1)

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in state file: {exc}", file=sys.stderr)
        sys.exit(1)

    theme = args.theme.lower()
    if theme not in LEVEL_TITLES:
        print(f"Warning: unknown theme '{theme}', falling back to minimalist", file=sys.stderr)
        theme = "minimalist"

    # 2. Extract state fields
    character    = state.get("character", {})
    stats        = state.get("stats", {})
    weekly_stats = state.get("weekly_stats", {})
    quests       = state.get("quests", {})

    total_xp = character.get("total_xp_earned", 0)
    gold     = character.get("gold", 0)
    attributes   = character.get("attributes", {})
    active_buffs = character.get("active_buffs", [])
    achievements = character.get("achievements", {})

    # 3. Derived values
    level = calculate_level(total_xp)
    title = get_level_title(theme, level)
    xp_progress_val, xp_needed, xp_percent = xp_progress(total_xp)

    if level >= len(XP_THRESHOLDS):
        xp_needed_display = "MAX"
        xp_progress_display = total_xp - XP_THRESHOLDS[-1]
    else:
        xp_needed_display = xp_needed
        xp_progress_display = xp_progress_val

    # 4. Build HTML fragments
    achievements_html  = build_achievements_html(achievements)
    weekly_stats_html  = build_weekly_stats_html(weekly_stats)
    attributes_html    = build_attributes_html(attributes)
    buffs_html         = build_buffs_html(active_buffs)
    quests_html        = build_quests_html(quests)

    # 5. Load template
    script_dir = Path(__file__).resolve().parent
    template_path = script_dir.parent / "assets" / "dashboard.html"

    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        print(
            f"Warning: template not found at {template_path}, using built-in fallback template",
            file=sys.stderr,
        )
        template = FALLBACK_TEMPLATE

    # 6. Replace placeholders
    replacements = {
        "THEME_CLASS":       f"theme-{theme}",
        "TITLE":             title,
        "LEVEL":             level,
        "XP_PROGRESS":       xp_progress_display,
        "XP_NEEDED":         xp_needed_display,
        "XP_PERCENT":        xp_percent,
        "GOLD":              gold,
        "ACHIEVEMENTS_HTML": achievements_html,
        "WEEKLY_STATS_HTML": weekly_stats_html,
        "ATTRIBUTES_HTML":   attributes_html,
        "BUFFS_HTML":        buffs_html,
        "QUESTS_HTML":       quests_html,
    }

    html = render_template(template, replacements)

    # 7. Inline CSS if available
    css = load_css(script_dir)
    html = inline_css(html, css)

    # 8. Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    file_uri = output_path.resolve().as_uri()
    print(f"Dashboard written to {output_path}")
    print(f"Open in browser: {file_uri}")

    if not args.no_open:
        import webbrowser
        webbrowser.open(output_path.resolve().as_uri())


if __name__ == "__main__":
    main()
