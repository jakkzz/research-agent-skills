# Roadmap

This alpha roadmap distinguishes implemented repository behavior from unverified runtime compatibility.

## Now

- **Truthful alpha baseline:** Implemented on this branch; pending review. Includes safe installer ownership/rollback, correctness guardrails, claim cleanup, and cross-platform CI ([Issue #13](https://github.com/jakkzz/research-agent-skills/issues/13)).
- **Runtime evidence:** Pending. Capture reproducible discovery and invocation evidence before marking any agent compatibility Verified.

## Next

- Add live-runtime compatibility fixtures or transcripts with version and platform metadata.
- Improve BibTeX parsing coverage without claiming metadata or claim-support verification.
- Add explicit visual validation guidance and fixtures for the generic Thai DOCX preset.
- Add provider retry/rate-limit policy for arXiv and Crossref candidate discovery.

## Later

- Manuscript structure assistance for CARS and IMRaD, with clear heuristic limitations.
- Zotero and CSL integration.
- Optional additional literature providers after provider-specific tests and failure reporting exist.

## Ideas / Inbox

- University-specific thesis profiles backed by supplied, versioned institutional templates.
- Thai government correspondence profiles.
- TCI submission preflight profiles.
- Human-reviewed rebuttal drafting assistance.
