"""
SQL data quality checks on the SQLite database.

Covers the task: "write and optimize queries and quality checks, ensure data
quality, integrity and traceability".

Produces a markdown report (outputs/quality_report.md) listing each check,
its result and its status (OK / ALERT).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "risk.sqlite"
REPORT_PATH = ROOT / "outputs" / "quality_report.md"

# Each check: (label, SQL query, validation rule on the value)
CHECKS = [
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


def run() -> dict:
    """Run the checks and write the markdown report. Return the results."""
    results = []
    with sqlite3.connect(DB_PATH) as con:
        for label, sql, rule in CHECKS:
            value = con.execute(sql).fetchone()[0]
            status = "OK" if rule(value) else "ALERT"
            results.append((label, value, status))
        default_rate = con.execute(
            "SELECT ROUND(AVG(default_flag)*100, 2) FROM clients"
        ).fetchone()[0]

    lines = [
        "# Data quality report",
        "",
        "SQL checks run against the relational database `outputs/risk.sqlite`.",
        "",
        "| Check | Value | Status |",
        "|-------|------:|:------:|",
    ]
    for label, value, status in results:
        lines.append(f"| {label} | {value:,} | {status} |")
    lines.append(f"| Target default rate | {default_rate} % | INFO |")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    n_alerts = sum(1 for _, _, s in results if s == "ALERT")
    print(f"[quality] {len(results)} checks, {n_alerts} alert(s) "
          f"-> {REPORT_PATH.name}")
    return {"results": results, "default_rate": default_rate, "n_alerts": n_alerts}


if __name__ == "__main__":
    run()
