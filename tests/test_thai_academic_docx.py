#!/usr/bin/env python3
"""Tests for the minimal Thai DOCX preset."""

import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "thai-academic-docx", "scripts")))
import build_thai_docx


class TestThaiAcademicDocx(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_date_and_numeral_conversions(self):
        converted = build_thai_docx.to_buddhist_era("ค.ศ. 2026 C.E. 2030")
        self.assertIn("พ.ศ. 2569", converted)
        self.assertIn("พ.ศ. 2573", converted)
        self.assertEqual(build_thai_docx.to_thai_numerals("1 2.4 150"), "๑ ๒.๔ ๑๕๐")

    def test_create_docx_defines_every_referenced_heading_style(self):
        output = self.root / "document.docx"
        build_thai_docx.create_thai_docx("# One\n## Two\n### Three\nBody", str(output))
        with zipfile.ZipFile(output) as archive:
            document = archive.read("word/document.xml").decode()
            styles = archive.read("word/styles.xml").decode()
            ET.fromstring(document)
            ET.fromstring(styles)
            for level in (1, 2, 3):
                self.assertIn(f'w:val="Heading{level}"', document)
                self.assertIn(f'w:styleId="Heading{level}"', styles)
            self.assertIn("TH Sarabun New", document)

    def test_invalid_xml_control_character_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "XML 1.0-invalid control character U\\+0001"):
            build_thai_docx.create_thai_docx("valid\x01invalid", str(self.root / "bad.docx"))
        self.assertFalse((self.root / "bad.docx").exists())

    def test_unmatched_and_unsupported_inline_markdown_remains_visible(self):
        text = "unmatched * star and ` tick plus ~~strike~~ and [link](url)"
        xml = build_thai_docx.markdown_to_document_xml(text, apply_be=False)
        visible = "".join(ET.fromstring(xml).itertext())
        self.assertEqual(visible.strip(), text)

    def test_existing_output_requires_force(self):
        output = self.root / "existing.docx"
        output.write_bytes(b"original")
        with self.assertRaises(FileExistsError):
            build_thai_docx.create_thai_docx("body", str(output))
        self.assertEqual(output.read_bytes(), b"original")
        build_thai_docx.create_thai_docx("body", str(output), force=True)
        self.assertTrue(zipfile.is_zipfile(output))

    def test_broken_symlink_output_requires_force(self):
        output = self.root / "broken.docx"
        try:
            output.symlink_to(self.root / "missing.docx")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        with self.assertRaises(FileExistsError):
            build_thai_docx.create_thai_docx("body", str(output))
        self.assertTrue(output.is_symlink())

    def test_no_force_publish_does_not_clobber_concurrent_output(self):
        output = self.root / "raced.docx"
        real_link = os.link

        def create_competitor_then_link(source, destination):
            output.write_bytes(b"competitor")
            return real_link(source, destination)

        with patch.object(build_thai_docx.os, "link", side_effect=create_competitor_then_link):
            with self.assertRaises(FileExistsError):
                build_thai_docx.create_thai_docx("body", str(output))
        self.assertEqual(output.read_bytes(), b"competitor")
        self.assertEqual(list(self.root.glob(".raced.docx.*.tmp")), [])

    def test_atomic_failure_preserves_existing_output(self):
        output = self.root / "existing.docx"
        output.write_bytes(b"original")
        with patch.object(build_thai_docx.os, "replace", side_effect=OSError("activation failed")):
            with self.assertRaisesRegex(OSError, "activation failed"):
                build_thai_docx.create_thai_docx("body", str(output), force=True)
        self.assertEqual(output.read_bytes(), b"original")
        self.assertEqual(list(self.root.glob(".existing.docx.*.tmp")), [])

    def test_cli_refuses_input_equal_output(self):
        path = self.root / "same.md"
        path.write_text("body", encoding="utf-8")
        with patch.object(sys, "argv", ["build_thai_docx.py", str(path), "--output", str(path)]):
            with self.assertRaises(SystemExit) as raised:
                build_thai_docx.main()
        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(path.read_text(encoding="utf-8"), "body")

    def test_cli_reports_invalid_utf8_as_normal_error(self):
        source = self.root / "invalid.md"
        source.write_bytes(b"\xff")
        stderr = StringIO()
        with patch.object(sys, "argv", ["build_thai_docx.py", str(source), "--output", str(self.root / "out.docx")]), \
             redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                build_thai_docx.main()
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("Error:", stderr.getvalue())
        self.assertIn("UTF-8", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
