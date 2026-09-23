---
name: thai-academic-docx
description: 'Builds a minimal generic Thai-oriented DOCX preset from basic Markdown. Use when creating a draft with TH Sarabun New references, spacing, margins, headings, lists, tables, and optional date or numeral conversion.'
---

# Thai Academic DOCX

> Alpha generic preset; not a universal Thai university standard or institution-specific template.

The script creates a minimal OpenXML document with A4 page size, configured margins, 1.5-line spacing, body and heading styles, basic lists/tables, optional Buddhist Era conversion, and optional Thai numerals.

```bash
python3 scripts/build_thai_docx.py chapter.md --output chapter.docx
python3 scripts/build_thai_docx.py report.md --output report.docx --thai-numerals
python3 scripts/build_thai_docx.py paper.md --output paper.docx --no-be
```

Existing output is refused unless `--force` is explicit. Input and output paths must differ. Unsupported inline Markdown remains visible as text rather than being silently dropped.

`TH Sarabun New` is referenced but **not embedded**. The receiving system must have the font installed. Open the result in the target Word/LibreOffice environment and perform visual validation. Compare margins, styles, pagination, front matter, numbering, and required forms against the current rules of the specific institution before use.
