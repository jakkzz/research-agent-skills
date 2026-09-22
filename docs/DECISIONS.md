# Architectural Decision Records (ADR)

This document records the foundational architectural decisions for `research-agent-skills`. Each entry explains the context, rationale, trade-offs, and consequences.

---

### D-001: Use Modular, Composable Skills Instead of One Monolithic Skill
- **Date:** 2026-09-21
- **Status:** Accepted
- **Context:** Academic research workflows encompass literature discovery, structural drafting, citation verification, Thai DOCX formatting, and peer review. We considered packaging everything into a single massive `academic-research` skill.
- **Decision:** Deconstruct the domain into focused, composable, single-purpose skills (`skills/citation-integrity`, `skills/thai-academic-docx`, etc.).
- **Reason:** Monolithic agent skills overload context windows, create brittle tool schemas, and make targeted updates difficult. Modular skills allow users and agents to install only what they need.
- **Alternatives Considered:** Monolithic mega-skill (rejected due to context bloat and poor tool-selection accuracy across smaller models).
- **Consequences:** Requires a consistent cross-skill contract, standardized directory conventions, and composable CLI scripts.

---

### D-002: Support Copy as the Default Installation Mode with Symlink as Developer Option
- **Date:** 2026-09-21
- **Status:** Accepted
- **Context:** AI agents run in varying environments—some within containerized sandboxes or remote servers, others in local developer terminals.
- **Decision:** The installer (`install.sh`) defaults to copying skills into agent target directories, but provides a `--symlink` flag for local development.
- **Reason:** Symlinks break across container boundaries, file-mount boundaries, and Windows/WSL interoperability layers. Copying ensures absolute isolation and portability by default.
- **Alternatives Considered:** Symlink-only (fails in Docker/isolated agent sandboxes).
- **Consequences:** When running in copy mode, updates require re-running `./install.sh`.

---

### D-003: Citation Integrity Is the First Vertical Slice
- **Date:** 2026-09-21
- **Status:** Accepted
- **Context:** We need a concrete, testable capability to validate our multi-agent installation and execution pipeline before expanding to more complex tasks.
- **Decision:** Build `skills/citation-integrity` as the first vertical slice.
- **Reason:** Citation checking has deterministic inputs (`.tex`, `.md`, `.bib`), objective outputs (pass/fail, missing keys, hallucination warnings), and requires no heavy external machine learning models.
- **Alternatives Considered:** Starting with literature discovery or Thai DOCX formatting.
- **Consequences:** Provides a battle-tested baseline for testing Claude, Hermes, Pi, and Gemini before tackling complex visual or generative tasks.

---

### D-004: Anti-AI Rhetorical Cleanup Focused on Scholarly Rigor Rather Than Watermark Gaming
- **Date:** 2026-09-21
- **Status:** Accepted
- **Context:** Many writing tools attempt to "bypass AI detectors" using obfuscation or random synonym insertion, which severely degrades scientific clarity.
- **Decision:** The project explicitly scopes "humanizing" as eradicating hollow rhetoric (AI clichés like *delve, testament, pivotal, multifaceted*), enforcing precise claim-evidence alignment, and maintaining authentic scholarly voice. We will not build brittle detector-evasion tricks.
- **Reason:** Scientific credibility depends on precision and evidence, not on tricking statistical perplexity detectors.
- **Alternatives Considered:** Adopting third-party AI bypass paraphrasers (rejected as unscholarly).
- **Consequences:** All polishing tools focus on technical rigor, brevity, and active/passive voice balance.
