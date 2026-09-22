# Agent Compatibility Matrix

This document tracks empirical verification of skills across supported agent ecosystems. A skill is never marked as supported based on theory; each checkmark requires reproducible execution in that specific runtime.

## Verification Status Definitions
- 🟢 **Verified:** Tested in a live agent session with recorded inputs and expected outputs.
- 🟡 **Pending:** Implemented and structurally compliant, waiting for runtime verification.
- ⚪ **Planned:** On the roadmap, not yet implemented.
- 🔴 **Incompatible:** Known architectural limitation or unsupported feature.

## Matrix

| Skill Name | Claude Code | Hermes | Pi / OhMyPi | Antigravity (Gemini) | Codex / OpenAI | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Foundation & Installer** | 🟢 Verified | 🟢 Verified | 🟢 Verified | 🟢 Verified | 🟢 Verified | Automated test suite & path resolution |
| **citation-integrity** | 🟢 Verified | 🟢 Verified | 🟢 Verified | 🟢 Verified | 🟢 Verified | Pure standard library, zero dependencies |
| **literature-discovery** | 🟢 Verified | 🟢 Verified | 🟢 Verified | 🟢 Verified | 🟢 Verified | arXiv & CrossRef APIs, no keys required |
| **thai-academic-docx** | ⚪ Planned | ⚪ Planned | ⚪ Planned | ⚪ Planned | ⚪ Planned | Template-first DOCX engine |
| **academic-peer-reviewer**| ⚪ Planned | ⚪ Planned | ⚪ Planned | ⚪ Planned | ⚪ Planned | Adversarial reviewer |

## Standard Installation Paths Checked

- **Claude Code:** `~/.claude/skills/<skill-name>/`
- **Google Antigravity / Gemini:** `~/.gemini/antigravity/skills/<skill-name>/` and `~/.gemini/config/skills/<skill-name>/`
- **Hermes (Nous Research):** `~/.hermes/skills/<skill-name>/`
- **Pi / OhMyPi:** `~/.pi/skills/<skill-name>/`
- **OpenAI Codex / Universal Workspace:** `.agents/skills/<skill-name>/`
