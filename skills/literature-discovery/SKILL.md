---
name: literature-discovery
description: Discovers, searches, and extracts scholarly papers and verified BibTeX metadata from open academic repositories (arXiv and CrossRef) with zero hallucination.
---

# Literature Discovery

Enables autonomous agents to discover relevant peer-reviewed and preprint academic literature across scientific disciplines without requiring paid API keys. Resolves complete metadata, abstracts, and verified BibTeX records directly into research workflows.

## When to Use
- Gathering foundational and state-of-the-art literature for thesis chapters or paper introductions.
- Finding verified references for specific algorithms, benchmarks, or models (e.g., YOLO, BoT-SORT, ResNet).
- Extracting clean, verified BibTeX records directly to an existing `.bib` bibliography.
- Surveying competitive methods for methodology or related work sections.

## Tools and Scripts Included

### Scholarly Search Engine (`scripts/search_papers.py`)
Queries arXiv API and CrossRef REST API using pure Python standard library.

```bash
# Search for papers by topic
python3 scripts/search_papers.py "traffic flow estimation computer vision" --limit 5

# Search arXiv preprints only with a minimum year filter
python3 scripts/search_papers.py "BoT-SORT tracking" --source arxiv --min-year 2022

# Output verified BibTeX directly and append to references.bib
python3 scripts/search_papers.py "YOLOv8 real-time object detection" --bib --append references.bib

# Machine-readable JSON output for agent reasoning
python3 scripts/search_papers.py "edge coral tpu inference" --json
```

## Step-by-Step Agent Workflow

1. **Formulate Research Query:**
   Extract 3–5 high-signal keywords from the researcher's topic (e.g., `"deep sort vehicle tracking highway"`).
2. **Execute Search:**
   Run `search_papers.py` with `--limit 5` and `--json` to inspect abstracts and methodology summaries.
3. **Verify Relevance & Publication Date:**
   Ensure papers represent recognized baselines or recent peer-reviewed advances.
4. **Append Verified BibTeX:**
   Use `--bib --append <file.bib>` to integrate the papers into the project's bibliography without manual transcription errors.
5. **Cross-Check with Citation Integrity:**
   Run `verify_citations.py` to confirm that cited keys in the manuscript match the harvested BibTeX entries.
