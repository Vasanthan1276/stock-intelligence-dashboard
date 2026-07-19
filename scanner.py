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
    "MU": "Micron Technology",
    "NVDA": "NVIDIA",
    "AMD": "Advanced Micro Devices",
    "AVGO": "Broadcom",
    "QCOM": "Qualcomm",
    "TXN": "Texas Instruments",
    "INTC": "Intel",
    "AMAT": "Applied Materials",
    "LRCX": "Lam Research",
    "KLAC": "KLA",
    "TSM": "TSMC",
    "ASML": "ASML",

    # Large Technology
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "ORCL": "Oracle",
    "CRM": "Salesforce",
    "ADBE": "Adobe",

    # Financials
    "JPM": "JPMorgan Chase",
    "BAC": "Bank of America",
    "GS": "Goldman Sachs",
    "MS": "Morgan Stanley",
    "V": "Visa",
    "MA": "Mastercard",
    "AXP": "American Express",
    "BLK": "BlackRock",

    # Healthcare
    "LLY": "Eli Lilly",
    "UNH": "UnitedHealth",
    "JNJ": "Johnson & Johnson",
    "ABBV": "AbbVie",
    "MRK": "Merck",
    "TMO": "Thermo Fisher Scientific",

    # Consumer
    "COST": "Costco",
    "WMT": "Walmart",
    "HD": "Home Depot",
    "MCD": "McDonald's",
    "NKE": "Nike",
    "SBUX": "Starbucks",
    "PG": "Procter & Gamble",
    "KO": "Coca-Cola",

    # Industrials
    "CAT": "Caterpillar",
    "GE": "GE Aerospace",
    "HON": "Honeywell",
    "RTX": "RTX",
    "BA": "Boeing",
    "DE": "Deere",
    "UPS": "UPS",

    # Energy
    "XOM": "Exxon Mobil",
    "CVX": "Chevron",
    "COP": "ConocoPhillips",
    "SLB": "SLB",

    # Communication / Media
    "NFLX": "Netflix",
    "DIS": "Walt Disney",
    "TMUS": "T-Mobile",
    "VZ": "Verizon",

    # Other Growth / High Interest
    "TSLA": "Tesla",
    "PLTR": "Palantir",
    "UBER": "Uber",
    "SHOP": "Shopify",
}


SINGAPORE_STOCKS = {

    # Banks
    "D05.SI": "DBS Group",
    "O39.SI": "OCBC",
    "U11.SI": "UOB",

    # Telecom
    "Z74.SI": "Singtel",
    "CC3.SI": "StarHub",

    # Industrials
    "BN4.SI": "Keppel",
    "U96.SI": "Sembcorp Industries",
    "S63.SI": "ST Engineering",
    "5E2.SI": "Seatrium",
    "BS6.SI": "Yangzijiang Shipbuilding",

    # Transport
    "C6L.SI": "Singapore Airlines",
    "S58.SI": "SATS",
    "C52.SI": "ComfortDelGro",

    # Exchange / Financial Services
    "S68.SI": "Singapore Exchange",
    "AIY.SI": "iFAST",

    # REITs
    "C38U.SI": "CapitaLand Integrated Commercial Trust",
    "A17U.SI": "CapitaLand Ascendas REIT",
    "M44U.SI": "Mapletree Logistics Trust",
    "N2IU.SI": "Mapletree Pan Asia Commercial Trust",
    "ME8U.SI": "Mapletree Industrial Trust",
    "AJBU.SI": "Keppel DC REIT",
    "J69U.SI": "Frasers Centrepoint Trust",

    # Property
    "9CI.SI": "CapitaLand Investment",
    "U14.SI": "UOL Group",
    "H78.SI": "Hongkong Land",
    "F34.SI": "Wilmar International",

    # Consumer / Defensive
    "D01.SI": "DFI Retail Group",
    "C07.SI": "Jardine Cycle & Carriage",
    "Y92.SI": "Thai Beverage",

    # Conglomerates / Others
    "J36.SI": "Jardine Matheson",
    "G13.SI": "Genting Singapore",
}


def analyze_stock(
    ticker,
    name,
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


        technical, rsi = technical_score(
            history
        )


        momentum = momentum_score(
            history
        )


        fundamental_data = fundamental_score(
            info
        )


        fundamental = fundamental_data[
            "score"
        ]


        valuation = valuation_score(
            info
        )


        final_score = overall_score(
            technical,
            momentum,
            fundamental,
            valuation,
        )


        return {

            "ticker": ticker,

            "name": name,

            "market": market,

            "price": price,

            "daily_change": daily_change,

            "technical": technical,

            "momentum": momentum,

            "fundamental": fundamental,

            "valuation": valuation,

            "overall": final_score,

            "rating": rating(
                final_score
            ),

            "rsi": rsi,

            "data_quality":
                fundamental_data[
                    "data_quality"
                ],

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


    for ticker, name in stocks.items():

        print(
            f"Scanning {ticker}..."
        )


        result = analyze_stock(
            ticker,
            name,
            market,
        )


        if result:

            results.append(
                result
            )


    results.sort(

        key=lambda stock:
            stock["overall"],

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

            stock["ticker"],

            stock["overall"],

            stock["rating"],

        )


    print(
        "\nTop Singapore stocks:"
    )


    for stock in data[
        "singapore"
    ][:10]:

        print(

            stock["ticker"],

            stock["overall"],

            stock["rating"],

        )
