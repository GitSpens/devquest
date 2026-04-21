# DevQuest — Improvements

Planned improvements and polish items.

---

## Backlog

### 1. Interactive option selection for settings
Settings changes (`/devquest-settings`, `/devquest-theme`, `/devquest-enable` setup) should present numbered options for the user to pick from rather than requiring them to type the exact setting value. This applies to all enum-type inputs: environment, display mode, and theme.

### 2. Test run tracking (deferred from v1)
Track test pass/fail results to award XP/gold. Options: wrapper CLI command (`dq test <cmd>`), test framework plugins (Jest reporter, pytest plugin), or file-based signal. Requires a detection mechanism outside git hooks since test runs don't always correspond to commits.

Base rewards: Test pass = 30 XP, 10 Gold per run. Test fail = 10 XP, 0 Gold per run.

### 3. Documentation tracking (deferred from v1)
Track documentation of functions/modules to award XP/gold. Could be detected via git diff analysis (docstring/comment additions in commits) or IDE plugin signals.

Base rewards: 10 XP, 2 Gold per function documented.

### 4. Bug fix / debugging tracking (deferred from v1)
Track bug fixes to award XP/gold. Could be detected via commit message convention (`fix:` prefix) in the post-commit hook, or via IDE/tool integrations. Includes debugging attribute (+10% XP per level from bug fixes) and related quests/achievements.

Base rewards: Bug fix = 20 XP, 5 Gold each.

### 5. Non-git activity tracking
Extend tracking beyond git to support other software integrations (IDE plugins, file watchers, etc.) for environments where git isn't the primary workflow.

### 6. Seamless permissions for script-based commands
`/devquest-theme`, `/devquest-settings`, and `/devquest-shop` currently trigger an "Allow Claude to run…" prompt on first use. Root cause: Claude Code auto-prefixes skill bash commands with `cd "<skill-dir>" && …`, and our permission patterns (`Bash(python *scripts/menu.py*)`) start with the literal `python` — they don't match a command that starts with `cd`. Additionally, the thin sibling SKILL.md files use a relative `python scripts/menu.py` path, so the script is only found by accident (Claude's path rewriting). Fix: (a) change the patterns in `setup-permissions.py` to allow a prefix, e.g. `Bash(*python *scripts/menu.py*)` and `Bash(*python *scripts/update-state.py*)` (consider the same for existing script entries); (b) update the sibling SKILL.md prose to use an absolute path, e.g. `python "$HOME/.claude/skills/devquest/scripts/menu.py"`; (c) re-run `setup-permissions.py --repo <project>` in test projects so new patterns land in `.claude/settings.local.json`; (d) add a regression test on the pattern shape.

### 7. Bring sibling skills into the devquest repo
The sibling skills (`devquest-theme`, `devquest-settings`, `devquest-shop`, `devquest-enable`, `devquest-disable`, `devquest-character`, `devquest-quests`) live at `~/.claude/skills/devquest-*/SKILL.md` and are not tracked by any git repo — Claude Code requires top-level skill directories for auto-discovery, so they can't nest inside the devquest repo. Edits made in the `feat/script-based-state-mutations` branch (Tasks 4, 7, 10 — the three thin-router rewrites for theme/settings/shop) currently exist only on disk, not in version control. Fix: store canonical SKILL.md sources inside the devquest repo (e.g., `skills/devquest-theme/SKILL.md`) and extend `setup-project.py` / `devquest-enable.py` to copy them out to `~/.claude/skills/devquest-*/` on install, overwriting stale versions. The uninstall flow (`/devquest-disable`) should optionally clean them up too. One-time migration: copy the current on-disk SKILL.md files into the repo as the initial source of truth. Bring all seven sibling skills in for consistency, not just the three touched in this branch.

---

## Completed

_(none yet)_
