#!/usr/bin/env python3
"""Tests for the DevQuest permission installer."""

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

perms = import_module("setup-permissions")


class TestInstallPermissions(unittest.TestCase):
    def test_creates_settings_from_scratch(self):
        with tempfile.TemporaryDirectory() as tmp:
            success, msg = perms.install_permissions(tmp)
            self.assertTrue(success)

            settings_path = os.path.join(tmp, ".claude", "settings.local.json")
            self.assertTrue(os.path.exists(settings_path))

            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)

            allow = settings["permissions"]["allow"]
            for p in perms.DEVQUEST_PERMISSIONS:
                self.assertIn(p, allow)

    def test_includes_new_mutation_permissions(self):
        self.assertIn("Bash(python *scripts/menu.py*)", perms.DEVQUEST_PERMISSIONS)
        self.assertIn("Bash(python *scripts/update-state.py*)", perms.DEVQUEST_PERMISSIONS)

    def test_preserves_existing_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = os.path.join(tmp, ".claude")
            os.makedirs(settings_dir)
            settings_path = os.path.join(settings_dir, "settings.local.json")
            with open(settings_path, "w") as f:
                json.dump({"permissions": {"allow": ["Bash(npm test)"]}}, f)

            perms.install_permissions(tmp)

            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)

            allow = settings["permissions"]["allow"]
            self.assertIn("Bash(npm test)", allow)
            for p in perms.DEVQUEST_PERMISSIONS:
                self.assertIn(p, allow)

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            perms.install_permissions(tmp)
            perms.install_permissions(tmp)

            settings_path = os.path.join(tmp, ".claude", "settings.local.json")
            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)

            allow = settings["permissions"]["allow"]
            for p in perms.DEVQUEST_PERMISSIONS:
                self.assertEqual(allow.count(p), 1)

    def test_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = os.path.join(tmp, ".claude")
            os.makedirs(settings_dir)
            settings_path = os.path.join(settings_dir, "settings.local.json")
            with open(settings_path, "w") as f:
                json.dump({"model": "opus", "permissions": {"allow": []}}, f)

            perms.install_permissions(tmp)

            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)

            self.assertEqual(settings["model"], "opus")


class TestUninstallPermissions(unittest.TestCase):
    def test_removes_devquest_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            perms.install_permissions(tmp)
            success, msg = perms.uninstall_permissions(tmp)
            self.assertTrue(success)

            settings_path = os.path.join(tmp, ".claude", "settings.local.json")
            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)

            self.assertNotIn("permissions", settings)

    def test_preserves_other_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = os.path.join(tmp, ".claude")
            os.makedirs(settings_dir)
            settings_path = os.path.join(settings_dir, "settings.local.json")
            with open(settings_path, "w") as f:
                json.dump({"permissions": {"allow": ["Bash(npm test)"]}}, f)

            perms.install_permissions(tmp)
            perms.uninstall_permissions(tmp)

            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)

            allow = settings["permissions"]["allow"]
            self.assertIn("Bash(npm test)", allow)
            for p in perms.DEVQUEST_PERMISSIONS:
                self.assertNotIn(p, allow)

    def test_uninstall_no_prior_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            success, msg = perms.uninstall_permissions(tmp)
            self.assertTrue(success)


class TestCLI(unittest.TestCase):
    def _run(self, *args):
        cmd = [sys.executable, str(SCRIPT_DIR / "setup-permissions.py")] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_cli_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run("--repo", tmp)
            self.assertEqual(result.returncode, 0)
            self.assertIn("installed", result.stdout.lower())

    def test_cli_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._run("--repo", tmp)
            result = self._run("--repo", tmp, "--uninstall")
            self.assertEqual(result.returncode, 0)
            self.assertIn("removed", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
