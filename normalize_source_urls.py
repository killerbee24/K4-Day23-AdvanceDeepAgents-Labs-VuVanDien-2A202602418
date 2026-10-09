"""Normalize source URLs before the canonical citation finalizer runs.

This helper runs inside the sandbox.  Some otherwise valid publisher URLs contain
literal parentheses or square brackets, but the lab's citation validator treats
those characters as reference delimiters.  Percent-encoding them preserves the
resource while making the generated reference line unambiguous.
"""
import json
import sys
import urllib.parse


SOURCES = "/tmp/work/research/sources.json"
_URL_SAFE = ":/?#@!$&'*+,;=%~-._"


def normalize_url(value):
    return urllib.parse.quote(str(value).strip(), safe=_URL_SAFE)


def normalize_sources(sources):
    if not isinstance(sources, list) or not all(isinstance(item, dict) for item in sources):
        raise ValueError("sources.json must be a JSON list of objects")
    normalized = []
    for item in sources:
        copy = dict(item)
        if isinstance(copy.get("url"), str):
            copy["url"] = normalize_url(copy["url"])
        normalized.append(copy)
    return normalized


def main(argv):
    path = argv[1] if len(argv) > 1 else SOURCES
    try:
        with open(path, encoding="utf-8") as handle:
            sources = json.load(handle)
        sources = normalize_sources(sources)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(sources, handle, ensure_ascii=False, indent=2)
    except (OSError, ValueError) as exc:
        print(f"cannot normalize source URLs: {exc}")
        return 1
    print(f"NORMALIZED: {len(sources)} source URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
