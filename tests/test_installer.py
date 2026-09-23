#!/usr/bin/env python3
"""Regression tests for the safe cross-agent installer."""

import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import install


class TestInstaller(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.fake_home = self.root / "home"
        self.fake_home.mkdir()
        self.repo_root = Path(__file__).resolve().parent.parent
        self.skill_src = self.repo_root / "skills" / "citation-integrity"
        self.state_path = self.root / "state.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def install(self, target, **kwargs):
        return install.install_skill(
            "citation-integrity", self.skill_src, target,
            state_path=self.state_path, repo_root=self.repo_root, **kwargs
        )

    def test_discover_skills(self):
        skills = install.discover_skills(self.repo_root)
        self.assertIn("citation-integrity", skills)
        self.assertTrue((skills["citation-integrity"] / "SKILL.md").is_file())

    def test_install_copy_is_default_and_executable(self):
        target = self.fake_home / ".claude" / "skills"
        success, message = self.install(target)
        self.assertTrue(success, message)
        destination = target / "citation-integrity"
        self.assertTrue(destination.is_dir())
        self.assertFalse(destination.is_symlink())
        if os.name == "posix":
            self.assertTrue((destination / "scripts" / "verify_citations.py").stat().st_mode & stat.S_IXUSR)

    def test_existing_unowned_destination_is_refused_without_force(self):
        target = self.root / "skills"
        destination = target / "citation-integrity"
        destination.mkdir(parents=True)
        marker = destination / "mine.txt"
        marker.write_text("keep", encoding="utf-8")
        success, _ = self.install(target)
        self.assertFalse(success)
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
        self.assertFalse(self.state_path.exists())

    def test_symlink_is_opt_in(self):
        target = self.fake_home / ".hermes" / "skills"
        success, message = self.install(target, symlink=True)
        self.assertTrue(success, message)
        self.assertTrue((target / "citation-integrity").is_symlink())
        self.assertEqual((target / "citation-integrity").resolve(), self.skill_src.resolve())

    def test_atomic_copy_rolls_back_existing_destination(self):
        target = self.root / "skills"
        destination = target / "citation-integrity"
        destination.mkdir(parents=True)
        marker = destination / "original.txt"
        marker.write_text("original", encoding="utf-8")
        real_replace = os.replace

        def fail_staging(source, dest):
            if ".staging-" in Path(source).name:
                raise OSError("simulated activation failure")
            return real_replace(source, dest)

        with patch.object(install.os, "replace", side_effect=fail_staging):
            success, message = self.install(target, force=True)
        self.assertFalse(success, message)
        self.assertEqual(marker.read_text(encoding="utf-8"), "original")
        self.assertFalse(any(target.glob(".citation-integrity.staging-*")))
        self.assertFalse(any(target.glob(".citation-integrity.backup-*")))

    def test_manifest_failure_restores_original_even_if_quarantine_cleanup_fails(self):
        target = self.root / "skills"
        destination = target / "citation-integrity"
        destination.mkdir(parents=True)
        marker = destination / "original.txt"
        marker.write_text("original", encoding="utf-8")
        real_remove = install._remove_path

        def fail_quarantine_cleanup(path):
            if ".quarantine-" in Path(path).name:
                raise OSError("simulated cleanup failure")
            return real_remove(path)

        with patch.object(install, "_write_state", side_effect=OSError("manifest failed")), \
             patch.object(install, "_remove_path", side_effect=fail_quarantine_cleanup):
            success, message = self.install(target, force=True)

        self.assertFalse(success, message)
        self.assertEqual(marker.read_text(encoding="utf-8"), "original")
        self.assertFalse(any(target.glob(".citation-integrity.backup-*")))

    def test_manifest_records_ownership_and_source(self):
        target = self.root / "skills"
        success, message = self.install(target)
        self.assertTrue(success, message)
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(len(state["installations"]), 1)
        record = state["installations"][0]
        self.assertEqual(record["skill"], "citation-integrity")
        self.assertEqual(record["destination"], str(target.resolve() / "citation-integrity"))
        self.assertEqual(record["mode"], "copy")
        self.assertTrue(record["installed_at"])
        self.assertTrue(record["source_repo"])
        self.assertIn("SKILL.md", record["content_hashes"])
        self.assertTrue(record["content_hashes"]["SKILL.md"].startswith("file:"))

    def test_remote_metadata_redacts_url_credentials(self):
        self.assertEqual(
            install._sanitize_remote_url("https://user:secret@example.test/owner/repo.git"),
            "https://example.test/owner/repo.git",
        )
        self.assertEqual(
            install._sanitize_remote_url("git@example.test:owner/repo.git"),
            "example.test:owner/repo.git",
        )

    def test_copy_install_rejects_source_symlinks(self):
        source = self.root / "source-skill"
        source.mkdir()
        (source / "SKILL.md").write_text("---\nname: source-skill\n---\n", encoding="utf-8")
        secret = self.root / "secret.txt"
        secret.write_text("do not copy", encoding="utf-8")
        try:
            (source / "outside.txt").symlink_to(secret)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

        target = self.root / "skills"
        success, message = install.install_skill(
            "source-skill", source, target,
            state_path=self.state_path, repo_root=self.repo_root,
        )

        self.assertFalse(success)
        self.assertIn("symlink", message.lower())
        self.assertFalse((target / "source-skill").exists())

    def test_snapshot_does_not_follow_nested_symlinks(self):
        tree = self.root / "tree"
        external = self.root / "external"
        tree.mkdir()
        external.mkdir()
        (external / "secret.txt").write_text("external", encoding="utf-8")
        try:
            (tree / "linked").symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

        snapshot = install.content_hashes(tree)

        self.assertTrue(snapshot["linked"].startswith("symlink:"))
        self.assertNotIn("linked/secret.txt", snapshot)

    def test_replaced_install_symlink_is_drift_without_external_traversal(self):
        target = self.root / "skills"
        success, message = self.install(target, symlink=True)
        self.assertTrue(success, message)
        destination = target / "citation-integrity"
        external = self.root / "external"
        external.mkdir()
        (external / "do-not-read.txt").write_text("external", encoding="utf-8")
        destination.unlink()
        destination.symlink_to(external, target_is_directory=True)

        success, message = install.uninstall_skill(
            "citation-integrity", target, state_path=self.state_path
        )

        self.assertFalse(success)
        self.assertIn("drifted", message)
        self.assertTrue(destination.is_symlink())

    def test_broken_install_symlink_is_reported_as_drift(self):
        target = self.root / "skills"
        success, message = self.install(target, symlink=True)
        self.assertTrue(success, message)
        destination = target / "citation-integrity"
        destination.unlink()
        destination.symlink_to(self.root / "missing", target_is_directory=True)

        success, message = install.uninstall_skill(
            "citation-integrity", target, state_path=self.state_path
        )

        self.assertFalse(success)
        self.assertIn("drifted", message)
        self.assertTrue(destination.is_symlink())

    def test_forced_uninstall_skips_snapshot_traversal(self):
        target = self.root / "skills"
        self.assertTrue(self.install(target)[0])
        with patch.object(install, "content_hashes", side_effect=AssertionError("must not inspect")):
            success, message = install.uninstall_skill(
                "citation-integrity", target, state_path=self.state_path, force=True
            )
        self.assertTrue(success, message)

    def test_uninstall_refuses_unowned_destination(self):
        target = self.root / "skills"
        (target / "citation-integrity").mkdir(parents=True)
        success, message = install.uninstall_skill(
            "citation-integrity", target, state_path=self.state_path
        )
        self.assertFalse(success)
        self.assertIn("unowned", message)
        self.assertTrue((target / "citation-integrity").exists())

    def test_uninstall_refuses_drift_unless_forced(self):
        target = self.root / "skills"
        self.assertTrue(self.install(target)[0])
        destination = target / "citation-integrity"
        (destination / "SKILL.md").write_text("changed", encoding="utf-8")
        success, message = install.uninstall_skill(
            "citation-integrity", target, state_path=self.state_path
        )
        self.assertFalse(success)
        self.assertIn("drifted", message)
        success, message = install.uninstall_skill(
            "citation-integrity", target, state_path=self.state_path, force=True
        )
        self.assertTrue(success, message)
        self.assertFalse(destination.exists())
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["installations"], [])

    def test_missing_owned_uninstall_is_failure(self):
        target = self.root / "skills"
        self.assertTrue(self.install(target)[0])
        destination = target / "citation-integrity"
        for item in sorted(destination.rglob("*"), reverse=True):
            item.unlink() if item.is_file() else item.rmdir()
        destination.rmdir()
        success, message = install.uninstall_skill(
            "citation-integrity", target, state_path=self.state_path
        )
        self.assertFalse(success)
        self.assertIn("missing", message)

    def test_dry_run_writes_nothing(self):
        target = self.root / "skills"
        success, message = self.install(target, dry_run=True)
        self.assertTrue(success, message)
        self.assertIn("Would copy", message)
        self.assertFalse(target.exists())
        self.assertFalse(self.state_path.exists())

    def test_dry_run_uninstall_does_not_create_state_directory(self):
        fresh_state = self.root / "unused" / "install-state.json"
        success, message = install.uninstall_skill(
            "citation-integrity", self.root / "skills",
            state_path=fresh_state, dry_run=True,
        )
        self.assertFalse(success)
        self.assertIn("unowned", message)
        self.assertFalse(fresh_state.parent.exists())

    def test_stale_lock_file_does_not_block_new_lock(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.state_path.with_name(f"{self.state_path.name}.lock")
        lock_path.write_text("stale metadata", encoding="utf-8")
        with install._state_lock(self.state_path, timeout=0.1):
            self.assertTrue(lock_path.is_file())

    def test_explicit_agent_and_scope_are_required(self):
        with self.assertRaises(SystemExit):
            install.build_parser().parse_args([])
        with self.assertRaises(SystemExit):
            install.build_parser().parse_args(["--agent", "claude"])
        with self.assertRaises(SystemExit):
            install.main(["--agent", "claude", "--scope", "project"])
        with self.assertRaises(SystemExit):
            install.main(["--agent", "claude", "--scope", "user", "--uninstall"])
        with self.assertRaises(SystemExit):
            install.main(["--agent", "claude", "--scope", "user", "--force"])

    def test_status_fails_for_malformed_state_manifest(self):
        self.state_path.write_text("not json", encoding="utf-8")
        result = install.main([
            "--agent", "claude", "--scope", "user",
            "--state-path", str(self.state_path), "--status",
        ])
        self.assertEqual(result, 1)

    def test_load_state_rejects_malformed_schema(self):
        valid_record = {
            "source_repo": "repo", "source_revision": None, "skill": "one",
            "destination": str(self.root / "one"), "mode": "copy",
            "installed_at": "2026-01-01T00:00:00+00:00",
            "content_hashes": {".": "directory:755", "SKILL.md": "file:644:" + "0" * 64},
        }
        malformed = [
            [],
            {"version": True, "installations": []},
            {"version": 1, "installations": {}},
            {"version": 1, "installations": ["record"]},
            {"version": 1, "installations": [{**valid_record, "skill": 1}]},
            {"version": 1, "installations": [{key: value for key, value in valid_record.items() if key != "source_revision"}]},
            {"version": 1, "installations": [{**valid_record, "content_hashes": []}]},
            {"version": 1, "installations": [{**valid_record, "content_hashes": {"x": 1}}]},
            {"version": 1, "installations": [{**valid_record, "content_hashes": {"x": "bad-hash"}}]},
            {"version": 1, "installations": [valid_record, dict(valid_record)]},
        ]
        for index, value in enumerate(malformed):
            with self.subTest(index=index):
                self.state_path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(ValueError):
                    install._load_state(self.state_path)

    def test_uninstall_returns_controlled_error_for_malformed_record(self):
        self.state_path.write_text(
            json.dumps({"version": 1, "installations": [{"destination": 3}]}),
            encoding="utf-8",
        )
        success, message = install.uninstall_skill(
            "citation-integrity", self.root / "skills", state_path=self.state_path
        )
        self.assertFalse(success)
        self.assertIn("state manifest", message)

    def test_concurrent_installs_preserve_both_ownership_records(self):
        target_a = self.root / "target-a"
        target_b = self.root / "target-b"
        first_write_started = threading.Event()
        release_first_write = threading.Event()
        second_finished = threading.Event()
        real_write_state = install._write_state

        def delayed_write(state_path, state):
            destinations = {record["destination"] for record in state["installations"]}
            if str(target_a.resolve() / "citation-integrity") in destinations and not first_write_started.is_set():
                first_write_started.set()
                self.assertTrue(release_first_write.wait(3), "timed out releasing first manifest write")
            return real_write_state(state_path, state)

        def run_second():
            try:
                return self.install(target_b)
            finally:
                second_finished.set()

        with patch.object(install, "_write_state", side_effect=delayed_write):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(self.install, target_a)
                self.assertTrue(first_write_started.wait(3), "first install did not reach state write")
                second = pool.submit(run_second)
                second_finished.wait(0.25)
                release_first_write.set()
                first_result = first.result(timeout=5)
                second_result = second.result(timeout=5)

        self.assertTrue(first_result[0], first_result[1])
        self.assertTrue(second_result[0], second_result[1])
        state = install._load_state(self.state_path)
        self.assertEqual(
            {record["destination"] for record in state["installations"]},
            {
                str(target_a.resolve() / "citation-integrity"),
                str(target_b.resolve() / "citation-integrity"),
            },
        )

    def test_install_and_uninstall_serialize_destination_and_state(self):
        target = self.root / "target"
        self.assertTrue(self.install(target)[0])
        install_write_started = threading.Event()
        release_install_write = threading.Event()
        uninstall_finished = threading.Event()
        real_write_state = install._write_state

        def delayed_write(state_path, state):
            if state["installations"] and not install_write_started.is_set():
                install_write_started.set()
                self.assertTrue(release_install_write.wait(3), "timed out releasing install write")
            return real_write_state(state_path, state)

        def run_uninstall():
            try:
                return install.uninstall_skill(
                    "citation-integrity", target, state_path=self.state_path
                )
            finally:
                uninstall_finished.set()

        with patch.object(install, "_write_state", side_effect=delayed_write):
            with ThreadPoolExecutor(max_workers=2) as pool:
                reinstall = pool.submit(self.install, target, force=True)
                self.assertTrue(install_write_started.wait(3), "install did not reach state write")
                uninstall = pool.submit(run_uninstall)
                uninstall_finished.wait(0.25)
                release_install_write.set()
                reinstall_result = reinstall.result(timeout=5)
                uninstall_result = uninstall.result(timeout=5)

        self.assertTrue(reinstall_result[0], reinstall_result[1])
        self.assertTrue(uninstall_result[0], uninstall_result[1])
        self.assertFalse((target / "citation-integrity").exists())
        self.assertEqual(install._load_state(self.state_path)["installations"], [])

    def test_agent_path_matrix_and_hermes_home(self):
        expected_user = {
            "claude": ".claude/skills", "hermes": ".hermes/skills",
            "pi": ".pi/agent/skills", "omp": ".omp/agent/skills",
            "gemini": ".gemini/skills", "antigravity": ".gemini/config/skills",
            "antigravity-cli": ".gemini/antigravity-cli/skills", "codex": ".agents/skills",
        }
        for agent, suffix in expected_user.items():
            with self.subTest(agent=agent):
                self.assertEqual(
                    install.resolve_agent_path(agent, custom_home=self.fake_home, env={}),
                    (self.fake_home / suffix).resolve(),
                )
        hermes_home = self.root / "custom-hermes"
        self.assertEqual(
            install.resolve_agent_path("hermes", custom_home=self.fake_home,
                                       env={"HERMES_HOME": str(hermes_home)}),
            hermes_home.resolve() / "skills",
        )
        project = self.root / "project"
        expected_project = {
            "claude": ".claude/skills", "hermes": ".hermes/skills",
            "pi": ".pi/skills", "omp": ".omp/skills", "gemini": ".gemini/skills",
            "antigravity": ".agents/skills", "antigravity-cli": ".agents/skills",
            "codex": ".agents/skills",
        }
        for agent, suffix in expected_project.items():
            self.assertEqual(
                install.resolve_agent_path(agent, scope="project", project_root=project),
                (project / suffix).resolve(),
            )

    def test_duplicate_agent_destinations_are_deduplicated(self):
        args = install.build_parser().parse_args([
            "--agent", "all", "--scope", "project", "--project-root", str(self.root)
        ])
        targets = install._target_dirs(args)
        self.assertEqual(len(targets), len(set(targets)))
        self.assertEqual(targets.count((self.root / ".agents/skills").resolve()), 1)


if __name__ == "__main__":
    unittest.main()
