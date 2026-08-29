# Econ Abstracts Viewer (MVP)

Batch publisher → immutable snapshot → dumb, fast reader (tiles + masks).

Abstract Scroller is a **review snapshot compiler and static reader**, not a paper corpus authority. It consumes prepared review records, compiles immutable snapshot assets, and serves them cheaply without requiring the upstream producer at runtime.

## Canonical paper-review input

The preferred machine interface is producer-owned `paper.review-record@1` JSONL. Paper KB is one current producer, but Abstract Scroller validates only the compatibility surface it actually needs: schema identity/version, canonical `paper_uid`, title, and supported review fields. It does **not** vendor or become authority for the Paper KB schema.

```bash
make snapshot-review-records \
  INPUT=/path/to/paper.review-record.v1.jsonl \
  OUT=data/snapshots/paper-review
```

For this interface, `paper_uid` becomes the snapshot `doc_id`, preserving producer identity across the projection.

Legacy/convenience inputs remain supported:

- CSV (`--format csv`), including the previously proven Paper KB CSV export;
- `review_node_jsonl`, retained for compatibility with the earlier local review-node experiment.

Those formats are compatibility surfaces, not the preferred domain contract.

## Quick start

1. Create a venv and install dependencies:

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -e .
   ```

2. Build the toy CSV snapshot:

   ```bash
   make snapshot
   ```

3. Serve with Brotli headers:

   ```bash
   make serve
   ```

4. Open `frontend/index.html` (or equivalent for your OS).

## Boundary

Abstract Scroller owns snapshot ordering, manifest/tile representation, immutable snapshot generation, and the lightweight reader. It does not own paper ingestion, paper identity semantics, review-record domain contracts, evidence selection, or upstream corpus mutation.
