import math

import pandas as pd


# ============================================================
# BASIC HELPERS
# ============================================================

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


def clamp(
    value,
    minimum=0,
    maximum=100,
):
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


# ============================================================
# SCORING MODEL SELECTION
# ============================================================

def scoring_model_name(sector):

    sector_value = (
        sector
        or ""
    ).lower()


    if sector_value == "banks":
        return "Bank"


    if sector_value == "reit":
        return "REIT"


    if (
        "semiconductor"
        in sector_value
    ):
        return "Semiconductor"


    return "General Company"


def scoring_weights(sector):

    model = scoring_model_name(
        sector
    )


    if model == "Bank":

        return {
            "technical": 0.15,
            "momentum": 0.15,
            "fundamental": 0.45,
            "valuation": 0.25,
        }


    if model == "REIT":

        return {
            "technical": 0.10,
            "momentum": 0.10,
            "fundamental": 0.45,
            "valuation": 0.35,
        }


    if model == "Semiconductor":

        return {
            "technical": 0.20,
            "momentum": 0.25,
            "fundamental": 0.40,
            "valuation": 0.15,
        }


    return {
        "technical": 0.25,
        "momentum": 0.20,
        "fundamental": 0.40,
        "valuation": 0.15,
    }


# ============================================================
# TECHNICAL INDICATORS
# ============================================================

def calculate_rsi(
    close,
    period=14,
):

    if (
        close is None
        or len(close) <= period
    ):
        return None


    delta = close.diff()


    gains = delta.clip(
        lower=0
    )


    losses = (
        -delta.clip(
            upper=0
        )
    )


    average_gain = gains.rolling(
        period
    ).mean()


    average_loss = losses.rolling(
        period
    ).mean()


    latest_gain = safe_number(
        average_gain.iloc[-1]
    )


    latest_loss = safe_number(
        average_loss.iloc[-1]
    )


    if (
        latest_gain is None
        or latest_loss is None
    ):
        return None


    if latest_loss == 0:
        return 100.0


    rs = (
        latest_gain
        /
        latest_loss
    )


    rsi = (
        100
        -
        (
            100
            /
            (
                1
                +
                rs
            )
        )
    )


    return round(
        rsi,
        1,
    )


def calculate_return(
    history,
    periods,
):

    if (
        history is None
        or history.empty
        or len(history) <= periods
    ):
        return None


    current = safe_number(
        history[
            "Close"
        ].iloc[-1]
    )


    previous = safe_number(
        history[
            "Close"
        ].iloc[
            -periods - 1
        ]
    )


    if (
        current is None
        or previous is None
        or previous == 0
    ):
        return None


    return (
        current
        /
        previous
    ) - 1


# ============================================================
# TECHNICAL SCORE
# ============================================================

def technical_score(history):

    if (
        history is None
        or history.empty
        or len(history) < 30
    ):
        return 50, None


    close = history[
        "Close"
    ]


    price = safe_number(
        close.iloc[-1]
    )


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
        -
        ema26
    )


    signal = macd.ewm(
        span=9,
        adjust=False,
    ).mean()


    latest_macd = safe_number(
        macd.iloc[-1]
    )


    latest_signal = safe_number(
        signal.iloc[-1]
    )


    rsi = calculate_rsi(
        close
    )


    score = 0


    if (
        price is not None
        and ma20 is not None
        and price > ma20
    ):
        score += 15


    if (
        price is not None
        and ma50 is not None
        and price > ma50
    ):
        score += 20


    if (
        price is not None
        and ma200 is not None
        and price > ma200
    ):
        score += 25


    if (
        ma50 is not None
        and ma200 is not None
        and ma50 > ma200
    ):
        score += 10


    if (
        latest_macd is not None
        and latest_signal is not None
        and latest_macd > latest_signal
    ):
        score += 15


    if rsi is not None:

        if 40 <= rsi <= 65:
            score += 15

        elif rsi < 30:
            score += 10

        elif 30 <= rsi < 40:
            score += 8

        elif 65 < rsi <= 75:
            score += 8


    return (
        round(
            clamp(score)
        ),
        rsi,
    )


# ============================================================
# MOMENTUM SCORE
# ============================================================

def momentum_score(history):

    periods = [

        (
            5,
            10,
        ),

        (
            21,
            20,
        ),

        (
            63,
            30,
        ),

        (
            126,
            40,
        ),

    ]


    score = 0


    for (
        days,
        weight,
    ) in periods:

        performance = calculate_return(
            history,
            days,
        )


        if performance is None:
            continue


        if performance > 0.20:

            score += (
                weight
                * 1.00
            )


        elif performance > 0.10:

            score += (
                weight
                * 0.85
            )


        elif performance > 0.03:

            score += (
                weight
                * 0.70
            )


        elif performance >= 0:

            score += (
                weight
                * 0.55
            )


        elif performance > -0.05:

            score += (
                weight
                * 0.40
            )


        elif performance > -0.15:

            score += (
                weight
                * 0.20
            )


    return round(
        clamp(score)
    )


