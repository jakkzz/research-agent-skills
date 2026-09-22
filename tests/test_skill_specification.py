#!/usr/bin/env python3
"""Test suite validating repository governance and Open Agent Skills specification."""

import os
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestRepositoryGovernance(unittest.TestCase):
    """Ensure governance files exist and strictly follow the supervision model."""

    def test_required_governance_files_exist(self):
        required_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "ROADMAP.md",
            REPO_ROOT / "docs" / "DECISIONS.md",
            REPO_ROOT / "COMPATIBILITY.md",
            REPO_ROOT / "CONTRIBUTING.md",
            REPO_ROOT / ".github" / "pull_request_template.md",
        ]
        for path in required_files:
            self.assertTrue(path.exists(), f"Missing required governance file: {path.relative_to(REPO_ROOT)}")

    def test_roadmap_structure(self):
        roadmap_path = REPO_ROOT / "docs" / "ROADMAP.md"
        content = roadmap_path.read_text(encoding="utf-8")
        for section in ["## Now", "## Next", "## Later", "## Ideas / Inbox"]:
            self.assertIn(section, content, f"ROADMAP.md is missing required section: {section}")

    def test_decisions_structure(self):
        decisions_path = REPO_ROOT / "docs" / "DECISIONS.md"
        content = decisions_path.read_text(encoding="utf-8")
        decisions = re.findall(r"### (D-\d{3}):\s*(.+)", content)
        self.assertGreaterEqual(len(decisions), 4, "Expected at least foundational decisions D-001 to D-004")

        required_fields = ["- **Date:**", "- **Status:**", "- **Decision:**", "- **Reason:**", "- **Alternatives Considered:**", "- **Consequences:**"]
        for field in required_fields:
            self.assertIn(field, content, f"DECISIONS.md entries must include field: {field}")

    def test_pr_template_questions(self):
        pr_template_path = REPO_ROOT / ".github" / "pull_request_template.md"
        content = pr_template_path.read_text(encoding="utf-8")
        for q in [
            "## 1. What Changed?",
            "## 2. Why?",
            "## 3. How Was It Tested?",
            "## 4. What Remains Incomplete?",
            "## 5. What Decision Do I Need from Jakkrit?",
        ]:
            self.assertIn(q, content, f"PR template must include question header: {q}")


class TestSkillSpecification(unittest.TestCase):
    """Validate any skill in skills/ conforms to the Open Agent Skills specification."""

    def test_skills_conform_to_spec(self):
        skills_dir = REPO_ROOT / "skills"
        if not skills_dir.exists():
            return  # No skills added yet; foundation pass

        skill_folders = [d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        for skill_dir in skill_folders:
            skill_md = skill_dir / "SKILL.md"
            self.assertTrue(skill_md.exists(), f"Skill {skill_dir.name} is missing SKILL.md")

            content = skill_md.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---"), f"{skill_md} must start with YAML frontmatter delimiter '---'")

            # Frontmatter check
            frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
            self.assertIsNotNone(frontmatter_match, f"{skill_md} has invalid frontmatter formatting")
            fm_text = frontmatter_match.group(1)

            self.assertIn("name:", fm_text, f"{skill_md} frontmatter missing 'name'")
            self.assertIn("description:", fm_text, f"{skill_md} frontmatter missing 'description'")

            # Name match directory name
            name_match = re.search(r"name:\s*([a-zA-Z0-9_\-]+)", fm_text)
            self.assertIsNotNone(name_match)
            self.assertEqual(name_match.group(1), skill_dir.name, f"Skill name '{name_match.group(1)}' does not match directory '{skill_dir.name}'")

            # Check scripts directory permissions
            scripts_dir = skill_dir / "scripts"
            if scripts_dir.exists():
                for script in scripts_dir.iterdir():
                    if script.is_file() and script.suffix in [".py", ".sh"]:
                        self.assertTrue(os.access(script, os.X_OK), f"Script {script} must be executable (chmod +x)")


if __name__ == "__main__":
    unittest.main()
