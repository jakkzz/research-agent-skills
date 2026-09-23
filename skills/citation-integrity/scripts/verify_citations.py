#!/usr/bin/env python3
"""Check manuscript citation-key consistency against BibTeX files.

This utility does not verify metadata, retractions, or whether a source supports
a manuscript claim. DOI/arXiv lookup is a separate, explicit operation.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

MANUSCRIPT_EXTENSIONS = (".tex", ".latex", ".md", ".markdown", ".rmd", ".qmd")
LATEX_CITE_RE = re.compile(
    r"\\(?:cite|citep|citet|citeauthor|citeyear|autocite|textcite|parencite|nocite)\*?(?:\[.*?\])?\{([^}]+)\}"
)
PANDOC_BRACKET_RE = re.compile(r"\[([^\]]*?@[A-Za-z0-9_:.\-]+[^\]]*?)\]")
PANDOC_INLINE_RE = re.compile(r"(?<![\w.\-])@([A-Za-z0-9_:.\-]+)")
BIB_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.I)
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".gif")


def extract_latex_keys(text: str) -> Set[str]:
    return {
        key.strip()
        for match in LATEX_CITE_RE.finditer(text)
        for key in match.group(1).split(",")
        if key.strip()
    }


def extract_markdown_keys(text: str) -> Set[str]:
    keys = set()
    for match in PANDOC_BRACKET_RE.finditer(text):
        keys.update(
            key for key in re.findall(r"@([A-Za-z0-9_:.\-]+)", match.group(1))
            if not key.lower().endswith(IMAGE_EXTENSIONS)
        )
    for match in PANDOC_INLINE_RE.finditer(text):
        key = match.group(1).strip()
        if key and not key.lower().endswith(IMAGE_EXTENSIONS):
            keys.add(key)
    return keys


def extract_keys_from_manuscript(filepath: str) -> Set[str]:
    content = Path(filepath).read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError("manuscript is empty")
    extension = Path(filepath).suffix.lower()
    if extension in (".tex", ".latex"):
        return extract_latex_keys(content)
    if extension in (".md", ".markdown", ".rmd", ".qmd"):
        return extract_markdown_keys(content) | extract_latex_keys(content)
    return extract_latex_keys(content) | extract_markdown_keys(content)


def parse_bibtex(filepath: str) -> Tuple[Dict[str, Dict[str, str]], List[Dict]]:
    content = Path(filepath).read_text(encoding="utf-8")
    entries: Dict[str, Dict[str, str]] = {}
    duplicates: List[Dict] = []
    for match in BIB_ENTRY_RE.finditer(content):
        entry_type = match.group(1).lower()
        if entry_type in {"comment", "string", "preamble"}:
            continue
        key = match.group(2).strip()
        location = {"source": str(filepath), "line": content.count("\n", 0, match.start()) + 1}
        if key in entries:
            duplicates.append({"key": key, "locations": [entries[key]["location"], location]})
        else:
            entries[key] = {"type": entry_type, "source": str(filepath), "location": location}
    return entries, duplicates


def _expand_manuscripts(paths: List[str], errors: List[str]) -> List[str]:
    files: List[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            errors.append(f"Manuscript path does not exist: {raw_path}")
        elif path.is_dir():
            discovered = sorted(
                str(item) for item in path.rglob("*")
                if item.is_file() and item.suffix.lower() in MANUSCRIPT_EXTENSIONS
            )
            files.extend(discovered)
        elif path.is_file():
            if path.suffix.lower() in MANUSCRIPT_EXTENSIONS:
                files.append(str(path))
            else:
                errors.append(
                    f"Unsupported manuscript extension for {raw_path}; expected one of "
                    + ", ".join(MANUSCRIPT_EXTENSIONS)
                )
        else:
            errors.append(f"Manuscript path is not a regular file or directory: {raw_path}")
    return list(dict.fromkeys(files))


def audit_citations(manuscript_paths: List[str], bib_paths: List[str]) -> Dict:
    errors: List[str] = []
    manuscript_files = _expand_manuscripts(manuscript_paths, errors)
    keys_by_file: Dict[str, List[str]] = {}
    cited: Set[str] = set()
    wildcard_nocite = False
    for path in manuscript_files:
        try:
            keys = extract_keys_from_manuscript(path)
        except ValueError:
            errors.append(f"Empty manuscript: {path}")
            continue
        except (OSError, UnicodeError) as exc:
            errors.append(f"Cannot read manuscript {path}: {exc}")
            continue
        wildcard_nocite = wildcard_nocite or "*" in keys
        keys.discard("*")
        keys_by_file[path] = sorted(keys)
        cited.update(keys)

    entries: Dict[str, Dict[str, str]] = {}
    duplicates: List[Dict] = []
    locations_by_key: Dict[str, List[Dict]] = {}
    parsed_bib_files = 0
    for raw_path in bib_paths:
        path = Path(raw_path)
        if not path.is_file():
            errors.append(f"BibTeX path does not exist or is not a file: {raw_path}")
            continue
        try:
            parsed, within_file_duplicates = parse_bibtex(str(path))
        except (OSError, UnicodeError) as exc:
            errors.append(f"Cannot read BibTeX file {raw_path}: {exc}")
            continue
        parsed_bib_files += 1
        duplicates.extend(within_file_duplicates)
        for key, entry in parsed.items():
            location = entry["location"]
            if key in entries:
                locations = locations_by_key[key] + [location]
                duplicates.append({"key": key, "locations": locations})
                locations_by_key[key] = locations
            else:
                entries[key] = entry
                locations_by_key[key] = [location]

    if not keys_by_file:
        errors.append("Zero manuscript files were scanned")
    if parsed_bib_files == 0:
        errors.append("Zero BibTeX files were parsed")
    if not entries:
        errors.append("Zero BibTeX entries were parsed")

    # Deduplicate duplicate reports while retaining every source location.
    duplicate_map: Dict[str, List[Dict]] = {}
    for duplicate in duplicates:
        bucket = duplicate_map.setdefault(duplicate["key"], [])
        for location in duplicate["locations"]:
            if location not in bucket:
                bucket.append(location)
    duplicate_reports = [
        {"key": key, "locations": locations}
        for key, locations in sorted(duplicate_map.items())
    ]

    bib_keys = set(entries)
    missing = sorted(cited - bib_keys)
    unreferenced = [] if wildcard_nocite else sorted(bib_keys - cited)
    matched = sorted(cited & bib_keys)
    return {
        "ok": not errors and not missing,
        "input_errors": errors,
        "scope_note": "Citation-key consistency only; metadata, retractions, and claim support are not checked.",
        "summary": {
            "total_manuscript_files": len(keys_by_file),
            "total_bib_files": parsed_bib_files,
            "total_bib_entries": len(entries),
            "total_citation_keys": len(cited),
            "matched_citation_keys": len(matched),
            "missing_citation_keys": len(missing),
            "unreferenced_bib_entries": len(unreferenced),
            "duplicate_bib_keys": len(duplicate_reports),
            "nocite_all": wildcard_nocite,
        },
        "missing": missing,
        "unreferenced": unreferenced,
        "duplicates": duplicate_reports,
        "matched": matched,
        "valid": matched,
        "citations_by_file": keys_by_file,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check manuscript citation keys against BibTeX keys.")
    parser.add_argument("manuscripts", nargs="+", help="Manuscript files or directories")
    parser.add_argument("--bib", "-b", nargs="+", required=True, help="BibTeX files")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--strict", action="store_true", help="Also fail on duplicates or unreferenced entries")
    args = parser.parse_args(argv)
    report = audit_citations(args.manuscripts, args.bib)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report["summary"]
        print("CITATION-KEY CONSISTENCY CHECK")
        print(report["scope_note"])
        print(f"Manuscripts scanned: {summary['total_manuscript_files']}")
        print(f"BibTeX entries parsed: {summary['total_bib_entries']}")
        print(f"Matched keys: {summary['matched_citation_keys']}")
        print(f"Missing keys: {summary['missing_citation_keys']}")
        print(f"Unreferenced entries: {summary['unreferenced_bib_entries']}")
        print(f"Duplicate keys: {summary['duplicate_bib_keys']}")
        for error in report["input_errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        strict_failure = args.strict and (report["duplicates"] or report["unreferenced"])
        if report["ok"] and not report["duplicates"] and not strict_failure:
            print("Citation-key consistency check passed; metadata and claim support were not verified.")
    if report["input_errors"] or report["missing"]:
        return 2 if report["input_errors"] else 1
    if args.strict and (report["duplicates"] or report["unreferenced"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
