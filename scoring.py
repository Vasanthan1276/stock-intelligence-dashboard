import math


def safe_number(value):
    try:
        if value is None:
            return None

        value = float(value)

        if math.isnan(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def clamp(value, minimum=0, maximum=100):
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


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

    start = float(
        close.iloc[-days - 1]
    )

    end = float(
        close.iloc[-1]
    )

    return (
        end / start
    ) - 1


def technical_score(history):
    close = history["Close"]

    if len(close) < 200:
        return 50, None

    price = float(
        close.iloc[-1]
    )

    ma20 = float(
        close
        .rolling(20)
        .mean()
        .iloc[-1]
    )

    ma50 = float(
        close
        .rolling(50)
        .mean()
        .iloc[-1]
    )

    ma200 = float(
        close
        .rolling(200)
        .mean()
        .iloc[-1]
    )

    rsi_series = calculate_rsi(
        close
    )

    rsi = float(
        rsi_series.iloc[-1]
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
        ema12
        - ema26
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

    if (
        macd.iloc[-1]
        >
        macd_signal.iloc[-1]
    ):
        score += 15

    if 40 <= rsi <= 65:
        score += 15

    elif rsi < 30:
        score += 10

    elif 30 <= rsi < 40:
        score += 8

    elif 65 < rsi <= 75:
        score += 8

    return (
        clamp(
            round(score)
        ),
        rsi,
    )


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
            score += (
                weight * 0.85
            )

        elif value > 0.03:
            score += (
                weight * 0.70
            )

        elif value >= 0:
            score += (
                weight * 0.55
            )

        elif value > -0.05:
            score += (
                weight * 0.40
            )

        elif value > -0.15:
            score += (
                weight * 0.20
            )

    return clamp(
        round(score)
    )


def fundamental_score(info):
    components = {}

    maximum_points = 0

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


    # Revenue growth - 15

    if revenue_growth is not None:

        maximum_points += 15

        if revenue_growth >= 0.40:
            score = 15

        elif revenue_growth >= 0.20:
            score = 13

        elif revenue_growth >= 0.10:
            score = 10

        elif revenue_growth > 0:
            score = 7

        else:
            score = 2

        components[
            "Revenue Growth"
        ] = score


    # Earnings growth - 15

    if earnings_growth is not None:

        maximum_points += 15

        if earnings_growth >= 0.50:
            score = 15

        elif earnings_growth >= 0.25:
            score = 13

        elif earnings_growth >= 0.10:
            score = 10

        elif earnings_growth > 0:
            score = 7

        else:
            score = 2

        components[
            "Earnings Growth"
        ] = score


    # Forward valuation - 15

    if forward_pe is not None:

        maximum_points += 15

        if 0 < forward_pe <= 12:
            score = 15

        elif forward_pe <= 18:
            score = 13

        elif forward_pe <= 25:
            score = 10

        elif forward_pe <= 35:
            score = 6

        else:
            score = 2

        components[
            "Forward Valuation"
        ] = score


    # Gross margin - 15

    if gross_margin is not None:

        maximum_points += 15

        if gross_margin >= 0.50:
            score = 15

        elif gross_margin >= 0.40:
            score = 13

        elif gross_margin >= 0.30:
            score = 10

        elif gross_margin >= 0.20:
            score = 7

        else:
            score = 3

        components[
            "Gross Margin"
        ] = score


    # Operating margin - 10

    if operating_margin is not None:

        maximum_points += 10

        if operating_margin >= 0.30:
            score = 10

        elif operating_margin >= 0.20:
            score = 8

        elif operating_margin >= 0.10:
            score = 6

        elif operating_margin > 0:
            score = 4

        else:
            score = 1

        components[
            "Operating Margin"
        ] = score


    # ROE - 10

    if roe is not None:

        maximum_points += 10

        if roe >= 0.25:
            score = 10

        elif roe >= 0.15:
            score = 8

        elif roe >= 0.08:
            score = 6

        elif roe > 0:
            score = 4

        else:
            score = 1

        components[
            "Return on Equity"
        ] = score


    # Debt - 10

    if debt_to_equity is not None:

        maximum_points += 10

        if debt_to_equity <= 30:
            score = 10

        elif debt_to_equity <= 60:
            score = 8

        elif debt_to_equity <= 100:
            score = 6

        elif debt_to_equity <= 150:
            score = 4

        else:
            score = 2

        components[
            "Balance Sheet"
        ] = score


    # Liquidity - 10

    if current_ratio is not None:

        maximum_points += 10

        if current_ratio >= 2:
            score = 10

        elif current_ratio >= 1.5:
            score = 8

        elif current_ratio >= 1:
            score = 6

        else:
            score = 2

        components[
            "Liquidity"
        ] = score


    if maximum_points == 0:

        return {
            "score": 50,
            "components": {},
            "data_quality": 0,
        }


    earned_points = sum(
        components.values()
    )


    normalized = round(

        earned_points

        / maximum_points

        * 100

    )


    # No stock receives a perfect fundamental
    # score from these basic metrics alone.

    normalized = min(
        normalized,
        95,
    )


    data_quality = round(
        maximum_points
    )


    return {
        "score": normalized,
        "components": components,
        "data_quality": data_quality,
    }


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

    scores = []

    if forward_pe is not None:

        if 0 < forward_pe <= 12:
            scores.append(90)

        elif forward_pe <= 18:
            scores.append(80)

        elif forward_pe <= 25:
            scores.append(65)

        elif forward_pe <= 35:
            scores.append(45)

        else:
            scores.append(25)


    if price_to_book is not None:

        if price_to_book <= 1.5:
            scores.append(85)

        elif price_to_book <= 3:
            scores.append(70)

        elif price_to_book <= 6:
            scores.append(50)

        else:
            scores.append(30)


    if not scores:
        return 50


    return round(
        sum(scores)
        / len(scores)
    )


def overall_score(
    technical,
    momentum,
    fundamental,
    valuation,
):
    return round(

        technical
        * 0.25

        +

        momentum
        * 0.20

        +

        fundamental
        * 0.40

        +

        valuation
        * 0.15

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
