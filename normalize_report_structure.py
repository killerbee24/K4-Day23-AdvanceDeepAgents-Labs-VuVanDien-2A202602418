"""Normalize the one report heading whose exact spelling is required by the lab."""
import re
import sys


REPORT = "/tmp/work/report/report.md"
CANONICAL = "## Trends and open problems"
_HEADING = re.compile(r"(?mi)^##[ \t]+([^\n]+?)[ \t]*$")


def normalize_structure(report):
    def clean(value):
        return "\n".join(line.rstrip() for line in value.splitlines()) + ("\n" if value.endswith("\n") else "")

    headings = list(_HEADING.finditer(report))
    exact = [match for match in headings if match.group(0) == CANONICAL]
    if len(exact) == 1:
        return clean(report)

    candidates = [
        match for match in headings
        if "trend" in match.group(1).casefold() and (
            "open problem" in match.group(1).casefold() or "future direction" in match.group(1).casefold()
        )
    ]
    if not candidates:
        candidates = [match for match in headings if "open problem" in match.group(1).casefold()]
    if not candidates:
        raise ValueError("cannot find a Trends/Open Problems heading to normalize")

    chosen = candidates[-1]
    normalized = report[:chosen.start()] + CANONICAL + report[chosen.end():]
    # If a malformed report already contained more than one exact copy, keep only the chosen one exact.
    seen = 0
    parts = []
    last = 0
    for match in _HEADING.finditer(normalized):
        if match.group(0) != CANONICAL:
            continue
        seen += 1
        parts.append(normalized[last:match.start()])
        parts.append(CANONICAL if seen == 1 else "## Additional outlook")
        last = match.end()
    return clean("".join(parts) + normalized[last:] if parts else normalized)


def main(argv):
    path = argv[1] if len(argv) > 1 else REPORT
    try:
        with open(path, encoding="utf-8") as handle:
            report = handle.read()
        report = normalize_structure(report)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(report)
    except (OSError, ValueError) as exc:
        print(f"cannot normalize report structure: {exc}")
        return 1
    print("STRUCTURE: normalized required heading")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
