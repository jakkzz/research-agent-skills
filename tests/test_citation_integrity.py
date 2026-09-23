#!/usr/bin/env python3
"""Tests for citation-key consistency checks."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "citation-integrity", "scripts")))
import verify_citations


class TestCitationIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_markdown_and_latex_extraction(self):
        markdown = "@vaswani2017attention [@devlin2018bert; @radford2019language] info@example.com \\cite{brown2020language}"
        keys = verify_citations.extract_markdown_keys(markdown) | verify_citations.extract_latex_keys(markdown)
        self.assertEqual(keys, {"vaswani2017attention", "devlin2018bert", "radford2019language", "brown2020language"})
        latex = r"\cite{he2016deep, simonyan2014very} \nocite{*}"
        self.assertEqual(verify_citations.extract_latex_keys(latex), {"he2016deep", "simonyan2014very", "*"})

    def test_duplicate_keys_inside_and_across_files_retain_locations(self):
        first = self.write("one.bib", "@article{same,\n title={A}\n}\n@misc{same,\n title={B}\n}")
        second = self.write("two.bib", "@book{same,\n title={C}\n}")
        manuscript = self.write("paper.md", "[@same]")
        entries, duplicates = verify_citations.parse_bibtex(str(first))
        self.assertIn("same", entries)
        self.assertEqual(duplicates[0]["locations"][0]["line"], 1)
        report = verify_citations.audit_citations([str(manuscript)], [str(first), str(second)])
        self.assertEqual(report["summary"]["duplicate_bib_keys"], 1)
        self.assertEqual(len(report["duplicates"][0]["locations"]), 3)
        self.assertEqual({Path(item["source"]).name for item in report["duplicates"][0]["locations"]}, {"one.bib", "two.bib"})

    def test_audit_reports_matched_missing_and_unreferenced_keys(self):
        manuscript = self.write("paper.md", "[@he2016deep] [@missing2025]")
        bib = self.write("refs.bib", "@article{he2016deep, title={Deep}}\n@article{unused, title={Unused}}")
        report = verify_citations.audit_citations([str(manuscript)], [str(bib)])
        self.assertIn("he2016deep", report["matched"])
        self.assertEqual(report["missing"], ["missing2025"])
        self.assertEqual(report["unreferenced"], ["unused"])
        self.assertFalse(report["ok"])
        self.assertIn("not checked", report["scope_note"])

    def test_nocite_all_does_not_create_missing_key_or_unreferenced_entries(self):
        manuscript = self.write("paper.tex", r"\nocite{*}")
        bib = self.write("refs.bib", "@article{one, title={One}}\n@book{two, title={Two}}")
        report = verify_citations.audit_citations([str(manuscript)], [str(bib)])
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["unreferenced"], [])
        self.assertTrue(report["summary"]["nocite_all"])
        self.assertTrue(report["ok"])

    def test_missing_inputs_and_zero_entries_are_errors_and_nonzero(self):
        missing = self.root / "missing.md"
        empty_bib = self.write("empty.bib", "% no entries")
        report = verify_citations.audit_citations([str(missing)], [str(empty_bib)])
        self.assertTrue(report["input_errors"])
        self.assertFalse(report["ok"])
        self.assertEqual(verify_citations.main([str(missing), "--bib", str(empty_bib), "--json"]), 2)

    def test_empty_directory_scans_zero_manuscripts(self):
        bib = self.write("refs.bib", "@article{one, title={One}}")
        report = verify_citations.audit_citations([str(self.root)], [str(bib)])
        self.assertIn("Zero manuscript files were scanned", report["input_errors"])

    def test_empty_manuscript_is_an_input_error(self):
        manuscript = self.root / "empty.md"
        bibliography = self.root / "references.bib"
        manuscript.write_text("", encoding="utf-8")
        bibliography.write_text(
            "@article{source2024, title={A source}, year={2024}}",
            encoding="utf-8",
        )
        report = verify_citations.audit_citations(
            [str(manuscript)], [str(bibliography)]
        )
        self.assertFalse(report["ok"])
        self.assertTrue(
            any("empty" in error.lower() for error in report["input_errors"])
        )

    def test_direct_and_directory_extension_sets_match(self):
        bib = self.write("refs.bib", "@article{one, title={One}}")
        for extension in verify_citations.MANUSCRIPT_EXTENSIONS:
            self.write(f"paper{extension}", "[@one]")
        report = verify_citations.audit_citations([str(self.root)], [str(bib)])
        self.assertEqual(report["summary"]["total_manuscript_files"], len(verify_citations.MANUSCRIPT_EXTENSIONS))
        for extension in verify_citations.MANUSCRIPT_EXTENSIONS:
            direct = verify_citations.audit_citations([str(self.root / f"paper{extension}")], [str(bib)])
            self.assertEqual(direct["summary"]["total_manuscript_files"], 1)

        unsupported = self.write("paper.txt", "[@one]")
        direct = verify_citations.audit_citations([str(unsupported)], [str(bib)])
        self.assertIn("Unsupported manuscript extension", direct["input_errors"][0])


if __name__ == "__main__":
    unittest.main()
