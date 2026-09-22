#!/usr/bin/env python3
"""
install.py
Cross-agent universal skill installer and manager for research-agent-skills.
Zero external dependencies. Works on Linux, macOS, and POSIX environments.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

AGENT_DIRS: Dict[str, str] = {
    "claude": "~/.claude/skills",
    "hermes": "~/.hermes/skills",
    "pi": "~/.pi/skills",
    "antigravity": "~/.gemini/antigravity/skills",
    "gemini": "~/.gemini/config/skills",
    "workspace": ".agents/skills",
}


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def discover_skills(repo_root: Path) -> Dict[str, Path]:
    skills_dir = repo_root / "skills"
    skills = {}
    if skills_dir.exists() and skills_dir.is_dir():
        for entry in skills_dir.iterdir():
            if entry.is_dir() and (entry / "SKILL.md").is_file():
                skills[entry.name] = entry
    return skills


def resolve_agent_path(agent_key: str, custom_home: Optional[Path] = None) -> Path:
    raw_path = AGENT_DIRS[agent_key]
    if raw_path.startswith("~"):
        home = custom_home if custom_home else Path.home()
        return home / raw_path[2:]
    return Path(raw_path).resolve()


def install_skill(
    skill_name: str,
    skill_src: Path,
    target_dir: Path,
    symlink: bool = False,
    force: bool = True
) -> Tuple[bool, str]:
    dest_path = target_dir / skill_name

    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        if dest_path.is_symlink() or dest_path.exists():
            if not force:
                return False, f"Destination {dest_path} already exists (use --force to overwrite)"
            if dest_path.is_symlink() or dest_path.is_file():
                dest_path.unlink()
            elif dest_path.is_dir():
                shutil.rmtree(dest_path)

        if symlink:
            dest_path.symlink_to(skill_src.resolve(), target_is_directory=True)
            return True, f"Symlinked -> {dest_path}"
        else:
            shutil.copytree(skill_src, dest_path)
            # Ensure scripts remain executable
            scripts_dir = dest_path / "scripts"
            if scripts_dir.exists():
                for item in scripts_dir.iterdir():
                    if item.is_file():
                        item.chmod(item.stat().st_mode | 0o111)
            return True, f"Copied -> {dest_path}"
    except Exception as e:
        return False, f"Failed: {e}"


def uninstall_skill(skill_name: str, target_dir: Path) -> Tuple[bool, str]:
    dest_path = target_dir / skill_name
    if not dest_path.exists() and not dest_path.is_symlink():
        return False, f"Not found at {dest_path}"

    try:
        if dest_path.is_symlink() or dest_path.is_file():
            dest_path.unlink()
        elif dest_path.is_dir():
            shutil.rmtree(dest_path)
        return True, f"Removed from {dest_path}"
    except Exception as e:
        return False, f"Failed to remove {dest_path}: {e}"


def check_status(skills: Dict[str, Path], custom_home: Optional[Path] = None):
    print("\n================ RESEARCH AGENT SKILLS STATUS ================")
    headers = f"{'Skill Name':<24}" + "".join(f"{agent:<14}" for agent in AGENT_DIRS.keys())
    print(headers)
    print("-" * len(headers))

    for name in sorted(skills.keys()):
        row = f"{name:<24}"
        for agent in AGENT_DIRS.keys():
            target_base = resolve_agent_path(agent, custom_home)
            skill_dest = target_base / name
            if skill_dest.is_symlink():
                row += f"{'[symlink]':<14}"
            elif skill_dest.is_dir():
                row += f"{'[installed]':<14}"
            else:
                row += f"{'-':<14}"
        print(row)
    print("==============================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Universal multi-agent skill installer for research-agent-skills.")
    parser.add_argument("skills", nargs="*", help="Specific skill name(s) to install (default: all)")
    parser.add_argument("--agent", "-a", choices=list(AGENT_DIRS.keys()) + ["all"], default="all",
                        help="Target agent ecosystem (default: all)")
    parser.add_argument("--symlink", "-s", action="store_true",
                        help="Create symbolic links instead of copying (recommended for skill developers)")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall specified skills")
    parser.add_argument("--status", action="store_true", help="Display current installation status across all agents")
    parser.add_argument("--target-dir", help="Install directly to a custom destination directory")

    args = parser.parse_args()
    repo_root = get_repo_root()
    available_skills = discover_skills(repo_root)

    if not available_skills:
        print("No valid skills discovered in skills/ directory.", file=sys.stderr)
        sys.exit(1)

    if args.status:
        check_status(available_skills)
        sys.exit(0)

    # Filter target skills
    selected_names = args.skills if args.skills else list(available_skills.keys())
    for name in selected_names:
        if name not in available_skills:
            print(f"Error: Unknown skill '{name}'. Available: {', '.join(available_skills.keys())}", file=sys.stderr)
            sys.exit(1)

    # Determine target directories
    target_dirs = []
    if args.target_dir:
        target_dirs.append(Path(args.target_dir).resolve())
    elif args.agent == "all":
        for a in AGENT_DIRS.keys():
            target_dirs.append(resolve_agent_path(a))
    else:
        target_dirs.append(resolve_agent_path(args.agent))

    # Execute action
    action_label = "Uninstalling" if args.uninstall else ("Symlinking" if args.symlink else "Installing")
    print(f"\n{action_label} {len(selected_names)} skill(s) across {len(target_dirs)} location(s)...")

    overall_success = True
    for sname in selected_names:
        src = available_skills[sname]
        for tdir in target_dirs:
            if args.uninstall:
                success, msg = uninstall_skill(sname, tdir)
            else:
                success, msg = install_skill(sname, src, tdir, symlink=args.symlink)

            status_icon = "✅" if success else "⚠️"
            print(f"  {status_icon} [{sname}] {msg}")
            if not success and not args.uninstall:
                overall_success = False

    print("\nDone.")
    if not overall_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
