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
    "MU": "Micron Technology",
    "NVDA": "NVIDIA",
    "AMD": "Advanced Micro Devices",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "AVGO": "Broadcom",
    "TSM": "TSMC",
    "JPM": "JPMorgan Chase",
    "BAC": "Bank of America",
    "V": "Visa",
    "MA": "Mastercard",
    "XOM": "Exxon Mobil",
    "CVX": "Chevron",
    "CAT": "Caterpillar",
    "GE": "GE Aerospace",
    "LLY": "Eli Lilly",
    "COST": "Costco",
}


SINGAPORE_STOCKS = {
    "D05.SI": "DBS Group",
    "O39.SI": "OCBC",
    "U11.SI": "UOB",
    "Z74.SI": "Singtel",
    "BN4.SI": "Keppel",
    "U96.SI": "Sembcorp Industries",
    "C6L.SI": "Singapore Airlines",
    "S68.SI": "Singapore Exchange",
    "C38U.SI": "CapitaLand Integrated Commercial Trust",
    "A17U.SI": "CapitaLand Ascendas REIT",
    "M44U.SI": "Mapletree Logistics Trust",
    "N2IU.SI": "Mapletree Pan Asia Commercial Trust",
    "ME8U.SI": "Mapletree Industrial Trust",
    "J36.SI": "Jardine Matheson",
    "F34.SI": "Wilmar International",
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
    ][:5]:

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
    ][:5]:

        print(

            stock["ticker"],

            stock["overall"],

            stock["rating"],

        )
