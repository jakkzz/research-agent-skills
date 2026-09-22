#!/usr/bin/env python3
"""
test_citation_integrity.py
Comprehensive unit tests for the citation-integrity skill scripts.
Zero external dependencies (pure standard library unittest).
"""

import os
import sys
import tempfile
import unittest

# Add skills scripts to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "citation-integrity", "scripts")))

import verify_citations
import fetch_doi


class TestCitationIntegrity(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_markdown_citation_extraction(self):
        sample_md = """
        # Literature Review

        Recent work by @vaswani2017attention showed transformative results.
        Other studies have corroborated this [@devlin2018bert; @radford2019language, p. 14].
        Contact us at info@example.com for further inquiries.
        Also see embedded LaTeX \\cite{brown2020language}.
        """
        keys = verify_citations.extract_markdown_keys(sample_md)
        self.assertIn("vaswani2017attention", keys)
        self.assertIn("devlin2018bert", keys)
        self.assertIn("radford2019language", keys)
        self.assertNotIn("example.com", keys)

    def test_latex_citation_extraction(self):
        sample_latex = r"""
        \section{Background}
        As observed in \cite{he2016deep}, residual connections ease training.
        Parenthetical citations \citep{krizhevsky2012imagenet, simonyan2014very} demonstrate convolutional scaling.
        Furthermore, \textcite{lecun1998gradient} introduced modern backprop benchmarks.
        """
        keys = verify_citations.extract_latex_keys(sample_latex)
        self.assertEqual(keys, {
            "he2016deep",
            "krizhevsky2012imagenet",
            "simonyan2014very",
            "lecun1998gradient"
        })

    def test_bibtex_parser(self):
        bib_content = """
        @article{he2016deep,
          title={Deep residual learning for image recognition},
          author={He, Kaiming and Zhang, Xiangyu and Ren, Shaoqing and Sun, Jian},
          journal={CVPR},
          year={2016}
        }

        @inproceedings{krizhevsky2012imagenet,
          title={Imagenet classification with deep convolutional neural networks},
          author={Krizhevsky, Alex and Sutskever, Ilya and Hinton, Geoffrey E},
          booktitle={NeurIPS},
          year={2012}
        }

        % Duplicate key test
        @misc{he2016deep,
          title={Duplicate entry},
          year={2016}
        }

        @comment{This is a comment}
        """
        bib_path = os.path.join(self.temp_dir.name, "refs.bib")
        with open(bib_path, "w", encoding="utf-8") as f:
            f.write(bib_content)

        entries, duplicates = verify_citations.parse_bibtex(bib_path)
        self.assertIn("he2016deep", entries)
        self.assertIn("krizhevsky2012imagenet", entries)
        self.assertEqual(duplicates, ["he2016deep"])

    def test_audit_citations_end_to_end(self):
        md_content = """
        Deep learning methods [@he2016deep] have outperformed traditional pipelines.
        However, @missing2025author remains unverified.
        """
        md_path = os.path.join(self.temp_dir.name, "paper.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        bib_content = """
        @article{he2016deep,
          title={Deep Residual Learning},
          author={He, K.},
          year={2016}
        }
        @article{unused2020paper,
          title={Unused Paper},
          author={Nobody, N.},
          year={2020}
        }
        """
        bib_path = os.path.join(self.temp_dir.name, "refs.bib")
        with open(bib_path, "w", encoding="utf-8") as f:
            f.write(bib_content)

        report = verify_citations.audit_citations([md_path], [bib_path])

        self.assertIn("he2016deep", report["valid"])
        self.assertIn("missing2025author", report["missing"])
        self.assertIn("unused2020paper", report["unreferenced"])
        self.assertEqual(report["summary"]["missing_citations"], 1)
        self.assertEqual(report["summary"]["unreferenced_bib_entries"], 1)

    def test_arxiv_bibtex_generation(self):
        # Test clean arXiv ID regex parsing and key generation
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
          <entry>
            <id>http://arxiv.org/abs/1706.03762v7</id>
            <title>Attention Is All You Need</title>
            <author><name>Ashish Vaswani</name></author>
            <author><name>Noam Shazeer</name></author>
            <published>2017-06-12T00:00:00Z</published>
            <arxiv:primary_category term="cs.CL"/>
          </entry>
        </feed>"""

        import xml.etree.ElementTree as ET
        root = ET.fromstring(sample_xml)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        entry = root.find("atom:entry", ns)
        self.assertIsNotNone(entry)

        title = entry.find("atom:title", ns).text.strip()
        self.assertEqual(title, "Attention Is All You Need")


if __name__ == "__main__":
    unittest.main()
