"""FX enrichment. The UCI amounts are in New Taiwan Dollars, so we fetch the TWD->EUR
rate from a free public API and add an EUR column. If the API is unreachable, a
fixed fallback rate keeps the pipeline reproducible.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "risk.sqlite"
FX_API = "https://open.er-api.com/v6/latest/TWD"
FALLBACK_RATE = 0.0276  # documented TWD->EUR fallback, used only if the API is down


def fetch_fx_rate() -> tuple[float, str]:
    """Return (twd_to_eur_rate, source). Falls back to a fixed rate if offline."""
    try:
        with urlopen(FX_API, timeout=10) as resp:
            rate = float(json.load(resp)["rates"]["EUR"])
        return rate, "open.er-api.com"
    except Exception:
        return FALLBACK_RATE, "fallback"


def run() -> dict:
    """Fetch the FX rate, add limit_bal_eur, persist an fx_reference table."""
    rate, source = fetch_fx_rate()
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with sqlite3.connect(DB_PATH) as con:
        clients = pd.read_sql("SELECT * FROM clients", con)
        clients["limit_bal_eur"] = (clients["LIMIT_BAL"] * rate).round(0)
        clients.to_sql("clients", con, if_exists="replace", index=False)

        fx = pd.DataFrame([{"base": "TWD", "target": "EUR", "rate": rate,
                            "source": source, "fetched_at": fetched_at}])
        fx.to_sql("fx_reference", con, if_exists="replace", index=False)

    print(f"[enrich] FX TWD->EUR = {rate} ({source}); added limit_bal_eur")
    return {"rate": rate, "source": source}


if __name__ == "__main__":
    run()
