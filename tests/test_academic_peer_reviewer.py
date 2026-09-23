#!/usr/bin/env python3
"""Tests for deterministic manuscript preflight safety."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "academic-peer-reviewer", "scripts")))
import review_manuscript


class TestAcademicPeerReviewer(unittest.TestCase):
    def test_hype_detection_has_evidence_span(self):
        report = review_manuscript.audit_manuscript(
            "# Introduction\nOur revolutionary framework is flawless and unprecedented."
        )
        terms = [finding["term"] for finding in report["hype_findings"]]
        self.assertEqual(terms, ["revolutionary", "unprecedented", "flawless"])
        self.assertEqual(report["hype_findings"][0]["span"].lower(), "revolutionary")
        self.assertEqual(report["preflight_status"], "review-needed")

    def test_cars_indicators_use_extracted_markdown_introduction(self):
        manuscript = """# Abstract
However, this abstract has a gap and we propose something.

# Introduction
Traffic estimation is critical for infrastructure [@smith2020].
However, existing systems remain limited under occlusion.
In this paper, we propose an edge-native tracking system.

# Methods
Method text.
"""
        report = review_manuscript.audit_manuscript(manuscript)
        cars = report["cars_model_assessment"]
        self.assertEqual(cars["introduction_extraction"], "markdown-heading")
        self.assertTrue(cars["move_1_territory"])
        self.assertTrue(cars["move_2_niche_gap_identified"])
        self.assertTrue(cars["move_3_occupying_niche_declared"])
        self.assertTrue(cars["evidence"]["move_2"])
        self.assertEqual(report["preflight_status"], "pass-with-warnings")

    def test_dotted_numbered_introduction_heading_is_recognized(self):
        introduction, start, status = review_manuscript.extract_introduction(
            "# 1. Introduction\nPrior research is important.\n# 2. Methods\nMethod text."
        )
        self.assertEqual(status, "markdown-heading")
        self.assertEqual(start, 2)
        self.assertEqual(introduction, "Prior research is important.")

    def test_missing_introduction_is_unknown_not_assumed_true(self):
        report = review_manuscript.audit_manuscript(
            "Traffic research is critical. However, a gap remains. In this paper, we propose X."
        )
        cars = report["cars_model_assessment"]
        self.assertIsNone(cars["move_1_territory"])
        self.assertIsNone(cars["move_2_niche_gap_identified"])
        self.assertIsNone(cars["move_3_occupying_niche_declared"])
        self.assertEqual(report["preflight_status"], "review-needed")

    def test_latex_introduction_is_bounded_by_next_section(self):
        text = r"""\section{Introduction}
Prior research is important. However, a limitation remains. We propose an approach.
\section{Methods}
This paper has no gap.
"""
        intro, start, status = review_manuscript.extract_introduction(text)
        self.assertEqual(status, "latex-heading")
        self.assertEqual(start, 2)
        self.assertNotIn("Methods", intro)

    def test_marker_only_sentence_cannot_receive_pass_like_status(self):
        report = review_manuscript.audit_manuscript(
            "# Introduction\nHowever gap limitation. In this paper, we propose."
        )
        self.assertFalse(report["cars_model_assessment"]["move_1_territory"])
        self.assertEqual(report["preflight_status"], "review-needed")
        self.assertNotIn("recommendation", report)
        self.assertNotIn("scores", report)

    def test_strict_fails_only_review_needed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "draft.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("No identified introduction.")
            self.assertEqual(review_manuscript.main([path, "--strict", "--json"]), 1)


if __name__ == "__main__":
    unittest.main()
