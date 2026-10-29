# SPF Risk Scoring

A pipeline that loads financial data from several sources, checks its quality with SQL, scores risk with an unsupervised model and shows the result in a Streamlit dashboard. It follows the tasks of a data analyst in a tax administration (the SPF Finances vacancy AFG26149). Real tax data is confidential, so it runs on public data: UCI *Default of Credit Card Clients* (30,000 clients) and the Kaggle credit card fraud dataset.

## Pipeline

```
credit_default.csv + segments.json -> ingest.py -> SQLite
public FX API (open.er-api.com)    -> enrich.py  -> EUR column
                                      quality.py -> quality_report.md (6 SQL checks)
                                      scoring.py -> scored_clients.csv (Isolation Forest, score 0-100)
                                      app.py     -> dashboard
```

`segments.json` is a synthetic reference that decodes the business codes.

## Results

The model never sees the target. `default_flag` is only used afterwards to check the score means something: the default rate rises with the risk decile.

| Risk decile | 1 (low) | 5 | 10 (high) |
|---|---|---|---|
| Default rate | 10.8% | 19.6% | 37.8% |

Flagged anomalies default at 35.5% against 22.1% overall. A logistic regression baseline reaches AUC 0.743, the Isolation Forest 0.651.

`src/fraud.py` applies the same method to 284,807 transactions (0.17% fraud): AUC 0.945, and flagged transactions are 10% fraudulent, a lift of x58 over the base rate. Run it with `python -m src.fraud`.

## Run

```bash
pip install -r requirements.txt
python run.py            # ingestion, quality checks, scoring
streamlit run app.py     # dashboard
```

The datasets are git-ignored. Download [Default of Credit Card Clients](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) as CSV into `data/raw/credit_default.csv`, and [creditcard.csv](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) into `data/raw/creditcard.csv`. The exploratory analysis is in `notebooks/01_full_analysis.ipynb`.

Stack: Python, pandas, SQLite, scikit-learn, Streamlit, Plotly.
