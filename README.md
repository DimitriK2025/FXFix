# FXFix

Compare stock and ETF returns as they look to an investor counting in another currency.
Same broadsheet styling as [Pocket Atlas](https://github.com/dimitrik2025/Pocket-Atlas).

Pick a currency at the top, up to six listings on the left, absolute or relative performance,
and a period (1 day, 1 month, 1 year, 3 years, 5 years or custom back to 2010). The page shows:

- cumulative total return in the chosen currency, with volume of the first listing underneath
- the headline split between return at home and the currency effect
- a scorecard: return at home, return in your currency, currency effect, annualised return,
  volatility and worst drop
- the same holding measured in each of 29 currencies, ranked

## Data

- **Prices:** Yahoo Finance chart API, dividend- and split-adjusted daily closes since 2010,
  plus the latest session at 5-minute intervals. Returns are total returns.
- **Exchange rates:** European Central Bank reference rates via [frankfurter.dev](https://frankfurter.dev).
  Prices are translated at each day's rate. The 1-day view holds rates fixed, since the ECB publishes daily.

## Adding listings

Add a Yahoo Finance ticker to `tickers.txt` (e.g. `SREN.SW`, `ULVR.L`, `ADS.DE`) and push.
The listing's currency must be one the ECB quotes.

## How it updates

`.github/workflows/pages.yml` runs `scripts/fetch.py` on every push to `main` and twice each
weekday (16:47 and 22:17 UTC, after the European and US closes), then publishes `docs/` plus the
fresh data to GitHub Pages. Data files are built in CI and never committed. Run it by hand from
the Actions tab with **Run workflow**.

Repository setting needed once: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## Running locally

```bash
python scripts/fetch.py
python -m http.server -d docs 8000
```

Then open http://localhost:8000.
