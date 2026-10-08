"""Offline regression tests for strict immigration ownership checks."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_scope.py"
SPEC = importlib.util.spec_from_file_location("immigration_verify_scope", MODULE_PATH)
scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scope)


class PathRulesTest(unittest.TestCase):
    def test_own_files_and_workflow_are_allowed(self):
        for path in (
            "topics/immigration/README.md",
            "topics/immigration/data/2025/source.json",
            "topics/immigration/tests/test_verify_scope.py",
            ".github/workflows/immigration-scope-guard.yml",
        ):
            with self.subTest(path=path):
                self.assertTrue(scope.path_allowed(path))

    def test_public_and_drugs_paths_are_rejected(self):
        for path in (
            "index.html", "js/app.js", "js/core/geo-stats.js",
            "js/layers/state-layer.js", "js/layers/county-layer.js",
            "js/panels/area-panel.js", "css/map.css",
            "data/germany-counties.geojson", "data/germany-counties-display.geojson",
            "data/germany-states.geojson", "data/city_layers.json",
            "topics/drugs/topic.js", "README.md",
            ".github/workflows/germany-homicide-map.yml",
            ".github/workflows/immigration_bad.yml",
            "topics/immigration", "topics/immigration/../drugs/foo",
        ):
            with self.subTest(path=path):
                self.assertFalse(scope.path_allowed(path))

    def test_violations_are_sorted_and_deduplicated(self):
        self.assertEqual(
            scope.find_violations(["topics/immigration/a.js", "index.html", "js/app.js", "index.html"]),
            ["index.html", "js/app.js"],
        )


class GitDiffTest(unittest.TestCase):
    def test_changed_paths_detects_forbidden_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def git(*args):
                return subprocess.run(["git", "-C", str(root), *args],
                                      check=True, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE).stdout.decode().strip()

            git("init", "-q")
            git("config", "user.email", "tests@example.invalid")
            git("config", "user.name", "Immigration QA")
            (root / "README.md").write_text("base\n")
            git("add", ".")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD")
            (root / "topics/immigration").mkdir(parents=True)
            (root / "topics/immigration/README.md").write_text("new\n")
            (root / "js").mkdir()
            (root / "js/app.js").write_text("forbidden\n")
            git("add", ".")
            git("commit", "-qm", "changes")
            head = git("rev-parse", "HEAD")
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(root)
                names = scope.changed_paths(base, head)
            finally:
                os.chdir(original_cwd)
            self.assertEqual(scope.find_violations(names), ["js/app.js"])


if __name__ == "__main__":
    unittest.main()
