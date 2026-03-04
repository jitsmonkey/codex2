from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd


def _safe_quantile(series: pd.Series, q: float, default: float = 0.0) -> float:
    clean = series.dropna()
    if clean.empty:
        return default
    return float(clean.quantile(q))


def summarize_market(df: pd.DataFrame, lookback_days: int = 90) -> dict:
    if df.empty:
        return {
            "count": 0,
            "median_price": 0.0,
            "p25": 0.0,
            "p75": 0.0,
            "brands": {},
        }

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    frame = df.copy()
    frame["sold_at"] = pd.to_datetime(frame["sold_at"], errors="coerce", utc=True)
    frame = frame[frame["sold_at"] >= cutoff]

    return {
        "count": int(frame.shape[0]),
        "median_price": _safe_quantile(frame["total_price"], 0.5),
        "p25": _safe_quantile(frame["total_price"], 0.25),
        "p75": _safe_quantile(frame["total_price"], 0.75),
        "brands": frame["brand"].fillna("Unknown").value_counts().head(10).to_dict(),
    }


def score_opportunities(
    sold_df: pd.DataFrame,
    active_df: pd.DataFrame,
    min_margin: float = 120.0,
    max_candidates: int = 40,
) -> pd.DataFrame:
    if sold_df.empty or active_df.empty:
        return pd.DataFrame()

    sold = sold_df.copy()
    active = active_df.copy()

    sold["group"] = sold["model_hint"].fillna(sold["brand"].fillna("unknown")).str.lower()
    active["group"] = active["model_hint"].fillna(active["brand"].fillna("unknown")).str.lower()

    sold_baseline = (
        sold.groupby("group", dropna=False)["total_price"]
        .agg(["median", "count"])
        .rename(columns={"median": "expected_resale", "count": "samples"})
        .reset_index()
    )

    merged = active.merge(sold_baseline, on="group", how="left")
    merged = merged[merged["samples"].fillna(0) >= 2]
    merged["expected_resale"] = merged["expected_resale"].fillna(merged["total_price"])
    merged["gross_margin"] = merged["expected_resale"] - merged["total_price"]
    merged["roi_pct"] = merged["gross_margin"] / merged["total_price"] * 100

    ranked = merged[(merged["gross_margin"] >= min_margin) & (merged["roi_pct"] > 15)]
    ranked = ranked.sort_values(["roi_pct", "gross_margin"], ascending=False)

    cols = [
        "source",
        "title",
        "brand",
        "model_hint",
        "total_price",
        "expected_resale",
        "gross_margin",
        "roi_pct",
        "samples",
        "listing_url",
    ]
    return ranked[cols].head(max_candidates)
