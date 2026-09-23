#!/usr/bin/env python3
"""Safe, dependency-free installer for research-agent-skills."""

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

if os.name == "nt":
    import msvcrt
else:
    import fcntl

AGENT_PATHS: Dict[str, Dict[str, str]] = {
    "claude": {"user": ".claude/skills", "project": ".claude/skills"},
    "hermes": {"user": ".hermes/skills", "project": ".hermes/skills"},
    "pi": {"user": ".pi/agent/skills", "project": ".pi/skills"},
    "omp": {"user": ".omp/agent/skills", "project": ".omp/skills"},
    "gemini": {"user": ".gemini/skills", "project": ".gemini/skills"},
    "antigravity": {"user": ".gemini/config/skills", "project": ".agents/skills"},
    "antigravity-cli": {"user": ".gemini/antigravity-cli/skills", "project": ".agents/skills"},
    "codex": {"user": ".agents/skills", "project": ".agents/skills"},
}
# Compatibility alias for callers that enumerate agents.
AGENT_DIRS = {name: paths["user"] for name, paths in AGENT_PATHS.items()}
STATE_LOCK_TIMEOUT_SECONDS = 10.0
STATE_LOCK_POLL_SECONDS = 0.05


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def discover_skills(repo_root: Path) -> Dict[str, Path]:
    skills_dir = repo_root / "skills"
    if not skills_dir.is_dir():
        return {}
    return {
        entry.name: entry
        for entry in sorted(skills_dir.iterdir())
        if entry.is_dir() and (entry / "SKILL.md").is_file()
    }


