"""Create small source-tool-grounded anchor notes for the sandbox pipeline."""
import json
import re

from tools import arxiv_search, hf_search_papers, web_search


def _clean(value, limit=800):
    return " ".join(str(value or "").split())[:limit]


def _note(record, family):
    title = _clean(record.get("title"), 300) or "Untitled"
    evidence = _clean(record.get("summary") or record.get("evidence"), 900)
    if not evidence:
        evidence = f'The source is titled "{title}".'
    return (
        f"### {title}\n"
        f"- id: {_clean(record.get('id'), 200)}\n"
        f"- url: {_clean(record.get('url'), 1000)}\n"
        f"- date: {_clean(record.get('date') or record.get('published'), 10) or 'n.d.'}\n"
        f"- source: {family}\n"
        "- evidence:\n"
        f"  - {evidence}\n"
    ).encode("utf-8")


def _first_json_record(raw):
    if not isinstance(raw, str) or raw.startswith(("ERROR:", "NO RESULTS")):
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    return payload[0] if isinstance(payload, list) and payload and isinstance(payload[0], dict) else None


def _first_web_record(raw):
    if not isinstance(raw, str) or raw.startswith(("ERROR:", "NO RESULTS")):
        return None
    first = re.split(r"(?m)^---\s*$", raw, maxsplit=1)[0]
    title = re.search(r"(?m)^Title:\s*(.+)$", first)
    url = re.search(r"(?m)^URL:\s*(\S+)", first)
    published = re.search(r"(?m)^Published:\s*(.+)$", first)
    if not title or not url:
        return None
    highlights = first.split("Highlights:", 1)[-1] if "Highlights:" in first else ""
    evidence = ""
    clean_title = _clean(title.group(1), 300)
    for line in highlights.splitlines():
        candidate = _clean(line.lstrip("#- "), 900)
        if len(candidate) >= 80 and candidate != clean_title and candidate != "...":
            evidence = candidate
            break
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", published.group(1) if published else "")
    return {
        "id": "",
        "url": url.group(1),
        "title": clean_title,
        "date": date_match.group(0) if date_match else "n.d.",
        "evidence": evidence,
    }


def build_anchor_notes(topic, *, arxiv_tool=arxiv_search, hf_tool=hf_search_papers, web_tool=web_search):
    """Return sandbox-path -> note bytes for every source family that answered successfully."""
    topic = _clean(topic, 300)
    notes = {}
    arxiv = _first_json_record(arxiv_tool.invoke({"query": topic, "max_results": 2}))
    if arxiv:
        notes["/tmp/work/research/notes/00-bootstrap-arxiv.md"] = _note(arxiv, "arxiv")
    hf = _first_json_record(hf_tool.invoke({"query": topic, "limit": 2}))
    if hf:
        notes["/tmp/work/research/notes/00-bootstrap-hf-search.md"] = _note(hf, "hf-search")
    web = _first_web_record(web_tool.invoke({
        "query": topic,
        "objective": f"Find a reliable primary or survey source about {topic}",
        "num_results": 2,
    }))
    if web:
        notes["/tmp/work/research/notes/00-bootstrap-web.md"] = _note(web, "web")
    return notes
