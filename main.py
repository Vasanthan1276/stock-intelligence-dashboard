import base64
import html
import io
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import yfinance as yf

from scoring import (
    fundamental_score as shared_fundamental_score,
    momentum_score as shared_momentum_score,
    overall_score as shared_overall_score,
    rating as shared_rating,
    technical_score as shared_technical_score,
    valuation_score as shared_valuation_score,
)


TICKER = "MU"
COMPANY_NAME = "Micron Technology"
SECTOR = "Semiconductors"


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_number(
    value,
    default=None,
):
    try:

        if value is None:
            return default

        value = float(
            value
        )

        if math.isnan(
            value
        ):
            return default

        return value

    except (
        TypeError,
        ValueError,
    ):

        return default


def format_money(
    value,
    decimals=2,
):
    value = safe_number(
        value
    )

    if value is None:
        return "N/A"

    return (
        f"${value:,.{decimals}f}"
    )


def format_large_number(
    value,
):
    value = safe_number(
        value
    )

    if value is None:
        return "N/A"

    if abs(value) >= 1_000_000_000_000:

        return (
            f"${value / 1_000_000_000_000:.2f}T"
        )

    if abs(value) >= 1_000_000_000:

        return (
            f"${value / 1_000_000_000:.2f}B"
        )

    if abs(value) >= 1_000_000:

        return (
            f"${value / 1_000_000:.2f}M"
        )

    return (
        f"${value:,.0f}"
    )


def format_percent(
    value,
    signed=True,
):
    value = safe_number(
        value
    )

    if value is None:
        return "N/A"

    if signed:

        return (
            f"{value * 100:+.1f}%"
        )

    return (
        f"{value * 100:.1f}%"
    )


def format_ratio(
    value,
):
    value = safe_number(
        value
    )

    if value is None:
        return "N/A"

    return (
        f"{value:.1f}"
    )


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


