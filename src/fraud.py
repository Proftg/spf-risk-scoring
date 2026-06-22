"""
Large-volume anomaly detection on the Credit Card Fraud dataset (284k transactions).

Separate demonstration from the credit-default pipeline: it shows the same
unsupervised method (Isolation Forest) scales to a larger, highly imbalanced
dataset (0.17% fraud).

Dataset: data/raw/creditcard.csv (git-ignored, see README). Features V1..V28 are
PCA components; Amount and Time are raw. The Class label is used only to validate.

Run: python -m src.fraud
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "raw" / "creditcard.csv"
REPORT_PATH = ROOT / "outputs" / "fraud_report.md"
CONTAMINATION = 0.01  # expected share of suspicious transactions


def load() -> pd.DataFrame:
    """Load the fraud dataset and clean the quoted Class label (OpenML mirror)."""
    df = pd.read_csv(CSV_PATH)
    df["Class"] = df["Class"].astype(str).str.strip("'").astype(int)
    return df


def run() -> dict:
    """Score transactions, validate against the fraud label, write a report."""
    df = load()
    features = [c for c in df.columns if c != "Class"]
    X = StandardScaler().fit_transform(df[features])

    model = IsolationForest(n_estimators=100, contamination=CONTAMINATION,
                            random_state=42, n_jobs=-1)
    model.fit(X)
    raw = model.score_samples(X)
    risk = 100 * (raw.max() - raw) / (raw.max() - raw.min())
    flagged = model.predict(X) == -1

    auc = roc_auc_score(df["Class"], risk)
    fraud_rate = df["Class"].mean()
    fraud_in_flagged = df.loc[flagged, "Class"].mean()
    lift = fraud_in_flagged / fraud_rate

    lines = [
        "# Fraud anomaly-detection report", "",
        f"- Transactions: {len(df):,}",
        f"- Fraud rate (global): {fraud_rate:.4%}",
        f"- Flagged as anomalies: {flagged.sum():,} ({CONTAMINATION:.0%} target)",
        f"- Fraud rate among flagged: {fraud_in_flagged:.2%} (lift x{lift:.1f})",
        f"- AUC of the risk score vs fraud: {auc:.3f}", "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"[fraud] {len(df):,} transactions | AUC={auc:.3f} | "
          f"fraud lift in flagged x{lift:.1f} -> {REPORT_PATH.name}")
    return {"auc": auc, "lift": lift, "n": len(df)}


if __name__ == "__main__":
    run()
