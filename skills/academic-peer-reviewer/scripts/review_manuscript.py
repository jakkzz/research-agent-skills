#!/usr/bin/env python3
"""Deterministic lexical/structural manuscript preflight.

This tool reports indicators for human review. It does not assess novelty,
mathematical correctness, claim truth, or publication suitability.
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

HYPE_PATTERNS = [
    (r"\brevolutionary\b", "revolutionary", "notable / significant"),
    (r"\bgame-?changing\b", "game-changing", "substantive / influential"),
    (r"\bground-?breaking\b", "groundbreaking", "important / foundational"),
    (r"\bunprecedented\b", "unprecedented", "distinct / previously unobserved"),
    (r"\bflawless(?:ly)?\b", "flawless", "robust / consistent"),
    (r"\bmiraculous(?:ly)?\b", "miraculous", "effective / marked"),
    (r"\bparadigm-?shift(?:ing)?\b", "paradigm shift", "structural development"),
    (r"\bdisruptive\b", "disruptive", "novel / alternative"),
    (r"\bunquestionabl[ey]\b", "unquestionably", "evidently / clearly indicated"),
    (r"\bperfect(?:ly)?\b", "perfect", "optimal / reliable"),
]
VAGUE_QUANTIFIERS = [
    (r"\ba lot of\b", "a lot of", "use a measured quantity"),
    (r"\bhuge\b", "huge", "use a measured quantity"),
    (r"\btons of\b", "tons of", "use a measured quantity"),
    (r"\bvery (?:good|bad|big|small|high|low)\b", "very [adjective]", "report an exact metric"),
    (r"\bextremely (?:good|high|fast)\b", "extremely [adjective]", "report an exact metric"),
]
CARS_MOVE1_MARKERS = [r"\b(?:important|critical|central|widely studied|increasing attention)\b", r"\bprior (?:work|research|studies)\b"]
CARS_MOVE2_MARKERS = [
    r"\bhowever\b", r"\bnevertheless\b", r"\byet\b", r"\bdespite\b",
    r"\bremains? (?:challenging|unclear|limited)\b", r"\bresearch gap\b",
    r"\blimitation\b", r"\bdrawback\b", r"\bfails? to\b", r"\black of\b",
]
CARS_MOVE3_MARKERS = [
    r"\bin this (?:paper|study|work|article|thesis)\b", r"\bwe propose\b",
    r"\bwe introduce\b", r"\bwe present\b", r"\bthis research aims to\b",
    r"\bthe objective of this study\b",
]
LIMITATIONS = [
    "Findings are lexical and structural indicators, not publication decisions.",
    "The tool does not verify claims, citations, novelty, methods, statistics, or mathematics.",
    "CARS indicators require human interpretation and may produce false positives or negatives.",
]


def extract_introduction(text: str) -> Tuple[Optional[str], Optional[int], str]:
    """Return Introduction body, 1-based starting line, and extraction status."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        md = re.match(
            r"^\s*(#{1,6})\s+(?:\d+(?:\.\d+)*[.)]?\s+)?introduction\s*$",
            line,
            re.I,
        )
        if md:
            level = len(md.group(1))
            end = len(lines)
            for candidate in range(index + 1, len(lines)):
                next_heading = re.match(r"^\s*(#{1,6})\s+", lines[candidate])
                if next_heading and len(next_heading.group(1)) <= level:
                    end = candidate
                    break
            return "\n".join(lines[index + 1:end]), index + 2, "markdown-heading"
        latex = re.match(r"^\s*\\(chapter|section|section\*|subsection|subsection\*)\{\s*introduction\s*\}\s*$", line, re.I)
        if latex:
            command = latex.group(1).replace("*", "")
            rank = {"chapter": 1, "section": 2, "subsection": 3}[command]
            end = len(lines)
            for candidate in range(index + 1, len(lines)):
                heading = re.match(r"^\s*\\(chapter|section|section\*|subsection|subsection\*)\{", lines[candidate], re.I)
                if heading:
                    next_rank = {"chapter": 1, "section": 2, "subsection": 3}[heading.group(1).replace("*", "").lower()]
                    if next_rank <= rank:
                        end = candidate
                        break
            return "\n".join(lines[index + 1:end]), index + 2, "latex-heading"
    return None, None, "unknown-no-introduction-heading"


def _indicator_evidence(text: str, start_line: int, patterns: List[str]) -> List[Dict]:
    evidence = []
    for offset, line in enumerate(text.splitlines()):
        for pattern in patterns:
            match = re.search(pattern, line, re.I)
            if match:
                evidence.append({
                    "line": start_line + offset,
                    "span": match.group(0),
                    "context": line.strip()[:160],
                })
    return evidence