# ============================================================
# GENERIC SCORING HELPERS
# ============================================================

def positive_growth_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value >= 0.30:
        multiplier = 1.00

    elif value >= 0.15:
        multiplier = 0.85

    elif value >= 0.05:
        multiplier = 0.70

    elif value >= 0:
        multiplier = 0.50

    elif value >= -0.10:
        multiplier = 0.25

    else:
        multiplier = 0.05


    return (
        maximum_points
        *
        multiplier
    )


def margin_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value >= 0.40:
        multiplier = 1.00

    elif value >= 0.25:
        multiplier = 0.85

    elif value >= 0.15:
        multiplier = 0.70

    elif value >= 0.08:
        multiplier = 0.50

    elif value > 0:
        multiplier = 0.30

    else:
        multiplier = 0.05


    return (
        maximum_points
        *
        multiplier
    )


def roe_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value >= 0.25:
        multiplier = 1.00

    elif value >= 0.15:
        multiplier = 0.85

    elif value >= 0.10:
        multiplier = 0.70

    elif value >= 0.05:
        multiplier = 0.50

    elif value > 0:
        multiplier = 0.25

    else:
        multiplier = 0.05


    return (
        maximum_points
        *
        multiplier
    )


def roa_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value >= 0.03:
        multiplier = 1.00

    elif value >= 0.02:
        multiplier = 0.85

    elif value >= 0.01:
        multiplier = 0.70

    elif value >= 0.005:
        multiplier = 0.50

    elif value > 0:
        multiplier = 0.30

    else:
        multiplier = 0.05


    return (
        maximum_points
        *
        multiplier
    )


def dividend_yield_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value >= 0.06:
        multiplier = 1.00

    elif value >= 0.04:
        multiplier = 0.90

    elif value >= 0.025:
        multiplier = 0.75

    elif value >= 0.01:
        multiplier = 0.50

    elif value > 0:
        multiplier = 0.25

    else:
        multiplier = 0.05


    return (
        maximum_points
        *
        multiplier
    )


def debt_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value <= 30:
        multiplier = 1.00

    elif value <= 60:
        multiplier = 0.80

    elif value <= 100:
        multiplier = 0.60

    elif value <= 150:
        multiplier = 0.35

    else:
        multiplier = 0.10


    return (
        maximum_points
        *
        multiplier
    )


def liquidity_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value >= 2:
        multiplier = 1.00

    elif value >= 1.5:
        multiplier = 0.85

    elif value >= 1:
        multiplier = 0.65

    elif value >= 0.75:
        multiplier = 0.35

    else:
        multiplier = 0.10


    return (
        maximum_points
        *
        multiplier
    )


def normalize_components(
    components,
):

    score = 0

    available_points = 0

    component_results = {}


    for (
        name,
        result,
        maximum_points,
    ) in components:

        if result is None:

            component_results[
                name
            ] = None

            continue


        score += result

        available_points += (
            maximum_points
        )


        component_results[
            name
        ] = round(
            result,
            1,
        )


    if available_points == 0:

        return {
            "score": 50,
            "components":
                component_results,
            "data_quality": 0,
        }


    normalized_score = (

        score

        /

        available_points

        *

        100

    )


    return {

        "score":

            round(
                min(
                    normalized_score,
                    95,
                )
            ),


        "components":

            component_results,


        "data_quality":

            round(
                available_points
            ),

    }


# ============================================================
# GENERAL COMPANY FUNDAMENTALS
# ============================================================

def general_fundamental_score(info):

    components = []


    components.append((

        "Revenue Growth",

        positive_growth_score(

            info.get(
                "revenueGrowth"
            ),

            15,

        ),

        15,

    ))


    components.append((

        "Earnings Growth",

        positive_growth_score(

            info.get(
                "earningsGrowth"
            ),

            15,

        ),

        15,

    ))


    components.append((

        "Forward Valuation",

        forward_pe_component_score(

            info.get(
                "forwardPE"
            ),

            15,

        ),

        15,

    ))


    components.append((

        "Gross Margin",

        margin_score(

            info.get(
                "grossMargins"
            ),

            15,

        ),

        15,

    ))


    components.append((

        "Operating Margin",

        margin_score(

            info.get(
                "operatingMargins"
            ),

            10,

        ),

        10,

    ))


    components.append((

        "Return on Equity",

        roe_score(

            info.get(
                "returnOnEquity"
            ),

            10,

        ),

        10,

    ))


    components.append((

        "Debt / Equity",

        debt_score(

            info.get(
                "debtToEquity"
            ),

            10,

        ),

        10,

    ))


    components.append((

        "Liquidity",

        liquidity_score(

            info.get(
                "currentRatio"
            ),

            10,

        ),

        10,

    ))


    return normalize_components(
        components
    )


