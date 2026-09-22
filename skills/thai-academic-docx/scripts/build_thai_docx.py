#!/usr/bin/env python3
"""
build_thai_docx.py
Generates academic Word DOCX documents adhering to Thai university thesis formatting:
- Font: TH Sarabun New (16pt body, 18pt bold Heading 1, 16pt bold Heading 2)
- Line Spacing: 1.5 lines (360 twips)
- Margins: Top 1.5", Left 1.5", Bottom 1.0", Right 1.0"
- First-line paragraph indent: 0.5" (720 twips)
- Buddhist Era (พ.ศ.) date conversions and Thai numerals option
Zero external dependencies (pure standard library zipfile + xml).
"""

import argparse
import io
import os
import re
import sys
import zipfile
from typing import List, Tuple


THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")


def to_buddhist_era(text: str) -> str:
    """Converts 4-digit CE years (e.g. 1900-2099) to Buddhist Era (พ.ศ. = CE + 543)."""
    def replace_year(match):
        ce_year = int(match.group(1))
        be_year = ce_year + 543
        return f"พ.ศ. {be_year}"

    # Replace "ค.ศ. 2026" or "C.E. 2026" -> "พ.ศ. 2569"
    text = re.sub(r"(?:ค\.ศ\.|C\.E\.)\s*(\d{4})", replace_year, text)
    return text


def to_thai_numerals(text: str) -> str:
    return text.translate(THAI_DIGITS)


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_run_xml(text: str, bold: bool = False, italic: bool = False) -> str:
    escaped = escape_xml(text)
    rpr = "<w:rPr>"
    rpr += '<w:rFonts w:ascii="TH Sarabun New" w:hAnsi="TH Sarabun New" w:cs="TH Sarabun New"/>'
    if bold:
        rpr += "<w:b/><w:bCs/>"
    if italic:
        rpr += "<w:i/><w:iCs/>"
    rpr += '<w:sz w:val="32"/><w:szCs w:val="32"/>'
    rpr += "</w:rPr>"
    return f"<w:r>{rpr}<w:t xml:space=\"preserve\">{escaped}</w:t></w:r>"


def parse_inline_markdown(line: str) -> str:
    """Parses bold, italic, and regular text into OpenXML runs."""
    runs_xml = []
    # Pattern to match **bold**, *italic*, or plain text
    pattern = re.compile(r"(\*\*.*?\*\*|\*.*?\*|`.*?`|[^*`]+)")
    tokens = pattern.findall(line)

    for token in tokens:
        if token.startswith("**") and token.endswith("**") and len(token) >= 4:
            runs_xml.append(build_run_xml(token[2:-2], bold=True))
        elif token.startswith("*") and token.endswith("*") and len(token) >= 2:
            runs_xml.append(build_run_xml(token[1:-1], italic=True))
        elif token.startswith("`") and token.endswith("`") and len(token) >= 2:
            runs_xml.append(build_run_xml(token[1:-1]))
        else:
            runs_xml.append(build_run_xml(token))

    return "".join(runs_xml)


def build_heading_xml(text: str, level: int) -> str:
    escaped = escape_xml(text)
    sz = "36" if level == 1 else "32"
    jc = ' w:jc="center"' if level == 1 else ""
    before = "240" if level == 1 else "180"
    after = "120" if level == 1 else "80"

    return f"""<w:p>
  <w:pPr>
    <w:pStyle w:val="Heading{level}"/>
    <w:spacing w:before="{before}" w:after="{after}" w:line="360" w:lineRule="auto"/>
    {f'<w:jc w:val="{ "center" if level == 1 else "left" }"/>' if level == 1 else ''}
    <w:rPr>
      <w:rFonts w:ascii="TH Sarabun New" w:hAnsi="TH Sarabun New" w:cs="TH Sarabun New"/>
      <w:b/><w:bCs/>
      <w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>
    </w:rPr>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="TH Sarabun New" w:hAnsi="TH Sarabun New" w:cs="TH Sarabun New"/>
      <w:b/><w:bCs/>
      <w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>
    </w:rPr>
    <w:t>{escaped}</w:t>
  </w:r>
</w:p>"""


def build_paragraph_xml(line: str, indent: bool = True) -> str:
    runs = parse_inline_markdown(line)
    ind_xml = '<w:ind w:firstLine="720"/>' if indent else ""
    return f"""<w:p>
  <w:pPr>
    {ind_xml}
    <w:spacing w:line="360" w:lineRule="auto" w:after="120"/>
  </w:pPr>
  {runs}
</w:p>"""


def build_list_item_xml(line: str, bullet_char: str = "•") -> str:
    runs = parse_inline_markdown(line)
    return f"""<w:p>
  <w:pPr>
    <w:ind w:left="720" w:hanging="360"/>
    <w:spacing w:line="360" w:lineRule="auto" w:after="80"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="TH Sarabun New" w:hAnsi="TH Sarabun New" w:cs="TH Sarabun New"/>
      <w:sz w:val="32"/><w:szCs w:val="32"/>
    </w:rPr>
    <w:t xml:space="preserve">{bullet_char}  </w:t>
  </w:r>
  {runs}
</w:p>"""