def resolve_agent_path(
    agent_key: str,
    custom_home: Optional[Path] = None,
    scope: str = "user",
    project_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Path:
    if agent_key not in AGENT_PATHS:
        raise ValueError(f"Unknown agent: {agent_key}")
    if scope not in {"user", "project"}:
        raise ValueError(f"Unknown scope: {scope}")
    environment = os.environ if env is None else env
    if scope == "project":
        if project_root is None:
            raise ValueError("--project-root is required for project scope")
        return (Path(project_root).expanduser().resolve() / AGENT_PATHS[agent_key][scope]).resolve()
    if agent_key == "hermes" and environment.get("HERMES_HOME"):
        return (Path(environment["HERMES_HOME"]).expanduser().resolve() / "skills").resolve()
    home = Path(custom_home).expanduser().resolve() if custom_home else Path.home().resolve()
    return (home / AGENT_PATHS[agent_key][scope]).resolve()


def default_state_path(custom_home: Optional[Path] = None) -> Path:
    home = Path(custom_home).expanduser().resolve() if custom_home else Path.home().resolve()
    return home / ".research-agent-skills" / "install-state.json"


def _load_state(state_path: Path) -> Dict:
    if not state_path.exists() and not state_path.is_symlink():
        return {"version": 1, "installations": []}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read state manifest {state_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid state manifest {state_path}: root must be an object")
    if type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError(f"Invalid state manifest {state_path}: version must be integer 1")
    installations = data.get("installations")
    if not isinstance(installations, list):
        raise ValueError(f"Invalid state manifest {state_path}: installations must be a list")

    required_string_fields = ("source_repo", "skill", "destination", "mode", "installed_at")
    destinations = set()
    for index, record in enumerate(installations):
        prefix = f"Invalid state manifest {state_path}: installation {index}"
        if not isinstance(record, dict):
            raise ValueError(f"{prefix} must be an object")
        for field in required_string_fields:
            if not isinstance(record.get(field), str) or not record[field]:
                raise ValueError(f"{prefix}.{field} must be a non-empty string")
        if "source_revision" not in record:
            raise ValueError(f"{prefix}.source_revision is required")
        revision = record["source_revision"]
        if revision is not None and not isinstance(revision, str):
            raise ValueError(f"{prefix}.source_revision must be a string or null")
        if record["mode"] not in {"copy", "symlink"}:
            raise ValueError(f"{prefix}.mode must be 'copy' or 'symlink'")
        snapshot = record.get("content_hashes")
        if not isinstance(snapshot, dict) or not snapshot:
            raise ValueError(f"{prefix}.content_hashes must be a non-empty object")
        for relative_path, metadata in snapshot.items():
            if not isinstance(relative_path, str) or not relative_path:
                raise ValueError(f"{prefix}.content_hashes keys must be non-empty strings")
            parts = Path(relative_path).parts
            if Path(relative_path).is_absolute() or ".." in parts:
                raise ValueError(f"{prefix}.content_hashes contains an unsafe path")
            if not isinstance(metadata, str) or not metadata:
                raise ValueError(f"{prefix}.content_hashes values must be non-empty strings")
            legacy_hash = len(metadata) == 64 and all(character in "0123456789abcdef" for character in metadata)
            descriptor = metadata.split(":", 2)
            descriptor_valid = False
            if descriptor[0] == "directory" and len(descriptor) == 2:
                descriptor_valid = bool(descriptor[1]) and all(character in "01234567" for character in descriptor[1])
            elif descriptor[0] == "file" and len(descriptor) == 3:
                descriptor_valid = (
                    bool(descriptor[1])
                    and all(character in "01234567" for character in descriptor[1])
                    and len(descriptor[2]) == 64
                    and all(character in "0123456789abcdef" for character in descriptor[2])
                )
            elif descriptor[0] == "symlink" and len(descriptor) == 3:
                descriptor_valid = (
                    bool(descriptor[1])
                    and all(character in "01234567" for character in descriptor[1])
                    and bool(descriptor[2])
                )
            elif descriptor[0] == "other" and len(descriptor) == 3:
                descriptor_valid = all(
                    value and all(character in "01234567" for character in value)
                    for value in descriptor[1:]
                )
            if not legacy_hash and not descriptor_valid:
                raise ValueError(f"{prefix}.content_hashes contains invalid metadata")
        destination = record["destination"]
        if destination in destinations:
            raise ValueError(f"Invalid state manifest {state_path}: duplicate destination {destination}")
        destinations.add(destination)
    return data


def _write_state(state_path: Path, state: Dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{state_path.name}.", dir=str(state_path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, state_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


@contextmanager
def _state_lock(state_path: Path, timeout: float = STATE_LOCK_TIMEOUT_SECONDS):
    """Serialize transactions with an OS lock released on process exit."""
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_name(f"{state_path.name}.lock")
    deadline = time.monotonic() + timeout
    with lock_path.open("a+b") as lock_file:
        if os.name == "nt":
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
        while True:
            try:
                if os.name == "nt":
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for installer lock {lock_path}")
                time.sleep(STATE_LOCK_POLL_SECONDS)
        try:
            yield
        finally:
            if os.name == "nt":
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _path_exists(path: Path) -> bool:
    # Check link identity first so existence checks never dereference symlinks.
    return path.is_symlink() or path.exists()


def content_hashes(path: Path) -> Dict[str, str]:
    """Snapshot a path without ever following a destination or nested symlink."""
    root = Path(path)
    snapshot: Dict[str, str] = {}

    def visit(item: Path, relative_path: str) -> None:
        item_stat = item.lstat()
        mode = stat.S_IMODE(item_stat.st_mode)
        if stat.S_ISLNK(item_stat.st_mode):
            snapshot[relative_path] = f"symlink:{mode:o}:{os.readlink(item)}"
            return
        if stat.S_ISREG(item_stat.st_mode):
            digest = hashlib.sha256()
            with item.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            snapshot[relative_path] = f"file:{mode:o}:{digest.hexdigest()}"
            return
        if stat.S_ISDIR(item_stat.st_mode):
            snapshot[relative_path] = f"directory:{mode:o}"
            with os.scandir(item) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
            for child in children:
                child_relative = child.name if relative_path == "." else f"{relative_path}/{child.name}"
                visit(item / child.name, child_relative)
            return
        snapshot[relative_path] = f"other:{stat.S_IFMT(item_stat.st_mode):o}:{mode:o}"

    visit(root, ".")
    return snapshot


def _sanitize_remote_url(remote: str) -> str:
    """Remove URL credentials and query data before persisting provenance."""
    if "://" in remote:
        parsed = urlsplit(remote)
        if parsed.hostname:
            host = parsed.hostname
            if ":" in host and not host.startswith("["):
                host = f"[{host}]"
            try:
                port = parsed.port
            except ValueError:
                port = None
            netloc = f"{host}:{port}" if port is not None else host
            return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    at_index = remote.find("@")
    colon_index = remote.find(":", at_index + 1)
    if at_index > 0 and colon_index > at_index and not any(
        separator in remote[:at_index] for separator in ("/", "\\")
    ):
        return remote[at_index + 1:]
    return remote


def _repo_metadata(repo_root: Path) -> Tuple[str, Optional[str]]:
    source_repo = str(repo_root.resolve())
    revision: Optional[str] = None
    try:
        remote = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"], cwd=repo_root,
            check=False, capture_output=True, text=True,
        ).stdout.strip()
        revision_result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root,
            check=False, capture_output=True, text=True,
        )
        if remote:
            source_repo = _sanitize_remote_url(remote)
        if revision_result.returncode == 0:
            revision = revision_result.stdout.strip() or None
    except OSError:
        pass
    return source_repo, revision


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _best_effort_remove(path: Path) -> None:
    try:
        _remove_path(path)
    except OSError:
        pass


def _rollback_install(dest_path: Path, backup: Path, quarantine: Path, had_destination: bool) -> None:
    """Deactivate a failed install before restoring the prior destination."""
    if _path_exists(dest_path):
        os.replace(dest_path, quarantine)
    if had_destination and _path_exists(backup):
        os.replace(backup, dest_path)
    _best_effort_remove(quarantine)


def _upsert_record(state: Dict, record: Dict) -> None:
    destination = record["destination"]
    state["installations"] = [
        item for item in state["installations"] if item.get("destination") != destination
    ]
    state["installations"].append(record)


def install_skill(
    skill_name: str,
    skill_src: Path,
    target_dir: Path,
    symlink: bool = False,
    force: bool = False,
    state_path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """Install one skill, using sibling staging and rollback for copy mode."""
    source_argument = Path(skill_src)
    if source_argument.is_symlink():
        return False, f"Invalid skill source: symlinked skill roots are not allowed: {source_argument}"
    skill_src = source_argument.resolve()
    target_dir = Path(target_dir).resolve()
    dest_path = target_dir / skill_name
    if not skill_src.is_dir() or not (skill_src / "SKILL.md").is_file():
        return False, f"Invalid skill source: {skill_src}"
    try:
        source_snapshot = content_hashes(skill_src)
    except OSError as exc:
        return False, f"Invalid skill source {skill_src}: {exc}"
    if any(metadata.startswith("symlink:") for metadata in source_snapshot.values()):
        return False, f"Invalid skill source: symlinks are not allowed inside {skill_src}"
    if dry_run:
        if _path_exists(dest_path) and not force:
            return False, f"Destination {dest_path} already exists (use --force to replace it)"
        action = "symlink" if symlink else "copy"
        return True, f"Would {action} {skill_src} to {dest_path}"
    state_path = Path(state_path) if state_path is not None else None
    lock = _state_lock(state_path) if state_path is not None else nullcontext()
    try:
        with lock:
            state = _load_state(state_path) if state_path is not None else None
            target_dir.mkdir(parents=True, exist_ok=True)
            had_destination = _path_exists(dest_path)
            if had_destination and not force:
                return False, f"Destination {dest_path} already exists (use --force to replace it)"

            staging = target_dir / f".{skill_name}.staging-{uuid.uuid4().hex}"
            backup = target_dir / f".{skill_name}.backup-{uuid.uuid4().hex}"
            quarantine = target_dir / f".{skill_name}.quarantine-{uuid.uuid4().hex}"
            try:
                if symlink:
                    staging.symlink_to(skill_src, target_is_directory=True)
                else:
                    shutil.copytree(skill_src, staging, symlinks=True)
                    staging_snapshot = content_hashes(staging)
                    if any(metadata.startswith("symlink:") for metadata in staging_snapshot.values()):
                        raise ValueError("Skill source changed during copy and contains a symlink")
                    if os.name == "posix":
                        scripts_dir = staging / "scripts"
                        if scripts_dir.is_dir():
                            for item in scripts_dir.iterdir():
                                if item.is_file():
                                    item.chmod(item.stat().st_mode | 0o111)
                if had_destination:
                    os.replace(dest_path, backup)
                try:
                    os.replace(staging, dest_path)
                    if state is not None:
                        source_repo, revision = _repo_metadata(repo_root or get_repo_root())
                        record = {
                            "source_repo": source_repo,
                            "source_revision": revision,
                            "skill": skill_name,
                            "destination": str(dest_path),
                            "mode": "symlink" if symlink else "copy",
                            "installed_at": datetime.now(timezone.utc).isoformat(),
                            "content_hashes": content_hashes(dest_path),
                        }
                        _upsert_record(state, record)
                        _write_state(state_path, state)
                except Exception:
                    _rollback_install(dest_path, backup, quarantine, had_destination)
                    raise
                _best_effort_remove(backup)
                return True, f"Installed {dest_path} ({'symlink' if symlink else 'copy'})"
            finally:
                _best_effort_remove(staging)
    except Exception as exc:
        return False, f"Failed to install {dest_path}: {exc}"


def uninstall_skill(
    skill_name: str,
    target_dir: Path,
    state_path: Optional[Path] = None,
    force: bool = False,
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """Remove only a manifest-owned destination, refusing content drift by default."""
    dest_path = Path(target_dir).resolve() / skill_name
    if state_path is None:
        return False, "A state manifest is required for uninstall"
    state_path = Path(state_path)
    try:
        lock = nullcontext() if dry_run else _state_lock(state_path)
        with lock:
            state = _load_state(state_path)
            record = next(
                (item for item in state["installations"] if item["destination"] == str(dest_path)), None
            )
            if record is None:
                return False, f"Refusing to remove unowned destination {dest_path}"
            if not _path_exists(dest_path):
                return False, f"Owned destination is missing: {dest_path}"
            if not force:
                try:
                    current_hashes = content_hashes(dest_path)
                except OSError as exc:
                    return False, f"Failed to inspect {dest_path}: {exc}"
                if current_hashes != record["content_hashes"]:
                    return False, f"Destination has drifted: {dest_path} (use --force to remove it)"
            if dry_run:
                return True, f"Would remove owned destination {dest_path}"

            backup = dest_path.parent / f".{dest_path.name}.uninstall-{uuid.uuid4().hex}"
            os.replace(dest_path, backup)
            new_state = dict(state)
            new_state["installations"] = [
                item for item in state["installations"] if item["destination"] != str(dest_path)
            ]
            try:
                _write_state(state_path, new_state)
            except Exception:
                os.replace(backup, dest_path)
                raise
            _best_effort_remove(backup)
            return True, f"Removed {dest_path}"
    except Exception as exc:
        return False, f"Failed to remove {dest_path}: {exc}"


def _selected_agents(agent: str) -> List[str]:
    return list(AGENT_PATHS) if agent == "all" else [agent]


def _target_dirs(args: argparse.Namespace) -> List[Path]:
    paths = [
        resolve_agent_path(
            agent,
            scope=args.scope,
            project_root=Path(args.project_root) if args.project_root else None,
        )
        for agent in _selected_agents(args.agent)
    ]
    return list(dict.fromkeys(paths))


def check_status(skills: Dict[str, Path], target_dirs: List[Path], state_path: Path) -> bool:
    try:
        state = _load_state(state_path)
        owned = {item.get("destination") for item in state["installations"]}
    except ValueError as exc:
        print(f"State error: {exc}", file=sys.stderr)
        return False
    for target in target_dirs:
        print(f"Target: {target}")
        for name in sorted(skills):
            destination = target / name
            present = destination.exists() or destination.is_symlink()
            label = "owned" if str(destination) in owned else "unowned"
            presence = "present" if present else "absent"
            print(f"  {name}: {presence}, {label}")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely install research-agent-skills (alpha).")
    parser.add_argument("skills", nargs="*", help="Skill names; install defaults to all, uninstall requires names")
    parser.add_argument("--agent", "-a", required=True, choices=list(AGENT_PATHS) + ["all"],
                        help="Explicit target agent; use 'all' deliberately")
    parser.add_argument("--scope", required=True, choices=["user", "project"], help="Installation scope")
    parser.add_argument("--project-root", help="Project root; required with --scope project")
    parser.add_argument("--state-path", type=Path, help="Override installer state manifest path")
    parser.add_argument("--symlink", "-s", action="store_true", help="Opt in to symlink mode")
    parser.add_argument("--force", action="store_true", help="Replace existing installs or remove drifted owned installs")
    parser.add_argument("--dry-run", action="store_true", help="Report requested changes without writing")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall named, manifest-owned skills")
    parser.add_argument("--status", action="store_true", help="Report presence and manifest ownership")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.scope == "project" and not args.project_root:
        parser.error("--project-root is required with --scope project")
    if args.uninstall and not args.skills:
        parser.error("uninstall requires at least one explicit skill name")
    if args.force and not args.skills:
        parser.error("--force requires at least one explicit skill name")
    repo_root = get_repo_root()
    available_skills = discover_skills(repo_root)
    if not available_skills:
        print("Error: no valid skills found in skills/", file=sys.stderr)
        return 1
    unknown = [name for name in args.skills if name not in available_skills]
    if unknown:
        print(f"Error: unknown skill(s): {', '.join(unknown)}", file=sys.stderr)
        return 1
    targets = _target_dirs(args)
    state_path = args.state_path or default_state_path()
    if args.status:
        return 0 if check_status(available_skills, targets, state_path) else 1
    selected = args.skills or list(available_skills)
    succeeded = True
    for skill_name in selected:
        for target in targets:
            if args.uninstall:
                ok, message = uninstall_skill(
                    skill_name, target, state_path=state_path, force=args.force, dry_run=args.dry_run
                )
            else:
                ok, message = install_skill(
                    skill_name, available_skills[skill_name], target,
                    symlink=args.symlink, force=args.force, state_path=state_path,
                    repo_root=repo_root, dry_run=args.dry_run,
                )
            print(f"{'OK' if ok else 'ERROR'} [{skill_name}] {message}")
            succeeded = succeeded and ok
    return 0 if succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
