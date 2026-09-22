#!/usr/bin/env python3
"""
verify_citations.py
Validates manuscript citations (LaTeX / Markdown) against BibTeX reference files.
Zero external dependencies. Works across all agent environments.
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Tuple


# Regex patterns for citation extraction
LATEX_CITE_RE = re.compile(
    r'\\(?:cite|citep|citet|citeauthor|citeyear|autocite|textcite|parencite|nocite)\*?(?:\[.*?\])?\{([^}]+)\}'
)

# Pandoc Markdown citation regex:
# Matches [@smith2020], [@smith2020, pp. 20; @jones2021], and inline @smith2020
# Excludes email addresses by ensuring preceding character is not an alphanumeric or dot
PANDOC_BRACKET_RE = re.compile(r'\[([^\]]*?@[a-zA-Z0-9_:\.\-]+[^\]]*?)\]')
PANDOC_INLINE_RE = re.compile(r'(?<![\w\.\-])@([a-zA-Z0-9_:\.\-]+)')

# BibTeX entry regex: @type{citation_key,
BIB_ENTRY_RE = re.compile(r'@(\w+)\s*\{\s*([^,\s]+)\s*,', re.IGNORECASE)


def extract_latex_keys(text: str) -> Set[str]:
    keys = set()
    for match in LATEX_CITE_RE.finditer(text):
        raw_keys = match.group(1).split(',')
        for k in raw_keys:
            cleaned = k.strip()
            if cleaned:
                keys.add(cleaned)
    return keys


def extract_markdown_keys(text: str) -> Set[str]:
    keys = set()
    # 1. Bracketed citations: [@key; @key2, p. 10]
    for match in PANDOC_BRACKET_RE.finditer(text):
        bracket_content = match.group(1)
        inline_keys = re.findall(r'@([a-zA-Z0-9_:\.\-]+)', bracket_content)
        for k in inline_keys:
            cleaned = k.strip()
            if cleaned and not cleaned.endswith(('.png', '.jpg', '.jpeg', '.svg', '.gif')):
                keys.add(cleaned)

    # 2. Inline citations: @smith2020 shows that...
    for match in PANDOC_INLINE_RE.finditer(text):
        k = match.group(1).strip()
        # Avoid emails or accidental matches
        if k and not k.endswith(('.png', '.jpg', '.jpeg', '.svg', '.gif')):
            keys.add(k)
    return keys


def extract_keys_from_manuscript(filepath: str) -> Set[str]:
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    _, ext = os.path.splitext(filepath.lower())
    if ext in ['.tex', '.latex']:
        return extract_latex_keys(content)
    elif ext in ['.md', '.markdown', '.rmd', '.qmd']:
        # Support both Pandoc markdown syntax and LaTeX commands embedded in markdown
        return extract_markdown_keys(content) | extract_latex_keys(content)
    else:
        # Generic: scan for both
        return extract_latex_keys(content) | extract_markdown_keys(content)


def parse_bibtex(filepath: str) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    """
    Parses a .bib file and returns:
      entries: dict of key -> {type, raw}
      duplicates: list of duplicate keys
    """
    entries: Dict[str, Dict[str, str]] = {}
    duplicates: List[str] = []

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    for match in BIB_ENTRY_RE.finditer(content):
        entry_type = match.group(1).lower()
        if entry_type in ['comment', 'string', 'preamble']:
            continue
        key = match.group(2).strip()
        if key in entries:
            duplicates.append(key)
        else:
            entries[key] = {
                'type': entry_type,
                'source': filepath
            }

    return entries, duplicates


def audit_citations(manuscript_paths: List[str], bib_paths: List[str]) -> Dict:
    all_cited_keys: Set[str] = set()
    keys_by_file: Dict[str, List[str]] = {}

    for path in manuscript_paths:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in files:
                    if f.lower().endswith(('.tex', '.md', '.rmd', '.qmd')):
                        full_path = os.path.join(root, f)
                        fkeys = extract_keys_from_manuscript(full_path)
                        keys_by_file[full_path] = sorted(list(fkeys))
                        all_cited_keys.update(fkeys)
        elif os.path.isfile(path):
            fkeys = extract_keys_from_manuscript(path)
            keys_by_file[path] = sorted(list(fkeys))
            all_cited_keys.update(fkeys)

    bib_entries: Dict[str, Dict[str, str]] = {}
    all_duplicates: List[str] = []

    for bib_path in bib_paths:
        if os.path.isfile(bib_path):
            entries, dups = parse_bibtex(bib_path)
            bib_entries.update(entries)
            all_duplicates.extend(dups)

    bib_keys = set(bib_entries.keys())
    missing_keys = sorted(list(all_cited_keys - bib_keys))
    unreferenced_keys = sorted(list(bib_keys - all_cited_keys))
    valid_citations = sorted(list(all_cited_keys & bib_keys))

    report = {
        'summary': {
            'total_manuscript_files': len(keys_by_file),
            'total_citations_found': len(all_cited_keys),
            'valid_citations': len(valid_citations),
            'missing_citations': len(missing_keys),
            'unreferenced_bib_entries': len(unreferenced_keys),
            'duplicate_bib_keys': len(all_duplicates)
        },
        'missing': missing_keys,
        'unreferenced': unreferenced_keys,
        'duplicates': all_duplicates,
        'valid': valid_citations,
        'citations_by_file': keys_by_file
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Verify academic manuscript citations against BibTeX databases.")
    parser.add_argument("manuscripts", nargs="+", help="Path to manuscript file(s) (.tex, .md) or directory")
    parser.add_argument("--bib", "-b", nargs="+", required=True, help="Path to BibTeX file(s) (.bib)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="Fail if missing or unreferenced citations exist")

    args = parser.parse_args()

    report = audit_citations(args.manuscripts, args.bib)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report['summary']
        print("\n================ CITATION INTEGRITY AUDIT ================")
        print(f"Manuscript Files Scanned: {summary['total_manuscript_files']}")
        print(f"Total Unique Citations:   {summary['total_citations_found']}")
        print(f"Valid Citations:          {summary['valid_citations']}")
        print(f"Missing Citations:        {summary['missing_citations']}")
        print(f"Unreferenced Bib Entries: {summary['unreferenced_bib_entries']}")
        print(f"Duplicate Bib Keys:       {summary['duplicate_bib_keys']}")
        print("=========================================================\n")

        if report['missing']:
            print("❌ MISSING CITATIONS (referenced in text but absent in .bib):")
            for k in report['missing']:
                print(f"  - {k}")
            print()

        if report['duplicates']:
            print("⚠️  DUPLICATE KEYS IN BIBTEX:")
            for k in report['duplicates']:
                print(f"  - {k}")
            print()

        if report['unreferenced']:
            print(f"ℹ️  UNREFERENCED BIBTEX ENTRIES ({len(report['unreferenced'])} total):")
            for k in report['unreferenced'][:10]:
                print(f"  - {k}")
            if len(report['unreferenced']) > 10:
                print(f"  ... and {len(report['unreferenced']) - 10} more")
            print()

        if not report['missing'] and not report['duplicates']:
            print("✅ All citations successfully resolved with 100% integrity.")

    # Return exit codes
    if report['missing']:
        sys.exit(1)
    if args.strict and (report['duplicates'] or report['unreferenced']):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
