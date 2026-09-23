# Agent compatibility (alpha)

Compatibility has separate layers:

1. **Filesystem path:** the installer resolves and writes the intended directory.
2. **Installation:** copy/symlink, manifest, rollback, and uninstall behavior succeeds.
3. **Discovery:** a live agent runtime finds the installed `SKILL.md` package.
4. **Invocation:** that runtime selects and executes the skill successfully.

Unit tests currently provide repository evidence for path resolution and installer behavior only. No committed live-runtime transcripts or fixtures establish discovery or invocation, so all runtime compatibility is **Pending**.

## Status definitions

- **Verified:** committed, reproducible evidence from the named live runtime covers the stated layer.
- **Pending:** not yet supported by committed runtime evidence.
- **Incompatible:** committed evidence shows a known conflict.

## Runtime matrix

| Runtime/surface | Filesystem/install | Discovery | Invocation |
| --- | --- | --- | --- |
| Claude Code | Tested in unit tests | Pending | Pending |
| Hermes | Tested in unit tests | Pending | Pending |
| Pi | Tested in unit tests | Pending | Pending |
| OhMyPi (`omp`) | Tested in unit tests | Pending | Pending |
| Gemini | Tested in unit tests | Pending | Pending |
| Antigravity | Tested in unit tests | Pending | Pending |
| Antigravity CLI | Tested in unit tests | Pending | Pending |
| Codex | Tested in unit tests | Pending | Pending |

## Primary path model

| Agent | User scope | Project scope |
| --- | --- | --- |
| `claude` | `~/.claude/skills` | `<project>/.claude/skills` |
| `hermes` | `$HERMES_HOME/skills` or `~/.hermes/skills` | `<project>/.hermes/skills` |
| `pi` | `~/.pi/agent/skills` | `<project>/.pi/skills` |
| `omp` | `~/.omp/agent/skills` | `<project>/.omp/skills` |
| `gemini` | `~/.gemini/skills` | `<project>/.gemini/skills` |
| `antigravity` | `~/.gemini/config/skills` | `<project>/.agents/skills` |
| `antigravity-cli` | `~/.gemini/antigravity-cli/skills` | `<project>/.agents/skills` |
| `codex` | `~/.agents/skills` | `<project>/.agents/skills` |

Shared project destinations are deduplicated. Paths are the installer's current model, not claims that each runtime will discover or invoke the package.
