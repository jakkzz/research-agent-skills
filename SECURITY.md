# Security Policy

## Alpha status

This repository is alpha software. Do not treat generated documents, citation reports, search records, or manuscript preflight findings as authoritative. Review outputs before using them in academic or institutional workflows.

## Supported versions

Security fixes are applied to the current default branch only while the project remains alpha.

## Reporting a vulnerability

Report suspected vulnerabilities privately through GitHub's security advisory interface for this repository. Include affected paths, reproduction steps, impact, and any suggested mitigation. Do not include sensitive manuscripts, credentials, API tokens, or unpublished research in a public issue.

## Operational cautions

- The installer refuses existing destinations by default and tracks owned installs. Review `--force`, `--symlink`, and project-root targets before use.
- Literature and identifier tools contact arXiv, Crossref, DOI, or related endpoints. Their responses are untrusted external data and require validation.
- DOCX output references a local font but does not embed it.
