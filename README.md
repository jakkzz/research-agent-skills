# research-agent-skills

> **Alpha:** interfaces, output schemas, and installation behavior may change. Human validation remains required.

A standard-library-first collection of modular research workflow skills using `SKILL.md` packages. The repository currently provides deterministic utilities and API wrappers; it does not guarantee factual correctness, publication readiness, or compatibility with every agent runtime.

## Current alpha capabilities

- **citation-integrity:** checks citation-key consistency between Markdown/LaTeX and BibTeX; DOI/arXiv retrieval is a separate explicit lookup.
- **literature-discovery:** discovers candidate records from arXiv and Crossref and reports provider failures separately from zero results.
- **thai-academic-docx:** creates a minimal generic Thai-oriented DOCX preset. It is not a university-specific template.
- **academic-peer-reviewer:** runs deterministic lexical and structural preflight checks. Its findings are indicators, not peer-review or publication decisions.

## Installation

The cross-platform entry point is Python 3:

```bash
python3 scripts/install.py citation-integrity --agent hermes --scope user
python3 scripts/install.py literature-discovery --agent codex --scope project --project-root /path/to/project
```

Both `--agent` and `--scope` are required. Copy mode is the default; `--symlink` is opt-in. Existing destinations are refused unless `--force` is explicit. Installer-owned destinations are recorded in a JSON state manifest; `--state-path` can override its location. Uninstall requires explicit skill names and removes only manifest-owned destinations. Use `--dry-run` to preview.

`install.sh` is an optional Bash wrapper around the Python entry point:

```bash
./install.sh citation-integrity --agent claude --scope user --dry-run
```

See [COMPATIBILITY.md](COMPATIBILITY.md) for the path model and evidence status. Filesystem placement does not prove runtime discovery or invocation.

## Validation

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts skills tests
```

The tests exercise deterministic code paths and mocked providers. They are not committed evidence of live agent-runtime compatibility or external-service availability.

## Project records

- [Roadmap](docs/ROADMAP.md)
- [Architectural decisions](docs/DECISIONS.md)
- [Compatibility evidence policy](COMPATIBILITY.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT License; see [LICENSE](LICENSE).
