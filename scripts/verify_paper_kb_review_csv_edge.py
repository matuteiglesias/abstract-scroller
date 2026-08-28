from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import brotli


EXPECTED_CSV_FIELDS = [
    "doc_id",
    "title",
    "abstract",
    "date",
    "year",
    "venue",
    "tags",
    "badges",
    "source_url",
    "paper_id",
]


def _fail(message: str) -> None:
    raise RuntimeError(message)


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_chunk_set(
    path: Path,
    *,
    paper_id: str,
    title: str,
    text: str,
) -> None:
    payload = {
        "artifact_family": "chunk_bus",
        "artifact_kind": "chunk_set",
        "schema_version": 1,
        "run_id": path.stem,
        "producer": "paper-kb",
        "entrypoint": "paper_tei_parse",
        "source_items": [f"{paper_id}.xml"],
        "chunk_count": 1,
        "paper_meta": {
            "paper_id": paper_id,
            "title": title,
            "source_file": f"{paper_id}.tei.xml",
        },
        "chunks": [
            {
                "chunk_id": f"{paper_id}-c1",
                "paper_id": paper_id,
                "text": text,
                "chunk_index": 0,
                "char_len": len(text),
                "source_file": f"{paper_id}.tei.xml",
                "metadata": {},
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--producer-root", required=True)
    parser.add_argument("--expected-producer-commit", required=True)
    args = parser.parse_args()

    consumer_root = Path(__file__).resolve().parents[1]
    producer_root = Path(args.producer_root).resolve(strict=True)
    producer_commit = _git_head(producer_root)
    if producer_commit != args.expected_producer_commit:
        _fail(
            "Paper KB checkout does not match pinned producer commit: "
            f"expected {args.expected_producer_commit}, got {producer_commit}"
        )

    sys.path.insert(0, str(producer_root))
    from backend.app.storage_adapter import ChunkSetStorageAdapter  # type: ignore
    from backend.exports.export_review_csv import (  # type: ignore
        CSV_FIELDS,
        export_review_csv,
    )

    if list(CSV_FIELDS) != EXPECTED_CSV_FIELDS:
        _fail(
            "Paper KB review CSV field contract changed: "
            f"expected {EXPECTED_CSV_FIELDS}, got {list(CSV_FIELDS)}"
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        chunk_sets = temp / "chunk_sets"
        chunk_sets.mkdir()

        _write_chunk_set(
            chunk_sets / "r1.chunk_set.json",
            paper_id="p1",
            title="Paper One",
            text="First governed abstract from Paper KB.",
        )
        _write_chunk_set(
            chunk_sets / "r2.chunk_set.json",
            paper_id="p2",
            title="Paper Two",
            text="Second governed abstract from Paper KB.",
        )

        review_csv = temp / "paper-kb-review.csv"
        storage = ChunkSetStorageAdapter(chunk_sets_dir=str(chunk_sets))
        export_review_csv(review_csv, storage=storage)

        raw_csv = review_csv.read_bytes()
        with review_csv.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            if reader.fieldnames != EXPECTED_CSV_FIELDS:
                _fail("Generated review CSV header differs from pinned interface")

        if len(rows) != 2:
            _fail(f"Expected 2 Paper KB rows, got {len(rows)}")
        by_id = {row["doc_id"]: row for row in rows}
        if set(by_id) != {"p1", "p2"}:
            _fail(f"Unexpected exported document IDs: {sorted(by_id)}")
        if by_id["p1"]["title"] != "Paper One":
            _fail("Paper KB did not preserve p1 title")
        if not by_id["p1"]["abstract"].startswith("First governed abstract"):
            _fail("Paper KB did not export the expected p1 abstract")

        snapshot = temp / "snapshot"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "backend.jobs.mvp_snapshot",
                "--input",
                str(review_csv),
                "--format",
                "csv",
                "--out",
                str(snapshot),
            ],
            cwd=consumer_root,
            check=True,
        )

        manifest = json.loads(
            (snapshot / "manifest.json").read_text(encoding="utf-8")
        )
        if manifest.get("counts", {}).get("docs") != 2:
            _fail("Abstract Scroller snapshot manifest does not contain 2 docs")

        tile_path = snapshot / "tiles" / "tile_00000.json.br"
        tile = json.loads(
            brotli.decompress(tile_path.read_bytes()).decode("utf-8")
        )
        docs = tile.get("docs")
        if not isinstance(docs, list) or len(docs) != 2:
            _fail("Abstract Scroller first tile does not contain 2 docs")
        tiled = {doc.get("doc_id"): doc for doc in docs}
        if set(tiled) != {"p1", "p2"}:
            _fail(f"Snapshot changed document identity: {sorted(tiled)}")
        if tiled["p1"].get("title") != "Paper One":
            _fail("Snapshot changed p1 title")
        if not str(tiled["p1"].get("abstract_300", "")).startswith(
            "First governed abstract"
        ):
            _fail("Snapshot changed p1 abstract")

        summary = {
            "status": "PASS",
            "producer_repository": "matuteiglesias/paper-kb",
            "producer_commit": producer_commit,
            "producer_surface": "backend.exports.export_review_csv",
            "interface": "review CSV",
            "csv_fields": EXPECTED_CSV_FIELDS,
            "csv_sha256": hashlib.sha256(raw_csv).hexdigest(),
            "exported_docs": len(rows),
            "consumer_repository": "matuteiglesias/abstract-scroller",
            "consumer_surface": "backend.jobs.mvp_snapshot --format csv",
            "snapshot_docs": manifest["counts"]["docs"],
            "identity_preserved": sorted(tiled) == ["p1", "p2"],
        }
        print(json.dumps(summary, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
