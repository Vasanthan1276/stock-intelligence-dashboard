import math
import json
import time
from pathlib import Path

import yfinance as yf

from scoring import (
    fundamental_score,
    momentum_score,
    overall_score,
    rating,
    scoring_model_name,
    technical_score,
    valuation_score,
)


# ============================================================
# OPTIONAL PORTFOLIO UNIVERSE
# ============================================================

PORTFOLIO_UNIVERSE_PATH = Path(
    "portfolio-universe.json"
)

MARKET_DATA_MAX_ATTEMPTS = 3
MARKET_DATA_RETRY_SECONDS = 5
MU_MIN_HISTORY_ROWS = 200


def load_portfolio_universe():
    """
    Load optional portfolio holdings that should always be scanned.

    The file is deliberately separate from watchlist.json:
      - watchlist.json controls what is highlighted on the dashboard
      - portfolio-universe.json controls extra scan coverage

    Missing or malformed files are non-fatal; the normal static universe
    continues to work.
    """

    empty = {
        "us": {},
        "singapore": {},
    }

    if not PORTFOLIO_UNIVERSE_PATH.exists():
        return empty

    try:
        payload = json.loads(
            PORTFOLIO_UNIVERSE_PATH.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(payload, dict):
            return empty

        output = {
            "us": {},
            "singapore": {},
        }

        for market_key in (
            "us",
            "singapore",
        ):
            raw_market = payload.get(
                market_key,
                {},
            )

            if not isinstance(
                raw_market,
                dict,
            ):
                continue

            for raw_ticker, raw_meta in raw_market.items():
                ticker = str(
                    raw_ticker
                ).strip().upper()

                if not ticker:
                    continue

                meta = (
                    raw_meta
                    if isinstance(
                        raw_meta,
                        dict,
                    )
                    else {}
                )

                name = str(
                    meta.get(
                        "name",
                        ticker,
                    )
                    or ticker
                ).strip()

                sector = str(
                    meta.get(
                        "sector",
                        "General Company",
                    )
                    or "General Company"
                ).strip()

                output[
                    market_key
                ][
                    ticker
                ] = {
                    "name": name,
                    "sector": sector,
                }

        return output

    except Exception as error:
        print(
            "Could not read "
            "portfolio-universe.json: "
            f"{error}"
        )

        return empty


def merged_stock_universe(
    base_universe,
    extra_universe,
):
    """
    Return a copy of the standard universe plus portfolio-specific tickers.

    Portfolio metadata wins for duplicate tickers so the portfolio file can
    correct a company name or sector without editing scanner.py.
    """

    merged = dict(
        base_universe
    )

    merged.update(
        extra_universe
        or {}
    )

    return merged


# ============================================================
# STOCK UNIVERSES
# ============================================================

US_STOCKS = {

    # Semiconductors
    "MU": {
        "name": "Micron Technology",
        "sector": "Semiconductors",
    },
    "NVDA": {
        "name": "NVIDIA",
        "sector": "Semiconductors",
    },
    "AMD": {
        "name": "Advanced Micro Devices",
        "sector": "Semiconductors",
    },
    "AVGO": {
        "name": "Broadcom",
        "sector": "Semiconductors",
    },
    "QCOM": {
        "name": "Qualcomm",
        "sector": "Semiconductors",
    },
    "TXN": {
        "name": "Texas Instruments",
        "sector": "Semiconductors",
    },
    "INTC": {
        "name": "Intel",
        "sector": "Semiconductors",
    },
    "AMAT": {
        "name": "Applied Materials",
        "sector": "Semiconductor Equipment",
    },
    "LRCX": {
        "name": "Lam Research",
        "sector": "Semiconductor Equipment",
    },
    "KLAC": {
        "name": "KLA",
        "sector": "Semiconductor Equipment",
    },
    "TSM": {
        "name": "TSMC",
        "sector": "Semiconductors",
    },
    "ASML": {
        "name": "ASML",
        "sector": "Semiconductor Equipment",
    },

    # Technology
    "AAPL": {
        "name": "Apple",
        "sector": "Technology",
    },
    "MSFT": {
        "name": "Microsoft",
        "sector": "Technology",
    },
    "GOOGL": {
        "name": "Alphabet",
        "sector": "Communication Services",
    },
    "AMZN": {
        "name": "Amazon",
        "sector": "Consumer / Technology",
    },
    "META": {
        "name": "Meta Platforms",
        "sector": "Communication Services",
    },
    "ORCL": {
        "name": "Oracle",
        "sector": "Technology",
    },
    "CRM": {
        "name": "Salesforce",
        "sector": "Technology",
    },
    "ADBE": {
        "name": "Adobe",
        "sector": "Technology",
    },

    # Financials
    "JPM": {
        "name": "JPMorgan Chase",
        "sector": "Financials",
    },
    "BAC": {
        "name": "Bank of America",
        "sector": "Financials",
    },
    "GS": {
        "name": "Goldman Sachs",
        "sector": "Financials",
    },
    "MS": {
        "name": "Morgan Stanley",
        "sector": "Financials",
    },
    "V": {
        "name": "Visa",
        "sector": "Financials",
    },
    "MA": {
        "name": "Mastercard",
        "sector": "Financials",
    },
    "AXP": {
        "name": "American Express",
        "sector": "Financials",
    },
    "BLK": {
        "name": "BlackRock",
        "sector": "Financials",
    },

    # Healthcare
    "LLY": {
        "name": "Eli Lilly",
        "sector": "Healthcare",
    },
    "UNH": {
        "name": "UnitedHealth",
        "sector": "Healthcare",
    },
    "JNJ": {
        "name": "Johnson & Johnson",
        "sector": "Healthcare",
    },
    "ABBV": {
        "name": "AbbVie",
        "sector": "Healthcare",
    },
    "MRK": {
        "name": "Merck",
        "sector": "Healthcare",
    },
    "TMO": {
        "name": "Thermo Fisher Scientific",
        "sector": "Healthcare",
    },

    # Consumer
    "COST": {
        "name": "Costco",
        "sector": "Consumer",
    },
    "WMT": {
        "name": "Walmart",
        "sector": "Consumer",
    },
    "HD": {
        "name": "Home Depot",
        "sector": "Consumer",
    },
    "MCD": {
        "name": "McDonald's",
        "sector": "Consumer",
    },
    "NKE": {
        "name": "Nike",
        "sector": "Consumer",
    },
    "SBUX": {
        "name": "Starbucks",
        "sector": "Consumer",
    },
    "PG": {
        "name": "Procter & Gamble",
        "sector": "Consumer Staples",
    },
    "KO": {
        "name": "Coca-Cola",
        "sector": "Consumer Staples",
    },

    # Industrials
    "CAT": {
        "name": "Caterpillar",
        "sector": "Industrials",
    },
    "GE": {
        "name": "GE Aerospace",
        "sector": "Industrials",
    },
    "HON": {
        "name": "Honeywell",
        "sector": "Industrials",
    },
    "RTX": {
        "name": "RTX",
        "sector": "Industrials",
    },
    "BA": {
        "name": "Boeing",
        "sector": "Industrials",
    },
    "DE": {
        "name": "Deere",
        "sector": "Industrials",
    },
    "UPS": {
        "name": "UPS",
        "sector": "Industrials",
    },

    # Energy
    "XOM": {
        "name": "Exxon Mobil",
        "sector": "Energy",
    },
    "CVX": {
        "name": "Chevron",
        "sector": "Energy",
    },
    "COP": {
        "name": "ConocoPhillips",
        "sector": "Energy",
    },
    "SLB": {
        "name": "SLB",
        "sector": "Energy",
    },

    # Communication
    "NFLX": {
        "name": "Netflix",
        "sector": "Communication Services",
    },
    "DIS": {
        "name": "Walt Disney",
        "sector": "Communication Services",
    },
    "TMUS": {
        "name": "T-Mobile",
        "sector": "Communication Services",
    },
    "VZ": {
        "name": "Verizon",
        "sector": "Communication Services",
    },

    # Growth
    "TSLA": {
        "name": "Tesla",
        "sector": "Consumer / Technology",
    },
    "PLTR": {
        "name": "Palantir",
        "sector": "Technology",
    },
    "UBER": {
        "name": "Uber",
        "sector": "Technology",
    },
    "SHOP": {
        "name": "Shopify",
        "sector": "Technology",
    },
}


SINGAPORE_STOCKS = {

    # Banks
    "D05.SI": {
        "name": "DBS Group",
        "sector": "Banks",
    },
    "O39.SI": {
        "name": "OCBC",
        "sector": "Banks",
    },
    "U11.SI": {
        "name": "UOB",
        "sector": "Banks",
    },

    # Telecom
    "Z74.SI": {
        "name": "Singtel",
        "sector": "Telecom",
    },
    "CC3.SI": {
        "name": "StarHub",
        "sector": "Telecom",
    },

    # Industrials
    "BN4.SI": {
        "name": "Keppel",
        "sector": "Industrials",
    },
    "U96.SI": {
        "name": "Sembcorp Industries",
        "sector": "Industrials",
    },
    "S63.SI": {
        "name": "ST Engineering",
        "sector": "Industrials",
    },
    "5E2.SI": {
        "name": "Seatrium",
        "sector": "Industrials",
    },
    "BS6.SI": {
        "name": "Yangzijiang Shipbuilding",
        "sector": "Industrials",
    },

    # Transport
    "C6L.SI": {
        "name": "Singapore Airlines",
        "sector": "Transport",
    },
    "S58.SI": {
        "name": "SATS",
        "sector": "Transport",
    },
    "C52.SI": {
        "name": "ComfortDelGro",
        "sector": "Transport",
    },

    # Financial Services
    "S68.SI": {
        "name": "Singapore Exchange",
        "sector": "Financial Services",
    },
    "AIY.SI": {
        "name": "iFAST",
        "sector": "Financial Services",
    },

    # REITs
    "C38U.SI": {
        "name": "CapitaLand Integrated Commercial Trust",
        "sector": "REIT",
    },
    "A17U.SI": {
        "name": "CapitaLand Ascendas REIT",
        "sector": "REIT",
    },
    "M44U.SI": {
        "name": "Mapletree Logistics Trust",
        "sector": "REIT",
    },
    "N2IU.SI": {
        "name": "Mapletree Pan Asia Commercial Trust",
        "sector": "REIT",
    },
    "ME8U.SI": {
        "name": "Mapletree Industrial Trust",
        "sector": "REIT",
    },
    "AJBU.SI": {
        "name": "Keppel DC REIT",
        "sector": "REIT",
    },
    "J69U.SI": {
        "name": "Frasers Centrepoint Trust",
        "sector": "REIT",
    },

    # Property
    "9CI.SI": {
        "name": "CapitaLand Investment",
        "sector": "Property",
    },
    "U14.SI": {
        "name": "UOL Group",
        "sector": "Property",
    },
    "H78.SI": {
        "name": "Hongkong Land",
        "sector": "Property",
    },

    # Consumer
    "F34.SI": {
        "name": "Wilmar International",
        "sector": "Consumer",
    },
    "D01.SI": {
        "name": "DFI Retail Group",
        "sector": "Consumer",
    },
    "C07.SI": {
        "name": "Jardine Cycle & Carriage",
        "sector": "Consumer",
    },
    "Y92.SI": {
        "name": "Thai Beverage",
        "sector": "Consumer",
    },

    # Others
    "J36.SI": {
        "name": "Jardine Matheson",
        "sector": "Conglomerate",
    },
    "G13.SI": {
        "name": "Genting Singapore",
        "sector": "Consumer / Leisure",
    },
}


# ============================================================
# HELPERS
# ============================================================

def safe_number(value):
    try:
        if value is None:
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def is_valid_price(value):
    number = safe_number(
        value
    )

    return (
        number is not None
        and number > 0
    )


def validate_price_history(
    history,
    ticker,
    min_rows=2,
):
    if history is None or history.empty:
        raise RuntimeError(
            f"No market data returned for {ticker}."
        )

    if "Close" not in history.columns:
        raise RuntimeError(
            f"Market data for {ticker} has no Close column."
        )

    raw_close = history[
        "Close"
    ]

    if len(raw_close) < 2:
        raise RuntimeError(
            f"Market data for {ticker} has fewer than 2 rows."
        )

    latest_raw_price = safe_number(
        raw_close.iloc[-1]
    )

    if (
        latest_raw_price is None
        or latest_raw_price <= 0
    ):
        raise RuntimeError(
            f"Latest Close for {ticker} is invalid: "
            f"{raw_close.iloc[-1]!r}."
        )

    valid_close_mask = raw_close.map(
        is_valid_price
    )

    cleaned_history = history.loc[
        valid_close_mask
    ].copy()

    if len(cleaned_history) < min_rows:
        raise RuntimeError(
            f"Only {len(cleaned_history)} valid price rows "
            f"were returned for {ticker}; "
            f"at least {min_rows} are required."
        )

    previous_price = safe_number(
        cleaned_history[
            "Close"
        ].iloc[-2]
    )

    if (
        previous_price is None
        or previous_price <= 0
    ):
        raise RuntimeError(
            f"Previous Close for {ticker} is invalid."
        )

    removed_rows = (
        len(history)
        - len(cleaned_history)
    )

    if removed_rows:
        print(
            f"Removed {removed_rows} invalid historical "
            f"price row(s) for {ticker}."
        )

    return cleaned_history


def download_valid_market_data(
    ticker,
    min_rows=2,
):
    last_error = None

    for attempt in range(
        1,
        MARKET_DATA_MAX_ATTEMPTS + 1,
    ):
        try:
            stock = yf.Ticker(
                ticker
            )

            history = stock.history(
                period="1y",
                interval="1d",
                auto_adjust=False,
            )

            history = validate_price_history(
                history,
                ticker,
                min_rows=min_rows,
            )

            price = safe_number(
                history[
                    "Close"
                ].iloc[-1]
            )

            print(
                f"{ticker} market data validated: "
                f"${price:,.2f} "
                f"({len(history)} valid rows, "
                f"attempt {attempt}/"
                f"{MARKET_DATA_MAX_ATTEMPTS})."
            )

            return stock, history

        except Exception as error:
            last_error = error

            print(
                f"{ticker} market data attempt "
                f"{attempt}/"
                f"{MARKET_DATA_MAX_ATTEMPTS} failed: "
                f"{error}"
            )

            if attempt < MARKET_DATA_MAX_ATTEMPTS:
                print(
                    f"Retrying {ticker} market data in "
                    f"{MARKET_DATA_RETRY_SECONDS} seconds..."
                )

                time.sleep(
                    MARKET_DATA_RETRY_SECONDS
                )

    raise RuntimeError(
        f"Unable to obtain valid market data for {ticker} "
        f"after {MARKET_DATA_MAX_ATTEMPTS} attempts. "
        f"Last error: {last_error}"
    )


def percentage_change(
    current,
    earlier,
):
    if (
        current is None
        or earlier is None
        or earlier == 0
    ):
        return None

    return (
        current
        /
        earlier
    ) - 1


def get_return(
    close,
    trading_days,
):
    if len(close) <= trading_days:
        return None

    return percentage_change(
        float(
            close.iloc[-1]
        ),
        float(
            close.iloc[
                -trading_days - 1
            ]
        ),
    )


def normalized_recommendation(value):
    if not value:
        return "N/A"

    return (
        str(value)
        .replace(
            "_",
            " ",
        )
        .upper()
    )


# ============================================================
# STOCK ANALYSIS
# ============================================================

def analyze_stock(
    ticker,
    metadata,
    market,
):
    try:

        print(
            f"Scanning {ticker}..."
        )

        minimum_rows = (
            MU_MIN_HISTORY_ROWS
            if ticker == "MU"
            else 2
        )

        stock, history = download_valid_market_data(
            ticker,
            min_rows=minimum_rows,
        )


        info = (
            stock.info
            or {}
        )


        close = history[
            "Close"
        ]

        high = history[
            "High"
        ]

        low = history[
            "Low"
        ]


        # ====================================================
        # PRICE DATA
        # ====================================================

        price = float(
            close.iloc[-1]
        )

        previous_price = float(
            close.iloc[-2]
        )

        daily_change = (
            price
            /
            previous_price
        ) - 1


        # ====================================================
        # SECTOR-SPECIFIC SCORING
        # ====================================================

        sector = metadata[
            "sector"
        ]

        scoring_model = (
            scoring_model_name(
                sector
            )
        )


        technical, rsi = (
            technical_score(
                history
            )
        )


        momentum = (
            momentum_score(
                history
            )
        )


        fundamental_data = (
            fundamental_score(
                info,
                sector=sector,
            )
        )


        fundamental = (
            fundamental_data[
                "score"
            ]
        )


        valuation = (
            valuation_score(
                info,
                sector=sector,
            )
        )


        final_score = (
            overall_score(
                technical,
                momentum,
                fundamental,
                valuation,
                sector=sector,
            )
        )


        # ====================================================
        # TECHNICAL DETAIL
        # ====================================================

        ma20 = safe_number(
            close
            .rolling(20)
            .mean()
            .iloc[-1]
        )


        ma50 = safe_number(
            close
            .rolling(50)
            .mean()
            .iloc[-1]
        )


        ma200 = safe_number(
            close
            .rolling(200)
            .mean()
            .iloc[-1]
        )


        low_52 = safe_number(
            low.min()
        )


        high_52 = safe_number(
            high.max()
        )


        recent_60 = history.tail(
            60
        )


        support = safe_number(
            recent_60[
                "Low"
            ].min()
        )


        resistance = safe_number(
            recent_60[
                "High"
            ].max()
        )


        # ====================================================
        # PERFORMANCE
        # ====================================================

        return_1m = get_return(
            close,
            21,
        )


        return_3m = get_return(
            close,
            63,
        )


        return_6m = get_return(
            close,
            126,
        )


        # ====================================================
        # FUNDAMENTALS
        # ====================================================

        market_cap = safe_number(
            info.get(
                "marketCap"
            )
        )


        trailing_pe = safe_number(
            info.get(
                "trailingPE"
            )
        )


        forward_pe = safe_number(
            info.get(
                "forwardPE"
            )
        )


        price_to_book = safe_number(
            info.get(
                "priceToBook"
            )
        )


        revenue_growth = safe_number(
            info.get(
                "revenueGrowth"
            )
        )


        earnings_growth = safe_number(
            info.get(
                "earningsGrowth"
            )
        )


        gross_margin = safe_number(
            info.get(
                "grossMargins"
            )
        )


        operating_margin = safe_number(
            info.get(
                "operatingMargins"
            )
        )


        # ====================================================
        # ANALYST DATA
        # ====================================================

        analyst_target = safe_number(
            info.get(
                "targetMeanPrice"
            )
        )


        analyst_high = safe_number(
            info.get(
                "targetHighPrice"
            )
        )


        analyst_low = safe_number(
            info.get(
                "targetLowPrice"
            )
        )


        analyst_recommendation = (
            normalized_recommendation(
                info.get(
                    "recommendationKey"
                )
            )
        )


        analyst_count = info.get(
            "numberOfAnalystOpinions"
        )


        analyst_upside = None


        if (
            analyst_target is not None
            and price > 0
        ):

            analyst_upside = (
                analyst_target
                /
                price
            ) - 1


        # ====================================================
        # DATA QUALITY
        # ====================================================

        data_quality = min(
            round(
                fundamental_data[
                    "data_quality"
                ]
            ),
            100,
        )


        # ====================================================
        # BALANCED SCORE
        # ====================================================

        component_scores = [
            technical,
            momentum,
            fundamental,
            valuation,
        ]


        average_score = (
            sum(
                component_scores
            )
            /
            len(
                component_scores
            )
        )


        score_spread = (
            max(
                component_scores
            )
            -
            min(
                component_scores
            )
        )


        balanced_score = round(
            average_score
            -
            score_spread
            * 0.15
        )


        # ====================================================
        # CHART DATA
        # ====================================================

        chart_close = (
            close
            .tail(126)
        )


        chart_prices = [

            round(
                float(value),
                4,
            )

            for value

            in chart_close
        ]


        return {

            "ticker":
                ticker,

            "name":
                metadata[
                    "name"
                ],

            "sector":
                metadata[
                    "sector"
                ],

            "scoring_model":
                scoring_model,

            "market":
                market,

            "price":
                price,

            "daily_change":
                daily_change,


            # Scores
            "technical":
                technical,

            "momentum":
                momentum,

            "fundamental":
                fundamental,

            "valuation":
                valuation,

            "overall":
                final_score,

            "balanced_score":
                balanced_score,

            "rating":
                rating(
                    final_score
                ),

            "data_quality":
                data_quality,


            # Technical detail
            "rsi":
                rsi,

            "ma20":
                ma20,

            "ma50":
                ma50,

            "ma200":
                ma200,

            "low_52":
                low_52,

            "high_52":
                high_52,

            "support":
                support,

            "resistance":
                resistance,


            # Performance
            "return_1m":
                return_1m,

            "return_3m":
                return_3m,

            "return_6m":
                return_6m,


            # Fundamentals
            "market_cap":
                market_cap,

            "trailing_pe":
                trailing_pe,

            "forward_pe":
                forward_pe,

            "price_to_book":
                price_to_book,

            "revenue_growth":
                revenue_growth,

            "earnings_growth":
                earnings_growth,

            "gross_margin":
                gross_margin,

            "operating_margin":
                operating_margin,


            # Analysts
            "analyst_target":
                analyst_target,

            "analyst_high":
                analyst_high,

            "analyst_low":
                analyst_low,

            "analyst_upside":
                analyst_upside,

            "analyst_recommendation":
                analyst_recommendation,

            "analyst_count":
                analyst_count,


            # Chart
            "chart_prices":
                chart_prices,

        }


    except Exception as error:

        print(
            f"Error scanning "
            f"{ticker}: "
            f"{error}"
        )

        if ticker == "MU":
            raise RuntimeError(
                "Critical MU scan failed. "
                "Dashboard generation is being aborted so "
                "the previous valid site remains published."
            ) from error

        return None


# ============================================================
# MARKET SCANNING
# ============================================================

def scan_market(
    stocks,
    market,
):

    results = []


    for ticker, metadata in stocks.items():

        result = analyze_stock(
            ticker,
            metadata,
            market,
        )


        if result:

            results.append(
                result
            )


    results.sort(

        key=lambda stock:

            stock[
                "overall"
            ],

        reverse=True,

    )


    return results


def run_scanner():

    portfolio_universe = (
        load_portfolio_universe()
    )


    us_universe = (
        merged_stock_universe(
            US_STOCKS,
            portfolio_universe.get(
                "us",
                {},
            ),
        )
    )


    singapore_universe = (
        merged_stock_universe(
            SINGAPORE_STOCKS,
            portfolio_universe.get(
                "singapore",
                {},
            ),
        )
    )


    extra_us_count = max(
        0,
        len(
            us_universe
        )
        -
        len(
            US_STOCKS
        ),
    )


    extra_sg_count = max(
        0,
        len(
            singapore_universe
        )
        -
        len(
            SINGAPORE_STOCKS
        ),
    )


    if (
        extra_us_count
        or extra_sg_count
    ):

        print(
            "Portfolio universe loaded: "
            f"+{extra_us_count} US, "
            f"+{extra_sg_count} Singapore "
            "additional ticker(s)."
        )


    us_results = scan_market(
        us_universe,
        "US",
    )


    singapore_results = scan_market(
        singapore_universe,
        "Singapore",
    )


    return {

        "us":
            us_results,

        "singapore":
            singapore_results,

    }


if __name__ == "__main__":

    data = run_scanner()


    print(
        "\nTop US stocks:"
    )


    for stock in data[
        "us"
    ][:10]:

        print(

            stock[
                "ticker"
            ],

            stock[
                "overall"
            ],

            stock[
                "rating"
            ],

            stock[
                "scoring_model"
            ],

        )


    print(
        "\nTop Singapore stocks:"
    )


    for stock in data[
        "singapore"
    ][:10]:

        print(

            stock[
                "ticker"
            ],

            stock[
                "overall"
            ],

            stock[
                "rating"
            ],

            stock[
                "scoring_model"
            ],

        )
