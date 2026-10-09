"""check_citations.py - STUDENT IMPLEMENTS `check`.   Runs INSIDE the sandbox (standard library only).

research.py uploads this file to the sandbox and the lead agent runs it with the `execute` tool:
    python3 /tmp/work/research/check_citations.py [report.md] [sources.json]
It must exit 0 and print "OK: ..." when the report is consistent, else print each problem and exit 1.
"""
import json
import re
import sys

REPORT = "/tmp/work/report/report.md"
SOURCES = "/tmp/work/research/sources.json"

_REFERENCE_HEADING = re.compile(r"(?m)^##[ \t]+References[ \t]*$")
_REFERENCE_LINE = re.compile(r"(?m)^[ \t]*\[(\d+)\][ \t]+(.+?)[ \t]*$")
_CITATION_GROUP = re.compile(r"\[(\d+(?:\s*(?:,|[-–])\s*\d+)*)\](?!\()")
_CODE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
_URL = re.compile(r"https?://[^\s<>\])]+")


def _citation_numbers(group):
    """Expand a citation group such as ``1, 3-5`` into individual numbers."""
    numbers = []
    for part in re.split(r"\s*,\s*", group):
        span = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", part)
        if span:
            start, end = int(span.group(1)), int(span.group(2))
            # Do not let malicious or accidental citations allocate a huge range.
            numbers.extend(range(start, end + 1) if 0 <= end - start <= 200 else (start, end))
        else:
            numbers.append(int(part))
    return numbers


def _body_citations(body):
    """Return citations from prose, excluding fenced/inline code and Markdown links."""
    citations = set()
    for index, segment in enumerate(_CODE.split(body)):
        if index % 2:  # odd segments are code captured by _CODE
            continue
        for match in _CITATION_GROUP.finditer(segment):
            citations.update(_citation_numbers(match.group(1)))
    return citations


def check(report_text, sources):
    """Return a list of problem strings (empty list = OK).

    PSEUDO-CODE:
      problems = []
      if sources is empty: return ["no sources in sources.json"]
      for each source entry:
          n must be an int                       -> problem if not
          url must start with http:// or https://-> problem if not
          the same url must not appear twice     -> problem if duplicated
      split report_text at the heading "## References":
          body = text before it; if the heading is missing -> problem
      cited = set of numbers found as [n] in the BODY only (not in the reference list; use a regex)
      every number in `cited` must exist in sources -> problem "[n] cited but missing from sources.json"
      every source number must be in `cited`        -> problem "source [n] never cited"
      the lines of the References section that start with "[n]" (regex) are the reference lines:
          every source needs exactly ONE reference line (none missing, no number twice, no number that is not a source)
          each reference line holds exactly ONE http(s) URL and it must equal that source's url
          (a line bundling several sources under one number is a problem)
      return problems
    """
    problems = []
    if not isinstance(report_text, str):
        return ["report must be text"]
    if not isinstance(sources, list):
        return ["sources.json must be a JSON list"]
    if not sources:
        return ["no sources in sources.json"]

    source_by_n = {}
    seen_urls = {}
    for index, source in enumerate(sources):
        label = f"source entry {index + 1}"
        if not isinstance(source, dict):
            problems.append(f"{label} is not an object")
            continue

        number = source.get("n")
        url = source.get("url")
        if type(number) is not int:  # bool is an int subclass, but not a valid citation number
            problems.append(f"{label} has non-integer n={number!r}")
        elif number in source_by_n:
            problems.append(f"source number [{number}] appears more than once")
        else:
            source_by_n[number] = source

        if not isinstance(url, str) or not re.match(r"^https?://", url):
            problems.append(f"{label} has invalid url={url!r}")
        elif url in seen_urls:
            problems.append(f"duplicate source url {url!r} in entries {seen_urls[url]} and {index + 1}")
        else:
            seen_urls[url] = index + 1

    headings = list(_REFERENCE_HEADING.finditer(report_text))
    if not headings:
        problems.append("report is missing the ## References heading")
        body, references = report_text, ""
    else:
        if len(headings) > 1:
            problems.append("report has more than one ## References heading")
        heading = headings[0]
        body, references = report_text[:heading.start()], report_text[heading.end():]

    cited = _body_citations(body)
    for number in sorted(cited):
        if number not in source_by_n:
            problems.append(f"[{number}] cited but missing from sources.json")
    for number in sorted(source_by_n):
        if number not in cited:
            problems.append(f"source [{number}] never cited")

    reference_lines = {}
    for match in _REFERENCE_LINE.finditer(references):
        number = int(match.group(1))
        reference_lines.setdefault(number, []).append(match.group(2))

    for number in sorted(reference_lines):
        if number not in source_by_n:
            problems.append(f"reference [{number}] has no matching source")
        if len(reference_lines[number]) > 1:
            problems.append(f"reference [{number}] appears more than once")

    for number in sorted(source_by_n):
        lines = reference_lines.get(number, [])
        if not lines:
            problems.append(f"source [{number}] has no reference line")
            continue
        # Validate every duplicate line too; the duplicate itself remains a separate problem.
        for line in lines:
            urls = _URL.findall(line)
            if len(urls) != 1:
                problems.append(f"reference [{number}] must contain exactly one URL (found {len(urls)})")
            elif urls[0] != source_by_n[number].get("url"):
                problems.append(
                    f"reference [{number}] URL {urls[0]!r} does not match sources.json "
                    f"{source_by_n[number].get('url')!r}"
                )

    return problems


def main(argv):
    report_path = argv[1] if len(argv) > 1 else REPORT
    sources_path = argv[2] if len(argv) > 2 else SOURCES
    try:
        with open(report_path, encoding="utf-8") as f:
            report = f.read()
        with open(sources_path, encoding="utf-8") as f:
            sources = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"cannot read inputs: {exc}")
        return 1
    problems = check(report, sources)
    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {len(sources)} sources, all citations resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
