---
name: thai-academic-docx
description: Generates Microsoft Word (DOCX) academic manuscripts formatted to Thai university thesis standards (TH Sarabun New, 16pt, 1.5 line spacing, 1.5"/1.0" margins, Buddhist Era conversion).
---

# Thai Academic DOCX

Automates the production of publication-ready Word documents conforming to Thai higher education and graduate school thesis formatting regulations. Zero external dependencies (uses standard Python `zipfile` and OpenXML architecture).

## Key Formatting Standards Implemented
- **Typography:** `TH Sarabun New` (or `TH Sarabun PSK`), size 16pt for Normal text, 18pt bold for Chapter/Section titles (Heading 1), 16pt bold for subsections (Heading 2).
- **Line Spacing:** 1.5 lines (`line="360"`), standard for Thai academic reviews and thesis submissions.
- **Margins:**
  - Top: 1.5 inches (3.81 cm / 2160 twips)
  - Left: 1.5 inches (3.81 cm / 2160 twips - binding margin)
  - Bottom: 1.0 inch (2.54 cm / 1440 twips)
  - Right: 1.0 inch (2.54 cm / 1440 twips)
- **First-Line Indent:** 0.5 inches (720 twips) on all standard body paragraphs.
- **Dating & Numerals:**
  - Automatic Buddhist Era conversion (`ค.ศ. 2026` -> `พ.ศ. 2569`).
  - Optional Thai numeral conversion (`0-9` -> `๐-๙`) for official royal/ministry publications (`--thai-numerals`).

## Tools and Scripts Included

### Thesis DOCX Generator (`scripts/build_thai_docx.py`)
Converts structured Markdown manuscripts containing headings, bold/italics, bullet lists, numbered lists, and Markdown tables into valid Word OpenXML packages.

```bash
# Basic conversion with default Thai thesis formatting
python3 scripts/build_thai_docx.py chapter1.md --output chapter1.docx

# Convert with Thai numerals (๐-๙) for formal government/official reports
python3 scripts/build_thai_docx.py report.md --output report.docx --thai-numerals

# Disable automatic Buddhist Era conversion (preserve CE/ค.ศ.)
python3 scripts/build_thai_docx.py paper.md --output paper.docx --no-be
```

## Step-by-Step Agent Workflow

1. **Draft Manuscript in Markdown:**
   Write or refine the thesis chapter or report in clean Markdown using standard headers (`#`, `##`, `###`), lists, and tables.
2. **Review Formatting Directives:**
   Verify whether the target department requires Arabic numerals (default) or Thai numerals (`--thai-numerals`).
3. **Compile to DOCX:**
   Execute `build_thai_docx.py` pointing to the output path.
4. **Validate OpenXML Package:**
   Confirm file size and verify that standard Word/LibreOffice readers display the exact `TH Sarabun New` font and 1.5" left/top margins.