def escape_text(
    value,
):
    if value is None:
        return ""

    return html.escape(
        str(value)
    )


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    series,
    period=14,
):

    delta = series.diff()

    gains = delta.clip(
        lower=0
    )

    losses = (
        -delta.clip(
            upper=0
        )
    )

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

    rs = (
        average_gain
        /
        average_loss
    )

    return (

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


# ============================================================
# TECHNICAL ANALYSIS
# ============================================================

def analyze_technical(
    history,
):

    close = history[
        "Close"
    ]

    price = float(
        close.iloc[-1]
    )

    ma20_series = (
        close
        .rolling(20)
        .mean()
    )

    ma50_series = (
        close
        .rolling(50)
        .mean()
    )

    ma200_series = (
        close
        .rolling(200)
        .mean()
    )

    ma20 = float(
        ma20_series.iloc[-1]
    )

    ma50 = float(
        ma50_series.iloc[-1]
    )

    ma200 = float(
        ma200_series.iloc[-1]
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

    macd_series = (
        ema12
        -
        ema26
    )

    macd_signal_series = (
        macd_series
        .ewm(
            span=9,
            adjust=False,
        )
        .mean()
    )

    macd = float(
        macd_series.iloc[-1]
    )

    macd_signal = float(
        macd_signal_series.iloc[-1]
    )

    score = 0

    reasons = []


    if price > ma20:

        score += 15

        reasons.append(
            "Price is above the 20-day moving average."
        )

    else:

        reasons.append(
            "Price is below the 20-day moving average."
        )


    if price > ma50:

        score += 20

        reasons.append(
            "Price is above the 50-day moving average."
        )

    else:

        reasons.append(
            "Price is below the 50-day moving average."
        )


    if price > ma200:

        score += 25

        reasons.append(
            "The long-term trend remains above the 200-day moving average."
        )

    else:

        reasons.append(
            "Price is below the 200-day moving average."
        )


    if ma50 > ma200:

        score += 10

        reasons.append(
            "The 50-day average remains above the 200-day average."
        )

    else:

        reasons.append(
            "The medium-term trend is below the long-term trend."
        )


    if macd > macd_signal:

        score += 15

        reasons.append(
            "MACD momentum is bullish."
        )

    else:

        reasons.append(
            "MACD momentum is bearish."
        )


    if 40 <= rsi <= 65:

        score += 15

        reasons.append(
            "RSI is in a healthy momentum range."
        )

    elif rsi < 30:

        score += 10

        reasons.append(
            "RSI indicates oversold conditions."
        )

    elif 30 <= rsi < 40:

        score += 8

        reasons.append(
            "RSI is weak but approaching oversold territory."
        )

    elif 65 < rsi <= 75:

        score += 8

        reasons.append(
            "RSI shows strong momentum but is becoming elevated."
        )

    else:

        reasons.append(
            "RSI is at an extreme level."
        )


    score = clamp(
        round(score)
    )


    return {

        "price":
            price,

        "ma20":
            ma20,

        "ma50":
            ma50,

        "ma200":
            ma200,

        "rsi":
            rsi,

        "macd":
            macd,

        "macd_signal":
            macd_signal,

        "score":
            score,

        "reasons":
            reasons,

        "ma20_series":
            ma20_series,

        "ma50_series":
            ma50_series,

        "ma200_series":
            ma200_series,

    }


# ============================================================
# MOMENTUM
# ============================================================

def calculate_return(
    close,
    trading_days,
):

    if len(
        close
    ) <= trading_days:

        return None


    start = float(
        close.iloc[
            -trading_days - 1
        ]
    )

    end = float(
        close.iloc[-1]
    )


    return (

        end
        /
        start

    ) - 1


def analyze_momentum(
    history,
):

    close = history[
        "Close"
    ]


    week_1 = calculate_return(
        close,
        5,
    )

    month_1 = calculate_return(
        close,
        21,
    )

    month_3 = calculate_return(
        close,
        63,
    )

    month_6 = calculate_return(
        close,
        126,
    )


    return {

        "week_1":
            week_1,

        "month_1":
            month_1,

        "month_3":
            month_3,

        "month_6":
            month_6,

    }


# ============================================================
# FUNDAMENTAL DATA
# ============================================================

def analyze_fundamentals(
    info,
):

    return {

        "market_cap":

            safe_number(
                info.get(
                    "marketCap"
                )
            ),


        "trailing_pe":

            safe_number(
                info.get(
                    "trailingPE"
                )
            ),


        "forward_pe":

            safe_number(
                info.get(
                    "forwardPE"
                )
            ),


        "price_to_book":

            safe_number(
                info.get(
                    "priceToBook"
                )
            ),


        "price_to_sales":

            safe_number(
                info.get(
                    "priceToSalesTrailing12Months"
                )
            ),


        "peg_ratio":

            safe_number(
                info.get(
                    "pegRatio"
                )
            ),


        "eps":

            safe_number(
                info.get(
                    "trailingEps"
                )
            ),


        "forward_eps":

            safe_number(
                info.get(
                    "forwardEps"
                )
            ),


        "revenue_growth":

            safe_number(
                info.get(
                    "revenueGrowth"
                )
            ),


        "earnings_growth":

            safe_number(
                info.get(
                    "earningsGrowth"
                )
            ),


        "gross_margin":

            safe_number(
                info.get(
                    "grossMargins"
                )
            ),


        "operating_margin":

            safe_number(
                info.get(
                    "operatingMargins"
                )
            ),


        "profit_margin":

            safe_number(
                info.get(
                    "profitMargins"
                )
            ),


        "return_on_equity":

            safe_number(
                info.get(
                    "returnOnEquity"
                )
            ),


        "debt_to_equity":

            safe_number(
                info.get(
                    "debtToEquity"
                )
            ),


        "current_ratio":

            safe_number(
                info.get(
                    "currentRatio"
                )
            ),

    }


# ============================================================
# ANALYST DATA
# ============================================================

def analyze_analysts(
    info,
    price,
):

    mean_target = safe_number(
        info.get(
            "targetMeanPrice"
        )
    )


    high_target = safe_number(
        info.get(
            "targetHighPrice"
        )
    )


    low_target = safe_number(
        info.get(
            "targetLowPrice"
        )
    )


    recommendation = (
        info.get(
            "recommendationKey"
        )
        or
        "N/A"
    )


    recommendation = (

        recommendation
        .replace(
            "_",
            " ",
        )
        .upper()

    )


    analyst_count = info.get(
        "numberOfAnalystOpinions"
    )


    upside = None


    if (

        mean_target is not None

        and

        price > 0

    ):

        upside = (

            mean_target
            /
            price

        ) - 1


    return {

        "mean_target":
            mean_target,

        "high_target":
            high_target,

        "low_target":
            low_target,

        "recommendation":
            recommendation,

        "analyst_count":
            analyst_count,

        "upside":
            upside,

    }


# ============================================================
# NEWS
# ============================================================

def get_news(
    stock,
):

    results = []


    try:

        raw_news = (
            stock.news
            or
            []
        )

    except Exception:

        raw_news = []


    for item in raw_news[
        :12
    ]:

        content = item.get(
            "content",
            item,
        )


        title = (
            content.get(
                "title"
            )
            or
            ""
        )


        provider = (
            content.get(
                "provider"
            )
            or
            {}
        )


        publisher = (
            provider.get(
                "displayName"
            )
            or
            ""
        )


        canonical_url = (
            content.get(
                "canonicalUrl"
            )
            or
            {}
        )


        url = (
            canonical_url.get(
                "url"
            )
            or
            "#"
        )


        if title:

            results.append({

                "title":
                    title,

                "publisher":
                    publisher,

                "url":
                    url,

            })


    return results


# ============================================================
# MICRON NEWS INTELLIGENCE
# ============================================================

def classify_news(
    news_items,
):

    categories = {

        "HBM & AI":
            [],

        "DRAM":
            [],

        "NAND":
            [],

        "Earnings & Outlook":
            [],

        "Company Developments":
            [],

    }


    for item in news_items:

        title = (
            item[
                "title"
            ]
            .lower()
        )


        assigned = False


        if any(

            word in title

            for word

            in [

                "hbm",

                "high bandwidth",

                "ai",

                "data center",

                "datacenter",

                "nvidia",

                "accelerator",

            ]

        ):

            categories[
                "HBM & AI"
            ].append(
                item
            )

            assigned = True


        if any(

            word in title

            for word

            in [

                "dram",

                "memory price",

                "memory pricing",

            ]

        ):

            categories[
                "DRAM"
            ].append(
                item
            )

            assigned = True


        if "nand" in title:

            categories[
                "NAND"
            ].append(
                item
            )

            assigned = True


        if any(

            word in title

            for word

            in [

                "earnings",

                "revenue",

                "profit",

                "guidance",

                "forecast",

                "outlook",

                "quarter",

                "results",

            ]

        ):

            categories[
                "Earnings & Outlook"
            ].append(
                item
            )

            assigned = True


        if not assigned:

            categories[
                "Company Developments"
            ].append(
                item
            )


    return categories


# ============================================================
# CHART
# ============================================================

def create_chart(
    history,
    technical,
):

    plt.figure(
        figsize=(
            12,
            5.2,
        )
    )


    plt.plot(

        history.index,

        history[
            "Close"
        ],

        linewidth=2,

        label="MU Price",

    )


    plt.plot(

        history.index,

        technical[
            "ma20_series"
        ],

        linewidth=1,

        label="20 Day MA",

    )


    plt.plot(

        history.index,

        technical[
            "ma50_series"
        ],

        linewidth=1,

        label="50 Day MA",

    )


    plt.plot(

        history.index,

        technical[
            "ma200_series"
        ],

        linewidth=1,

        label="200 Day MA",

    )


    plt.title(
        "Micron Technology · 1 Year Price Trend"
    )


    plt.ylabel(
        "Price (USD)"
    )


    plt.legend()


    plt.grid(
        alpha=0.2
    )


    plt.tight_layout()


    buffer = io.BytesIO()


    plt.savefig(

        buffer,

        format="png",

        dpi=140,

    )


    plt.close()


    buffer.seek(
        0
    )


    return (

        base64
        .b64encode(
            buffer.read()
        )
        .decode(
            "utf-8"
        )

    )


# ============================================================
# SCORE DESCRIPTION
# ============================================================

def score_description(
    score,
):

    if score >= 80:
        return "STRONG"

    if score >= 65:
        return "POSITIVE"

    if score >= 50:
        return "NEUTRAL"

    if score >= 35:
        return "WEAK"

    return "VERY WEAK"


# ============================================================
# INVESTMENT COMMENTARY
# ============================================================

def create_investment_view(
    technical,
    fundamentals,
    analysts,
):

    bull_points = []

    bear_points = []


    if (

        technical[
            "price"
        ]

        >

        technical[
            "ma200"
        ]

    ):

        bull_points.append(

            "The longer-term price trend remains above "
            "the 200-day moving average."

        )

    else:

        bear_points.append(

            "The share price is below its "
            "200-day moving average."

        )


    if technical[
        "rsi"
    ] < 30:

        bull_points.append(

            "The stock is currently oversold on RSI, "
            "creating potential for a technical rebound."

        )


    if (

        technical[
            "macd"
        ]

        >

        technical[
            "macd_signal"
        ]

    ):

        bull_points.append(

            "MACD currently supports improving "
            "short-term momentum."

        )

    else:

        bear_points.append(

            "MACD remains bearish and indicates "
            "weak near-term momentum."

        )


    revenue_growth = fundamentals[
        "revenue_growth"
    ]


    if revenue_growth is not None:

        if revenue_growth > 0.20:

            bull_points.append(
                "Revenue growth remains strong."
            )

        elif revenue_growth < 0:

            bear_points.append(
                "Revenue growth is currently negative."
            )


    earnings_growth = fundamentals[
        "earnings_growth"
    ]


    if earnings_growth is not None:

        if earnings_growth > 0.20:

            bull_points.append(
                "Earnings growth remains strong."
            )

        elif earnings_growth < 0:

            bear_points.append(
                "Recent earnings growth is negative."
            )


    gross_margin = fundamentals[
        "gross_margin"
    ]


    if gross_margin is not None:

        if gross_margin >= 0.40:

            bull_points.append(
                "Gross margins are at a healthy level."
            )

        elif gross_margin < 0.25:

            bear_points.append(
                "Gross margins remain relatively weak."
            )


    forward_pe = fundamentals[
        "forward_pe"
    ]


    if forward_pe is not None:

        if forward_pe <= 18:

            bull_points.append(

                "Forward valuation appears reasonable "
                "relative to expected earnings."

            )

        elif forward_pe > 35:

            bear_points.append(

                "The forward valuation appears demanding."

            )


    analyst_upside = analysts[
        "upside"
    ]


    if analyst_upside is not None:

        if analyst_upside > 0.20:

            bull_points.append(

                "The analyst consensus target indicates "
                "significant potential upside."

            )

        elif analyst_upside < -0.10:

            bear_points.append(

                "The share price is above the current "
                "analyst consensus target."

            )


    watch_points = [

        (
            "HBM demand and Micron's ability to increase "
            "high-bandwidth memory supply."
        ),

        (
            "Micron's competitive position in HBM relative "
            "to SK hynix and Samsung."
        ),

        (
            "DRAM contract pricing and overall memory "
            "industry supply discipline."
        ),

        (
            "NAND pricing and demand recovery."
        ),

        (
            "AI data-center capital spending by major "
            "hyperscale customers."
        ),

        (
            "Gross margin improvement and manufacturing "
            "cost reductions."
        ),

        (
            "Customer concentration and changes in demand "
            "from major AI accelerator platforms."
        ),

        (
            "Future earnings guidance and analyst earnings "
            "estimate revisions."
        ),

    ]


    if not bull_points:

        bull_points.append(

            "No major quantitative bull factor is "
            "currently strong enough to highlight."

        )


    if not bear_points:

        bear_points.append(

            "No major quantitative bear factor is "
            "currently strong enough to highlight."

        )


    return {

        "bull_points":
            bull_points,

        "bear_points":
            bear_points,

        "watch_points":
            watch_points,

    }


# ============================================================
# HTML HELPERS
# ============================================================

def bullet_list(
    items,
):

    return "".join(

        f"""
        <li>
            {escape_text(item)}
        </li>
        """

        for item

        in items

    )


def news_cards(
    news_items,
):

    if not news_items:

        return """

        <div class="muted">
            No relevant headlines were returned.
        </div>

        """


    output = ""


    for item in news_items[
        :8
    ]:

        output += f"""

        <a
            class="news-item"
            href="{escape_text(item["url"])}"
            target="_blank"
            rel="noopener noreferrer"
        >

            <div class="news-title">
                {escape_text(item["title"])}
            </div>

            <div class="news-publisher">
                {escape_text(item["publisher"])}
            </div>

        </a>

        """


    return output


def intelligence_cards(
    categories,
):

    output = ""


    for (
        category,
        items,
    ) in categories.items():


        output += f"""

        <div class="intelligence-card">

            <div class="intelligence-title">
                {escape_text(category)}
            </div>

        """


        if not items:

            output += """

            <div class="muted small">
                No major headline detected.
            </div>

            """


        else:

            for item in items[
                :3
            ]:

                output += f"""

                <a
                    class="intelligence-link"
                    href="{escape_text(item["url"])}"
                    target="_blank"
                    rel="noopener noreferrer"
                >

                    {escape_text(item["title"])}

                </a>

                """


        output += """

        </div>

        """


    return output


def score_component_rows(
    components,
):

    if not components:

        return """

        <div class="muted">
            Fundamental component data is currently unavailable.
        </div>

        """


    output = ""


    for (
        name,
        score,
    ) in components.items():


        display_score = (

            "N/A"

            if score is None

            else score

        )


        output += f"""

        <div class="component-row">

            <span>
                {escape_text(name)}
            </span>

            <strong>
                {display_score}
            </strong>

        </div>

        """


    return output


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Downloading Micron market data..."
    )


    stock = yf.Ticker(
        TICKER
    )


    history = stock.history(

        period="1y",

        interval="1d",

        auto_adjust=False,

    )


    if history.empty:

        raise RuntimeError(
            "No market data returned for MU."
        )


    info = (
        stock.info
        or
        {}
    )


    # ========================================================
    # SHARED SECTOR-SPECIFIC SCORING ENGINE
    #
    # Micron is scored using the Semiconductor model:
    #
    # Technical      20%
    # Momentum       25%
    # Fundamentals   40%
    # Valuation      15%
    # ========================================================

    shared_technical, shared_rsi = (
        shared_technical_score(
            history
        )
    )


    shared_momentum = (
        shared_momentum_score(
            history
        )
    )


    shared_fundamental_data = (
        shared_fundamental_score(

            info,

            sector=SECTOR,

        )
    )


    shared_fundamental = (
        shared_fundamental_data[
            "score"
        ]
    )


    shared_valuation = (
        shared_valuation_score(

            info,

            sector=SECTOR,

        )
    )


    shared_overall = (
        shared_overall_score(

            shared_technical,

            shared_momentum,

            shared_fundamental,

            shared_valuation,

            sector=SECTOR,

        )
    )


    shared_overall_rating = (
        shared_rating(
            shared_overall
        )
    )


    # ========================================================
    # DETAILED MICRON ANALYSIS
    # ========================================================

    technical = analyze_technical(
        history
    )


    momentum = analyze_momentum(
        history
    )


    fundamentals = analyze_fundamentals(
        info
    )


    analysts = analyze_analysts(

        info,

        technical[
            "price"
        ],

    )


    news_items = get_news(
        stock
    )


    news_categories = classify_news(
        news_items
    )


    investment_view = create_investment_view(

        technical,

        fundamentals,

        analysts,

    )


    chart_base64 = create_chart(

        history,

        technical,

    )


    # ========================================================
    # USE SHARED SCORES
    # ========================================================

    technical[
        "score"
    ] = shared_technical


    momentum[
        "score"
    ] = shared_momentum


    fundamentals[
        "score"
    ] = shared_fundamental


    fundamentals[
        "components"
    ] = shared_fundamental_data[
        "components"
    ]


    fundamentals[
        "data_quality"
    ] = shared_fundamental_data[
        "data_quality"
    ]


    overall_score = (
        shared_overall
    )


    overall_rating = (
        shared_overall_rating
    )


    # Short-term view:
    # technical + momentum.

    short_term_score = round(

        shared_technical
        * 0.65

        +

        shared_momentum
        * 0.35

    )


    short_term_rating = (
        shared_rating(
            short_term_score
        )
    )


    # Long-term view:
    # semiconductor fundamentals,
    # valuation and technical trend.

    long_term_score = round(

        shared_fundamental
        * 0.65

        +

        shared_valuation
        * 0.25

        +

        shared_technical
        * 0.10

    )


    long_term_rating = (
        shared_rating(
            long_term_score
        )
    )


    close = history[
        "Close"
    ]


    price = float(
        close.iloc[-1]
    )


    previous_close = float(
        close.iloc[-2]
    )


    daily_change = (
        price
        -
        previous_close
    )


    daily_change_pct = (

        daily_change

        /

        previous_close

        *

        100

    )


    low_52 = float(
        history[
            "Low"
        ].min()
    )


    high_52 = float(
        history[
            "High"
        ].max()
    )


    recent_60 = history.tail(
        60
    )


    support = float(
        recent_60[
            "Low"
        ].min()
    )


    resistance = float(
        recent_60[
            "High"
        ].max()
    )


    updated = datetime.now(

        ZoneInfo(
            "Asia/Singapore"
        )

    ).strftime(

        "%d %B %Y, %H:%M SGT"

    )


    price_change_class = (

        "positive"

        if daily_change >= 0

        else

        "negative"

    )


    page = f"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
V Stock Intelligence · Micron
</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: #07111f;
    color: #edf4ff;
    font-family: Arial, Helvetica, sans-serif;
}}

