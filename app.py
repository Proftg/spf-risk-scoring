"""
Analytical dashboard: anomaly detection and risk scoring.

Covers the task: "develop analytical reports and dashboards to identify trends,
anomalies and risks".

Launch: streamlit run app.py
(requires running `python run.py` first)
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
SCORED_CSV = ROOT / "outputs" / "scored_clients.csv"

st.set_page_config(page_title="SPF Risk Scoring", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    if not SCORED_CSV.exists():
        st.error("No data found. Run `python run.py` first.")
        st.stop()
    return pd.read_csv(SCORED_CSV)


df = load_data()

st.title("Anomaly detection & risk scoring")
st.caption("Proxy of a risk-detection workflow on public financial data "
           "(UCI Credit Default). No real personal data.")

# --- Filters ---
with st.sidebar:
    st.header("Filters")
    educ = st.multiselect("Education level",
                          sorted(df["education_label"].dropna().unique()))
    age = st.multiselect("Age band",
                         sorted(df["age_band"].dropna().unique()))

view = df.copy()
if educ:
    view = view[view["education_label"].isin(educ)]
if age:
    view = view[view["age_band"].isin(age)]

if view.empty:
    st.warning("No client matches these filters. Change your selection.")
    st.stop()

# --- KPIs ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Clients", f"{len(view):,}")
c2.metric("Anomalies", f"{int(view['anomaly'].sum()):,}",
          f"{view['anomaly'].mean():.1%}")
c3.metric("Default rate", f"{view['default_flag'].mean():.1%}")
c4.metric("Average risk score", f"{view['risk_score'].mean():.0f}/100")

st.divider()

# --- Charts ---
g1, g2 = st.columns(2)

with g1:
    st.subheader("Risk score distribution")
    fig = px.histogram(view, x="risk_score", nbins=40,
                       color=view["anomaly"].map({0: "Normal", 1: "Anomaly"}),
                       labels={"color": "Status", "risk_score": "Risk score"})
    fig.update_layout(legend_title_text="Status")
    st.plotly_chart(fig, width='stretch')

with g2:
    st.subheader("Validation: default rate per risk decile")
    by_dec = (view.groupby("risk_decile")["default_flag"].mean() * 100).reset_index()
    fig = px.bar(by_dec, x="risk_decile", y="default_flag",
                 labels={"risk_decile": "Risk decile (10 = highest risk)",
                         "default_flag": "Default rate (%)"})
    st.plotly_chart(fig, width='stretch')

# --- Anomalies per segment ---
st.subheader("Anomaly rate per education level")
by_seg = (view.groupby("education_label")["anomaly"].mean() * 100).reset_index()
fig = px.bar(by_seg.sort_values("anomaly"), x="education_label", y="anomaly",
             labels={"education_label": "Education", "anomaly": "Anomaly rate (%)"})
st.plotly_chart(fig, width='stretch')

# --- Highest-risk profiles table ---
st.subheader("Top 20 highest-risk profiles")
top = view.sort_values("risk_score", ascending=False).head(20)
st.dataframe(
    top[["ID", "risk_score", "anomaly", "default_flag", "limit_bal_eur",
         "education_label", "marriage_label", "age_band"]],
    width='stretch', hide_index=True,
)
