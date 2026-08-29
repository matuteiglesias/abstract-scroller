from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import brotli


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
    from pipeline.contracts.review_record import validate_review_record_dict  # type: ignore
    from pipeline.projections.review_records import export_review_records  # type: ignore
    from pipeline.writers.chunk_set_writer import write_chunk_set_artifact  # type: ignore

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        chunk_sets = temp / "chunk_sets"
        chunk_sets.mkdir()

        cases = [
            {
                "paper_uid": "paper_aaa111",
                "title": "First canonical paper",
                "abstract": "First canonical abstract from the producer-owned review record.",
                "year": 2025,
                "venue": "Synthetic Journal",
                "tags": ["economics"],
                "badges": ["has_code"],
            },
            {
                "paper_uid": "paper_bbb222",
                "title": "Second canonical paper",
                "abstract": "Second canonical abstract from the producer-owned review record.",
                "year": 2026,
                "venue": "Synthetic Conference",
                "tags": ["methods"],
                "badges": [],
            },
        ]

        for index, case in enumerate(cases, start=1):
            uid = case["paper_uid"]
            write_chunk_set_artifact(
                [
                    {
                        "chunk_id": f"{uid}-c1",
                        "paper_id": uid,
                        "paper_uid": uid,
                        "text": f"Synthetic governed chunk for {uid}.",
                        "chunk_index": 0,
                        "metadata": {},
                    }
                ],
                source_items=[f"{uid}.tei.xml"],
                run_id=f"p3-proof-{index}",
                out_dir=chunk_sets,
                paper_meta={
                    "paper_uid": uid,
                    "paper_id": uid,
                    "title": case["title"],
                    "abstract": case["abstract"],
                    "year": case["year"],
                    "venue": case["venue"],
                    "tags": case["tags"],
                    "badges": case["badges"],
                    "source_url": f"https://example.invalid/{uid}",
                },
            )

        review_jsonl = temp / "paper.review-record.v1.jsonl"
        export_summary = export_review_records(
            chunk_set_dir=chunk_sets,
            out_path=review_jsonl,
        )
        if export_summary.get("records") != 2:
            _fail(f"Paper KB exported unexpected record count: {export_summary}")

        raw_jsonl = review_jsonl.read_bytes()
        records = [
            json.loads(line)
            for line in review_jsonl.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if [record.get("paper_uid") for record in records] != ["paper_aaa111", "paper_bbb222"]:
            _fail("Paper KB review projection did not preserve deterministic canonical identity order")
        for record in records:
            validate_review_record_dict(record)

        snapshot = temp / "snapshot"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "backend.jobs.mvp_snapshot",
                "--input",
                str(review_jsonl),
                "--format",
                "paper_review_record_jsonl",
                "--out",
                str(snapshot),
            ],
            cwd=consumer_root,
            check=True,
        )

        manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("counts", {}).get("docs") != 2:
            _fail("Abstract Scroller snapshot manifest does not contain 2 docs")

        tile_path = snapshot / "tiles" / "tile_00000.json.br"
        tile = json.loads(brotli.decompress(tile_path.read_bytes()).decode("utf-8"))
        docs = tile.get("docs")
        if not isinstance(docs, list) or len(docs) != 2:
            _fail("Abstract Scroller first tile does not contain 2 docs")
        tiled = {doc.get("doc_id"): doc for doc in docs}
        if set(tiled) != {"paper_aaa111", "paper_bbb222"}:
            _fail(f"Snapshot changed canonical paper identity: {sorted(tiled)}")
        if tiled["paper_aaa111"].get("title") != "First canonical paper":
            _fail("Snapshot changed canonical title")
        if not str(tiled["paper_aaa111"].get("abstract_300", "")).startswith("First canonical abstract"):
            _fail("Snapshot changed canonical abstract")
        if tiled["paper_bbb222"].get("year") != 2026:
            _fail("Snapshot changed canonical year")

        summary = {
            "status": "PASS",
            "producer_repository": "matuteiglesias/paper-kb",
            "producer_commit": producer_commit,
            "producer_surface": "pipeline.projections.review_records",
            "interface": "paper.review-record@1 JSONL",
            "jsonl_sha256": hashlib.sha256(raw_jsonl).hexdigest(),
            "exported_docs": len(records),
            "consumer_repository": "matuteiglesias/abstract-scroller",
            "consumer_surface": "backend.jobs.mvp_snapshot --format paper_review_record_jsonl",
            "snapshot_docs": manifest["counts"]["docs"],
            "canonical_identity_preserved": set(tiled) == {"paper_aaa111", "paper_bbb222"},
        }
        print(json.dumps(summary, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