.container {{
    width: min(1220px, 94%);
    margin: auto;
    padding: 30px 0 60px;
}}

.back {{
    color: #68b9ff;
    text-decoration: none;
    font-size: 13px;
}}

.header {{
    margin-top: 25px;
}}

.title {{
    font-size: 38px;
    font-weight: 800;
}}

.subtitle {{
    color: #8ca5c4;
    margin-top: 6px;
}}

.card {{
    background: #111e31;
    border: 1px solid #263c5b;
    border-radius: 16px;
    padding: 22px;
}}

.section {{
    margin-top: 20px;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(200px, 1fr));
    gap: 14px;
}}

.hero {{
    margin-top: 24px;
}}

.metric {{
    background: #0b1728;
    border-radius: 12px;
    padding: 18px;
}}

.label {{
    color: #8ba4c3;
    font-size: 11px;
    text-transform: uppercase;
}}

.big {{
    font-size: 32px;
    font-weight: 800;
    margin-top: 8px;
}}

.section-title {{
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 16px;
}}

.small {{
    font-size: 12px;
}}

.muted {{
    color: #8ca5c4;
}}

.positive {{
    color: #51e0a0;
}}

.negative {{
    color: #ff7183;
}}

.model-badge {{
    display: inline-block;
    margin-top: 10px;
    padding: 6px 9px;
    border-radius: 7px;
    background: rgba(86,184,255,0.15);
    color: #66bdff;
    font-size: 11px;
    font-weight: 800;
}}

