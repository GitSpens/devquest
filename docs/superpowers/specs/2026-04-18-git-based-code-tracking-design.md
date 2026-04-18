# Git-Based Code Tracking for DevQuest

## Problem

DevQuest currently only tracks work done through Claude conversations. Users who write code manually — which is the intended workflow for earning XP and gold — get no credit. This breaks the core economy: you're supposed to earn rewards through hands-on coding, then spend gold when you want Claude to generate code.

## Solution

A `post-commit` git hook that automatically detects lines written, calculates rewards, updates state, and prints a notification in the terminal. Zero user action required after initial setup.

## Scope

**In scope:**
- Git post-commit hook for code-writing detection
- Lines-added counting with exclusion patterns
- Bug fix detection via commit message convention (`fix:` prefix)
- Reward pipeline (XP/gold calculation, attribute bonuses, buffs, level-ups, quests, achievements)
- Deduplication via commit SHA tracking
- Catch-up mechanism for missed commits on Claude session start
- Hook installation as part of `/devquest-enable`

**Out of scope (deferred):**
- Test run tracking
- Documentation tracking
- Non-git integrations (other software, file watchers)
- Real-time file system watching

## Architecture

### Components

**1. `scripts/track-commit.py`**
The core tracking script, called by the git hook. Responsibilities:
- Parse `git diff --numstat HEAD~1 HEAD` to count lines added per file
- Detect bug fixes from commit message (`git log -1 --format=%s`)
- Read `.devquest/state.json`
- Run the reward pipeline (shared with Claude's in-conversation tracking)
- Write updated state
- Print themed notification to stdout
- Record the commit SHA as `last_tracked_commit`

**2. Git post-commit hook (`.git/hooks/post-commit`)**
A thin shell script that calls `track-commit.py`. Installed automatically by `/devquest-enable`.

```bash
#!/bin/bash
# DevQuest post-commit hook
python "<skill-path>/scripts/track-commit.py" --state ".devquest/state.json" --theme "<theme>"
```

**3. State schema additions**
New fields in `.devquest/state.json`:

```json
{
  "tracking": {
    "last_tracked_commit": "<sha>",
    "excluded_patterns": ["*.lock", "*.min.js", "*.min.css", "package-lock.json", "yarn.lock", "*.map", "*.svg", "*.png", "*.jpg", "*.gif", "*.ico"]
  }
}
```

**4. `.devquest/config.json` (optional override)**
Users can customize exclusion patterns per-project:

```json
{
  "tracking": {
    "excluded_patterns": ["*.lock", "generated/**", "vendor/**"]
  }
}
```

If this file exists, its `excluded_patterns` replace the defaults in state. If not, defaults from state are used.

### Reward Pipeline

The `track-commit.py` script replicates the reward pipeline from SKILL.md:

1. **Count lines added** — `git diff --numstat HEAD~1 HEAD`, sum additions, filter out excluded patterns
2. **Calculate base rewards** — 1 XP and 0.5 gold per line added
3. **Detect bug fix** — if commit message matches `^fix(\(.*\))?:`, add 20 XP + 5 gold bonus
4. **Apply attribute bonuses** — `code_mastery` gives +3% gold per attribute level; `debugging` gives +10% XP per level (bug fixes only)
5. **Apply active buff multipliers** — check matching buffs, multiply, stack multiplicatively
6. **Decrement all active buffs** by 1 action; remove expired
7. **Round** final XP and gold to nearest integer
8. **Update state** — add XP, gold; increment `lines_written` (lifetime + weekly); increment `bugs_fixed` if applicable
9. **Check level-up** — compare `total_xp_earned` against thresholds in progression table
10. **Check quest progress** — update relevant quest progress counters
11. **Check achievements** — evaluate all achievement triggers
12. **Record commit SHA** as `last_tracked_commit`
13. **Write state** to disk
14. **Print notification** to stdout

### Notification Format

Standard action notification (themed):
```
⚔️ +{xp} XP, +{gold} Gold for {lines} lines! Level {level} "{title}" | XP: [{bar}] {progress}/{needed} | Gold: {gold_total}
```

On level-up, append themed level-up message. On achievement unlock, append `ACHIEVEMENT UNLOCKED: {name}!`. On quest complete, append `QUEST COMPLETE: {name}! +{xp} XP, +{gold} Gold`.

### Deduplication

State stores `tracking.last_tracked_commit` — the SHA of the most recently processed commit.

**Git hook flow:** After processing, the hook writes the current commit's SHA. Next commit only processes itself.

**Claude session catch-up:** On session start (when DevQuest is enabled), Claude runs:
```
git log --oneline <last_tracked_commit>..HEAD
```
If there are unprocessed commits (e.g., hook wasn't installed, or was bypassed), Claude processes them sequentially and awards accumulated rewards. This serves as a fallback, not the primary mechanism.

**Preventing double-counting:** The hook always writes the SHA after processing. Claude's catch-up checks the SHA before processing. If the hook already handled it, the catch-up finds nothing to do.

**First commit after enable:** When `last_tracked_commit` is empty/null, the hook processes only the current commit (HEAD~1..HEAD). It does not retroactively process the entire git history. The catch-up mechanism similarly only looks forward from the stored SHA — if no SHA exists, it skips catch-up.

### Hook Installation

During `/devquest-enable`, after creating state.json:

1. Check if `.git/hooks/post-commit` already exists
2. If it exists, check if it already contains the DevQuest marker comment
3. If no existing hook: create the file with the DevQuest hook script
4. If existing hook without DevQuest: append the DevQuest call to the end
5. If DevQuest already present: skip (idempotent)
6. Make the hook executable (`chmod +x`)

The hook script includes a marker comment (`# DevQuest hook — do not remove`) for identification.

During `/devquest-disable`:
- Remove the DevQuest section from the post-commit hook
- If the hook is now empty (only DevQuest was in it), delete the file

### Exclusion Patterns

Default exclusions (lockfiles, minified assets, binaries, source maps):
```
*.lock
*.min.js
*.min.css
package-lock.json
yarn.lock
*.map
*.svg
*.png
*.jpg
*.gif
*.ico
*.woff
*.woff2
*.ttf
*.eot
```

The script uses `git diff --numstat` which gives per-file line counts, then filters files against exclusion patterns before summing.

### Error Handling

- If `.devquest/state.json` doesn't exist or `enabled: false`: hook exits silently (exit 0)
- If Python is not available: hook prints a warning and exits (doesn't block commits)
- If state.json is malformed: hook prints a warning, exits without updating
- Hook must never block or fail a commit — all errors are non-fatal

### Cross-Platform Notes

- Hook uses `#!/bin/bash` — works on macOS, Linux, and Windows (Git Bash)
- Python called as `python3` with `python` fallback
- Paths use forward slashes (git hooks run in Git Bash on Windows)
- The skill path in the hook is resolved at install time to an absolute path

## SKILL.md Changes

1. Add `tracking` section to initial state schema
2. Update `/devquest-enable` flow to include hook installation
3. Update `/devquest-disable` flow to include hook removal
4. Add session-start catch-up logic to initialization check
5. Remove test/documentation passive tracking (defer to future)
6. Keep code-writing tracking for Claude-generated code (gold cost gate unchanged)

## Future Extensions

This design is intentionally extensible:
- **Test tracking**: Add a `pre-push` or test-runner hook that detects test results
- **Documentation tracking**: Detect docstring additions in commit diffs
- **Non-git tracking**: Add alternative signal sources (file watchers, IDE plugins) that write to the same state file format
- **Config UI**: `/devquest-settings` could expose exclusion pattern editing
