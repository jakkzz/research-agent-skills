# Architectural Decision Records (ADR)

## Decisions

### D-001: Use Modular, Composable Skills Instead of One Monolithic Skill
- **Date:** 2026-09-21
- **Status:** Accepted
- **Decision:** Keep literature discovery, citation checks, DOCX generation, and manuscript preflight in separate skill packages.
- **Reason:** Independent packages constrain context and allow targeted installation and testing.
- **Alternatives Considered:** One academic-research package.
- **Consequences:** Shared conventions and cross-skill integration require explicit maintenance.

### D-002: Default to Copy Installation and Make Symlinks Opt-In
- **Date:** 2026-09-21
- **Status:** Accepted
- **Decision:** Copy through sibling staging with rollback by default; expose symlinks only through `--symlink`.
- **Reason:** Copies are portable across common filesystem and sandbox boundaries, while staging protects existing destinations during replacement.
- **Alternatives Considered:** Symlink-only installation and direct in-place copy.
- **Consequences:** Copied installs require an explicit reinstall to receive updates and are tracked in a state manifest.

### D-003: Start with Deterministic Citation-Key Checks
- **Date:** 2026-09-21
- **Status:** Accepted
- **Decision:** Make citation-key consistency the first vertical slice and keep DOI/arXiv retrieval explicit.
- **Reason:** Key presence and absence are testable without pretending to verify metadata, retractions, or claim support.
- **Alternatives Considered:** Starting with literature search or document generation.
- **Consequences:** Users must independently validate source identity, quality, and relevance.

### D-004: Prefer Scholarly Clarity over Detector-Evasion Features
- **Date:** 2026-09-21
- **Status:** Accepted
- **Decision:** Do not implement AI-detector evasion; limit writing checks to transparent lexical and structural indicators.
- **Reason:** Obfuscation does not establish scientific quality or authorship.
- **Alternatives Considered:** Detector-targeted paraphrasing.
- **Consequences:** The project makes no claim that text is human-authored or detector-safe.

### D-005: Use Truthful Alpha Maturity and Claims Policy
- **Date:** 2026-09-23
- **Status:** Accepted
- **Decision:** Label the project alpha; make claims no stronger than committed evidence; distinguish filesystem installation, runtime discovery, and invocation; describe deterministic findings as indicators rather than semantic judgments.
- **Reason:** Unit tests and API responses cannot establish universal runtime support, publication quality, factual correctness, or institution-specific compliance.
- **Alternatives Considered:** Inferring compatibility from path resolution and retaining aspirational product claims.
- **Consequences:** Compatibility remains Pending without live-runtime evidence, outputs carry limitations, and documentation must be updated when evidence or scope changes.
