import json
import pathlib

import jsonschema
import pandas as pd


def _series_or_default(
    df: pd.DataFrame,
    column: str,
    default,
) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series(default, index=df.index)


def _normalize_common_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["year"] = (
        pd.to_numeric(
            _series_or_default(df, "year", 0),
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )
    df["has_code"] = (
        pd.to_numeric(
            _series_or_default(df, "has_code", 0),
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )
    df["date"] = pd.to_datetime(
        _series_or_default(df, "date", None),
        errors="coerce",
    )
    return df


def _load_csv(input_path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(
        input_path,
        dtype=str,
        keep_default_na=False,
    )
    return _normalize_common_types(df)


def _load_review_node_jsonl(input_path: pathlib.Path, schema_path: pathlib.Path) -> pd.DataFrame:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    rows = []

    with input_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            rec = json.loads(raw)
            jsonschema.validate(rec, schema)

            rows.append(
                {
                    "title": rec.get("title", ""),
                    "abstract": rec.get("abstract", ""),
                    "date": rec.get("date", ""),
                    "year": rec.get("year", 0),
                    "venue": rec.get("venue", ""),
                    "has_code": 1 if rec.get("has_code", False) else 0,
                    "doi": rec.get("doi", ""),
                    "arxiv_id": rec.get("arxiv_id", ""),
                    "repec_id": rec.get("repec_id", ""),
                    "doc_id": rec.get("doc_id", ""),
                    "source_node_id": rec.get("node_id", ""),
                    "tags": rec.get("tags", []),
                }
            )

    df = pd.DataFrame(rows)
    if "doc_id" in df.columns:
        df["doc_id"] = df["doc_id"].fillna("").astype(str)
    return _normalize_common_types(df)


def load_records(input_path: pathlib.Path, input_format: str) -> pd.DataFrame:
    if input_format == "csv":
        return _load_csv(input_path)
    if input_format == "review_node_jsonl":
        schema_path = pathlib.Path("contracts/schemas/review_node.v1.schema.json")
        return _load_review_node_jsonl(input_path, schema_path)
    raise ValueError(f"Unsupported --format: {input_format}")
