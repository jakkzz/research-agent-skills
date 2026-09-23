---
name: literature-discovery
description: 'Discovers candidate literature records from arXiv and Crossref with explicit provider status. Use when assembling a search shortlist that will be independently checked for relevance, publication status, and metadata accuracy.'
---

# Literature Discovery

> Alpha candidate discovery; results are not labeled peer-reviewed or fully verified.

The standard-library CLI queries arXiv and Crossref. JSON output distinguishes successful zero-result searches, partial provider failure, and complete failure. Returned BibTeX is generated from provider data and requires independent checking.

```bash
python3 scripts/search_papers.py "traffic flow estimation" --limit 5
python3 scripts/search_papers.py "tracking" --source arxiv --json
python3 scripts/search_papers.py "object detection" --bib
python3 scripts/search_papers.py "object detection" --bib --append references.bib
```

`--limit` accepts 1–100 results. `--append` is valid only with `--bib`.

Use results to build a human-reviewed candidate list. Confirm identity, venue, publication status, relevance, and metadata at the linked source before citing or appending records.
