#!/usr/bin/env python3
"""Repository governance and Agent Skills frontmatter checks."""

import ast
import os
import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_simple_frontmatter(content: str, source: Path):
    """Parse the repository's scalar-only frontmatter without a YAML dependency."""
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", content, re.DOTALL)
    if not match:
        raise ValueError(f"{source}: missing or malformed frontmatter delimiters")
    values = {}
    for line_number, raw_line in enumerate(match.group(1).splitlines(), 2):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        field = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", raw_line)
        if not field:
            raise ValueError(f"{source}:{line_number}: expected a scalar key: value pair")
        key, raw_value = field.groups()
        if key in values:
            raise ValueError(f"{source}:{line_number}: duplicate frontmatter key {key}")
        if not raw_value:
            value = ""
        elif raw_value[0] in "\"'":
            try:
                value = ast.literal_eval(raw_value)
            except (SyntaxError, ValueError) as exc:
                raise ValueError(f"{source}:{line_number}: invalid quoted scalar") from exc
            if not isinstance(value, str):
                raise ValueError(f"{source}:{line_number}: scalar must be text")
        else:
            # In an unquoted scalar, # begins a YAML comment.
            value = raw_value.split(" #", 1)[0].strip()
        values[key] = value
    return values


class TestRepositoryGovernance(unittest.TestCase):
    def test_required_governance_files_exist(self):
        required = [
            "README.md", "COMPATIBILITY.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md",
            "docs/ROADMAP.md", "docs/DECISIONS.md", ".github/pull_request_template.md",
            ".github/workflows/ci.yml",
        ]
        for relative in required:
            self.assertTrue((REPO_ROOT / relative).is_file(), f"Missing {relative}")

    def test_roadmap_structure(self):
        content = (REPO_ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
        for section in ["## Now", "## Next", "## Later", "## Ideas / Inbox"]:
            self.assertIn(section, content)

    def test_decisions_structure(self):
        content = (REPO_ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8")
        decisions = re.findall(r"### (D-\d{3}):\s*(.+)", content)
        self.assertGreaterEqual(len(decisions), 5)
        for field in ["- **Date:**", "- **Status:**", "- **Decision:**", "- **Reason:**", "- **Alternatives Considered:**", "- **Consequences:**"]:
            self.assertEqual(content.count(field), len(decisions), f"Every ADR must include {field}")

    def test_pr_template_questions(self):
        content = (REPO_ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
        for heading in ["## 1. What Changed?", "## 2. Why?", "## 3. How Was It Tested?", "## 4. What Remains Incomplete?", "## 5. What Decision Do I Need from Jakkrit?"]:
            self.assertIn(heading, content)

    def test_no_generated_binary_is_tracked(self):
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
        ).stdout.splitlines()
        offenders = [path for path in tracked if path.endswith((".pyc", ".pyo", ".docx")) or "__pycache__" in Path(path).parts]
        self.assertEqual(offenders, [])


class TestSkillSpecification(unittest.TestCase):
    def test_skills_conform_to_spec(self):
        skill_directories = sorted(path for path in (REPO_ROOT / "skills").iterdir() if path.is_dir() and not path.name.startswith("."))
        self.assertTrue(skill_directories)
        for directory in skill_directories:
            with self.subTest(skill=directory.name):
                skill_file = directory / "SKILL.md"
                self.assertTrue(skill_file.is_file())
                frontmatter = parse_simple_frontmatter(skill_file.read_text(encoding="utf-8"), skill_file)
                self.assertTrue({"name", "description"}.issubset(frontmatter))
                name = frontmatter["name"]
                description = frontmatter["description"]
                self.assertRegex(name, NAME_RE)
                self.assertLessEqual(len(name), 64)
                self.assertEqual(name, directory.name)
                self.assertTrue(description.strip())
                self.assertLessEqual(len(description), 1024)
                self.assertIn("Use when", description)
                scripts = directory / "scripts"
                if os.name == "posix" and scripts.is_dir():
                    for script in scripts.iterdir():
                        if script.is_file() and script.suffix in {".py", ".sh"}:
                            self.assertTrue(os.access(script, os.X_OK), f"{script} must be executable")

    def test_frontmatter_parser_preserves_hash_inside_quotes(self):
        parsed = parse_simple_frontmatter("---\nname: reviewer\ndescription: 'Use when running Reviewer #2 checks.'\n---\n", Path("test"))
        self.assertEqual(parsed["description"], "Use when running Reviewer #2 checks.")


if __name__ == "__main__":
    unittest.main()
