import json
import pathlib
import subprocess
import sys

import brotli
import jsonschema
import numpy as np
import pytest


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def _run_snapshot(tmp_path: pathlib.Path, input_rel: str, input_format: str = "csv") -> pathlib.Path:
    repo = _repo_root()
    sample = repo / input_rel
    out = tmp_path / f"snapshot_{input_format}"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.jobs.mvp_snapshot",
            "--input",
            str(sample),
            "--format",
            input_format,
            "--out",
            str(out),
        ],
        cwd=repo,
        check=True,
    )
    return out


def _load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "input_rel,input_format",
    [
        ("data/sample.csv", "csv"),
        ("data/review_nodes.sample.jsonl", "review_node_jsonl"),
    ],
)
def test_generated_manifest_matches_schema(tmp_path, input_rel, input_format):
    repo = _repo_root()
    snap = _run_snapshot(tmp_path, input_rel=input_rel, input_format=input_format)

    manifest = _load_json(snap / "manifest.json")
    schema = _load_json(repo / "contracts" / "schemas" / "manifest.schema.json")

    jsonschema.validate(manifest, schema)


@pytest.mark.parametrize(
    "input_rel,input_format",
    [
        ("data/sample.csv", "csv"),
        ("data/review_nodes.sample.jsonl", "review_node_jsonl"),
    ],
)
def test_generated_first_tile_matches_schema(tmp_path, input_rel, input_format):
    repo = _repo_root()
    snap = _run_snapshot(tmp_path, input_rel=input_rel, input_format=input_format)

    tile_path = snap / "tiles" / "tile_00000.json.br"
    tile_raw = brotli.decompress(tile_path.read_bytes()).decode("utf-8")
    tile = json.loads(tile_raw)

    schema = _load_json(repo / "contracts" / "schemas" / "tile.schema.json")
    jsonschema.validate(tile, schema)


@pytest.mark.parametrize(
    "input_rel,input_format",
    [
        ("data/sample.csv", "csv"),
        ("data/review_nodes.sample.jsonl", "review_node_jsonl"),
    ],
)
def test_order_bin_exists_and_length_matches_doc_count(tmp_path, input_rel, input_format):
    snap = _run_snapshot(tmp_path, input_rel=input_rel, input_format=input_format)

    manifest = _load_json(snap / "manifest.json")
    docs = manifest["counts"]["docs"]

    order_path = snap / "order" / "ORDER.bin"
    assert order_path.exists()

    order = np.frombuffer(order_path.read_bytes(), dtype=np.uint32)
    assert len(order) == docs
