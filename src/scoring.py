"""Anomaly detection and risk scoring with Isolation Forest.

The model is unsupervised and never sees default_flag. The target is only used to
check that higher scores go with higher default rates.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "risk.sqlite"
SCORED_CSV = ROOT / "outputs" / "scored_clients.csv"

PAY_COLS = ["PAY_1", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
BILL_COLS = [f"BILL_AMT{i}" for i in range(1, 7)]
AMT_COLS = [f"PAY_AMT{i}" for i in range(1, 7)]
CONTAMINATION = 0.05  # expected share of atypical profiles


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build aggregated features relevant to credit risk."""
    out = pd.DataFrame(index=df.index)
    out["limit_bal"] = df["LIMIT_BAL"]
    out["age"] = df["AGE"]
    out["avg_bill"] = df[BILL_COLS].mean(axis=1)
    out["avg_pay"] = df[AMT_COLS].mean(axis=1)
    # Credit utilization (average bill / limit)
    out["utilization"] = (out["avg_bill"] / out["limit_bal"]).clip(-2, 5)
    # Number of months in payment delay and maximum delay
    delays = df[PAY_COLS].clip(lower=0)
    out["n_delays"] = (delays > 0).sum(axis=1)
    out["max_delay"] = delays.max(axis=1)
    # Repayment ratio (payments / bills)
    total_bill = df[BILL_COLS].sum(axis=1).replace(0, np.nan)
    out["repayment_ratio"] = (df[AMT_COLS].sum(axis=1) / total_bill).clip(0, 3).fillna(0)
    return out


def run() -> pd.DataFrame:
    """Compute risk scores, validate and persist the results."""
    with sqlite3.connect(DB_PATH) as con:
        df = pd.read_sql("SELECT * FROM clients", con)

    feats = engineer_features(df)
    X = StandardScaler().fit_transform(feats.values)

    model = IsolationForest(
        n_estimators=200, contamination=CONTAMINATION, random_state=42
    )
    model.fit(X)

    # score_samples: the lower it is, the more atypical the profile.
    # Rescale to a 0-100 risk score (100 = most at risk).
    raw = model.score_samples(X)
    risk = 100 * (raw.max() - raw) / (raw.max() - raw.min())

    scored = df[["ID", "default_flag", "limit_bal_eur", "education_label",
                 "marriage_label", "sex_label", "age_band"]].copy()
    scored["risk_score"] = risk.round(1)
    scored["anomaly"] = (model.predict(X) == -1).astype(int)
    scored["risk_decile"] = pd.qcut(scored["risk_score"], 10,
                                    labels=False, duplicates="drop") + 1

    # Validation: default rate per risk decile (should increase)
    validation = scored.groupby("risk_decile")["default_flag"].mean().round(3)
    default_anomaly = scored.loc[scored["anomaly"] == 1, "default_flag"].mean()
    default_global = scored["default_flag"].mean()

    with sqlite3.connect(DB_PATH) as con:
        scored.to_sql("scored_clients", con, if_exists="replace", index=False)
    scored.to_csv(SCORED_CSV, index=False)

    print(f"[scoring] {scored['anomaly'].sum():,} anomalies detected "
          f"({CONTAMINATION:.0%} target)")
    print(f"[scoring] default rate: global={default_global:.1%} "
          f"vs anomalies={default_anomaly:.1%} "
          f"(x{default_anomaly / default_global:.1f})")
    print(f"[scoring] default rate per risk decile:\n{validation.to_string()}")
    return scored


if __name__ == "__main__":
    run()
