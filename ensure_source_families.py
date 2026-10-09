"""Ensure three required source families are cited before finalization.

The lead sometimes merges a valid source but forgets to cite it, so the canonical
finalizer removes that family.  This deterministic sandbox-only step uses only
source metadata and evidence already written by researcher subagents.  It never
contacts the network and never invents a source.
"""
import glob
import json
import re
import sys


REPORT = "/tmp/work/report/report.md"
SOURCES = "/tmp/work/research/sources.json"
NOTES_GLOB = "/tmp/work/research/notes/*.md"
REQUIRED = ("arxiv", "hf-search", "web")

_REF_HEADING = re.compile(r"(?m)^##[ \t]+References[ \t]*$")
_CITATION_GROUP = re.compile(r"\[(\d+(?:\s*(?:,|[-–])\s*\d+)*)\](?!\()")


def _clean(value):
    return " ".join(str(value or "").split())


def _citation_numbers(text):
    numbers = set()
    for match in _CITATION_GROUP.finditer(text):
        for part in re.split(r"\s*,\s*", match.group(1)):
            span = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", part)
            if span:
                start, end = map(int, span.groups())
                numbers.update(range(start, end + 1) if 0 <= end - start <= 200 else (start, end))
            else:
                numbers.add(int(part))
    return numbers


def parse_notes(note_texts):
    records = []
    for text in note_texts:
        for block in re.split(r"(?m)^###\s+", str(text)) [1:]:
            lines = block.splitlines()
            if not lines:
                continue
            record = {"title": _clean(lines[0])}
            evidence = []
            in_evidence = False
            for line in lines[1:]:
                field = re.match(r"^-\s+(id|url|date|source):\s*(.*)$", line.strip())
                if field:
                    key, value = field.groups()
                    record[key] = _clean(value)
                    in_evidence = key == "evidence"
                    continue
                if re.match(r"^-\s+evidence:\s*$", line.strip()):
                    in_evidence = True
                    continue
                item = re.match(r"^\s+-\s+(.+)$", line)
                if in_evidence and item:
                    evidence.append(_clean(item.group(1)))
            if record.get("url") and record.get("source"):
                record["evidence"] = evidence
                records.append(record)
    return records


def _valid_family_url(family, url):
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return False
    if family == "arxiv":
        return url.startswith("https://arxiv.org/abs/")
    if family == "hf-search":
        return url.startswith("https://huggingface.co/papers/")
    return family == "web"


def normalize_invalid_family_labels(sources):
    """Downgrade impossible arXiv/HF labels to web before coverage is measured."""
    for item in sources:
        family, url = item.get("source"), item.get("url")
        if family in {"arxiv", "hf-daily", "hf-search"} and not _valid_family_url(
            "hf-search" if family == "hf-daily" else family, url
        ):
            item["source"] = "web"
    return sources


def ensure_coverage(report, sources, note_texts):
    if not isinstance(sources, list) or not all(isinstance(item, dict) for item in sources):
        raise ValueError("sources.json must be a JSON list of objects")
    sources = normalize_invalid_family_labels(sources)
    heading = _REF_HEADING.search(report)
    body = report[:heading.start()].rstrip() if heading else report.rstrip()
    references = report[heading.start():] if heading else ""
    cited = _citation_numbers(body)
    by_number = {item.get("n"): item for item in sources if type(item.get("n")) is int}
    cited_families = {
        by_number[number].get("source") for number in cited if number in by_number
    }
    missing = [family for family in REQUIRED if family not in cited_families]
    if not missing:
        return report, sources, []

    notes = parse_notes(note_texts)
    notes_by_url = {item["url"]: item for item in notes}
    used_urls = {item.get("url") for item in sources}
    next_number = max((number for number in by_number if type(number) is int), default=0) + 1
    additions = []

    for family in missing:
        candidate = next(
            (item for item in sources if item.get("source") == family and _valid_family_url(family, item.get("url"))),
            None,
        )
        note = notes_by_url.get(candidate.get("url")) if candidate else None
        if candidate is None:
            note = next(
                (item for item in notes if item.get("source") == family
                 and item.get("url") not in used_urls and _valid_family_url(family, item.get("url"))),
                None,
            )
            if note is None:
                raise ValueError(f"no researcher-note source available for missing family {family}")
            candidate = {
                "n": next_number,
                "id": note.get("id", ""),
                "url": note["url"],
                "title": note.get("title") or "Untitled",
                "date": note.get("date") or "n.d.",
                "source": family,
            }
            sources.append(candidate)
            used_urls.add(candidate["url"])
            by_number[next_number] = candidate
            next_number += 1

        evidence = (note or {}).get("evidence") or []
        if evidence:
            fact = re.sub(r"\[(?:\d+[\s,–-]*)+\]", "", evidence[0]).strip().rstrip(".")
            sentence = f"The collected {family} evidence also reports that {fact} [{candidate['n']}]."
        else:
            title = _clean(candidate.get("title") or "Untitled").replace('"', "'")
            sentence = f'The {family} source "{title}" also contributes to this evidence base [{candidate["n"]}].'
        additions.append(sentence)

    repaired = body + "\n\n" + " ".join(additions)
    if references:
        repaired += "\n\n" + references
    else:
        repaired += "\n"
    return repaired, sources, missing


def main(argv):
    report_path = argv[1] if len(argv) > 1 else REPORT
    sources_path = argv[2] if len(argv) > 2 else SOURCES
    try:
        with open(report_path, encoding="utf-8") as handle:
            report = handle.read()
        with open(sources_path, encoding="utf-8") as handle:
            sources = json.load(handle)
        note_texts = []
        for path in sorted(glob.glob(NOTES_GLOB)):
            with open(path, encoding="utf-8") as handle:
                note_texts.append(handle.read())
        report, sources, repaired = ensure_coverage(report, sources, note_texts)
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write(report)
        with open(sources_path, "w", encoding="utf-8") as handle:
            json.dump(sources, handle, ensure_ascii=False, indent=2)
    except (OSError, ValueError) as exc:
        print(f"cannot ensure source-family coverage: {exc}")
        return 1
    print("SOURCE FAMILIES: " + ("repaired " + ", ".join(repaired) if repaired else "already complete"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