def _language_findings(lines: List[str], patterns: List[Tuple[str, str, str]]) -> List[Dict]:
    findings = []
    for line_number, line in enumerate(lines, 1):
        for pattern, term, suggestion in patterns:
            for match in re.finditer(pattern, line, re.I):
                findings.append({
                    "line": line_number,
                    "term": term,
                    "span": match.group(0),
                    "context": line.strip()[:160],
                    "recommendation": suggestion,
                })
    return findings


def audit_manuscript(text: str, filename: str = "manuscript") -> Dict:
    lines = text.splitlines()
    word_count = len(re.findall(r"\b\w+\b", text))
    citations = re.findall(r"(?:\\cite\*?\{[^}]+\}|\[@[^\]]+\]|(?<![\w.\-])@[A-Za-z0-9_:.\-]+)", text)
    hype = _language_findings(lines, HYPE_PATTERNS)
    vague = _language_findings(lines, VAGUE_QUANTIFIERS)
    intro, intro_start, extraction = extract_introduction(text)

    cars: Dict[str, object] = {
        "introduction_extraction": extraction,
        "move_1_territory": None,
        "move_2_niche_gap_identified": None,
        "move_3_occupying_niche_declared": None,
        "evidence": {"move_1": [], "move_2": [], "move_3": []},
        "interpretation": "Indicators only; absence or presence is not a semantic CARS judgment.",
    }
    if intro is not None and intro_start is not None:
        move1 = _indicator_evidence(intro, intro_start, CARS_MOVE1_MARKERS)
        move2 = _indicator_evidence(intro, intro_start, CARS_MOVE2_MARKERS)
        move3 = _indicator_evidence(intro, intro_start, CARS_MOVE3_MARKERS)
        cars.update({
            "move_1_territory": bool(move1),
            "move_2_niche_gap_identified": bool(move2),
            "move_3_occupying_niche_declared": bool(move3),
            "evidence": {"move_1": move1, "move_2": move2, "move_3": move3},
        })

    empirical_keywords = ["accuracy", "rmse", "mape", "f1", "precision", "recall", "latency", "fps"]
    metrics = [item for item in empirical_keywords if re.search(rf"\b{item}\b", text, re.I)]
    comparative = [
        {"line": n, "span": match.group(0), "context": line.strip()[:160]}
        for n, line in enumerate(lines, 1)
        for match in re.finditer(r"\b(?:outperforms?|superior|much better|significantly higher)\b", line, re.I)
    ]
    reasons = []
    if intro is None:
        reasons.append("Introduction section could not be identified; CARS indicators are unknown.")
    else:
        for move, label in [
            ("move_1_territory", "Move 1"), ("move_2_niche_gap_identified", "Move 2"),
            ("move_3_occupying_niche_declared", "Move 3"),
        ]:
            if cars[move] is False:
                reasons.append(f"No lexical indicator was found for {label} in the extracted Introduction.")
    if hype:
        reasons.append(f"Found {len(hype)} promotional-language indicator(s).")
    if vague:
        reasons.append(f"Found {len(vague)} vague-quantifier indicator(s).")
    if comparative and not metrics:
        reasons.append("Comparative language was found without a recognized metric token.")
    status = "review-needed" if reasons else "pass-with-warnings"
    density = len(citations) / word_count * 1000 if word_count else 0
    return {
        "manuscript": filename,
        "preflight_status": status,
        "status_reasons": reasons,
        "limitations": LIMITATIONS,
        "statistics": {
            "word_count": word_count,
            "paragraphs": len([p for p in text.split("\n\n") if p.strip()]),
            "citations_detected": len(citations),
            "citations_per_1000_words": round(density, 2),
        },
        "cars_model_assessment": cars,
        "hype_findings": hype,
        "vague_findings": vague,
        "metrics_found": metrics,
        "comparative_claims": comparative,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic lexical/structural manuscript preflight checks.")
    parser.add_argument("manuscript", help="Markdown or LaTeX manuscript path")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when preflight status is review-needed")
    args = parser.parse_args(argv)
    try:
        with open(args.manuscript, "r", encoding="utf-8") as handle:
            content = handle.read()
    except (OSError, UnicodeError) as exc:
        print(f"Error: cannot read manuscript {args.manuscript}: {exc}", file=sys.stderr)
        return 2
    report = audit_manuscript(content, os.path.basename(args.manuscript))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("MANUSCRIPT PREFLIGHT (indicators only; not a publication decision)")
        print(f"Manuscript: {report['manuscript']}")
        print(f"Status: {report['preflight_status']}")
        for reason in report["status_reasons"]:
            print(f"- {reason}")
        print("Limitations:")
        for limitation in report["limitations"]:
            print(f"- {limitation}")
    return 1 if args.strict and report["preflight_status"] == "review-needed" else 0


if __name__ == "__main__":
    sys.exit(main())
