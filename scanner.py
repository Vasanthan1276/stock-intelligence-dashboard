import math

import pandas as pd
import yfinance as yf


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


def safe_number(value):
    try:
        value = float(value)

        if math.isnan(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def calculate_rsi(series, period=14):
    delta = series.diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    average_loss = losses.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    rs = average_gain / average_loss

    return 100 - (
        100 / (1 + rs)
    )


def calculate_return(close, days):
    if len(close) <= days:
        return None

    old_price = float(
        close.iloc[-days - 1]
    )

    new_price = float(
        close.iloc[-1]
    )

    return (
        new_price / old_price
    ) - 1


def technical_score(history):
    close = history["Close"]

    if len(close) < 200:
        return 50, None

    price = float(
        close.iloc[-1]
    )

    ma20 = float(
        close.rolling(20).mean().iloc[-1]
    )

    ma50 = float(
        close.rolling(50).mean().iloc[-1]
    )

    ma200 = float(
        close.rolling(200).mean().iloc[-1]
    )

    rsi = float(
        calculate_rsi(
            close
        ).iloc[-1]
    )

    ema12 = close.ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
    ).mean()

    macd = (
        ema12 - ema26
    )

    macd_signal = macd.ewm(
        span=9,
        adjust=False,
    ).mean()

    score = 0

    if price > ma20:
        score += 15

    if price > ma50:
        score += 20

    if price > ma200:
        score += 25

    if ma50 > ma200:
        score += 10

    if macd.iloc[-1] > macd_signal.iloc[-1]:
        score += 15

    if 40 <= rsi <= 65:
        score += 15

    elif rsi < 30:
        score += 10

    elif 30 <= rsi < 40:
        score += 8

    elif 65 < rsi <= 75:
        score += 8

    return min(
        round(score),
        100,
    ), rsi


def momentum_score(history):
    close = history["Close"]

    periods = [
        (5, 10),
        (21, 20),
        (63, 30),
        (126, 40),
    ]

    score = 0

    for days, weight in periods:
        value = calculate_return(
            close,
            days,
        )

        if value is None:
            continue

        if value > 0.20:
            score += weight

        elif value > 0.10:
            score += weight * 0.85

        elif value > 0.03:
            score += weight * 0.70

        elif value >= 0:
            score += weight * 0.55

        elif value > -0.05:
            score += weight * 0.40

        elif value > -0.15:
            score += weight * 0.20

    return min(
        round(score),
        100,
    )


def fundamental_score(info):
    score = 0
    available = 0

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

    forward_pe = safe_number(
        info.get(
            "forwardPE"
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

    roe = safe_number(
        info.get(
            "returnOnEquity"
        )
    )

    debt_to_equity = safe_number(
        info.get(
            "debtToEquity"
        )
    )

    current_ratio = safe_number(
        info.get(
            "currentRatio"
        )
    )

    if revenue_growth is not None:
        available += 15

        if revenue_growth >= 0.30:
            score += 15

        elif revenue_growth >= 0.15:
            score += 12

        elif revenue_growth > 0:
            score += 8

        else:
            score += 2


    if earnings_growth is not None:
        available += 15

        if earnings_growth >= 0.30:
            score += 15

        elif earnings_growth >= 0.15:
            score += 12

        elif earnings_growth > 0:
            score += 8

        else:
            score += 2


    if forward_pe is not None:
        available += 15

        if 0 < forward_pe <= 12:
            score += 15

        elif forward_pe <= 18:
            score += 13

        elif forward_pe <= 25:
            score += 10

        elif forward_pe <= 35:
            score += 6

        else:
            score += 2


    if gross_margin is not None:
        available += 15

        if gross_margin >= 0.50:
            score += 15

        elif gross_margin >= 0.40:
            score += 13

        elif gross_margin >= 0.30:
            score += 10

        elif gross_margin > 0:
            score += 6


    if operating_margin is not None:
        available += 10

        if operating_margin >= 0.30:
            score += 10

        elif operating_margin >= 0.20:
            score += 8

        elif operating_margin >= 0.10:
            score += 6

        elif operating_margin > 0:
            score += 4


    if roe is not None:
        available += 10

        if roe >= 0.25:
            score += 10

        elif roe >= 0.15:
            score += 8

        elif roe >= 0.08:
            score += 6

        elif roe > 0:
            score += 4


    if debt_to_equity is not None:
        available += 10

        if debt_to_equity <= 30:
            score += 10

        elif debt_to_equity <= 60:
            score += 8

        elif debt_to_equity <= 100:
            score += 6

        else:
            score += 3


    if current_ratio is not None:
        available += 10

        if current_ratio >= 2:
            score += 10

        elif current_ratio >= 1.5:
            score += 8

        elif current_ratio >= 1:
            score += 6

        else:
            score += 2


    if available == 0:
        return 50, 0

    normalized_score = (
        score / available
    ) * 100

    normalized_score = min(
        round(
            normalized_score
        ),
        95,
    )

    data_quality = round(
        available
    )

    return (
        normalized_score,
        data_quality,
    )


def valuation_score(info):
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

    score = 50
    points = []

    if forward_pe is not None:

        if 0 < forward_pe <= 12:
            points.append(
                90
            )

        elif forward_pe <= 18:
            points.append(
                80
            )

        elif forward_pe <= 25:
            points.append(
                65
            )

        elif forward_pe <= 35:
            points.append(
                45
            )

        else:
            points.append(
                25
            )


    if price_to_book is not None:

        if price_to_book <= 1.5:
            points.append(
                85
            )

        elif price_to_book <= 3:
            points.append(
                70
            )

        elif price_to_book <= 6:
            points.append(
                50
            )

        else:
            points.append(
                30
            )


    if points:
        score = round(
            sum(points)
            / len(points)
        )

    return score


def overall_score(
    technical,
    momentum,
    fundamental,
    valuation,
):
    return round(

        technical * 0.25

        +

        momentum * 0.20

        +

        fundamental * 0.40

        +

        valuation * 0.15

    )


def rating(score):
    if score >= 80:
        return "STRONG BUY"

    if score >= 65:
        return "BUY"

    if score >= 50:
        return "HOLD"

    if score >= 35:
        return "WATCH"

    return "CAUTION"


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

        info = stock.info or {}

        price = float(
            history["Close"].iloc[-1]
        )

        previous = float(
            history["Close"].iloc[-2]
        )

        daily_change = (
            price / previous
        ) - 1

        technical, rsi = technical_score(
            history
        )

        momentum = momentum_score(
            history
        )

        fundamental, data_quality = (
            fundamental_score(
                info
            )
        )

        valuation = valuation_score(
            info
        )

        score = overall_score(
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
            "overall": score,
            "rating": rating(
                score
            ),
            "rsi": rsi,
            "data_quality": data_quality,
        }

    except Exception as error:

        print(
            f"Error scanning {ticker}: {error}"
        )

        return None


def scan_market(
    stock_list,
    market,
):
    results = []

    for ticker, name in stock_list.items():

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
        key=lambda item: item[
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

    for stock in data["us"][:5]:

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
        )


    print(
        "\nTop Singapore stocks:"
    )

    for stock in data[
        "singapore"
    ][:5]:

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
        )
