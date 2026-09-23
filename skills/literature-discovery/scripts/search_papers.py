#!/usr/bin/env python3
"""Discover candidate records from arXiv and Crossref APIs."""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

USER_AGENT = "research-agent-skills/0.1.0-alpha (mailto:academic-tools@users.noreply.github.com)"
MAX_RESULTS = 100


def clean_text(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", text).strip() if text else ""


def generate_cite_key(authors: List[str], year: str, title: str) -> str:
    first_author = "unknown"
    if authors:
        first_author = re.sub(r"\W+", "", authors[0].split()[-1].lower()) or "unknown"
    first_word = "paper"
    stopwords = {"a", "an", "the", "in", "on", "of", "and", "for", "to", "with", "at", "by"}
    for word in re.findall(r"[A-Za-z0-9]+", title.lower()):
        if word not in stopwords:
            first_word = word
            break
    return f"{first_author}{year or 'nd'}{first_word}"


def _provider_result(source: str, results=None, error=None) -> Dict:
    return {
        "source": source,
        "status": "error" if error else "ok",
        "error": str(error) if error else None,
        "results": results or [],
    }


def search_arxiv(query: str, limit: int = 5) -> Dict:
    encoded_query = urllib.parse.quote(query)
    url = f"https://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={limit}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            root = ET.fromstring(response.read())
    except Exception as exc:
        return _provider_result("arxiv", error=f"arXiv request or XML parsing failed: {exc}")
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    results = []
    for entry in root.findall("atom:entry", namespace):
        title_element = entry.find("atom:title", namespace)
        summary_element = entry.find("atom:summary", namespace)
        id_element = entry.find("atom:id", namespace)
        published_element = entry.find("atom:published", namespace)
        title = clean_text(title_element.text if title_element is not None else None) or "Untitled"
        raw_id = clean_text(id_element.text if id_element is not None else None)
        identifier_match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", raw_id)
        identifier = identifier_match.group(1) if identifier_match else raw_id
        year = (published_element.text or "")[:4] if published_element is not None else ""
        authors = [
            clean_text(name.text)
            for author in entry.findall("atom:author", namespace)
            for name in [author.find("atom:name", namespace)]
            if name is not None and name.text
        ]
        key = generate_cite_key(authors, year, title)
        author_string = " and ".join(authors) if authors else "Unknown"
        bibtex = (
            f"@article{{{key},\n  author = {{{author_string}}},\n  title = {{{title}}},\n"
            f"  journal = {{arXiv preprint arXiv:{identifier}}},\n  year = {{{year}}},\n"
            f"  eprint = {{{identifier}}},\n  archivePrefix = {{arXiv}}\n}}"
        )
        results.append({
            "source": "arxiv", "title": title, "authors": authors, "year": year,
            "id": identifier, "url": f"https://arxiv.org/abs/{identifier}",
            "pdf_url": f"https://arxiv.org/pdf/{identifier}.pdf" if identifier else "",
            "abstract": clean_text(summary_element.text if summary_element is not None else None),
            "cite_key": key, "bibtex": bibtex,
            "record_note": "Candidate metadata from arXiv; not peer-review or content verification.",
        })
    return _provider_result("arxiv", results=results)


def search_crossref(query: str, limit: int = 5) -> Dict:
    parameters = urllib.parse.urlencode({"query": query, "rows": limit, "mailto": "academic-tools@users.noreply.github.com"})
    request = urllib.request.Request(f"https://api.crossref.org/works?{parameters}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        items = data["message"]["items"]
        if not isinstance(items, list):
            raise ValueError("message.items is not a list")
    except Exception as exc:
        return _provider_result("crossref", error=f"Crossref request or JSON parsing failed: {exc}")
    results = []
    for item in items:
        try:
            titles = item.get("title") or []
            title = clean_text(titles[0]) if titles else "Untitled"
            authors = [
                f"{author.get('given', '')} {author.get('family', '')}".strip()
                for author in item.get("author", [])
                if f"{author.get('given', '')} {author.get('family', '')}".strip()
            ]
            published = item.get("published-print") or item.get("published-online") or item.get("created") or {}
            parts = published.get("date-parts") or []
            year = str(parts[0][0]) if parts and parts[0] else ""
            doi = item.get("DOI", "")
            containers = item.get("container-title") or []
            venue = containers[0] if containers else ""
            key = generate_cite_key(authors, year, title)
            author_string = " and ".join(authors) if authors else "Unknown"
            bibtex = (
                f"@article{{{key},\n  author = {{{author_string}}},\n  title = {{{title}}},\n"
                f"  journal = {{{venue}}},\n  year = {{{year}}},\n  doi = {{{doi}}}\n}}"
            )
            results.append({
                "source": "crossref", "title": title, "authors": authors, "year": year,
                "id": doi, "url": f"https://doi.org/{doi}" if doi else item.get("URL", ""),
                "abstract": clean_text(item.get("abstract", "")), "cite_key": key, "bibtex": bibtex,
                "record_note": "Candidate metadata from Crossref; publication and content require independent validation.",
            })
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            return _provider_result("crossref", results=results, error=f"Malformed Crossref item: {exc}")
    return _provider_result("crossref", results=results)


def search_all(query: str, limit: int = 5, source: str = "all", min_year: Optional[int] = None) -> Dict:
    providers = []
    if source in {"arxiv", "all"}:
        providers.append(search_arxiv(query, limit))
    if source in {"crossref", "all"}:
        providers.append(search_crossref(query, limit))
    combined = [record for provider in providers for record in provider["results"]]
    seen = set()
    results = []
    for record in combined:
        normalized = re.sub(r"\W+", "", record["title"].lower())
        if normalized in seen:
            continue
        if min_year and record.get("year"):
            try:
                if int(record["year"]) < min_year:
                    continue
            except ValueError:
                pass
        seen.add(normalized)
        results.append(record)
    failed = sum(provider["status"] == "error" for provider in providers)
    status = "ok" if failed == 0 else ("failure" if failed == len(providers) else "partial_failure")
    return {
        "status": status,
        "results": results[:limit],
        "sources": {provider["source"]: {"status": provider["status"], "error": provider["error"], "result_count": len(provider["results"])} for provider in providers},
        "scope_note": "Candidate discovery only; results are not labeled peer-reviewed or fully verified.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Discover candidate records from arXiv and Crossref.")
    parser.add_argument("query")
    parser.add_argument(
        "--limit", "-n", type=int, default=5,
        help=f"maximum combined results (1-{MAX_RESULTS}; default: 5)",
    )
    parser.add_argument("--source", choices=["arxiv", "crossref", "all"], default="all")
    parser.add_argument("--min-year", type=int)
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true")
    output_group.add_argument("--bib", action="store_true")
    parser.add_argument("--append", "-a")
    args = parser.parse_args(argv)
    if args.append and not args.bib:
        parser.error("--append requires --bib")
    if not 1 <= args.limit <= MAX_RESULTS:
        parser.error(f"--limit must be between 1 and {MAX_RESULTS}")
    report = search_all(args.query, args.limit, args.source, args.min_year)
    results = report["results"]
    if args.json:
        print(json.dumps(report, indent=2))
    elif args.bib:
        output = "\n\n".join(record["bibtex"] for record in results)
        print(output)
        if args.append and output:
            with open(args.append, "a", encoding="utf-8") as handle:
                handle.write("\n\n" + output + "\n")
    else:
        print("LITERATURE CANDIDATE DISCOVERY")
        print(report["scope_note"])
        print(f"Status: {report['status']} | Results: {len(results)}")
        for source_name, source_status in report["sources"].items():
            print(f"Source {source_name}: {source_status['status']}" + (f" - {source_status['error']}" if source_status["error"] else ""))
        for index, record in enumerate(results, 1):
            print(f"[{index}] {record['title']}\n    {record['url']}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
