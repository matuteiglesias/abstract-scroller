PY?=python3
INPUT?=data/paper.review-record.v1.jsonl
OUT?=data/snapshots/paper-review
LEGACY_CSV_INPUT?=data/sample.csv
LEGACY_REVIEW_NODE_INPUT?=data/review_node.jsonl

.PHONY: snapshot-review-records snapshot snapshot-csv-legacy snapshot-review-node-legacy validate serve clean smoke

snapshot-review-records:
	$(PY) -m backend.jobs.mvp_snapshot --input $(INPUT) --format paper_review_record_jsonl --out $(OUT)

snapshot:
	@echo "[DEMO/COMPATIBILITY] 'make snapshot' builds the historical toy CSV snapshot."
	@echo "[PREFERRED] use 'make snapshot-review-records INPUT=<paper.review-record.v1.jsonl> OUT=<snapshot-dir>' for machine integration."
	$(PY) -m backend.jobs.mvp_snapshot --input data/sample.csv --out data/snapshots/v2025-08-15

snapshot-csv-legacy:
	@echo "[COMPATIBILITY] CSV ingest is retained but is not the preferred paper-review contract."
	$(PY) -m backend.jobs.mvp_snapshot --input $(LEGACY_CSV_INPUT) --format csv --out $(OUT)

snapshot-review-node-legacy:
	@echo "[COMPATIBILITY] local review_node_jsonl ingest is retained without shared-contract authority."
	$(PY) -m backend.jobs.mvp_snapshot --input $(LEGACY_REVIEW_NODE_INPUT) --format review_node_jsonl --out $(OUT)

validate:
	$(PY) -m backend.publish.manifest --validate $(OUT)

serve:
	$(PY) -m backend.devserver --root data

clean:
	rm -rf $(OUT)

smoke:
	@echo "Building preferred review-record snapshot and serving on 127.0.0.1:8000"
	$(PY) -m backend.jobs.mvp_snapshot --input $(INPUT) --format paper_review_record_jsonl --out $(OUT)
	- fuser -k 8000/tcp 2>/dev/null || true
	$(PY) -m backend.devserver --root data --port 8000 --host 127.0.0.1
