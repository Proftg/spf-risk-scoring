"""
SQL data quality checks + column profiling on the SQLite database.

Covers the task: "write and optimize queries and quality checks, ensure data
quality, integrity and traceability".

Two parts:
  1. RULES: configurable business rules (add a tuple to extend).
  2. profile_columns: column-by-column profile (type, nulls, distinct, range).

Produces a markdown report (outputs/quality_report.md).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "risk.sqlite"
REPORT_PATH = ROOT / "outputs" / "quality_report.md"

# Configurable business rules: (label, SQL query, rule on the returned value).
# Add a tuple here to add a check, no other code change needed.
RULES = [
    ("Total client volume",
     "SELECT COUNT(*) FROM clients",
     lambda v: v > 0),
    ("Duplicate identifiers",
     "SELECT COUNT(*) FROM (SELECT ID FROM clients GROUP BY ID HAVING COUNT(*) > 1)",
     lambda v: v == 0),
    ("Ages out of range (18-100)",
     "SELECT COUNT(*) FROM clients WHERE AGE < 18 OR AGE > 100",
     lambda v: v == 0),
    ("Credit limits <= 0",
     "SELECT COUNT(*) FROM clients WHERE LIMIT_BAL <= 0",
     lambda v: v == 0),
    ("Orphan EDUCATION codes (referential integrity)",
     "SELECT COUNT(*) FROM clients c "
     "LEFT JOIN reference_segments r ON r.dimension='education' AND r.code=c.EDUCATION "
     "WHERE r.code IS NULL",
     lambda v: v == 0),
    ("Null values in LIMIT_BAL",
     "SELECT COUNT(*) FROM clients WHERE LIMIT_BAL IS NULL",
     lambda v: v == 0),
]


def check_rules(con: sqlite3.Connection) -> list[tuple]:
    """Run every business rule. Return (label, value, status)."""
    results = []
    for label, sql, rule in RULES:
        value = con.execute(sql).fetchone()[0]
        results.append((label, value, "OK" if rule(value) else "ALERT"))
    return results


def profile_columns(con: sqlite3.Connection) -> pd.DataFrame:
    """Column-by-column profile of the clients table."""
    df = pd.read_sql("SELECT * FROM clients", con)
    rows = []
    for col in df.columns:
        s = df[col]
        row = {"column": col, "dtype": str(s.dtype), "nulls": int(s.isna().sum()),
               "distinct": int(s.nunique())}
        if pd.api.types.is_numeric_dtype(s):
            row |= {"min": round(s.min(), 1), "mean": round(s.mean(), 1),
                    "max": round(s.max(), 1)}
        rows.append(row)
    return pd.DataFrame(rows).fillna("")


def _table(headers: list[str], rows: list[list]) -> list[str]:
    """Render a markdown table."""
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


def run() -> dict:
    """Run rules + profiling, write the markdown report, return a summary."""
    with sqlite3.connect(DB_PATH) as con:
        rule_results = check_rules(con)
        profile = profile_columns(con)

    lines = ["# Data quality report", "",
             "Run against the relational database `outputs/risk.sqlite`.", "",
             "## 1. Business rules", ""]
    lines += _table(["Check", "Value", "Status"],
                    [[lbl, f"{val:,}", st] for lbl, val, st in rule_results])
    lines += ["", "## 2. Column profile", ""]
    lines += _table(list(profile.columns), profile.values.tolist())
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    n_alerts = sum(1 for _, _, s in rule_results if s == "ALERT")
    print(f"[quality] {len(rule_results)} rules, {n_alerts} alert(s), "
          f"{len(profile)} columns profiled -> {REPORT_PATH.name}")
    return {"rules": rule_results, "profile": profile, "n_alerts": n_alerts}


if __name__ == "__main__":
    run()
