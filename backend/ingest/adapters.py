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


def _require_review_record_consumer_shape(rec: object, *, line_no: int) -> dict:
    if not isinstance(rec, dict):
        raise ValueError(f"line {line_no}: paper review record must be a JSON object")
    if rec.get("schema_id") != "paper.review-record":
        raise ValueError(f"line {line_no}: unsupported schema_id {rec.get('schema_id')!r}")
    if rec.get("schema_version") != 1:
        raise ValueError(f"line {line_no}: unsupported paper.review-record schema_version {rec.get('schema_version')!r}")
    for field in ("paper_uid", "title"):
        value = rec.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"line {line_no}: {field} must be a non-empty string")
    for field in ("tags", "badges"):
        value = rec.get(field, [])
        if value is None:
            continue
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"line {line_no}: {field} must be an array of strings when present")
    return rec


def _load_paper_review_record_jsonl(input_path: pathlib.Path) -> pd.DataFrame:
    """Load the consumer-compatible surface of producer-owned paper.review-record@1.

    Abstract Scroller deliberately does not vendor Paper KB's full schema. The
    producer owns domain validation; this adapter validates only the exact
    identity/version/field shapes required by snapshot compilation.
    """
    rows = []
    with input_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_no}: invalid JSON: {exc}") from exc
            rec = _require_review_record_consumer_shape(rec, line_no=line_no)
            badges = rec.get("badges") or []
            paper_uid = rec["paper_uid"].strip()
            rows.append(
                {
                    "paper_uid": paper_uid,
                    "paper_id": rec.get("paper_id") or paper_uid,
                    "doc_id": paper_uid,
                    "title": rec["title"].strip(),
                    "abstract": rec.get("abstract") or "",
                    "date": rec.get("date") or "",
                    "year": rec.get("year") or 0,
                    "venue": rec.get("venue") or "",
                    "has_code": 1 if "has_code" in badges else 0,
                    "doi": rec.get("doi") or "",
                    "arxiv_id": rec.get("arxiv_id") or "",
                    "repec_id": rec.get("repec_id") or "",
                    "source_url": rec.get("source_url") or "",
                    "tags": rec.get("tags") or [],
                    "badges": badges,
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
    if input_format == "paper_review_record_jsonl":
        return _load_paper_review_record_jsonl(input_path)
    raise ValueError(f"Unsupported --format: {input_format}")
