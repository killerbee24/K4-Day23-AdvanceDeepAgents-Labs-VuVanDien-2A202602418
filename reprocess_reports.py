"""Reprocess existing generated reports through the canonical sandbox pipeline."""
import json
import os
import sys
from pathlib import Path

from agents import REPORT_PATH, SOURCES_PATH, WORKDIR
from research import SOURCE_FAMILIES, restore_finalize_and_validate
from sandbox import download, open_sandbox, upload


def reprocess(report_path):
    report_path = Path(report_path).resolve()
    if report_path.suffix != ".md" or report_path.name.endswith(".meta.md"):
        raise ValueError("expected a generated reports/<slug>.md file")
    sources_path = report_path.with_suffix(".sources.json")
    meta_path = report_path.with_suffix(".meta.json")
    if not all(path.is_file() for path in (report_path, sources_path, meta_path)):
        raise ValueError(f"missing report triplet for {report_path.name}")

    with open_sandbox() as backend:
        prepared = backend.execute(f"mkdir -p {WORKDIR}/research/notes {WORKDIR}/report")
        if prepared.exit_code != 0:
            raise RuntimeError(prepared.output)
        upload(backend, {REPORT_PATH: report_path.read_bytes(), SOURCES_PATH: sources_path.read_bytes()})
        restore_finalize_and_validate(backend)
        generated = download(backend, [REPORT_PATH, SOURCES_PATH])
    report_bytes, sources_bytes = generated.get(REPORT_PATH), generated.get(SOURCES_PATH)
    if not report_bytes or not sources_bytes:
        raise RuntimeError("sandbox returned an incomplete report")

    sources = json.loads(sources_bytes.decode("utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["n_sources"] = len(sources)
    meta["source_families"] = sorted({
        item.get("source") for item in sources if item.get("source") in SOURCE_FAMILIES
    })
    outputs = {
        report_path: report_bytes,
        sources_path: sources_bytes,
        meta_path: (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }
    pending = []
    try:
        for final_path, content in outputs.items():
            temp_path = final_path.with_name(f".{final_path.name}.reprocess.tmp")
            temp_path.write_bytes(content)
            pending.append((temp_path, final_path))
        for temp_path, final_path in pending:
            os.replace(temp_path, final_path)
    finally:
        for temp_path, _ in pending:
            temp_path.unlink(missing_ok=True)
    return report_path


def main(argv):
    if not argv:
        print("Usage: python reprocess_reports.py reports/<slug>.md [...]", file=sys.stderr)
        return 2
    try:
        for path in argv:
            print(f"Reprocessed {reprocess(path)}")
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