# ============================================================
# BANK FUNDAMENTALS
# ============================================================

def bank_fundamental_score(info):

    components = []


    components.append((

        "Return on Equity",

        roe_score(

            info.get(
                "returnOnEquity"
            ),

            25,

        ),

        25,

    ))


    components.append((

        "Return on Assets",

        roa_score(

            info.get(
                "returnOnAssets"
            ),

            15,

        ),

        15,

    ))


    components.append((

        "Earnings Growth",

        positive_growth_score(

            info.get(
                "earningsGrowth"
            ),

            20,

        ),

        20,

    ))


    components.append((

        "Revenue Growth",

        positive_growth_score(

            info.get(
                "revenueGrowth"
            ),

            10,

        ),

        10,

    ))


    components.append((

        "Profit Margin",

        margin_score(

            info.get(
                "profitMargins"
            ),

            20,

        ),

        20,

    ))


    components.append((

        "Dividend Yield",

        dividend_yield_score(

            info.get(
                "dividendYield"
            ),

            10,

        ),

        10,

    ))


    return normalize_components(
        components
    )


# ============================================================
# REIT FUNDAMENTALS
# ============================================================

def reit_fundamental_score(info):

    components = []


    components.append((

        "Dividend Yield",

        dividend_yield_score(

            info.get(
                "dividendYield"
            ),

            25,

        ),

        25,

    ))


    components.append((

        "Revenue Growth",

        positive_growth_score(

            info.get(
                "revenueGrowth"
            ),

            15,

        ),

        15,

    ))


    components.append((

        "Earnings Growth",

        positive_growth_score(

            info.get(
                "earningsGrowth"
            ),

            10,

        ),

        10,

    ))


    components.append((

        "Operating Margin",

        margin_score(

            info.get(
                "operatingMargins"
            ),

            20,

        ),

        20,

    ))


    components.append((

        "Profit Margin",

        margin_score(

            info.get(
                "profitMargins"
            ),

            15,

        ),

        15,

    ))


    components.append((

        "Return on Assets",

        roa_score(

            info.get(
                "returnOnAssets"
            ),

            5,

        ),

        5,

    ))


    components.append((

        "Debt / Equity",

        debt_score(

            info.get(
                "debtToEquity"
            ),

            10,

        ),

        10,

    ))


    return normalize_components(
        components
    )


# ============================================================
# SEMICONDUCTOR FUNDAMENTALS
# ============================================================

def semiconductor_fundamental_score(info):

    components = []


    components.append((

        "Revenue Growth",

        positive_growth_score(

            info.get(
                "revenueGrowth"
            ),

            20,

        ),

        20,

    ))


    components.append((

        "Earnings Growth",

        positive_growth_score(

            info.get(
                "earningsGrowth"
            ),

            20,

        ),

        20,

    ))


    components.append((

        "Gross Margin",

        margin_score(

            info.get(
                "grossMargins"
            ),

            20,

        ),

        20,

    ))


    components.append((

        "Operating Margin",

        margin_score(

            info.get(
                "operatingMargins"
            ),

            15,

        ),

        15,

    ))


    components.append((

        "Return on Equity",

        roe_score(

            info.get(
                "returnOnEquity"
            ),

            10,

        ),

        10,

    ))


    components.append((

        "Debt / Equity",

        debt_score(

            info.get(
                "debtToEquity"
            ),

            10,

        ),

        10,

    ))


    components.append((

        "Liquidity",

        liquidity_score(

            info.get(
                "currentRatio"
            ),

            5,

        ),

        5,

    ))


    return normalize_components(
        components
    )


# ============================================================
# FUNDAMENTAL MODEL ROUTER
# ============================================================

def fundamental_score(
    info,
    sector=None,
):

    model = scoring_model_name(
        sector
    )


    if model == "Bank":

        return bank_fundamental_score(
            info
        )


    if model == "REIT":

        return reit_fundamental_score(
            info
        )


    if model == "Semiconductor":

        return semiconductor_fundamental_score(
            info
        )


    return general_fundamental_score(
        info
    )


# ============================================================
# VALUATION HELPERS
# ============================================================

def forward_pe_component_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value <= 0:
        multiplier = 0.10

    elif value <= 12:
        multiplier = 1.00

    elif value <= 18:
        multiplier = 0.85

    elif value <= 25:
        multiplier = 0.70

    elif value <= 35:
        multiplier = 0.45

    else:
        multiplier = 0.25


    return (
        maximum_points
        *
        multiplier
    )


