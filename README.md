# Mandolin Flip Finder

Personal-use app to analyze recent mandolin sales and estimate resale opportunities between **eBay sold comps** and **current Reverb asks**.

## What it does

- Pulls recent sold listings from eBay (completed/sold pages).
- Pulls recent Reverb marketplace listings (current asks).
- Filters to a configurable lookback window (default: 90 days).
- Calculates market summary stats (median, quartiles, brand activity).
- Scores potential flips with expected resale, gross margin, and ROI.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
streamlit run app.py
```

Then open the URL shown by Streamlit (usually `http://localhost:8501`).

## Important limitations

- Reverb sold-history data is not fully public in stable HTML endpoints; this tool uses Reverb asks + eBay sold comps.
- Scraping selectors can break if site markup changes.
- Data should be treated as directional. Confirm each listing manually before purchasing.

## Suggested workflow for flips

1. Run analysis with `search_term=mandolin` and 90-day lookback.
2. Increase eBay pages if too few sold comps appear.
3. Review top opportunities and open URLs directly from the table.
4. Validate fees, shipping, repair risk, and days-on-market before buying.
