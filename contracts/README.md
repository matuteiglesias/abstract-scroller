# Contract status

Abstract Scroller owns snapshot output contracts, not upstream paper-domain contracts.

## Preferred input

`paper.review-record@1` is producer-owned by Paper KB. Abstract Scroller intentionally does not vendor that schema. The consumer adapter validates only the compatibility surface needed to compile snapshots.

## Local compatibility schema

`contracts/schemas/review_node.v1.schema.json` is retained for the earlier `review_node_jsonl` ingest path. It is a **local compatibility schema**, not a shared knowledge-ecosystem contract and not the preferred Paper KB integration seam.

Do not extend this local schema to model new paper-domain semantics. New machine paper-review integrations should target `paper.review-record@1` or another explicitly governed producer-owned contract.

Snapshot manifests, tiles and reader-facing artifacts remain Abstract Scroller authority.
