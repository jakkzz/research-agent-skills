#!/usr/bin/env python3
"""Tests for arXiv/Crossref candidate discovery."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "literature-discovery", "scripts")))
import search_papers


class TestLiteratureDiscovery(unittest.TestCase):
    def response(self, payload):
        response = MagicMock()
        response.read.return_value = payload
        response.__enter__.return_value = response
        return response

    def test_clean_text_and_cite_key(self):
        self.assertEqual(search_papers.clean_text("  Attention \n Is  All "), "Attention Is All")
        self.assertEqual(search_papers.clean_text(None), "")
        self.assertEqual(search_papers.generate_cite_key(["Ashish Vaswani"], "2017", "Attention Is All You Need"), "vaswani2017attention")
        self.assertEqual(search_papers.generate_cite_key([], "", "A Study"), "unknownndstudy")

    @patch("urllib.request.urlopen")
    def test_arxiv_uses_https_and_returns_source_status(self, urlopen):
        urlopen.return_value = self.response(b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>https://arxiv.org/abs/2206.14651v2</id><title>BoT-SORT</title><summary>Tracking.</summary><author><name>Nir Aharon</name></author><published>2022-06-29T00:00:00Z</published></entry></feed>""")
        provider = search_papers.search_arxiv("tracking", 1)
        self.assertEqual(provider["status"], "ok")
        self.assertEqual(provider["results"][0]["id"], "2206.14651v2")
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.startswith("https://export.arxiv.org/"))
        self.assertIn("not peer-review", provider["results"][0]["record_note"])

    @patch("urllib.request.urlopen")
    def test_crossref_success(self, urlopen):
        payload = {"message": {"items": [{"title": ["Deep Residual Learning"], "author": [{"given": "Kaiming", "family": "He"}], "published-print": {"date-parts": [[2016]]}, "DOI": "10.1/test", "container-title": ["CVPR"]}]}}
        urlopen.return_value = self.response(json.dumps(payload).encode())
        provider = search_papers.search_crossref("resnet", 1)
        self.assertEqual(provider["status"], "ok")
        self.assertEqual(provider["results"][0]["cite_key"], "he2016deep")

    @patch.object(search_papers, "search_crossref")
    @patch.object(search_papers, "search_arxiv")
    def test_genuine_zero_results_is_success(self, arxiv, crossref):
        arxiv.return_value = {"source": "arxiv", "status": "ok", "error": None, "results": []}
        crossref.return_value = {"source": "crossref", "status": "ok", "error": None, "results": []}
        report = search_papers.search_all("nothing")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["results"], [])

    @patch.object(search_papers, "search_crossref")
    @patch.object(search_papers, "search_arxiv")
    def test_partial_failure_is_distinct_and_nonzero(self, arxiv, crossref):
        arxiv.return_value = {"source": "arxiv", "status": "error", "error": "timeout", "results": []}
        crossref.return_value = {"source": "crossref", "status": "ok", "error": None, "results": [{"title": "Candidate", "year": "2020", "bibtex": "x"}]}
        report = search_papers.search_all("query")
        self.assertEqual(report["status"], "partial_failure")
        self.assertEqual(report["sources"]["arxiv"]["error"], "timeout")
        self.assertEqual(len(report["results"]), 1)
        self.assertEqual(search_papers.main(["query", "--json"]), 1)

    @patch("urllib.request.urlopen")
    def test_malformed_xml_is_reported_without_exception(self, urlopen):
        urlopen.return_value = self.response(b"not xml")
        provider = search_papers.search_arxiv("query")
        self.assertEqual(provider["status"], "error")
        self.assertIn("XML parsing failed", provider["error"])

    @patch("urllib.request.urlopen")
    def test_malformed_json_is_reported_without_exception(self, urlopen):
        urlopen.return_value = self.response(b"not json")
        provider = search_papers.search_crossref("query")
        self.assertEqual(provider["status"], "error")
        self.assertIn("JSON parsing failed", provider["error"])

    @patch.object(search_papers, "search_all")
    def test_append_requires_bib_before_any_network_call(self, search_all):
        with self.assertRaises(SystemExit) as raised:
            search_papers.main(["query", "--append", "references.bib"])
        self.assertEqual(raised.exception.code, 2)
        search_all.assert_not_called()

    @patch.object(search_papers, "search_all")
    def test_json_and_bib_outputs_are_mutually_exclusive(self, search_all):
        for arguments in (
            ["query", "--json", "--bib"],
            ["query", "--json", "--bib", "--append", "references.bib"],
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit) as raised:
                search_papers.main(arguments)
            self.assertEqual(raised.exception.code, 2)
        search_all.assert_not_called()

    @patch.object(search_papers, "search_all")
    def test_limit_must_be_positive_and_bounded_before_network_calls(self, search_all):
        for value in ("0", "-1", "101"):
            with self.subTest(value=value), self.assertRaises(SystemExit) as raised:
                search_papers.main(["query", "--limit", value])
            self.assertEqual(raised.exception.code, 2)
        search_all.assert_not_called()


if __name__ == "__main__":
    unittest.main()
