---
name: citation-integrity
description: Validates academic citations in LaTeX and Markdown manuscripts against BibTeX reference databases, detects phantom/hallucinated citations, and resolves verified entries via DOI and arXiv APIs.
---

# Citation Integrity

Ensures 100% citation fidelity in academic manuscripts (theses, conference papers, journal articles). Eliminates AI reference hallucinations by enforcing bi-directional cross-referencing between manuscript prose and validated BibTeX entries.

## When to Use
- Auditing an existing paper, literature review, or thesis chapter before submission.
- Detecting hallucinated citations in text generated or modified by LLMs.
- Checking for unused BibTeX entries in `.bib` databases.
- Resolving verified BibTeX entries directly from DOI or arXiv identifiers.

## Tools and Scripts Included

### 1. Citation Audit Engine (`scripts/verify_citations.py`)
Scans Markdown (`[@key]`, `@key`) and LaTeX (`\cite{key}`, `\citep{key}`, `\citet{key}`, `\autocite{key}`) documents against one or more `.bib` files.

```bash
python3 scripts/verify_citations.py <manuscript-file-or-dir> --bib references.bib
```

**Options:**
- `--bib, -b <file.bib...>`: One or more BibTeX database files.
- `--json`: Output machine-readable JSON for agent parsing.
- `--strict`: Fail with exit code `1` if duplicate keys or unreferenced entries are found.

### 2. Identifier Resolver (`scripts/fetch_doi.py`)
Resolves DOIs or arXiv identifiers to verified BibTeX entries using official endpoints (CrossRef Content Negotiation and arXiv Export API).

```bash
# Fetch BibTeX from DOI
python3 scripts/fetch_doi.py 10.1145/3372278.3390678

# Fetch BibTeX from arXiv ID and append to references.bib
python3 scripts/fetch_doi.py 2301.00001 --append references.bib
```

## Step-by-Step Agent Workflow

1. **Scan Manuscript for Citations:**
   Run `verify_citations.py` on the target draft:
   ```bash
   python3 scripts/verify_citations.py draft.md --bib references.bib --json
   ```
2. **Review Missing Citations:**
   If `missing_citations` is non-empty, do **NOT** fabricate citations or make up author names.
   For each missing citation:
   - Ask the researcher for the paper's DOI / arXiv ID, or
   - Use `fetch_doi.py` to fetch verified metadata from official repositories.
3. **Audit Duplicate and Unreferenced Keys:**
   - Remove or merge duplicate keys in the `.bib` file.
   - Clean up unreferenced entries if preparing a final submission package.
4. **Final Verification:**
   Re-run with `--strict` to ensure zero missing citations and clean reference hygiene:
   ```bash
   python3 scripts/verify_citations.py draft.md --bib references.bib --strict
   ```
