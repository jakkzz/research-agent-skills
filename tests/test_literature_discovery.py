#!/usr/bin/env python3
"""
test_literature_discovery.py
Unit tests for literature-discovery skill scripts with mocked network responses.
Zero external dependencies.
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add script path to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "literature-discovery", "scripts")))

import search_papers


class TestLiteratureDiscovery(unittest.TestCase):

    def test_clean_text(self):
        dirty = "  Attention \n\n  Is   All You Need   "
        self.assertEqual(search_papers.clean_text(dirty), "Attention Is All You Need")
        self.assertEqual(search_papers.clean_text(None), "")

    def test_generate_cite_key(self):
        authors = ["Ashish Vaswani", "Noam Shazeer"]
        year = "2017"
        title = "Attention Is All You Need"
        key = search_papers.generate_cite_key(authors, year, title)
        self.assertEqual(key, "vaswani2017attention")

    def test_generate_cite_key_fallback(self):
        key = search_papers.generate_cite_key([], "", "A Study of Something")
        self.assertEqual(key, "unknownndstudy")

    @patch("urllib.request.urlopen")
    def test_search_arxiv_mocked(self, mock_urlopen):
        sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
          <entry>
            <id>http://arxiv.org/abs/2206.14651v2</id>
            <title>BoT-SORT: Robust Associations Multi-Pedestrian Tracking</title>
            <summary>Tracking multiple objects in complex scenes.</summary>
            <author><name>Nir Aharon</name></author>
            <author><name>Roy Orfaig</name></author>
            <published>2022-06-29T17:59:34Z</published>
          </entry>
        </feed>"""

        mock_resp = MagicMock()
        mock_resp.read.return_value = sample_xml
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        results = search_papers.search_arxiv("BoT-SORT", limit=1)
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res["source"], "arxiv")
        self.assertEqual(res["title"], "BoT-SORT: Robust Associations Multi-Pedestrian Tracking")
        self.assertEqual(res["year"], "2022")
        self.assertIn("Nir Aharon", res["authors"])
        self.assertEqual(res["id"], "2206.14651v2")
        self.assertIn("@article{aharon2022bot", res["bibtex"])

    @patch("urllib.request.urlopen")
    def test_search_crossref_mocked(self, mock_urlopen):
        sample_json = {
            "message": {
                "items": [
                    {
                        "title": ["Deep Residual Learning for Image Recognition"],
                        "author": [
                            {"given": "Kaiming", "family": "He"},
                            {"given": "Xiangyu", "family": "Zhang"}
                        ],
                        "published-print": {"date-parts": [[2016, 6, 27]]},
                        "DOI": "10.1109/cvpr.2016.90",
                        "container-title": ["CVPR"],
                        "abstract": "Deeper neural networks are more difficult to train."
                    }
                ]
            }
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(sample_json).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        results = search_papers.search_crossref("ResNet", limit=1)
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res["source"], "crossref")
        self.assertEqual(res["title"], "Deep Residual Learning for Image Recognition")
        self.assertEqual(res["year"], "2016")
        self.assertEqual(res["id"], "10.1109/cvpr.2016.90")
        self.assertIn("@article{he2016deep", res["bibtex"])


if __name__ == "__main__":
    unittest.main()