.score-grid {{
    display: grid;
    grid-template-columns:
        repeat(4, 1fr);
    gap: 14px;
}}

.score-number {{
    font-size: 28px;
    font-weight: 800;
    margin-top: 8px;
}}

.score-description {{
    margin-top: 6px;
    color: #7f99b9;
    font-size: 12px;
}}

.chart {{
    width: 100%;
    border-radius: 12px;
    display: block;
}}

.component-row {{
    display: flex;
    justify-content: space-between;
    gap: 15px;
    padding: 10px 0;
    border-bottom: 1px solid #243850;
    color: #a9bdd4;
    font-size: 13px;
}}

.component-row:last-child {{
    border-bottom: none;
}}

.intelligence-grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
}}

.intelligence-card {{
    background: #0b1728;
    border-radius: 12px;
    padding: 16px;
}}

.intelligence-title {{
    font-weight: 800;
    margin-bottom: 10px;
}}

.intelligence-link {{
    display: block;
    color: #9fc7ed;
    text-decoration: none;
    padding: 8px 0;
    font-size: 12px;
    line-height: 1.4;
    border-bottom: 1px solid #223650;
}}

.news-item {{
    display: block;
    text-decoration: none;
    color: inherit;
    padding: 13px 0;
    border-bottom: 1px solid #263a55;
}}

