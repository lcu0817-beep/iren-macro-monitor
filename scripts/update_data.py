from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import io
import json
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data.json"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 IREN-Macro-Monitor/1.1"
})

FRED = {
    "us2y": "DGS2",
    "us10y": "DGS10",
    "us30y": "DGS30",
    "real10y": "DFII10",
}

YF = {
    "iren": "IREN",
    "move": "^MOVE",
    "ndx": "^NDX",
    "sox": "^SOX",
    "wti": "CL=F",
    "gold": "GC=F",
    "copper": "HG=F",
    "dxy": "DX-Y.NYB",
    "btc": "BTC-USD",
}

def fred_last(series_id: str) -> float:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = SESSION.get(url, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if df.shape[1] < 2:
        raise RuntimeError("Unexpected FRED response")
    s = pd.to_numeric(df.iloc[:, 1], errors="coerce").dropna()
    if s.empty:
        raise RuntimeError("No FRED values")
    return float(s.iloc[-1])

def treasury_curve_latest() -> dict[str, float]:
    year = datetime.now(timezone.utc).year
    url = (
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
        f"pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}"
    )
    r = SESSION.get(url, timeout=25)
    r.raise_for_status()
    root = ET.fromstring(r.text)

    rows = []
    for elem in root.iter():
        if not elem.tag.lower().endswith("properties"):
            continue
        vals = {}
        for c in list(elem):
            key = c.tag.split("}")[-1]
            vals[key] = c.text
        dt = vals.get("NEW_DATE")
        if not dt:
            continue
        rows.append({
            "date": pd.to_datetime(dt, errors="coerce"),
            "us2y": pd.to_numeric(vals.get("BC_2YEAR"), errors="coerce"),
            "us10y": pd.to_numeric(vals.get("BC_10YEAR"), errors="coerce"),
            "us30y": pd.to_numeric(vals.get("BC_30YEAR"), errors="coerce"),
        })

    df = pd.DataFrame(rows).dropna(subset=["date"]).sort_values("date")
    if df.empty:
        raise RuntimeError("No Treasury rows parsed")

    last = df.iloc[-1]
    out = {}
    for k in ["us2y", "us10y", "us30y"]:
        if pd.notna(last[k]):
            out[k] = float(last[k])
    if not out:
        raise RuntimeError("No Treasury yield values")
    return out

def yf_series(ticker: str) -> pd.Series:
    df = yf.download(
        ticker,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        raise RuntimeError(f"No Yahoo data: {ticker}")
    c = df["Close"]
    if isinstance(c, pd.DataFrame):
        c = c.iloc[:, 0]
    return c.dropna().astype(float)

def yahoo_yield(ticker: str) -> float:
    # ^TNX / ^TYX are quoted as 10x the percentage yield.
    s = yf_series(ticker)
    return float(s.iloc[-1]) / 10.0

def pct(s: pd.Series, n: int):
    s = s.dropna()
    if len(s) <= n:
        return None
    return float((s.iloc[-1] / s.iloc[-n - 1] - 1) * 100)

def vs50(s: pd.Series):
    s = s.dropna()
    if len(s) < 50:
        return None
    return float((s.iloc[-1] / s.iloc[-50:].mean() - 1) * 100)

values = {}
warnings = []
sources = {}

# 1) Try FRED first.
for key, sid in FRED.items():
    try:
        values[key] = fred_last(sid)
        sources[key] = "FRED"
    except Exception as e:
        warnings.append(f"{key}: FRED failed")

# 2) Official U.S. Treasury fallback for nominal yields.
missing_nominal = [k for k in ["us2y", "us10y", "us30y"] if k not in values]
if missing_nominal:
    try:
        t = treasury_curve_latest()
        for k in missing_nominal:
            if k in t:
                values[k] = t[k]
                sources[k] = "U.S. Treasury"
    except Exception:
        warnings.append("Treasury fallback failed")

# 3) Yahoo fallback for 10Y / 30Y only.
if "us10y" not in values:
    try:
        values["us10y"] = yahoo_yield("^TNX")
        sources["us10y"] = "Yahoo ^TNX"
    except Exception:
        warnings.append("us10y: Yahoo fallback failed")

if "us30y" not in values:
    try:
        values["us30y"] = yahoo_yield("^TYX")
        sources["us30y"] = "Yahoo ^TYX"
    except Exception:
        warnings.append("us30y: Yahoo fallback failed")

# Market series.
series = {}
for key, ticker in YF.items():
    try:
        s = yf_series(ticker)
        series[key] = s
        values[key] = float(s.iloc[-1])
        sources[key] = "Yahoo Finance"
    except Exception:
        warnings.append(f"{key}: Yahoo failed")

momentum = {}
for key in ["ndx", "sox", "wti", "gold", "copper", "dxy", "btc"]:
    if key in series:
        s = series[key]
        momentum[key] = {
            "m1": pct(s, 21),
            "m3": pct(s, 63),
            "m6": pct(s, 126),
            "vs50d": vs50(s),
        }

payload = {
    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "values": values,
    "momentum": momentum,
    "macro_lab_url": "",
    "source_note": "Rates: FRED â U.S. Treasury â Yahoo fallback. Markets: Yahoo Finance.",
    "sources": sources,
    "warnings": warnings,
}

OUT.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("wrote", OUT)
print("sources:", sources)
print("warnings:", warnings)
