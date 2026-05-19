PY?=python3

.PHONY: snapshot validate serve clean

snapshot:
	$(PY) -m backend.jobs.mvp_snapshot --input data/sample.csv --out data/snapshots/v2025-08-15

validate:
	$(PY) -m backend.publish.manifest --validate data/snapshots/v2025-08-15

serve:
	$(PY) -m backend.devserver --root data

clean:
	rm -rf data/snapshots/v2025-08-15

.PHONY: smoke
smoke:
	@echo "Rebuilding snapshot and serving on 127.0.0.1:8000"
	$(PY) -m backend.jobs.mvp_snapshot --input data/sample.csv --out data/snapshots/v2025-08-15
	- fuser -k 8000/tcp 2>/dev/null || true
	$(PY) -m backend.devserver --root data --port 8000 --host 127.0.0.1
