===== README.md =====
# Econ Abstracts Viewer (MVP)

Batch publisher → immutable snapshot → dumb, fast reader (tiles + masks).
This repo scaffolds Milestone M1: manifest, tiles, and a simple viewer.

## Quick start



1) Create venv and install deps:
   python -m venv .venv && source .venv/bin/activate
   pip install -e .

2) Build a toy snapshot:
   make snapshot

3) Serve with Brotli headers:
   make serve    # http://localhost:8000/snapshots/v2025-08-15/manifest.json

4) Open frontend:
   open frontend/index.html  (or your OS equivalent)

===== EOF =====
