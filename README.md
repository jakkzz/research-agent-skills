# research-agent-skills

> Portable, evidence-grounded academic research skills for multi-agent AI ecosystems (Claude Code, Hermes, Pi/OhMyPi, Google Antigravity, and OpenAI Codex).

---

## Overview

`research-agent-skills` is a modular collection of specialized skills adhering to the open **Agent Skills Specification** (`SKILL.md`). Rather than building a brittle monolithic assistant, this repository provides discrete, composable capabilities engineered specifically for scientific research, academic drafting, citation verification, and institutional formatting.

## Core Capabilities on the Roadmap

- **Citation Integrity (`skills/citation-integrity`):** High-precision validation cross-referencing inline citations in LaTeX and Markdown against `.bib` databases and official registries (CrossRef, arXiv) with zero tolerance for hallucinations.
- **Thai Academic DOCX (`skills/thai-academic-docx`):** Template-first DOCX generator adhering to Thai academic typography (TH Sarabun New, 1.5 spacing, Buddhist Era dating, table borders, and university thesis guidelines).
- **Literature Discovery (`skills/literature-discovery`):** Deterministic query wrappers for arXiv, Semantic Scholar, and PubMed.
- **Adversarial Peer Reviewer (`skills/academic-peer-reviewer`):** "Reviewer #2" critique simulation evaluating novelty, baseline comparisons, mathematical consistency, and threats to validity.

## Project Governance & Transparency

This project is developed under a strict **Human-in-the-Loop Supervision Model**:
- **[docs/ROADMAP.md](docs/ROADMAP.md):** Visible backlog divided into *Now*, *Next*, *Later*, and *Ideas / Inbox*.
- **[docs/DECISIONS.md](docs/DECISIONS.md):** Architectural Decision Records (ADR) explaining why choices were made.
- **[COMPATIBILITY.md](COMPATIBILITY.md):** Multi-agent verification matrix tracking empirical tests on target runtimes.
- **[CONTRIBUTING.md](CONTRIBUTING.md):** Working agreement governing issues, short-lived branches, and pull requests.

## Running Tests

All governance and skill specification tests use standard Python `unittest` with zero third-party dependencies:

```bash
python3 -m unittest discover tests
```

## License

MIT License (see [LICENSE](LICENSE)).