.news-title {{
    font-weight: 700;
}}

.news-publisher {{
    color: #718baa;
    font-size: 11px;
    margin-top: 5px;
}}

ul {{
    margin: 0;
    padding-left: 20px;
}}

li {{
    margin: 9px 0;
    color: #b2c4d8;
    line-height: 1.5;
}}

.footer {{
    text-align: center;
    color: #6f88a8;
    margin-top: 30px;
    font-size: 12px;
    line-height: 1.6;
}}

@media (
    max-width: 800px
) {{

    .score-grid {{
        grid-template-columns:
            repeat(2, 1fr);
    }}

}}

@media (
    max-width: 520px
) {{

    .score-grid {{
        grid-template-columns:
            1fr;
    }}

}}

</style>

</head>

<body>

<div class="container">


<a
    class="back"
    href="../"
>
    ← Back to Market Dashboard
</a>


<div class="header">

    <div class="title">
        V Stock Intelligence
    </div>

    <div class="subtitle">
        Micron Technology · NASDAQ: MU
    </div>

    <div class="model-badge">
        Scoring Model: Semiconductor
    </div>

</div>


<div class="grid hero">


<div class="card">

    <div class="label">
        Current Price
    </div>

    <div class="big">
        {format_money(price)}
    </div>

    <div class="{price_change_class}">

        {daily_change:+,.2f}

        (

        {daily_change_pct:+.2f}%

        )

    </div>

