#!/usr/bin/env python3
"""
review_manuscript.py
Adversarial academic peer-review simulation ("Reviewer #2") and manuscript auditor.
Evaluates CARS model adherence, hype detection, unsubstantiated claims, and scholarly rigor.
Zero external dependencies.
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Tuple


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
    (r"\ba lot of\b", "a lot of", "numerous / substantial"),
    (r"\bhuge\b", "huge", "substantial / extensive"),
    (r"\btons of\b", "tons of", "numerous / abundant"),
    (r"\bvery (?:good|bad|big|small|high|low)\b", "very [adjective]", "quantify with exact metrics"),
    (r"\bextremely (?:good|high|fast)\b", "extremely [adjective]", "substantially / markedly"),
]

CARS_MOVE2_MARKERS = [
    r"\bhowever\b", r"\bnevertheless\b", r"\byet\b", r"\bdespite\b",
    r"\bremains? (?:challenging|unclear|limited)\b", r"\bgap\b",
    r"\blimitation\b", r"\bdrawback\b", r"\bfails? to\b", r"\black of\b"
]

CARS_MOVE3_MARKERS = [
    r"\bin this (?:paper|study|work|article|thesis)\b",
    r"\bwe propose\b", r"\bwe introduce\b", r"\bwe present\b",
    r"\bthis research aims to\b", r"\bthe objective of this study\b"
]


def audit_manuscript(text: str, filename: str = "manuscript") -> Dict:
    lines = text.splitlines()
    word_count = len(re.findall(r"\b\w+\b", text))
    paragraph_count = len([p for p in text.split("\n\n") if p.strip()])

    # Citation counts
    citations = re.findall(r"(?:\\cite\*?\{[^}]+\}|\[@[^\]]+\]|(?<![\w\.\-])@[a-zA-Z0-9_:\.\-]+)", text)
    citation_density = (len(citations) / word_count * 1000) if word_count > 0 else 0

    # Hype detection
    hype_findings = []
    for line_num, line in enumerate(lines, 1):
        for pat, word, suggestion in HYPE_PATTERNS:
            if re.search(pat, line, re.IGNORECASE):
                hype_findings.append({
                    "line": line_num,
                    "term": word,
                    "context": line.strip()[:100],
                    "recommendation": f"Replace with more neutral academic phrasing (e.g., '{suggestion}')."
                })

    # Vague language
    vague_findings = []
    for line_num, line in enumerate(lines, 1):
        for pat, term, suggestion in VAGUE_QUANTIFIERS:
            if re.search(pat, line, re.IGNORECASE):
                vague_findings.append({
                    "line": line_num,
                    "term": term,
                    "context": line.strip()[:100],
                    "recommendation": f"Avoid informal or vague quantifiers. {suggestion}."
                })

    # CARS Model check in Introduction (first 25% of text or section starting with Introduction)
    intro_sample = text[: max(int(len(text) * 0.35), 2000)]
    has_move2 = any(re.search(pat, intro_sample, re.IGNORECASE) for pat in CARS_MOVE2_MARKERS)
    has_move3 = any(re.search(pat, intro_sample, re.IGNORECASE) for pat in CARS_MOVE3_MARKERS)

    # Statistical & Empirical rigor checks
    empirical_keywords = ["accuracy", "rmse", "mape", "f1", "precision", "recall", "map", "latency", "fps"]
    metrics_found = [m for m in empirical_keywords if re.search(rf"\b{m}\b", text, re.IGNORECASE)]

    comparative_claims = re.findall(r"\b(?:outperforms?|superior|much better|significantly higher)\b", text, re.IGNORECASE)

    # Scoring out of 5
    tone_score = max(1.0, 5.0 - (len(hype_findings) * 0.5) - (len(vague_findings) * 0.2))
    structure_score = 5.0
    if not has_move2:
        structure_score -= 1.5
    if not has_move3:
        structure_score -= 1.0

    evidence_score = 5.0
    if comparative_claims and not metrics_found:
        evidence_score -= 2.0
    if citation_density < 5.0 and word_count > 300:
        evidence_score -= 1.5

    overall_avg = (tone_score + structure_score + evidence_score) / 3.0

    if overall_avg >= 4.2 and not hype_findings:
        recommendation = "Accept / Minor Revision"
    elif overall_avg >= 3.0:
        recommendation = "Major Revision"
    else:
        recommendation = "Reject / Resubmit"

    return {
        "manuscript": filename,
        "statistics": {
            "word_count": word_count,
            "paragraphs": paragraph_count,
            "citations_detected": len(citations),
            "citations_per_1000_words": round(citation_density, 2)
        },
        "cars_model_assessment": {
            "move_1_territory": True,
            "move_2_niche_gap_identified": has_move2,
            "move_3_occupying_niche_declared": has_move3
        },
        "scores": {
            "scholarly_tone": round(tone_score, 1),
            "introduction_structure": round(structure_score, 1),
            "empirical_evidence_support": round(evidence_score, 1),
            "overall_rating": round(overall_avg, 1)
        },
        "recommendation": recommendation,
        "hype_findings": hype_findings,
        "vague_findings": vague_findings,
        "metrics_found": metrics_found,
        "comparative_claims_count": len(comparative_claims)
    }


def main():
    parser = argparse.ArgumentParser(description="Adversarial peer review and academic quality auditor.")
    parser.add_argument("manuscript", help="Path to manuscript file (.md, .tex)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="Exit with code 1 if Major Revision or Reject")

    args = parser.parse_args()

    if not os.path.isfile(args.manuscript):
        print(f"Error: File not found: {args.manuscript}", file=sys.stderr)
        sys.exit(1)

    with open(args.manuscript, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    report = audit_manuscript(content, filename=os.path.basename(args.manuscript))

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        stats = report["statistics"]
        scores = report["scores"]
        cars = report["cars_model_assessment"]

        print("\n================ ADVERSARIAL PEER REVIEW REPORT ================")
        print(f"Manuscript:     {report['manuscript']}")
        print(f"Word Count:     {stats['word_count']} words | Citations: {stats['citations_detected']} ({stats['citations_per_1000_words']} / 1k words)")
        print(f"Recommendation: {report['recommendation']}")
        print("-----------------------------------------------------------------")
        print(f"  • Scholarly Tone & Objectivity:      {scores['scholarly_tone']} / 5.0")
        print(f"  • Introduction CARS Structure:       {scores['introduction_structure']} / 5.0")
        print(f"  • Empirical Evidence & Rigor:        {scores['empirical_evidence_support']} / 5.0")
        print(f"  • Overall Evaluation:                {scores['overall_rating']} / 5.0")
        print("=================================================================\n")

        # CARS Model Feedback
        print("🔍 CARS MODEL (INTRODUCTION ANALYSIS):")
        print(f"  - Move 1 (Establish Field / Importance):   {'✅ Present' if cars['move_1_territory'] else '❌ Weak'}")
        print(f"  - Move 2 (Identify Research Gap / Niche):   {'✅ Present' if cars['move_2_niche_gap_identified'] else '⚠️ Missing / Implicit'}")
        print(f"  - Move 3 (Declare Specific Contributions): {'✅ Present' if cars['move_3_occupying_niche_declared'] else '⚠️ Missing / Implicit'}")
        print()

        # Hype & Inflated claims
        if report["hype_findings"]:
            print(f"⚠️  UNSCHOLARLY HYPE / INFLATED CLAIMS ({len(report['hype_findings'])} found):")
            for h in report["hype_findings"]:
                print(f"  Line {h['line']}: '{h['term']}' -> {h['recommendation']}")
                print(f"    Context: \"{h['context']}\"")
            print()

        # Vague language
        if report["vague_findings"]:
            print(f"ℹ️  VAGUE QUANTIFIERS ({len(report['vague_findings'])} found):")
            for v in report["vague_findings"]:
                print(f"  Line {v['line']}: '{v['term']}' -> {v['recommendation']}")
            print()

        if not report["hype_findings"] and not report["vague_findings"] and cars["move_2_niche_gap_identified"]:
            print("✅ Manuscript demonstrates commendable scholarly restraint and structural compliance.")

    if args.strict and report["recommendation"] != "Accept / Minor Revision":
        sys.exit(1)


if __name__ == "__main__":
    main()
