# Econ Abstracts Viewer (MVP)

Batch publisher → immutable snapshot → dumb, fast reader (tiles + masks).

Abstract Scroller is a **review snapshot compiler and static reader**, not a paper corpus authority. It consumes prepared review records, compiles immutable snapshot assets, and serves them cheaply without requiring the upstream producer at runtime.

## Preferred machine input

The canonical paper-review interface is producer-owned `paper.review-record@1` JSONL. Paper KB is one current producer, but Abstract Scroller validates only the compatibility surface it actually needs. It does **not** vendor or become authority for the Paper KB schema.

```bash
make snapshot-review-records \
  INPUT=/path/to/paper.review-record.v1.jsonl \
  OUT=data/snapshots/paper-review

make validate OUT=data/snapshots/paper-review
```

For this interface, canonical `paper_uid` becomes snapshot `doc_id`, preserving producer identity across the projection.

## Compatibility inputs

CSV and the earlier local `review_node_jsonl` format remain supported so old workflows do not break, but they are not preferred machine seams:

```bash
make snapshot-csv-legacy \
  LEGACY_CSV_INPUT=/path/to/papers.csv \
  OUT=data/snapshots/legacy-csv

make snapshot-review-node-legacy \
  LEGACY_REVIEW_NODE_INPUT=/path/to/review-node.jsonl \
  OUT=data/snapshots/legacy-review-node
```

`make snapshot` is retained as the historical toy-CSV demo and prints its compatibility status explicitly.

## Local development

Create a venv and install dependencies:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Serve generated data with Brotli headers:

```bash
make serve
```

Then open `frontend/index.html` (or equivalent for your OS).

## Boundary

Abstract Scroller owns snapshot ordering, manifest/tile representation, immutable snapshot generation, and the lightweight reader. It does not own paper ingestion, paper identity semantics, review-record domain contracts, evidence selection, or upstream corpus mutation.

See `contracts/README.md` for the status of local compatibility schemas.
