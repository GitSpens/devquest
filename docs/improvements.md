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

### 4. Non-git activity tracking
Extend tracking beyond git to support other software integrations (IDE plugins, file watchers, etc.) for environments where git isn't the primary workflow.

---

## Completed

_(none yet)_
