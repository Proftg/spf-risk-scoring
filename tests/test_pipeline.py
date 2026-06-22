"""
End-to-end tests for the SPF risk-scoring pipeline.

Run with: pytest
The session fixture runs the full pipeline once, then tests assert on its outputs.
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import ingest, quality, scoring

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "risk.sqlite"
SCORED_CSV = ROOT / "outputs" / "scored_clients.csv"


@pytest.fixture(scope="session")
def scored() -> pd.DataFrame:
    ingest.run()
    quality.run()
    return scoring.run()


def test_outputs_exist(scored):
    assert DB_PATH.exists()
    assert SCORED_CSV.exists()


def test_client_count(scored):
    with sqlite3.connect(DB_PATH) as con:
        n = con.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    assert n == 30000


def test_no_duplicate_ids(scored):
    assert scored["ID"].duplicated().sum() == 0


def test_referential_integrity(scored):
    with sqlite3.connect(DB_PATH) as con:
        orphans = con.execute(
            "SELECT COUNT(*) FROM clients c "
            "LEFT JOIN reference_segments r "
            "ON r.dimension='education' AND r.code=c.EDUCATION "
            "WHERE r.code IS NULL"
        ).fetchone()[0]
    assert orphans == 0


def test_risk_score_bounds(scored):
    assert scored["risk_score"].between(0, 100).all()


def test_anomaly_share(scored):
    assert abs(scored["anomaly"].sum() - 1500) <= 5  # 5% of 30000


def test_validation_monotonic(scored):
    by_decile = scored.groupby("risk_decile")["default_flag"].mean()
    assert (by_decile.diff().dropna() >= 0).all()


def test_anomaly_lift(scored):
    lift = (scored.loc[scored["anomaly"] == 1, "default_flag"].mean()
            / scored["default_flag"].mean())
    assert lift > 1.4


def test_determinism(scored):
    rerun = scoring.run()
    assert np.allclose(rerun["risk_score"].values, scored["risk_score"].values)


def test_dashboard_filter_reduces_view(scored):
    view = scored[scored["education_label"] == "university"]
    assert 0 < len(view) < len(scored)


def test_empty_filter_is_detectable(scored):
    view = scored[scored["education_label"] == "__missing__"]
    assert view.empty
