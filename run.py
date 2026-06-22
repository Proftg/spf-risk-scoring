"""
Full pipeline orchestrator: ingestion -> enrichment -> quality -> scoring.

Usage: python run.py
"""

from src import enrich, ingest, quality, scoring


def main() -> None:
    print("=" * 60)
    print("SPF RISK SCORING PIPELINE")
    print("=" * 60)
    ingest.run()
    enrich.run()
    quality.run()
    scoring.run()
    print("=" * 60)
    print("Pipeline done. Launch the dashboard: streamlit run app.py")


if __name__ == "__main__":
    main()
