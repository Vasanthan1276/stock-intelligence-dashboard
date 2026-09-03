# V Stock Intelligence Dashboard

A personal, automated stock-research dashboard for monitoring selected **US and Singapore equities**, comparing them through a consistent scoring framework, and maintaining a deeper investment view on **Micron Technology (MU)**.

The dashboard is designed to make a large amount of market, technical, fundamental, valuation and analyst information easier to review in one place. It is a research and monitoring tool only; it does not execute trades and should not be treated as financial advice.

## Live Dashboard

**Main dashboard:**  
https://vasanthan1276.github.io/stock-intelligence-dashboard/

**Micron deep-dive:**  
https://vasanthan1276.github.io/stock-intelligence-dashboard/micron/

## What the Dashboard Provides

### US and Singapore stock rankings

The main page scans the configured stock universe and ranks each company using:

- Current market price and daily movement
- Technical score
- Momentum score
- Fundamental score
- Valuation score
- Overall score
- Data-quality indicator
- Automated dashboard rating

Each company also has its own stock-detail page with additional technical, valuation, analyst and price-trend information.

### Sector-specific scoring models

The scoring engine uses different weights depending on the type of company rather than applying one identical model to every stock.

| Model | Technical | Momentum | Fundamentals | Valuation |
|---|---:|---:|---:|---:|
| General Company | 25% | 20% | 40% | 15% |
| Semiconductor | 20% | 25% | 40% | 15% |
| Bank | 15% | 15% | 45% | 25% |
| REIT | 15% | 10% | 40% | 35% |

The current scoring methodology is versioned so that a change in the scoring model does not appear as a false day-to-day movement in score history.

### Opportunity screens

The dashboard includes automated screens intended to help focus further research, including:

- Oversold stocks
- Momentum leaders
- Value opportunities
- Balanced opportunities
- Watchlist monitoring
- Score and rating changes since the previous compatible scan

These screens are indicators for further review, not buy or sell instructions.

## Micron Technology Deep-Dive

Micron receives a dedicated report in addition to its normal dashboard entry.

The MU report combines:

- Current price and daily movement
- Moving averages and RSI
- MACD and technical trend
- Short-, medium- and longer-term momentum
- Semiconductor-specific fundamental scoring
- Valuation indicators
- Analyst consensus and price targets
- Bull and bear factors
- Items to monitor in the investment thesis
- Micron-related news grouped into areas such as HBM & AI, DRAM, NAND, earnings and company developments

The report also produces `docs/data/mu-signal.json`, which provides a small advisory signal that can be consumed by the separate Wealth Hub project. The signal does **not** authorise or execute a trade.

## Market-Data Reliability Protection

The project includes safeguards against incomplete market-data responses.

For critical price data, the scanner:

1. Downloads market history.
2. Checks that the latest usable closing price is finite and positive.
3. Cleans unusable historical rows.
4. Retries the market-data request up to three times when validation fails.
5. Requires sufficient valid history for Micron's longer-term analysis.
6. Prevents invalid MU data from being silently published as a normal successful update.

The GitHub Actions workflow performs additional checks on the generated Micron signal and dashboard artifacts before committing the refreshed website.

This protection was added after an intermittent market-data response caused the current MU price to appear as `N/A` during an automated run even though the workflow itself had completed.

## Automation

The dashboard is rebuilt automatically with GitHub Actions and can also be run manually from the **Actions** tab.

Current scheduled workflow:

```yaml
cron: "30 22 * * 0-5"
```

This corresponds to a scheduled start of approximately **06:30 Singapore time, Monday through Saturday**. GitHub Actions scheduled jobs can start later than the exact cron time depending on platform load.

The workflow performs the following sequence:

1. Checks out the repository.
2. Sets up Python.
3. Installs dependencies from `requirements.txt`.
4. Generates the Micron deep-dive report and Wealth Hub signal.
5. Validates the MU signal.
6. Moves the Micron report to its dedicated page.
7. Generates the main dashboard and individual stock pages.
8. Validates critical generated artifacts.
9. Commits and pushes updated files under `docs/` when changes exist.

## Repository Structure

```text
stock-intelligence-dashboard/
├── .github/
│   └── workflows/
│       └── update-dashboard.yml
├── docs/                       # Generated GitHub Pages website
│   ├── index.html              # Main dashboard
│   ├── micron/                 # Dedicated MU deep-dive
│   ├── stocks/                 # Individual stock detail pages
│   └── data/                   # Generated signals/history
├── dashboard.py                # Main dashboard/page generator
├── main.py                     # Micron deep-dive generator
├── scanner.py                  # Market scanning and stock-data collection
├── scoring.py                  # Shared scoring models and calculations
├── portfolio-universe.json     # Additional portfolio stocks to scan
├── watchlist.json              # Stocks highlighted on the dashboard
├── requirements.txt            # Python dependencies
└── README.md
```

## Key Files

### `scanner.py`

Downloads and validates market data for the US and Singapore stock universes, calculates stock-level inputs and passes them through the shared scoring engine.

### `scoring.py`

Contains the sector-specific scoring framework, technical indicators, momentum logic, fundamental scoring, valuation scoring and overall rating logic.

### `dashboard.py`

Builds the main GitHub Pages dashboard, opportunity screens, watchlist, score-history comparisons and individual stock-detail pages.

### `main.py`

Builds the dedicated Micron investment report and the Wealth Hub MU advisory signal.

### `portfolio-universe.json`

Adds portfolio-specific stocks to the normal scanner universe without requiring the base universe in `scanner.py` to be edited.

### `watchlist.json`

Controls which tracked stocks are highlighted in the dashboard watchlist.

## Running Locally

From the repository root:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
python dashboard.py
```

Generated website files are written under `docs/`.

## Data Sources and Limitations

The dashboard uses automated third-party market and financial data, primarily accessed through `yfinance`. Data can occasionally be delayed, unavailable, incomplete or inconsistent.

The quantitative scores also cannot fully capture company-specific risks, management quality, future events, macroeconomic changes, regulatory developments or sudden shifts in market sentiment.

Analyst targets and recommendations are external data points and are not endorsements by this project.

Always perform additional research before making an investment decision.

## Status

The project is actively maintained as a personal stock-intelligence and portfolio-research system, with particular emphasis on Micron Technology and the user's broader US and Singapore investment universe.
