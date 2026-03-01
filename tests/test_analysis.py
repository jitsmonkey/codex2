from datetime import datetime, timezone

import pandas as pd

from flipfinder.analysis import score_opportunities, summarize_market


def test_summarize_market_empty():
    summary = summarize_market(pd.DataFrame())
    assert summary["count"] == 0
    assert summary["median_price"] == 0.0


def test_score_opportunities_returns_candidate():
    sold_df = pd.DataFrame(
        [
            {
                "brand": "Eastman",
                "model_hint": "MD315",
                "total_price": 900,
                "sold_at": datetime.now(timezone.utc),
            },
            {
                "brand": "Eastman",
                "model_hint": "MD315",
                "total_price": 940,
                "sold_at": datetime.now(timezone.utc),
            },
            {
                "brand": "Eastman",
                "model_hint": "MD315",
                "total_price": 930,
                "sold_at": datetime.now(timezone.utc),
            },
        ]
    )
    active_df = pd.DataFrame(
        [
            {
                "source": "reverb_ask",
                "title": "Eastman MD315 mandolin",
                "brand": "Eastman",
                "model_hint": "MD315",
                "total_price": 650,
                "listing_url": "https://example.com/item",
            }
        ]
    )

    output = score_opportunities(sold_df, active_df, min_margin=100)
    assert output.shape[0] == 1
    assert output.iloc[0]["gross_margin"] > 100
