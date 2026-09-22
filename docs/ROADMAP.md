# Roadmap

This roadmap tracks the planned work for `research-agent-skills`. New ideas are first triaged in the **Ideas / Inbox** section before being prioritized.

---

## Now
- **Repository foundation & governance:** [Completed] Establish directory layout, supervision agreement, CI/test harness, and PR template ([Issue #1](https://github.com/jakkzz/research-agent-skills/issues/1)).
- **Skill specification validator:** [Completed] Lightweight test suite enforcing Open Agent Skills standard (`SKILL.md` frontmatter, kebab-case naming, script execution).
- **Citation integrity MVP (`skills/citation-integrity`):** [Completed] First vertical slice verifying LaTeX/Markdown citations against `.bib` or CrossRef/arXiv references with zero hallucinations ([Issue #3](https://github.com/jakkzz/research-agent-skills/issues/3)).
- **Cross-agent universal installer (`install.sh` / `scripts/install.py`):** [In Progress] Real-agent installation scripts ensuring skills install and execute across Claude Code, Hermes, Pi/OhMyPi, Google Antigravity, and Codex without manual path tweaking ([Issue #5](https://github.com/jakkzz/research-agent-skills/issues/5)).

## Next
- **Literature discovery (`skills/literature-discovery`):** Direct querying of arXiv, Semantic Scholar, and CrossRef APIs with structured JSON/BibTeX outputs.
- **Thai academic DOCX formatting (`skills/thai-academic-docx`):** Template-first DOCX generator adhering to Thai academic typography (TH Sarabun New, 1.5 line spacing, Buddhist Era dating, table layouts).

## Later
- **Literature discovery (`skills/literature-discovery`):** Direct querying of arXiv, Semantic Scholar, and CrossRef APIs with structured JSON/BibTeX outputs.
- **Manuscript structure & CARS model (`skills/manuscript-structure`):** Section-by-section engineering following the CARS (Create a Research Space) and IMRaD models.
- **Thai academic DOCX formatting (`skills/thai-academic-docx`):** Template-first DOCX generator adhering to Thai academic typography (TH Sarabun New, 1.5 line spacing, Buddhist Era dating, table layouts).
- **Adversarial peer reviewer (`skills/academic-peer-reviewer`):** "Reviewer #2" critique simulation evaluating novelty, methodology rigor, statistical claims, and baseline completeness.

## Ideas / Inbox
- University-specific thesis format profiles (e.g., NRRU, Chulalongkorn, Kasetsart).
- Thai government official correspondence document format (Saraban).
- Zotero local SQLite and cloud collection sync.
- TCI (Thai-Journal Citation Index) submission compliance profile.
- Automated rebuttal letter generator for journal revisions.
