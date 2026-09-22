#!/usr/bin/env python3
"""
test_installer.py
Unit tests for cross-agent universal skill installer.
Zero external dependencies.
"""

import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import install


class TestInstaller(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.fake_home = Path(self.temp_dir.name) / "fake_home"
        self.fake_home.mkdir(parents=True, exist_ok=True)
        self.repo_root = Path(__file__).resolve().parent.parent

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_discover_skills(self):
        skills = install.discover_skills(self.repo_root)
        self.assertIn("citation-integrity", skills)
        self.assertTrue((skills["citation-integrity"] / "SKILL.md").is_file())

    def test_install_skill_copy_mode(self):
        target_dir = self.fake_home / ".claude" / "skills"
        skill_src = self.repo_root / "skills" / "citation-integrity"

        success, msg = install.install_skill("citation-integrity", skill_src, target_dir, symlink=False)
        self.assertTrue(success, msg)

        installed_skill = target_dir / "citation-integrity"
        self.assertTrue(installed_skill.is_dir())
        self.assertFalse(installed_skill.is_symlink())
        self.assertTrue((installed_skill / "SKILL.md").is_file())

        # Check script execution permissions
        verify_script = installed_skill / "scripts" / "verify_citations.py"
        self.assertTrue(verify_script.is_file())
        st = verify_script.stat().st_mode
        self.assertTrue(bool(st & stat.S_IXUSR))

    def test_install_skill_symlink_mode(self):
        target_dir = self.fake_home / ".hermes" / "skills"
        skill_src = self.repo_root / "skills" / "citation-integrity"

        success, msg = install.install_skill("citation-integrity", skill_src, target_dir, symlink=True)
        self.assertTrue(success, msg)

        installed_skill = target_dir / "citation-integrity"
        self.assertTrue(installed_skill.is_symlink())
        self.assertEqual(installed_skill.resolve(), skill_src.resolve())

    def test_uninstall_skill(self):
        target_dir = self.fake_home / ".pi" / "skills"
        skill_src = self.repo_root / "skills" / "citation-integrity"

        install.install_skill("citation-integrity", skill_src, target_dir, symlink=False)
        installed_skill = target_dir / "citation-integrity"
        self.assertTrue(installed_skill.exists())

        success, msg = install.uninstall_skill("citation-integrity", target_dir)
        self.assertTrue(success, msg)
        self.assertFalse(installed_skill.exists())

    def test_resolve_agent_path_with_custom_home(self):
        claude_path = install.resolve_agent_path("claude", custom_home=self.fake_home)
        self.assertEqual(claude_path, self.fake_home / ".claude" / "skills")

        hermes_path = install.resolve_agent_path("hermes", custom_home=self.fake_home)
        self.assertEqual(hermes_path, self.fake_home / ".hermes" / "skills")


if __name__ == "__main__":
    unittest.main()
