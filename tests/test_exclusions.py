#!/usr/bin/env python3
"""Tests for file exclusion patterns in track-commit.py."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from importlib import import_module
import unittest

track = import_module("track-commit")


class TestConfigBoilerplateExcluded(unittest.TestCase):
    """Config and boilerplate files should NOT earn XP/gold."""

    def _excluded(self, filepath):
        return track.is_excluded(filepath, track.DEFAULT_EXCLUDED_PATTERNS)

    def test_yaml_excluded(self):
        self.assertTrue(self._excluded("ci.yml"))
        self.assertTrue(self._excluded(".github/workflows/deploy.yml"))
        self.assertTrue(self._excluded("config.yaml"))

    def test_json_excluded(self):
        self.assertTrue(self._excluded("package.json"))
        self.assertTrue(self._excluded("tsconfig.json"))
        self.assertTrue(self._excluded("settings.json"))

    def test_toml_excluded(self):
        self.assertTrue(self._excluded("pyproject.toml"))
        self.assertTrue(self._excluded("Cargo.toml"))

    def test_xml_excluded(self):
        self.assertTrue(self._excluded("pom.xml"))
        self.assertTrue(self._excluded("AndroidManifest.xml"))

    def test_env_excluded(self):
        self.assertTrue(self._excluded(".env"))
        self.assertTrue(self._excluded(".env.local"))

    def test_ini_cfg_excluded(self):
        self.assertTrue(self._excluded("setup.cfg"))
        self.assertTrue(self._excluded("tox.ini"))

    def test_dockerfile_excluded(self):
        self.assertTrue(self._excluded("Dockerfile"))

    def test_gitignore_excluded(self):
        self.assertTrue(self._excluded(".gitignore"))
        self.assertTrue(self._excluded(".editorconfig"))

    def test_markdown_excluded(self):
        self.assertTrue(self._excluded("README.md"))
        self.assertTrue(self._excluded("CHANGELOG.md"))

    def test_csv_excluded(self):
        self.assertTrue(self._excluded("data.csv"))

    def test_makefile_excluded(self):
        self.assertTrue(self._excluded("Makefile"))

    def test_license_excluded(self):
        self.assertTrue(self._excluded("LICENSE"))
        self.assertTrue(self._excluded("LICENSE.md"))


class TestRealCodeNotExcluded(unittest.TestCase):
    """Actual source code files should still earn XP/gold."""

    def _excluded(self, filepath):
        return track.is_excluded(filepath, track.DEFAULT_EXCLUDED_PATTERNS)

    def test_python_not_excluded(self):
        self.assertFalse(self._excluded("main.py"))
        self.assertFalse(self._excluded("src/utils/helpers.py"))

    def test_javascript_not_excluded(self):
        self.assertFalse(self._excluded("app.js"))
        self.assertFalse(self._excluded("src/components/Button.tsx"))

    def test_java_not_excluded(self):
        self.assertFalse(self._excluded("Main.java"))

    def test_csharp_not_excluded(self):
        self.assertFalse(self._excluded("Program.cs"))

    def test_go_not_excluded(self):
        self.assertFalse(self._excluded("main.go"))

    def test_rust_not_excluded(self):
        self.assertFalse(self._excluded("lib.rs"))

    def test_cpp_not_excluded(self):
        self.assertFalse(self._excluded("main.cpp"))
        self.assertFalse(self._excluded("header.h"))

    def test_ruby_not_excluded(self):
        self.assertFalse(self._excluded("app.rb"))

    def test_html_css_not_excluded(self):
        self.assertFalse(self._excluded("index.html"))
        self.assertFalse(self._excluded("styles.css"))

    def test_shell_not_excluded(self):
        self.assertFalse(self._excluded("deploy.sh"))

    def test_sql_not_excluded(self):
        self.assertFalse(self._excluded("migration.sql"))


if __name__ == "__main__":
    unittest.main()
