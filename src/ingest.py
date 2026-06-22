"""
Multi-source ingestion into a relational SQLite database.

Covers the task: "collect, clean and structure data from multiple, heterogeneous
sources (structured + semi-structured JSON)".

Two sources:
  1. data/raw/credit_default.csv     -> structured (proxy for financial data)
  2. data/reference/segments.json    -> semi-structured (business reference)

Result: a SQLite database with two tables joined on segment codes.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "raw" / "credit_default.csv"
JSON_PATH = ROOT / "data" / "reference" / "segments.json"
DB_PATH = ROOT / "outputs" / "risk.sqlite"

# EDUCATION/MARRIAGE codes treated as valid (anything else maps to "unknown" / 0)
VALID_EDUCATION = {1, 2, 3, 4}
VALID_MARRIAGE = {1, 2, 3}


def load_reference() -> dict:
    """Load the JSON reference (semi-structured source)."""
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_and_clean_csv(ref: dict) -> pd.DataFrame:
    """Load the structured CSV and apply basic cleaning."""
    df = pd.read_csv(CSV_PATH)

    # Readable, consistent renaming (PAY_0 -> PAY_1)
    df = df.rename(columns={
        "default payment next month": "default_flag",
        "PAY_0": "PAY_1",
    })

    # Map out-of-range codes to "unknown" (0, 5, 6 for EDUCATION)
    df["EDUCATION"] = df["EDUCATION"].where(df["EDUCATION"].isin(VALID_EDUCATION), 0)
    df["MARRIAGE"] = df["MARRIAGE"].where(df["MARRIAGE"].isin(VALID_MARRIAGE), 0)

    # Join business labels from the JSON reference
    df["education_label"] = df["EDUCATION"].astype(str).map(ref["education_labels"])
    df["marriage_label"] = df["MARRIAGE"].astype(str).map(ref["marriage_labels"])
    df["sex_label"] = df["SEX"].astype(str).map(ref["sex_labels"])

    # Age band (join on the age_bands reference)
    def to_band(age: int) -> str:
        for band in ref["age_bands"]:
            if band["min"] <= age <= band["max"]:
                return band["label"]
        return "unknown"

    df["age_band"] = df["AGE"].apply(to_band)
    return df


def build_reference_table(ref: dict) -> pd.DataFrame:
    """Flatten the JSON reference into a relational lookup table."""
    rows = []
    for dim in ("education", "marriage", "sex"):
        for code, label in ref[f"{dim}_labels"].items():
            rows.append({"dimension": dim, "code": int(code), "label": label})
    return pd.DataFrame(rows)


def run() -> Path:
    """Run ingestion and write the SQLite database. Return the database path."""
    ref = load_reference()
    clients = load_and_clean_csv(ref)
    reference = build_reference_table(ref)

    DB_PATH.parent.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        clients.to_sql("clients", con, if_exists="replace", index=False)
        reference.to_sql("reference_segments", con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS idx_clients_id ON clients(ID)")

    print(f"[ingest] {len(clients):,} clients + {len(reference)} reference rows "
          f"-> {DB_PATH.name}")
    return DB_PATH


if __name__ == "__main__":
    run()
