#!/usr/bin/env python3
"""
test_thai_academic_docx.py
Unit tests for thai-academic-docx script and OpenXML DOCX generator.
Zero external dependencies.
"""

import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

# Add script path to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "thai-academic-docx", "scripts")))

import build_thai_docx


class TestThaiAcademicDocx(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_to_buddhist_era(self):
        sample = "เอกสารนี้เขียนขึ้นเมื่อ ค.ศ. 2026 และจะทบทวนใน C.E. 2030"
        converted = build_thai_docx.to_buddhist_era(sample)
        self.assertIn("พ.ศ. 2569", converted)
        self.assertIn("พ.ศ. 2573", converted)
        self.assertNotIn("ค.ศ. 2026", converted)

    def test_to_thai_numerals(self):
        text = "บทที่ 1: ตารางที่ 2.4 สรุป 150 ตัวอย่าง"
        thai_num = build_thai_docx.to_thai_numerals(text)
        self.assertEqual(thai_num, "บทที่ ๑: ตารางที่ ๒.๔ สรุป ๑๕๐ ตัวอย่าง")

    def test_create_thai_docx_end_to_end(self):
        sample_md = """# บทที่ 1 บทนำ

การพัฒนาระบบตรวจวัดการจราจรด้วยปัญญาประดิษฐ์ในปี ค.ศ. 2026 มีความสำคัญอย่างยิ่งต่องานวิศวกรรมจราจร

## 1.1 วัตถุประสงค์การวิจัย
- เพื่อพัฒนาเครื่องมือต้นแบบ
- เพื่อประเมินความแม่นยำ

## 1.2 ข้อมูลการทดสอบ
| คอนฟิกูเรชัน | ความแม่นยำ (%) | อัตราความเร็ว (FPS) |
| :--- | :--- | :--- |
| Config 1 (Central GPU) | 94.5 | 30.0 |
| Config 2 (Edge Coral TPU) | 91.2 | 25.5 |
"""
        out_docx = os.path.join(self.temp_dir.name, "thesis_ch1.docx")
        build_thai_docx.create_thai_docx(sample_md, out_docx, apply_be=True, use_thai_num=False)

        self.assertTrue(os.path.isfile(out_docx))
        self.assertGreater(os.path.getsize(out_docx), 500)

        # Inspect zip entries
        with zipfile.ZipFile(out_docx, "r") as zf:
            namelist = zf.namelist()
            self.assertIn("[Content_Types].xml", namelist)
            self.assertIn("_rels/.rels", namelist)
            self.assertIn("word/styles.xml", namelist)
            self.assertIn("word/document.xml", namelist)

            doc_xml = zf.read("word/document.xml").decode("utf-8")
            self.assertIn("TH Sarabun New", doc_xml)
            self.assertIn("พ.ศ. 2569", doc_xml)  # BE conversion applied
            self.assertIn("บทที่ 1 บทนำ", doc_xml)
            self.assertIn("Config 1 (Central GPU)", doc_xml)

            # Check standard Thai thesis margins (top=2160, left=2160, bottom=1440, right=1440)
            self.assertIn('w:top="2160"', doc_xml)
            self.assertIn('w:left="2160"', doc_xml)
            self.assertIn('w:bottom="1440"', doc_xml)
            self.assertIn('w:right="1440"', doc_xml)


if __name__ == "__main__":
    unittest.main()
