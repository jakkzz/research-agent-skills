---
name: academic-peer-reviewer
description: 'Runs deterministic lexical and structural manuscript preflight checks with evidence spans. Use when reviewing Markdown or LaTeX drafts before human editorial review, including a Reviewer #2-style preflight.'
---

# Academic Peer Reviewer

> Alpha deterministic preflight; not peer review and not a publication decision.

The script identifies an Introduction by common Markdown or LaTeX headings, reports lexical indicators for CARS moves, and flags selected promotional or vague phrases with line evidence. It does not evaluate novelty, ground truth, methodology, mathematics, statistics, citation validity, or claim support.

## When to use

Use it to identify passages requiring human review before submission. Treat present and absent indicators as prompts, not semantic conclusions.

```bash
python3 scripts/review_manuscript.py draft.md
python3 scripts/review_manuscript.py draft.md --json
python3 scripts/review_manuscript.py draft.md --strict
```

`--strict` exits nonzero when the preflight status is `review-needed`. A `pass-with-warnings` status only means configured deterministic checks found no review trigger; it is not acceptance, approval, or readiness for publication.
