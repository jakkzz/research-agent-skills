---
name: citation-integrity
description: 'Checks citation-key consistency between Markdown or LaTeX manuscripts and BibTeX files. Use when auditing missing, duplicate, or unreferenced keys or explicitly looking up a known DOI or arXiv identifier.'
---

# Citation Integrity

> Alpha key-consistency tooling; it does not verify metadata, retractions, source quality, or claim support.

## Citation-key check

```bash
python3 scripts/verify_citations.py draft.md --bib references.bib
python3 scripts/verify_citations.py draft.md --bib references.bib --strict --json
```

The checker reports matched and missing citation keys, unreferenced BibTeX entries, duplicate keys with source locations, and input errors. `\\nocite{*}` intentionally marks all parsed BibTeX entries as referenced. Missing/unreadable inputs, zero scanned manuscripts, and zero parsed entries fail.

## Explicit identifier lookup

```bash
python3 scripts/fetch_doi.py 10.1145/3372278.3390678
python3 scripts/fetch_doi.py 2301.00001 --append references.bib
```

Lookup retrieves candidate BibTeX from DOI or arXiv endpoints for a supplied identifier. Independently inspect the returned record and source before citing it.