</div>


<div class="card">

    <div class="label">
        Overall Investment View
    </div>

    <div class="big">
        {overall_score}/100
    </div>

    <div>
        {overall_rating}
    </div>

</div>


<div class="card">

    <div class="label">
        Analyst Consensus
    </div>

    <div class="big">
        {escape_text(
            analysts["recommendation"]
        )}
    </div>

    <div class="muted">

        Target:

        {format_money(
            analysts["mean_target"]
        )}

    </div>

</div>


<div class="card">

    <div class="label">
        Analyst Target Upside
    </div>

    <div class="big">

        {format_percent(
            analysts["upside"]
        )}

    </div>

    <div class="muted">
        Consensus price target
    </div>

</div>


</div>


<div class="card section">

    <div class="section-title">
        Investment Time Horizon
    </div>

    <div class="grid">


        <div class="metric">

            <div class="label">
                Short-Term View
            </div>

            <div class="big">
                {short_term_score}/100
            </div>

            <div>
                {short_term_rating}
            </div>

            <div class="score-description">
                Technical + price momentum
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Long-Term Investment View
            </div>

            <div class="big">
                {long_term_score}/100
            </div>

            <div>
                {long_term_rating}
            </div>

            <div class="score-description">
                Semiconductor fundamentals + valuation + trend
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Overall View
            </div>

            <div class="big">
                {overall_score}/100
            </div>

            <div>
                {overall_rating}
            </div>

            <div class="score-description">
                Same Semiconductor model as the market dashboard
            </div>

        </div>


    </div>

