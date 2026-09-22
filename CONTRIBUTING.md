# Contributing & Supervision Working Agreement

This repository operates under a strict **Human-in-the-Loop Supervision Model**. The user (**Jakkrit**) serves as Product Owner and Principal Reviewer; the AI agent serves as Researcher, Architect, Implementer, Tester, and Documentation Maintainer.

---

## Core Rules

1. **Never Develop Directly on `main`**
   - Every single task begins with a GitHub Issue defining acceptance criteria.
   - Work happens on a short-lived topic branch (`foundation/*`, `feat/*`, `fix/*`, `spike/*`).
   - Work merges into `main` **only** after an approved Pull Request.

2. **One PR Answers Five Questions**
   Every Pull Request must explicitly answer:
   - What changed?
   - Why?
   - How was it tested? (Exact commands and agent checks)
   - What remains incomplete?
   - What decision do I need from Jakkrit?

3. **Acceptance Criteria Before Coding**
   - Issues must articulate the "Definition of Done" before writing implementation code.
   - Code must be verified against concrete tests and artifacts, not assumed progress.

4. **Roadmap & ADR Discipline**
   - New ideas go to `docs/ROADMAP.md` under **Ideas / Inbox** first.
   - Architectural shifts require an entry in `docs/DECISIONS.md`.
   - Never repeatedly debate settled decisions unless explicitly reopened.

5. **Empirical Verification Only**
   - `COMPATIBILITY.md` claims must be backed by real runtime testing on the target agent, not hypothetical compatibility.
   - Generated documents (e.g. DOCX/PDF) require visual inspection against approved golden samples.

---

## Branch Naming Conventions
- `foundation/<name>`: Core repo infrastructure and tooling
- `feat/<skill-name>/<capability>`: New feature or vertical slice
- `fix/<issue-number>-<name>`: Bugfix
- `spike/<investigation-name>`: Time-boxed exploratory research or feasibility prototype
