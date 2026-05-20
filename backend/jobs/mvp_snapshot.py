import argparse
import pathlib

from backend.ingest import load_records
from backend.publish import ids, manifest, order, tiles, writer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--format", default="csv", choices=["csv", "review_node_jsonl"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    df = load_records(pathlib.Path(args.input), args.format)

    if "doc_id" not in df.columns:
        df["doc_id"] = ""
    missing_doc_id = df["doc_id"].astype(str).str.strip() == ""
    if missing_doc_id.any():
        df.loc[missing_doc_id, "doc_id"] = df.loc[missing_doc_id].apply(ids.make_stable_id, axis=1)

    df, ord_idx = order.make_order_by_recency(df)

    writer.write_order(out, ord_idx)
    # empty dirs for contracts
    (out / "bitsets").mkdir(exist_ok=True, parents=True)
    (out / "bitsets" / "index.json").write_text('{"families":{}}', encoding="utf-8")
    (out / "nodes").mkdir(exist_ok=True, parents=True)
    (out / "nodes" / "summaries").mkdir(exist_ok=True, parents=True)
    (out / "nodes" / "tree.json.br").write_bytes(b"")

    tile_count = tiles.emit_tiles(out, df, ord_idx, snapshot_id=out.name)
    mani = manifest.build(out, out.name, {"docs": len(df), "tiles": tile_count})
    print("snapshot ready:", out, "docs:", mani["counts"]["docs"], "tiles:", mani["counts"]["tiles"])


if __name__ == "__main__":
    main()
