# Roadmap

This roadmap tracks the planned work for `research-agent-skills`. New ideas are first triaged in the **Ideas / Inbox** section before being prioritized.

---

## Now
- **Repository foundation & governance:** Establish directory layout, supervision agreement, CI/test harness, and PR template ([Issue #1](https://github.com/jakkzz/research-agent-skills/issues/1)).
- **Skill specification validator:** Lightweight test suite enforcing Open Agent Skills standard (`SKILL.md` frontmatter, kebab-case naming, script execution).

## Next
- **Citation integrity MVP (`skills/citation-integrity`):** First vertical slice verifying LaTeX/Markdown citations against `.bib` or CrossRef/arXiv references with zero hallucinations.
- **Claude and Hermes installation verification:** Real-agent runtime verification scripts ensuring skills install and execute without manual path tweaking.

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
