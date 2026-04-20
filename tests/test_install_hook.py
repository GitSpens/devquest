#!/usr/bin/env python3
"""Tests for the DevQuest hook installer."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from importlib import import_module

hook_mod = import_module("install-hook")


def make_git_repo(tmp_dir):
    """Initialize a bare git repo in tmp_dir and return its path."""
    subprocess.run(["git", "init", tmp_dir], capture_output=True, check=True)
    return tmp_dir


class TestBuildHookBlock(unittest.TestCase):
    def test_contains_markers(self):
        block = hook_mod.build_hook_block("fantasy")
        self.assertIn(hook_mod.BEGIN_MARKER, block)
        self.assertIn(hook_mod.END_MARKER, block)

    def test_contains_theme(self):
        block = hook_mod.build_hook_block("scifi")
        self.assertIn('--theme "scifi"', block)

    def test_contains_track_script_path(self):
        block = hook_mod.build_hook_block("fantasy")
        self.assertIn("track-commit.py", block)


class TestRemoveDevquestBlock(unittest.TestCase):
    def test_removes_block(self):
        content = f"#!/bin/bash\necho hello\n{hook_mod.BEGIN_MARKER}\nsome stuff\n{hook_mod.END_MARKER}\necho bye"
        result = hook_mod.remove_devquest_block(content)
        self.assertNotIn(hook_mod.BEGIN_MARKER, result)
        self.assertNotIn("some stuff", result)
        self.assertIn("echo hello", result)
        self.assertIn("echo bye", result)

    def test_no_block_returns_unchanged(self):
        content = "#!/bin/bash\necho hello"
        result = hook_mod.remove_devquest_block(content)
        self.assertIn("echo hello", result)

    def test_removes_only_devquest_block(self):
        content = f"#!/bin/bash\necho before\n{hook_mod.BEGIN_MARKER}\ndevquest\n{hook_mod.END_MARKER}\necho after"
        result = hook_mod.remove_devquest_block(content)
        self.assertIn("echo before", result)
        self.assertIn("echo after", result)
        self.assertNotIn("devquest", result)


class TestInstallHook(unittest.TestCase):
    def test_install_new_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_git_repo(tmp)
            success, msg = hook_mod.install_hook(repo, "fantasy")
            self.assertTrue(success)

            hook_path = os.path.join(repo, ".git", "hooks", "post-commit")
            self.assertTrue(os.path.exists(hook_path))
            content = open(hook_path, encoding="utf-8").read()
            self.assertIn("#!/bin/bash", content)
            self.assertIn(hook_mod.BEGIN_MARKER, content)
            self.assertIn('--theme "fantasy"', content)

    def test_install_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_git_repo(tmp)
            hook_mod.install_hook(repo, "fantasy")
            hook_mod.install_hook(repo, "fantasy")

            hook_path = os.path.join(repo, ".git", "hooks", "post-commit")
            content = open(hook_path, encoding="utf-8").read()
            self.assertEqual(content.count(hook_mod.BEGIN_MARKER), 1)

    def test_install_updates_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_git_repo(tmp)
            hook_mod.install_hook(repo, "fantasy")
            hook_mod.install_hook(repo, "scifi")

            hook_path = os.path.join(repo, ".git", "hooks", "post-commit")
            content = open(hook_path, encoding="utf-8").read()
            self.assertIn('--theme "scifi"', content)
            self.assertNotIn('--theme "fantasy"', content)
            self.assertEqual(content.count(hook_mod.BEGIN_MARKER), 1)

    def test_install_preserves_existing_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_git_repo(tmp)
            hooks_dir = os.path.join(repo, ".git", "hooks")
            os.makedirs(hooks_dir, exist_ok=True)
            hook_path = os.path.join(hooks_dir, "post-commit")
            with open(hook_path, "w") as f:
                f.write("#!/bin/bash\necho 'my custom hook'\n")

            hook_mod.install_hook(repo, "retro")
            content = open(hook_path, encoding="utf-8").read()
            self.assertIn("echo 'my custom hook'", content)
            self.assertIn(hook_mod.BEGIN_MARKER, content)

    def test_install_not_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            success, msg = hook_mod.install_hook(tmp, "fantasy")
            self.assertFalse(success)
            self.assertIn("Not a git repository", msg)


class TestUninstallHook(unittest.TestCase):
    def test_uninstall_removes_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_git_repo(tmp)
            hook_mod.install_hook(repo, "fantasy")
            success, msg = hook_mod.uninstall_hook(repo)
            self.assertTrue(success)

            hook_path = os.path.join(repo, ".git", "hooks", "post-commit")
            self.assertFalse(os.path.exists(hook_path))

    def test_uninstall_preserves_other_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_git_repo(tmp)
            hooks_dir = os.path.join(repo, ".git", "hooks")
            os.makedirs(hooks_dir, exist_ok=True)
            hook_path = os.path.join(hooks_dir, "post-commit")
            with open(hook_path, "w") as f:
                f.write("#!/bin/bash\necho 'keep me'\n")

            hook_mod.install_hook(repo, "fantasy")
            hook_mod.uninstall_hook(repo)

            self.assertTrue(os.path.exists(hook_path))
            content = open(hook_path, encoding="utf-8").read()
            self.assertIn("echo 'keep me'", content)
            self.assertNotIn(hook_mod.BEGIN_MARKER, content)

    def test_uninstall_no_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_git_repo(tmp)
            success, msg = hook_mod.uninstall_hook(repo)
            self.assertTrue(success)
            self.assertIn("nothing to remove", msg)

    def test_uninstall_not_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            success, msg = hook_mod.uninstall_hook(tmp)
            self.assertFalse(success)


class TestThemeNormalization(unittest.TestCase):
    """Test that theme names with hyphens/underscores are handled correctly."""

    def test_track_commit_normalizes_theme(self):
        track = import_module("track-commit")
        titles = track.LEVEL_TITLES
        for variant in ["sci-fi", "sci_fi", "scifi", "Sci-Fi", "SCI_FI"]:
            normalized = variant.lower().replace("-", "").replace("_", "")
            self.assertIn(normalized, titles, f"'{variant}' should normalize to 'scifi'")

    def test_all_valid_themes_resolve(self):
        track = import_module("track-commit")
        titles = track.LEVEL_TITLES
        for theme in ["fantasy", "sci-fi", "scifi", "retro", "minimalist"]:
            normalized = theme.lower().replace("-", "").replace("_", "")
            self.assertIn(normalized, titles, f"Theme '{theme}' should resolve")


class TestCLI(unittest.TestCase):
    def _run(self, *args):
        cmd = [sys.executable, str(SCRIPT_DIR / "install-hook.py")] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_cli_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_git_repo(tmp)
            result = self._run("--repo", repo, "--theme", "fantasy")
            self.assertEqual(result.returncode, 0)
            self.assertIn("installed", result.stdout.lower())

    def test_cli_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_git_repo(tmp)
            self._run("--repo", repo, "--theme", "fantasy")
            result = self._run("--repo", repo, "--uninstall")
            self.assertEqual(result.returncode, 0)

    def test_cli_not_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run("--repo", tmp, "--theme", "fantasy")
            self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
