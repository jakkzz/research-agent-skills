# research-agent-skills

> **Alpha:** interfaces, output schemas, and installation behavior may change. Human validation remains required.

This repository formerly published modular research workflow skills using `SKILL.md` packages. Those skills have been removed and no installable skills are currently published.

## Status

The former citation integrity, literature discovery, Thai DOCX, and manuscript preflight skills are no longer distributed from this repository. The installer framework is retained for historical maintenance and regression coverage.

## Installation

There are currently no skills to install.

## Validation

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
```

The remaining tests cover the generic installer framework.

## Project records

- [Roadmap](docs/ROADMAP.md)
- [Architectural decisions](docs/DECISIONS.md)
- [Compatibility evidence policy](COMPATIBILITY.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT License; see [LICENSE](LICENSE).
