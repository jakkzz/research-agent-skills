#!/usr/bin/env python3
"""
search_papers.py
Search scholarly literature across arXiv and CrossRef APIs with zero external dependencies.
Extracts verified metadata, abstracts, and BibTeX citations.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional


USER_AGENT = "research-agent-skills/0.1.0 (mailto:academic-tools@users.noreply.github.com)"


def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def generate_cite_key(authors: List[str], year: str, title: str) -> str:
    first_author = "unknown"
    if authors:
        first_author = authors[0].split()[-1].lower()
        first_author = re.sub(r"\W+", "", first_author)

    first_word = "paper"
    words = [w.lower() for w in re.findall(r"[a-zA-Z0-9]+", title)]
    stopwords = {"a", "an", "the", "in", "on", "of", "and", "for", "to", "with", "at", "by"}
    for w in words:
        if w not in stopwords:
            first_word = w
            break

    yr = year if year else "nd"
    return f"{first_author}{yr}{first_word}"


def search_arxiv(query: str, limit: int = 5) -> List[Dict]:
    encoded_query = urllib.parse.quote(query)
    url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml_data = resp.read()
    except Exception as e:
        print(f"Warning: arXiv search failed: {e}", file=sys.stderr)
        return []

    root = ET.fromstring(xml_data)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    results = []
    for entry in root.findall("atom:entry", ns):
        title_elem = entry.find("atom:title", ns)
        title = clean_text(title_elem.text) if title_elem is not None else "Untitled"

        summary_elem = entry.find("atom:summary", ns)
        summary = clean_text(summary_elem.text) if summary_elem is not None else ""

        id_elem = entry.find("atom:id", ns)
        raw_id = id_elem.text.strip() if id_elem is not None else ""
        arxiv_match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", raw_id)
        arxiv_id = arxiv_match.group(1) if arxiv_match else raw_id

        published_elem = entry.find("atom:published", ns)
        year = published_elem.text[:4] if published_elem is not None and published_elem.text else ""

        authors = []
        for author_elem in entry.findall("atom:author", ns):
            name = author_elem.find("atom:name", ns)
            if name is not None and name.text:
                authors.append(clean_text(name.text))

        pdf_link = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else ""
        cite_key = generate_cite_key(authors, year, title)

        author_str = " and ".join(authors) if authors else "Unknown"
        bibtex = f"""@article{{{cite_key},
  author    = {{{author_str}}},
  title     = {{{title}}},
  journal   = {{arXiv preprint arXiv:{arxiv_id}}},
  year      = {{{year}}},
  eprint    = {{{arxiv_id}}},
  archivePrefix = {{arXiv}}
}}"""

        results.append({
            "source": "arxiv",
            "title": title,
            "authors": authors,
            "year": year,
            "id": arxiv_id,
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "pdf_url": pdf_link,
            "abstract": summary,
            "cite_key": cite_key,
            "bibtex": bibtex
        })

    return results


def search_crossref(query: str, limit: int = 5) -> List[Dict]:
    params = urllib.parse.urlencode({
        "query": query,
        "rows": limit,
        "mailto": "academic-tools@users.noreply.github.com"
    })
    url = f"https://api.crossref.org/works?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Warning: CrossRef search failed: {e}", file=sys.stderr)
        return []

    items = data.get("message", {}).get("items", [])
    results = []

    for item in items:
        titles = item.get("title", [])
        title = clean_text(titles[0]) if titles else "Untitled"

        raw_authors = item.get("author", [])
        authors = []
        for a in raw_authors:
            given = a.get("given", "")
            family = a.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        year = ""
        published = item.get("published-print") or item.get("published-online") or item.get("created")
        if published and "date-parts" in published:
            parts = published["date-parts"]
            if parts and parts[0]:
                year = str(parts[0][0])

        doi = item.get("DOI", "")
        container = item.get("container-title", [])
        venue = container[0] if container else ""

        cite_key = generate_cite_key(authors, year, title)
        author_str = " and ".join(authors) if authors else "Unknown"

        bibtex = f"""@article{{{cite_key},
  author    = {{{author_str}}},
  title     = {{{title}}},
  journal   = {{{venue}}},
  year      = {{{year}}},
  doi       = {{{doi}}}
}}"""

        results.append({
            "source": "crossref",
            "title": title,
            "authors": authors,
            "year": year,
            "id": doi,
            "url": f"https://doi.org/{doi}" if doi else item.get("URL", ""),
            "abstract": clean_text(item.get("abstract", "")),
            "cite_key": cite_key,
            "bibtex": bibtex
        })

    return results


def search_all(query: str, limit: int = 5, source: str = "all", min_year: Optional[int] = None) -> List[Dict]:
    results = []
    if source in ["arxiv", "all"]:
        results.extend(search_arxiv(query, limit=limit))
    if source in ["crossref", "all"]:
        results.extend(search_crossref(query, limit=limit))

    # Deduplicate by normalized title
    seen_titles = set()
    unique_results = []
    for r in results:
        norm_title = re.sub(r"\W+", "", r["title"].lower())
        if norm_title in seen_titles:
            continue
        seen_titles.add(norm_title)

        if min_year and r.get("year"):
            try:
                if int(r["year"]) < min_year:
                    continue
            except ValueError:
                pass

        unique_results.append(r)

    return unique_results[:limit]


def main():
    parser = argparse.ArgumentParser(description="Search scholarly literature and generate verified BibTeX citations.")
    parser.add_argument("query", help="Search query (topics, keywords, or authors)")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Maximum results to return (default: 5)")
    parser.add_argument("--source", choices=["arxiv", "crossref", "all"], default="all", help="Source repository")
    parser.add_argument("--min-year", type=int, help="Filter papers published on or after this year")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data")
    parser.add_argument("--bib", action="store_true", help="Output BibTeX entries only")
    parser.add_argument("--append", "-a", help="Append retrieved BibTeX entries to a .bib file")

    args = parser.parse_args()

    results = search_all(args.query, limit=args.limit, source=args.source, min_year=args.min_year)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    if args.bib:
        bib_output = "\n\n".join(r["bibtex"] for r in results)
        print(bib_output)
        if args.append and bib_output:
            with open(args.append, "a", encoding="utf-8") as f:
                f.write("\n\n" + bib_output + "\n")
            print(f"\n[OK] Appended {len(results)} entries to {args.append}", file=sys.stderr)
        return

    # Default human-readable output
    print(f"\n================ SCHOLARLY LITERATURE SEARCH ================")
    print(f"Query:   '{args.query}'")
    print(f"Results: {len(results)} paper(s) found")
    print("=============================================================\n")

    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['title']}")
        print(f"    Authors: {', '.join(r['authors'][:3])}{' et al.' if len(r['authors']) > 3 else ''}")
        print(f"    Year:    {r['year']} | Source: {r['source'].upper()} | Key: {r['cite_key']}")
        print(f"    URL:     {r['url']}")
        if r.get("abstract"):
            snippet = r["abstract"][:200] + ("..." if len(r["abstract"]) > 200 else "")
            print(f"    Abstract: {snippet}")
        print()

    if args.append and results:
        bib_output = "\n\n".join(r["bibtex"] for r in results)
        with open(args.append, "a", encoding="utf-8") as f:
            f.write("\n\n" + bib_output + "\n")
        print(f"[OK] Appended {len(results)} entries to {args.append}")


if __name__ == "__main__":
    main()