</div>


<div class="card section">

    <div class="section-title">
        Core Investment Scores
    </div>

    <div class="score-grid">


        <div class="metric">

            <div class="label">
                Technical · 20%
            </div>

            <div class="score-number">
                {shared_technical}/100
            </div>

            <div class="score-description">

                {score_description(
                    shared_technical
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Momentum · 25%
            </div>

            <div class="score-number">
                {shared_momentum}/100
            </div>

            <div class="score-description">

                {score_description(
                    shared_momentum
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Fundamentals · 40%
            </div>

            <div class="score-number">
                {shared_fundamental}/100
            </div>

            <div class="score-description">

                {score_description(
                    shared_fundamental
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Valuation · 15%
            </div>

            <div class="score-number">
                {shared_valuation}/100
            </div>

            <div class="score-description">

                {score_description(
                    shared_valuation
                )}

            </div>

        </div>


    </div>

</div>


<div class="card section">

    <div class="section-title">
        Micron Intelligence
    </div>

    <div class="intelligence-grid">

        {intelligence_cards(
            news_categories
        )}

    </div>

</div>


<div class="card section">

    <div class="section-title">
        Micron Price Trend
    </div>

    <img
        class="chart"
        src="
            data:image/png;base64,
            {chart_base64}
        "
        alt="
            Micron one-year price chart
        "
    >

</div>


<div class="card section">

    <div class="section-title">
        Fundamental Snapshot
    </div>

    <div class="grid">


        <div class="metric">

            <div class="label">
                Market Cap
            </div>

            <div class="score-number">
                {format_large_number(
                    fundamentals["market_cap"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Forward P/E
            </div>

            <div class="score-number">
                {format_ratio(
                    fundamentals["forward_pe"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                PEG Ratio
            </div>

            <div class="score-number">
                {format_ratio(
                    fundamentals["peg_ratio"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Price / Sales
            </div>

            <div class="score-number">
                {format_ratio(
                    fundamentals["price_to_sales"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Revenue Growth
            </div>

            <div class="score-number">
                {format_percent(
                    fundamentals["revenue_growth"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Earnings Growth
            </div>

            <div class="score-number">
                {format_percent(
                    fundamentals["earnings_growth"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Gross Margin
            </div>

            <div class="score-number">

                {format_percent(

                    fundamentals[
                        "gross_margin"
                    ],

                    signed=False,

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Operating Margin
            </div>

            <div class="score-number">

                {format_percent(

                    fundamentals[
                        "operating_margin"
                    ],

                    signed=False,

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Return on Equity
            </div>

            <div class="score-number">

                {format_percent(

                    fundamentals[
                        "return_on_equity"
                    ],

                    signed=False,

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Debt / Equity
            </div>

            <div class="score-number">

                {format_ratio(
                    fundamentals[
                        "debt_to_equity"
                    ]
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Current Ratio
            </div>

            <div class="score-number">

                {format_ratio(
                    fundamentals[
                        "current_ratio"
                    ]
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Price / Book
            </div>

            <div class="score-number">

                {format_ratio(
                    fundamentals[
                        "price_to_book"
                    ]
                )}

            </div>

        </div>


    </div>

</div>


<div class="card section">

    <div class="section-title">
        Semiconductor Fundamental Score Breakdown
    </div>

    {score_component_rows(
        fundamentals[
            "components"
        ]
    )}

</div>


<div class="card section">

    <div class="section-title">
        Technical & Momentum
    </div>

    <div class="grid">


        <div class="metric">

            <div class="label">
                RSI
            </div>

            <div class="score-number">
                {technical["rsi"]:.1f}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                20 Day MA
            </div>

            <div class="score-number">
                {format_money(
                    technical["ma20"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                50 Day MA
            </div>

            <div class="score-number">
                {format_money(
                    technical["ma50"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                200 Day MA
            </div>

            <div class="score-number">
                {format_money(
                    technical["ma200"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                1 Week
            </div>

            <div class="score-number">

                {format_percent(
                    momentum["week_1"]
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                1 Month
            </div>

            <div class="score-number">

                {format_percent(
                    momentum["month_1"]
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                3 Months
            </div>

            <div class="score-number">

                {format_percent(
                    momentum["month_3"]
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                6 Months
            </div>

            <div class="score-number">

                {format_percent(
                    momentum["month_6"]
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Support
            </div>

            <div class="score-number">
                {format_money(
                    support
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Resistance
            </div>

            <div class="score-number">
                {format_money(
                    resistance
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                52 Week Low
            </div>

            <div class="score-number">
                {format_money(
                    low_52
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                52 Week High
            </div>

            <div class="score-number">
                {format_money(
                    high_52
                )}
            </div>

        </div>


    </div>

</div>


<div class="grid section">


<div class="card">

    <div class="section-title">
        Bull Case
    </div>

    <ul>

        {bullet_list(
            investment_view[
                "bull_points"
            ]
        )}

    </ul>

</div>


<div class="card">

    <div class="section-title">
        Bear Case
    </div>

    <ul>

        {bullet_list(
            investment_view[
                "bear_points"
            ]
        )}

    </ul>

</div>


</div>


<div class="card section">

    <div class="section-title">
        What I Would Watch
    </div>

    <ul>

        {bullet_list(
            investment_view[
                "watch_points"
            ]
        )}

    </ul>

</div>


<div class="card section">

    <div class="section-title">
        Latest Micron Headlines
    </div>

    {news_cards(
        news_items
    )}

</div>


<div class="footer">

    This report uses the Semiconductor-specific
    V Stock Intelligence scoring model.

    <br>

    Technical 20% · Momentum 25% ·
    Fundamentals 40% · Valuation 15%.

    <br><br>

    Analyst targets are displayed for information
    but do not determine the dashboard score.

    <br><br>

    Last updated:
    {updated}

</div>


</div>

</body>

</html>
"""


    output_folder = Path(
        "docs"
    )


    output_folder.mkdir(
        exist_ok=True
    )


    output_file = (
        output_folder
        /
        "index.html"
    )


    output_file.write_text(

        page,

        encoding="utf-8",

    )


    print(

        "Micron investment dashboard "
        "generated successfully."

    )


    print(

        f"Semiconductor model overall score: "

        f"{overall_score}/100 "

        f"{overall_rating}"

    )


if __name__ == "__main__":

    main()
