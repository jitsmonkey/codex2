from __future__ import annotations

import pandas as pd
import streamlit as st

from flipfinder.analysis import score_opportunities, summarize_market
from flipfinder.collectors import ScrapeError, fetch_ebay_sold, fetch_reverb_recent

st.set_page_config(page_title="Mandolin Flip Finder", layout="wide")
st.title("Mandolin Flip Finder (Reverb + eBay)")
st.caption("Personal-use research dashboard for recent sales and resale opportunities")

with st.sidebar:
    st.header("Parameters")
    search_term = st.text_input("Search term", value="mandolin")
    lookback_days = st.slider("Lookback days", 30, 120, 90)
    ebay_pages = st.slider("eBay pages", 1, 8, 4)
    reverb_pages = st.slider("Reverb pages", 1, 6, 3)
    min_margin = st.number_input("Minimum gross margin ($)", 25.0, 1000.0, 120.0, step=5.0)

if st.button("Run analysis", type="primary"):
    try:
        sold_df = fetch_ebay_sold(search_term=search_term, max_pages=ebay_pages)
        active_df = fetch_reverb_recent(search_term=search_term, max_pages=reverb_pages)
    except ScrapeError as error:
        st.error(f"Data collection failed: {error}")
        st.stop()

    if sold_df.empty:
        st.warning("No eBay sold listings were parsed. Try fewer filters or run later.")
        st.stop()

    sold_df["sold_at"] = pd.to_datetime(sold_df["sold_at"], errors="coerce", utc=True)
    sold_filtered = sold_df[sold_df["sold_at"] >= (pd.Timestamp.utcnow() - pd.Timedelta(days=lookback_days))]

    summary = summarize_market(sold_filtered, lookback_days=lookback_days)
    opportunities = score_opportunities(sold_filtered, active_df, min_margin=min_margin)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sold comps", summary["count"])
    c2.metric("Median sold", f"${summary['median_price']:.0f}")
    c3.metric("25th percentile", f"${summary['p25']:.0f}")
    c4.metric("75th percentile", f"${summary['p75']:.0f}")

    st.subheader("Top opportunities")
    if opportunities.empty:
        st.info("No opportunities met your threshold. Lower min margin or expand pages.")
    else:
        st.dataframe(opportunities, use_container_width=True)

    st.subheader("Brand activity (sold comps)")
    if summary["brands"]:
        brand_df = pd.DataFrame(
            [{"brand": k, "count": v} for k, v in summary["brands"].items()]
        ).sort_values("count", ascending=False)
        st.bar_chart(brand_df.set_index("brand"))

    with st.expander("Raw data"):
        st.write("eBay sold listings", sold_filtered)
        st.write("Reverb active listings", active_df)

st.markdown(
    """
    ### Notes
    - This app uses lightweight HTML scraping for personal research only.
    - Reverb sold-history endpoints are not public; current analysis compares eBay sold comps
      against current Reverb asks to estimate potential flips.
    - Always verify condition, shipping, fees, and return policy before buying.
    """
)
