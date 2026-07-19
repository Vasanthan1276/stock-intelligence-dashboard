import yfinance as yf

from scoring import (
    fundamental_score,
    momentum_score,
    overall_score,
    rating,
    technical_score,
    valuation_score,
)


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

    # Media / Telecom
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


def analyze_stock(
    ticker,
    metadata,
    market,
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

        if history.empty:
            return None

        info = (
            stock.info
            or {}
        )

        close = history[
            "Close"
        ]

        price = float(
            close.iloc[-1]
        )

        previous_price = float(
            close.iloc[-2]
        )

        daily_change = (
            price
            / previous_price
        ) - 1

        technical, rsi = (
            technical_score(
                history
            )
        )

        momentum = momentum_score(
            history
        )

        fundamental_data = (
            fundamental_score(
                info
            )
        )

        fundamental = (
            fundamental_data[
                "score"
            ]
        )

        valuation = valuation_score(
            info
        )

        final_score = overall_score(
            technical,
            momentum,
            fundamental,
            valuation,
        )

        data_quality = (
            fundamental_data[
                "data_quality"
            ]
        )

        data_quality_pct = min(
            round(
                data_quality
            ),
            100,
        )

        balance_score = round(
            (
                technical
                +
                momentum
                +
                fundamental
                +
                valuation
            )
            / 4
        )

        score_spread = (
            max(
                technical,
                momentum,
                fundamental,
                valuation,
            )
            -
            min(
                technical,
                momentum,
                fundamental,
                valuation,
            )
        )

        balanced_score = round(
            balance_score
            -
            score_spread
            * 0.15
        )

        return {

            "ticker": ticker,

            "name": metadata[
                "name"
            ],

            "sector": metadata[
                "sector"
            ],

            "market": market,

            "price": price,

            "daily_change": daily_change,

            "technical": technical,

            "momentum": momentum,

            "fundamental": fundamental,

            "valuation": valuation,

            "overall": final_score,

            "balanced_score":
                balanced_score,

            "rating": rating(
                final_score
            ),

            "rsi": rsi,

            "data_quality":
                data_quality_pct,

        }

    except Exception as error:

        print(
            f"Error scanning "
            f"{ticker}: "
            f"{error}"
        )

        return None


def scan_market(
    stocks,
    market,
):

    results = []

    for ticker, metadata in stocks.items():

        print(
            f"Scanning {ticker}..."
        )

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

    us_results = scan_market(
        US_STOCKS,
        "US",
    )

    singapore_results = scan_market(
        SINGAPORE_STOCKS,
        "Singapore",
    )

    return {
        "us": us_results,
        "singapore": singapore_results,
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
                "sector"
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
                "sector"
            ],
        )
