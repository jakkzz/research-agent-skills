#!/usr/bin/env python3
"""
fetch_doi.py
Retrieves candidate BibTeX records for explicit DOI or arXiv identifiers.
Zero external dependencies (uses standard library urllib).
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


USER_AGENT = "research-agent-skills/0.1.0 (https://github.com/jakkzz/research-agent-skills; mailto:academic-tools@users.noreply.github.com)"


def fetch_doi_bibtex(doi: str) -> str:
    # Clean DOI input
    doi_clean = doi.strip()
    if doi_clean.startswith("http://") or doi_clean.startswith("https://"):
        doi_clean = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi_clean)

    url = f"https://doi.org/{urllib.parse.quote(doi_clean)}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/x-bibtex",
            "User-Agent": USER_AGENT,
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            return content.strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"DOI fetch failed with HTTP {e.code}: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Failed to query DOI: {e}")


def fetch_arxiv_bibtex(arxiv_id: str) -> str:
    # Clean arXiv ID (e.g., "2301.00001", "arXiv:2301.00001v2")
    m = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", arxiv_id)
    if not m:
        raise ValueError(f"Invalid arXiv identifier format: {arxiv_id}")
    clean_id = m.group(1)

    url = f"https://export.arxiv.org/api/query?id_list={clean_id}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
    except Exception as e:
        raise RuntimeError(f"Failed to query arXiv API: {e}")

    # Parse Atom XML
    root = ET.fromstring(xml_data)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    entry = root.find("atom:entry", ns)
    if entry is None:
        raise RuntimeError(f"arXiv ID {clean_id} not found in repository")

    title_elem = entry.find("atom:title", ns)
    title = title_elem.text.strip().replace("\n", " ") if title_elem is not None else "Untitled"
    # Collapse consecutive spaces
    title = re.sub(r"\s+", " ", title)

    authors = []
    for author_elem in entry.findall("atom:author", ns):
        name = author_elem.find("atom:name", ns)
        if name is not None and name.text:
            authors.append(name.text.strip())
    author_str = " and ".join(authors) if authors else "Unknown"

    published_elem = entry.find("atom:published", ns)
    year = published_elem.text[:4] if published_elem is not None and published_elem.text else ""

    # Generate citation key: FirstAuthorSurnameYear
    first_surname = authors[0].split()[-1].lower() if authors else "arxiv"
    first_surname = re.sub(r"\W+", "", first_surname)
    cite_key = f"{first_surname}{year}{clean_id.split('.')[0]}"

    primary_cat = entry.find("arxiv:primary_category", ns)
    category = primary_cat.attrib.get("term", "") if primary_cat is not None else ""

    bibtex = f"""@article{{{cite_key},
  author    = {{{author_str}}},
  title     = {{{title}}},
  journal   = {{arXiv preprint arXiv:{clean_id}}},
  year      = {{{year}}},
  eprint    = {{{clean_id}}},
  archivePrefix = {{arXiv}},
  primaryClass = {{{category}}}
}}"""
    return bibtex


def main():
    parser = argparse.ArgumentParser(description="Fetch candidate BibTeX for an explicit DOI or arXiv identifier.")
    parser.add_argument("identifier", help="DOI (e.g. 10.1145/...) or arXiv ID (e.g. 2301.00001)")
    parser.add_argument("--append", "-a", help="Append the BibTeX entry to a specified .bib file")

    args = parser.parse_args()
    ident = args.identifier.strip()

    try:
        if "arxiv" in ident.lower() or re.match(r"^\d{4}\.\d{4,5}", ident):
            bibtex = fetch_arxiv_bibtex(ident)
        else:
            bibtex = fetch_doi_bibtex(ident)

        print(bibtex)

        if args.append:
            with open(args.append, "a", encoding="utf-8") as f:
                f.write("\n\n" + bibtex + "\n")
            print(f"\n[OK] Appended entry to {args.append}", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