def price_to_book_component_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value <= 0:
        multiplier = 0.10

    elif value <= 1:
        multiplier = 1.00

    elif value <= 1.5:
        multiplier = 0.90

    elif value <= 3:
        multiplier = 0.75

    elif value <= 6:
        multiplier = 0.50

    else:
        multiplier = 0.25


    return (
        maximum_points
        *
        multiplier
    )


def price_to_sales_component_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value <= 1:
        multiplier = 1.00

    elif value <= 3:
        multiplier = 0.85

    elif value <= 6:
        multiplier = 0.65

    elif value <= 10:
        multiplier = 0.40

    else:
        multiplier = 0.20


    return (
        maximum_points
        *
        multiplier
    )


def peg_component_score(
    value,
    maximum_points,
):

    value = safe_number(
        value
    )


    if value is None:
        return None


    if value <= 0:
        multiplier = 0.20

    elif value <= 1:
        multiplier = 1.00

    elif value <= 1.5:
        multiplier = 0.85

    elif value <= 2:
        multiplier = 0.65

    elif value <= 3:
        multiplier = 0.40

    else:
        multiplier = 0.20


    return (
        maximum_points
        *
        multiplier
    )


def normalized_valuation(
    components,
):

    score = 0

    available_points = 0


    for (
        result,
        maximum_points,
    ) in components:

        if result is None:
            continue


        score += result

        available_points += (
            maximum_points
        )


    if available_points == 0:
        return 50


    return round(

        clamp(

            score

            /

            available_points

            *

            100

        )

    )


# ============================================================
# GENERAL VALUATION
# ============================================================

def general_valuation_score(info):

    return normalized_valuation([

        (

            forward_pe_component_score(

                info.get(
                    "forwardPE"
                ),

                60,

            ),

            60,

        ),

        (

            price_to_book_component_score(

                info.get(
                    "priceToBook"
                ),

                40,

            ),

            40,

        ),

    ])


# ============================================================
# BANK VALUATION
# ============================================================

def bank_valuation_score(info):

    return normalized_valuation([

        (

            price_to_book_component_score(

                info.get(
                    "priceToBook"
                ),

                45,

            ),

            45,

        ),

        (

            forward_pe_component_score(

                info.get(
                    "forwardPE"
                ),

                35,

            ),

            35,

        ),

        (

            dividend_yield_score(

                info.get(
                    "dividendYield"
                ),

                20,

            ),

            20,

        ),

    ])


# ============================================================
# REIT VALUATION
# ============================================================

def reit_valuation_score(info):

    return normalized_valuation([

        (

            price_to_book_component_score(

                info.get(
                    "priceToBook"
                ),

                40,

            ),

            40,

        ),

        (

            dividend_yield_score(

                info.get(
                    "dividendYield"
                ),

                35,

            ),

            35,

        ),

        (

            forward_pe_component_score(

                info.get(
                    "forwardPE"
                ),

                25,

            ),

            25,

        ),

    ])


# ============================================================
# SEMICONDUCTOR VALUATION
# ============================================================

def semiconductor_valuation_score(info):

    return normalized_valuation([

        (

            forward_pe_component_score(

                info.get(
                    "forwardPE"
                ),

                55,

            ),

            55,

        ),

        (

            peg_component_score(

                info.get(
                    "pegRatio"
                ),

                25,

            ),

            25,

        ),

        (

            price_to_sales_component_score(

                info.get(
                    "priceToSalesTrailing12Months"
                ),

                20,

            ),

            20,

        ),

    ])


# ============================================================
# VALUATION MODEL ROUTER
# ============================================================

def valuation_score(
    info,
    sector=None,
):

    model = scoring_model_name(
        sector
    )


    if model == "Bank":

        return bank_valuation_score(
            info
        )


    if model == "REIT":

        return reit_valuation_score(
            info
        )


    if model == "Semiconductor":

        return semiconductor_valuation_score(
            info
        )


    return general_valuation_score(
        info
    )


# ============================================================
# OVERALL SCORE
# ============================================================

def overall_score(
    technical,
    momentum,
    fundamental,
    valuation,
    sector=None,
):

    weights = scoring_weights(
        sector
    )


    score = (

        technical
        *
        weights[
            "technical"
        ]

        +

        momentum
        *
        weights[
            "momentum"
        ]

        +

        fundamental
        *
        weights[
            "fundamental"
        ]

        +

        valuation
        *
        weights[
            "valuation"
        ]

    )


    return round(
        clamp(score)
    )


# ============================================================
# RATING
# ============================================================

def rating(score):

    if score >= 80:
        return "Strong Buy"

    if score >= 65:
        return "Buy"

    if score >= 50:
        return "Hold"

    if score >= 35:
        return "Watch"

    return "Caution"