def build_table_xml(rows: List[List[str]]) -> str:
    if not rows:
        return ""

    table_xml = ["""<w:tbl>
  <w:tblPr>
    <w:tblW w:w="0" w:type="auto"/>
    <w:tblBorders>
      <w:top w:val="single" w:sz="8" w:space="0" w:color="auto"/>
      <w:bottom w:val="single" w:sz="8" w:space="0" w:color="auto"/>
      <w:insideH w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>
      <w:insideV w:val="none"/>
      <w:left w:val="none"/>
      <w:right w:val="none"/>
    </w:tblBorders>
    <w:jc w:val="center"/>
  </w:tblPr>"""]

    for row_idx, row in enumerate(rows):
        is_header = (row_idx == 0)
        table_xml.append("<w:tr>")
        for cell in row:
            bold_flag = is_header
            runs = build_run_xml(cell.strip(), bold=bold_flag)
            table_xml.append(f"""<w:tc>
  <w:tcPr>
    <w:tcMar>
      <w:top w:w="120" w:type="dxa"/>
      <w:bottom w:w="120" w:type="dxa"/>
      <w:left w:w="180" w:type="dxa"/>
      <w:right w:w="180" w:type="dxa"/>
    </w:tcMar>
  </w:tcPr>
  <w:p>
    <w:pPr>
      <w:spacing w:line="280" w:lineRule="auto" w:after="0"/>
      {f'<w:jc w:val="center"/>' if is_header else ''}
    </w:pPr>
    {runs}
  </w:p>
</w:tc>""")
        table_xml.append("</w:tr>")

    table_xml.append("</w:tbl>")
    return "".join(table_xml)


def markdown_to_document_xml(markdown_text: str, apply_be: bool = True, use_thai_num: bool = False) -> str:
    if apply_be:
        markdown_text = to_buddhist_era(markdown_text)
    if use_thai_num:
        markdown_text = to_thai_numerals(markdown_text)

    lines = markdown_text.splitlines()
    body_elements = []

    in_table = False
    table_rows = []

    for line in lines:
        stripped = line.strip()

        # Handle Markdown Tables (| cell | cell |)
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # Check if this is a separator row (e.g. |---|---|)
            if all(re.match(r"^:?-+:?$", c) for c in cells):
                continue
            table_rows.append(cells)
            in_table = True
            continue
        else:
            if in_table:
                body_elements.append(build_table_xml(table_rows))
                table_rows = []
                in_table = False

        if not stripped:
            continue

        # Headings
        if stripped.startswith("# "):
            body_elements.append(build_heading_xml(stripped[2:], level=1))
        elif stripped.startswith("## "):
            body_elements.append(build_heading_xml(stripped[3:], level=2))
        elif stripped.startswith("### "):
            body_elements.append(build_heading_xml(stripped[4:], level=3))
        # Bullet list
        elif stripped.startswith("- ") or stripped.startswith("* "):
            body_elements.append(build_list_item_xml(stripped[2:], bullet_char="•"))
        # Numbered list
        elif re.match(r"^\d+\.\s+", stripped):
            num_match = re.match(r"^(\d+\.)\s+(.*)", stripped)
            if num_match:
                prefix, rest = num_match.group(1), num_match.group(2)
                body_elements.append(build_list_item_xml(rest, bullet_char=prefix))
        # Regular paragraph
        else:
            body_elements.append(build_paragraph_xml(stripped, indent=True))

    if in_table and table_rows:
        body_elements.append(build_table_xml(table_rows))

    # Page settings: Thai Thesis standard
    # Margins: Top 1.5" (2160 twips), Left 1.5" (2160 twips), Bottom 1.0" (1440 twips), Right 1.0" (1440 twips)
    # Page size: A4 (11906 x 16838 twips)
    sect_pr = """<w:sectPr>
  <w:pgSz w:w="11906" w:h="16838"/>
  <w:pgMar w:top="2160" w:right="1440" w:bottom="1440" w:left="2160" w:header="720" w:footer="720" w:gutter="0"/>
</w:sectPr>"""

    doc_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {"".join(body_elements)}
    {sect_pr}
  </w:body>
</w:document>"""
    return doc_xml


def create_thai_docx(markdown_content: str, output_path: str, apply_be: bool = True, use_thai_num: bool = False):
    document_xml = markdown_to_document_xml(markdown_content, apply_be=apply_be, use_thai_num=use_thai_num)

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    doc_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="TH Sarabun New" w:hAnsi="TH Sarabun New" w:cs="TH Sarabun New"/>
        <w:sz w:val="32"/>
        <w:szCs w:val="32"/>
        <w:lang w:val="th-TH"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:pPr>
      <w:spacing w:line="360" w:lineRule="auto" w:after="120"/>
    </w:pPr>
  </w:style>
</w:styles>"""

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/_rels/document.xml.rels", doc_rels_xml)
        zf.writestr("word/styles.xml", styles_xml)
        zf.writestr("word/document.xml", document_xml)


def main():
    parser = argparse.ArgumentParser(description="Convert Markdown to Thai Academic DOCX with thesis typography.")
    parser.add_argument("input_md", help="Path to input Markdown file")
    parser.add_argument("--output", "-o", required=True, help="Path to output .docx file")
    parser.add_argument("--no-be", action="store_true", help="Disable automatic Buddhist Era (พ.ศ.) conversion")
    parser.add_argument("--thai-numerals", action="store_true", help="Convert Arabic numerals to Thai numerals (๐-๙)")

    args = parser.parse_args()

    if not os.path.isfile(args.input_md):
        print(f"Error: File not found: {args.input_md}", file=sys.stderr)
        sys.exit(1)

    with open(args.input_md, "r", encoding="utf-8") as f:
        md_text = f.read()

    create_thai_docx(
        md_text,
        args.output,
        apply_be=(not args.no_be),
        use_thai_num=args.thai_numerals
    )
    print(f"[OK] Generated Thai Academic DOCX: {args.output}")


if __name__ == "__main__":
    main()
