# SPF Risk Scoring: anomaly detection & risk scoring

End-to-end data pipeline reproducing the workflow of a *data analyst* in a tax
administration: multi-source ingestion, SQL quality checks, unsupervised anomaly
detection, and delivery through an interactive dashboard.

> **Honest framing.** Real tax data is confidential. This project uses a **public**
> financial dataset (UCI Default of Credit Card Clients, 30,000 clients) as a
> **proxy** to demonstrate the method. No real personal data is used. The pipeline
> logic is directly transferable to a fiscal risk-detection context.

## Why this project

Built in direct response to the **Data Analyst (M/F/X), SPF Finances** vacancy
(code AFG26149). Each responsibility of the job description maps to a concrete
pipeline component:

| Job responsibility | Project component |
|---|---|
| Collect, clean and structure data from **multiple, heterogeneous sources** (structured + JSON + API) | `src/ingest.py`: CSV + JSON -> SQLite; `src/enrich.py`: public FX API -> EUR column |
| **Write and optimize SQL queries** | `sql/quality_checks.sql` + SQL queries in the pipeline |
| **Quality, integrity, traceability** checks | `src/quality.py`: 6 SQL checks -> `quality_report.md` |
| **Statistical and exploratory analysis** | Feature engineering + decile validation in `src/scoring.py` and the notebook |
| Contribute to **scoring and risk-detection models** | `src/scoring.py`: Isolation Forest -> 0-100 risk score |
| **Analytical reports and dashboards** | `app.py`: interactive Streamlit dashboard |
| **GDPR** compliance, sensitive data handling | Public data + synthetic reference, documented above |
| **Document** sources, procedures and methods | This README + module docstrings + notebook |

## Architecture

```
data/raw/credit_default.csv  ->|
                               |-> ingest.py -> SQLite (clients + reference_segments)
data/reference/segments.json ->|                   |
                                                   |-> enrich.py (public FX API -> EUR + fx_reference)
public FX API (open.er-api.com) ->|                |
                                                   |-> quality.py -> quality_report.md
                                                   |-> scoring.py -> scored_clients.csv
                                                                        |
                                                                        |-> app.py (dashboard)
```

## Key result (score validation)

The model is **unsupervised**: it flags atypical profiles without using the target.
The target (`default_flag`) is used only to **validate** that the score is
meaningful. The default rate increases monotonically with the risk score.

| Risk decile | 1 (low) | 5 | 10 (high) |
|---|---|---|---|
| Default rate | 10.8% | 19.6% | **37.8%** |

Flagged anomalies show a **35.5%** default rate against **22.1%** overall (x1.6).

The notebook also compares this with a supervised baseline (logistic regression):
AUC **0.743** (supervised) vs **0.651** (Isolation Forest), confirming the two
approaches are complementary: detect the atypical, and score the risk.

## Run the project

```bash
pip install -r requirements.txt
python run.py            # ingestion + quality + scoring
streamlit run app.py     # dashboard
```

The exploratory analysis lives in `notebooks/01_full_analysis.ipynb`.

## Dataset installation

The raw dataset is not versioned (it is git-ignored). To reproduce:

1. Download *Default of Credit Card Clients* from the
   [UCI repository](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients).
2. Convert it to CSV and place it at `data/raw/credit_default.csv`
   (columns kept as published; the pipeline handles renaming).

## Large-volume fraud detection

A second, separate demonstration (`src/fraud.py`) applies the same Isolation Forest
method to the Credit Card Fraud dataset (284,807 transactions, 0.17% fraud). It shows
the approach scales: AUC **0.945**, and flagged transactions are **10%** fraudulent
against **0.17%** overall (lift x58). Run with `python -m src.fraud`.

The dataset is git-ignored. Download `creditcard.csv` (e.g. from the
[Kaggle MLG-ULB dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud))
and place it at `data/raw/creditcard.csv`.

## Stack

`Python` · `pandas` · `SQLite` (relational SQL) · `scikit-learn` (Isolation Forest) ·
`Streamlit` · `Plotly`

## Data source

UCI Machine Learning Repository, *Default of Credit Card Clients* (Yeh & Lien, 2009),
30,000 clients, 23 variables. The `segments.json` reference is synthetic (decoding of
the business codes).

## Roadmap

- [x] Extended quality module (column-by-column profiling, configurable business rules)
- [x] Third source via a public API (FX enrichment, NT$ -> EUR via open.er-api.com)
- [x] Large-volume anomaly detection on the Credit Card Fraud dataset (284k transactions)
