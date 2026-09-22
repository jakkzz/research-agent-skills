#!/usr/bin/env python3
"""
test_academic_peer_reviewer.py
Unit tests for the academic-peer-reviewer skill scripts.
Zero external dependencies.
"""

import os
import sys
import unittest

# Add script path to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "academic-peer-reviewer", "scripts")))

import review_manuscript


class TestAcademicPeerReviewer(unittest.TestCase):

    def test_hype_detection(self):
        sample = """
        Our revolutionary framework introduces a game-changing edge pipeline.
        The performance is flawless and unprecedented in modern benchmarks.
        """
        report = review_manuscript.audit_manuscript(sample)
        terms = [h["term"] for h in report["hype_findings"]]
        self.assertIn("revolutionary", terms)
        self.assertIn("game-changing", terms)
        self.assertIn("flawless", terms)
        self.assertIn("unprecedented", terms)
        self.assertLess(report["scores"]["scholarly_tone"], 3.5)

    def test_cars_model_detection(self):
        intro_compliant = """
        Traffic volume estimation is critical for urban infrastructure [@smith2020].
        However, existing embedded solutions struggle under adverse nighttime lighting and high occlusion.
        In this paper, we propose an edge-native YOLO and BoT-SORT tracking system to address these limitations.
        Our empirical experiments demonstrate 94.2% accuracy on highway intersections.
        """
        report = review_manuscript.audit_manuscript(intro_compliant)
        cars = report["cars_model_assessment"]
        self.assertTrue(cars["move_1_territory"])
        self.assertTrue(cars["move_2_niche_gap_identified"])
        self.assertTrue(cars["move_3_occupying_niche_declared"])
        self.assertEqual(report["scores"]["introduction_structure"], 5.0)

    def test_cars_model_missing_gap(self):
        intro_missing_gap = """
        Deep learning is very popular in computer vision [@jones2021].
        We introduce a convolutional network for vehicle detection.
        Results show 90% accuracy.
        """
        report = review_manuscript.audit_manuscript(intro_missing_gap)
        cars = report["cars_model_assessment"]
        self.assertFalse(cars["move_2_niche_gap_identified"])
        self.assertLess(report["scores"]["introduction_structure"], 4.0)

    def test_recommendation_outcome(self):
        bad_draft = "This revolutionary system is huge and flawless with tons of speed."
        report = review_manuscript.audit_manuscript(bad_draft)
        self.assertIn(report["recommendation"], ["Major Revision", "Reject / Resubmit"])


if __name__ == "__main__":
    unittest.main()
