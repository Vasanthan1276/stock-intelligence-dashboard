import base64
import html
import io
import math
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf


TICKER = "MU"
COMPANY_NAME = "Micron Technology"


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_number(value, default=None):
    try:
        if value is None:
            return default

        value = float(value)

        if math.isnan(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def format_money(value, decimals=2):
    value = safe_number(value)

    if value is None:
        return "N/A"

    return f"${value:,.{decimals}f}"


def format_large_number(value):
    value = safe_number(value)

    if value is None:
        return "N/A"

    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"

    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"

    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    return f"${value:,.0f}"


def format_percent(value, signed=True):
    value = safe_number(value)

    if value is None:
        return "N/A"

    if signed:
        return f"{value * 100:+.1f}%"

    return f"{value * 100:.1f}%"


def format_ratio(value):
    value = safe_number(value)

    if value is None:
        return "N/A"

    return f"{value:.1f}"


def clamp(value, minimum=0, maximum=100):
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def escape_text(value):
    if value is None:
        return ""

    return html.escape(
        str(value)
    )


# ============================================================
# RSI
# ============================================================

def calculate_rsi(series, period=14):
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
        / average_loss
    )

    return (
        100
        - (
            100
            / (
                1 + rs
            )
        )
    )


# ============================================================
# TECHNICAL ANALYSIS
# ============================================================

def analyze_technical(history):
    close = history["Close"]

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
        - ema26
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
        "price": price,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "score": score,
        "reasons": reasons,
        "ma20_series": ma20_series,
        "ma50_series": ma50_series,
        "ma200_series": ma200_series,
    }


# ============================================================
# MOMENTUM
# ============================================================

def calculate_return(close, trading_days):
    if len(close) <= trading_days:
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
        end / start
    ) - 1


def analyze_momentum(history):
    close = history["Close"]

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

    score = 50

    weighted_returns = [
        (
            week_1,
            10,
        ),
        (
            month_1,
            20,
        ),
        (
            month_3,
            30,
        ),
        (
            month_6,
            40,
        ),
    ]

    score = 0

    for value, weight in weighted_returns:
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

    score = clamp(
        round(score)
    )

    return {
        "week_1": week_1,
        "month_1": month_1,
        "month_3": month_3,
        "month_6": month_6,
        "score": score,
    }


# ============================================================
# FUNDAMENTAL ANALYSIS
# ============================================================

def analyze_fundamentals(info):
    values = {
        "market_cap": safe_number(
            info.get(
                "marketCap"
            )
        ),

        "trailing_pe": safe_number(
            info.get(
                "trailingPE"
            )
        ),

        "forward_pe": safe_number(
            info.get(
                "forwardPE"
            )
        ),

        "price_to_book": safe_number(
            info.get(
                "priceToBook"
            )
        ),

        "eps": safe_number(
            info.get(
                "trailingEps"
            )
        ),

        "forward_eps": safe_number(
            info.get(
                "forwardEps"
            )
        ),

        "revenue_growth": safe_number(
            info.get(
                "revenueGrowth"
            )
        ),

        "earnings_growth": safe_number(
            info.get(
                "earningsGrowth"
            )
        ),

        "gross_margin": safe_number(
            info.get(
                "grossMargins"
            )
        ),

        "operating_margin": safe_number(
            info.get(
                "operatingMargins"
            )
        ),

        "profit_margin": safe_number(
            info.get(
                "profitMargins"
            )
        ),

        "return_on_equity": safe_number(
            info.get(
                "returnOnEquity"
            )
        ),

        "debt_to_equity": safe_number(
            info.get(
                "debtToEquity"
            )
        ),

        "current_ratio": safe_number(
            info.get(
                "currentRatio"
            )
        ),
    }

    components = {}

    # ------------------------------------------
    # Revenue growth: 15 points
    # ------------------------------------------

    revenue_growth = values[
        "revenue_growth"
    ]

    if revenue_growth is None:
        components[
            "Revenue Growth"
        ] = 7

    elif revenue_growth >= 0.40:
        components[
            "Revenue Growth"
        ] = 15

    elif revenue_growth >= 0.20:
        components[
            "Revenue Growth"
        ] = 13

    elif revenue_growth >= 0.10:
        components[
            "Revenue Growth"
        ] = 10

    elif revenue_growth > 0:
        components[
            "Revenue Growth"
        ] = 7

    else:
        components[
            "Revenue Growth"
        ] = 2


    # ------------------------------------------
    # Earnings growth: 15 points
    # ------------------------------------------

    earnings_growth = values[
        "earnings_growth"
    ]

    if earnings_growth is None:
        components[
            "Earnings Growth"
        ] = 7

    elif earnings_growth >= 0.50:
        components[
            "Earnings Growth"
        ] = 15

    elif earnings_growth >= 0.25:
        components[
            "Earnings Growth"
        ] = 13

    elif earnings_growth >= 0.10:
        components[
            "Earnings Growth"
        ] = 10

    elif earnings_growth > 0:
        components[
            "Earnings Growth"
        ] = 7

    else:
        components[
            "Earnings Growth"
        ] = 2


    # ------------------------------------------
    # Forward valuation: 15 points
    # ------------------------------------------

    forward_pe = values[
        "forward_pe"
    ]

    if forward_pe is None:
        components[
            "Forward Valuation"
        ] = 7

    elif 0 < forward_pe <= 12:
        components[
            "Forward Valuation"
        ] = 15

    elif forward_pe <= 18:
        components[
            "Forward Valuation"
        ] = 13

    elif forward_pe <= 25:
        components[
            "Forward Valuation"
        ] = 10

    elif forward_pe <= 35:
        components[
            "Forward Valuation"
        ] = 6

    else:
        components[
            "Forward Valuation"
        ] = 2


    # ------------------------------------------
    # Gross margin: 15 points
    # ------------------------------------------

    gross_margin = values[
        "gross_margin"
    ]

    if gross_margin is None:
        components[
            "Gross Margin"
        ] = 7

    elif gross_margin >= 0.50:
        components[
            "Gross Margin"
        ] = 15

    elif gross_margin >= 0.40:
        components[
            "Gross Margin"
        ] = 13

    elif gross_margin >= 0.30:
        components[
            "Gross Margin"
        ] = 10

    elif gross_margin >= 0.20:
        components[
            "Gross Margin"
        ] = 7

    else:
        components[
            "Gross Margin"
        ] = 3


    # ------------------------------------------
    # Operating margin: 10 points
    # ------------------------------------------

    operating_margin = values[
        "operating_margin"
    ]

    if operating_margin is None:
        components[
            "Operating Margin"
        ] = 5

    elif operating_margin >= 0.30:
        components[
            "Operating Margin"
        ] = 10

    elif operating_margin >= 0.20:
        components[
            "Operating Margin"
        ] = 8

    elif operating_margin >= 0.10:
        components[
            "Operating Margin"
        ] = 6

    elif operating_margin > 0:
        components[
            "Operating Margin"
        ] = 4

    else:
        components[
            "Operating Margin"
        ] = 1


    # ------------------------------------------
    # ROE: 10 points
    # ------------------------------------------

    roe = values[
        "return_on_equity"
    ]

    if roe is None:
        components[
            "Return on Equity"
        ] = 5

    elif roe >= 0.25:
        components[
            "Return on Equity"
        ] = 10

    elif roe >= 0.15:
        components[
            "Return on Equity"
        ] = 8

    elif roe >= 0.08:
        components[
            "Return on Equity"
        ] = 6

    elif roe > 0:
        components[
            "Return on Equity"
        ] = 4

    else:
        components[
            "Return on Equity"
        ] = 1


    # ------------------------------------------
    # Debt: 10 points
    # Yahoo often reports D/E as percentage
    # ------------------------------------------

    debt_to_equity = values[
        "debt_to_equity"
    ]

    if debt_to_equity is None:
        components[
            "Balance Sheet"
        ] = 5

    elif debt_to_equity <= 30:
        components[
            "Balance Sheet"
        ] = 10

    elif debt_to_equity <= 60:
        components[
            "Balance Sheet"
        ] = 8

    elif debt_to_equity <= 100:
        components[
            "Balance Sheet"
        ] = 6

    elif debt_to_equity <= 150:
        components[
            "Balance Sheet"
        ] = 4

    else:
        components[
            "Balance Sheet"
        ] = 2


    # ------------------------------------------
    # Liquidity: 10 points
    # ------------------------------------------

    current_ratio = values[
        "current_ratio"
    ]

    if current_ratio is None:
        components[
            "Liquidity"
        ] = 5

    elif current_ratio >= 2:
        components[
            "Liquidity"
        ] = 10

    elif current_ratio >= 1.5:
        components[
            "Liquidity"
        ] = 8

    elif current_ratio >= 1:
        components[
            "Liquidity"
        ] = 6

    else:
        components[
            "Liquidity"
        ] = 2


    score = clamp(
        round(
            sum(
                components.values()
            )
        )
    )

    values[
        "score"
    ] = score

    values[
        "components"
    ] = components

    return values


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
        or "N/A"
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
        and price > 0
    ):
        upside = (
            mean_target
            / price
        ) - 1

    return {
        "mean_target": mean_target,
        "high_target": high_target,
        "low_target": low_target,
        "recommendation": recommendation,
        "analyst_count": analyst_count,
        "upside": upside,
    }


# ============================================================
# NEWS
# ============================================================

def get_news(stock):
    results = []

    try:
        raw_news = stock.news or []

    except Exception:
        raw_news = []

    for item in raw_news[:12]:
        content = item.get(
            "content",
            item,
        )

        title = (
            content.get(
                "title"
            )
            or ""
        )

        provider = (
            content.get(
                "provider"
            )
            or {}
        )

        publisher = (
            provider.get(
                "displayName"
            )
            or ""
        )

        canonical_url = (
            content.get(
                "canonicalUrl"
            )
            or {}
        )

        url = (
            canonical_url.get(
                "url"
            )
            or "#"
        )

        if title:
            results.append(
                {
                    "title": title,
                    "publisher": publisher,
                    "url": url,
                }
            )

    return results


# ============================================================
# MICRON NEWS INTELLIGENCE
# ============================================================

def classify_news(news_items):
    categories = {
        "HBM & AI": [],
        "DRAM": [],
        "NAND": [],
        "Earnings & Outlook": [],
        "Company Developments": [],
    }

    for item in news_items:
        title = (
            item["title"]
            .lower()
        )

        assigned = False

        if any(
            word in title
            for word in [
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
            for word in [
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
            for word in [
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
        history["Close"],
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

    buffer.seek(0)

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
# RATING HELPERS
# ============================================================

def rating_from_score(score):
    if score >= 80:
        return "STRONG BUY"

    if score >= 65:
        return "BUY"

    if score >= 50:
        return "HOLD"

    if score >= 35:
        return "WATCH"

    return "CAUTION"


def score_description(score):
    if score >= 80:
        return "STRONG"

    if score >= 65:
        return "POSITIVE"

    if score >= 50:
        return "NEUTRAL"

    if score >= 35:
        return "WEAK"

    return "VERY WEAK"


def get_short_term_view(
    technical_score,
    momentum_score,
):
    score = round(
        technical_score
        * 0.65
        +
        momentum_score
        * 0.35
    )

    return (
        score,
        rating_from_score(
            score
        ),
    )


def get_long_term_view(
    fundamental_score,
    analyst_upside,
    technical_score,
):
    analyst_score = 50

    if analyst_upside is not None:

        if analyst_upside >= 0.40:
            analyst_score = 90

        elif analyst_upside >= 0.20:
            analyst_score = 80

        elif analyst_upside >= 0.10:
            analyst_score = 70

        elif analyst_upside >= 0:
            analyst_score = 60

        elif analyst_upside >= -0.10:
            analyst_score = 40

        else:
            analyst_score = 25

    score = round(
        fundamental_score
        * 0.60
        +
        analyst_score
        * 0.25
        +
        technical_score
        * 0.15
    )

    return (
        score,
        rating_from_score(
            score
        ),
    )


def get_overall_view(
    short_term_score,
    long_term_score,
):
    score = round(
        short_term_score
        * 0.35
        +
        long_term_score
        * 0.65
    )

    return (
        score,
        rating_from_score(
            score
        ),
    )


# ============================================================
# INVESTMENT COMMENTARY
# ============================================================

def create_investment_view(
    technical,
    momentum,
    fundamentals,
    analysts,
):
    bull_points = []
    bear_points = []
    watch_points = []

    if technical["price"] > technical["ma200"]:
        bull_points.append(
            "The longer-term price trend remains above the 200-day moving average."
        )

    else:
        bear_points.append(
            "The share price is below its 200-day moving average."
        )

    if technical["rsi"] < 30:
        bull_points.append(
            "The stock is currently oversold on RSI, creating potential for a technical rebound."
        )

    if technical["macd"] > technical["macd_signal"]:
        bull_points.append(
            "MACD currently supports improving short-term momentum."
        )

    else:
        bear_points.append(
            "MACD remains bearish and indicates weak near-term momentum."
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
                "Forward valuation appears reasonable relative to expected earnings."
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
                "The analyst consensus target indicates significant potential upside."
            )

        elif analyst_upside < -0.10:
            bear_points.append(
                "The share price is above the current analyst consensus target."
            )

    watch_points = [
        "HBM demand and Micron's ability to increase high-bandwidth memory supply.",
        "Micron's competitive position in HBM relative to SK hynix and Samsung.",
        "DRAM contract pricing and overall memory industry supply discipline.",
        "NAND pricing and demand recovery.",
        "AI data-center capital spending by major hyperscale customers.",
        "Gross margin improvement and manufacturing cost reductions.",
        "Customer concentration and changes in demand from major AI accelerator platforms.",
        "Future earnings guidance and analyst earnings estimate revisions.",
    ]

    if not bull_points:
        bull_points.append(
            "No major quantitative bull factor is currently strong enough to highlight."
        )

    if not bear_points:
        bear_points.append(
            "No major quantitative bear factor is currently strong enough to highlight."
        )

    return {
        "bull_points": bull_points,
        "bear_points": bear_points,
        "watch_points": watch_points,
    }


# ============================================================
# HTML HELPERS
# ============================================================

def bullet_list(items):
    return "".join(
        f"<li>{escape_text(item)}</li>"
        for item in items
    )


def news_cards(news_items):
    if not news_items:
        return """
        <div class="muted">
            No relevant headlines were returned.
        </div>
        """

    output = ""

    for item in news_items[:8]:

        output += f"""
        <a
            class="news-item"
            href="{escape_text(item['url'])}"
            target="_blank"
            rel="noopener noreferrer"
        >

            <div class="news-title">
                {escape_text(item["title"])}
            </div>

            <div class="news-source">
                {escape_text(item["publisher"])}
            </div>

        </a>
        """

    return output


def intelligence_cards(categories):
    output = ""

    for category, items in categories.items():

        output += f"""
        <div class="intel-card">

            <div class="intel-title">
                {escape_text(category)}
            </div>
        """

        if not items:

            output += """
            <div class="muted">
                No major headline detected.
            </div>
            """

        else:

            for item in items[:3]:

                output += f"""
                <a
                    class="intel-item"
                    href="{escape_text(item['url'])}"
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


def score_component_rows(components):
    output = ""

    for name, score in components.items():

        output += f"""
        <div class="component-row">

            <div>
                {escape_text(name)}
            </div>

            <div class="component-score">
                {score}
            </div>

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

    info = stock.info or {}

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
        technical["price"],
    )

    news_items = get_news(
        stock
    )

    news_categories = classify_news(
        news_items
    )

    investment_view = create_investment_view(
        technical,
        momentum,
        fundamentals,
        analysts,
    )

    chart_base64 = create_chart(
        history,
        technical,
    )

    short_term_score, short_term_rating = (
        get_short_term_view(
            technical["score"],
            momentum["score"],
        )
    )

    long_term_score, long_term_rating = (
        get_long_term_view(
            fundamentals["score"],
            analysts["upside"],
            technical["score"],
        )
    )

    overall_score, overall_rating = (
        get_overall_view(
            short_term_score,
            long_term_score,
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
        - previous_close
    )

    daily_change_pct = (
        daily_change
        / previous_close
        * 100
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

    recent_60 = (
        history
        .tail(60)
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
        timezone.utc
    ).strftime(
        "%d %B %Y, %H:%M UTC"
    )

    price_change_class = (
        "positive"
        if daily_change >= 0
        else "negative"
    )

    html_page = f"""
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
    width: min(1280px, 94%);
    margin: 0 auto;
    padding: 28px 0 60px;
}}

.title {{
    font-size: 35px;
    font-weight: 800;
}}

.subtitle {{
    color: #91a9c8;
    margin-top: 6px;
}}

.card {{
    background: #111e31;
    border: 1px solid #263c5b;
    border-radius: 16px;
    padding: 21px;
}}

.section {{
    margin-top: 20px;
}}

.hero {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
    margin-top: 25px;
}}

.label {{
    font-size: 11px;
    color: #91a8c6;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}

.big {{
    font-size: 37px;
    font-weight: 800;
    margin-top: 8px;
}}

.rating {{
    font-size: 27px;
    font-weight: 800;
    margin-top: 8px;
    color: #62b8ff;
}}

.small {{
    color: #96abc5;
    margin-top: 5px;
}}

.positive {{
    color: #4fe2a0;
}}

.negative {{
    color: #ff7183;
}}

.section-title {{
    font-size: 21px;
    font-weight: 800;
    margin-bottom: 16px;
}}

.view-grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(250px, 1fr));
    gap: 13px;
}}

.view-card {{
    background: #0b1728;
    border-radius: 13px;
    padding: 18px;
}}

.view-score {{
    font-size: 30px;
    font-weight: 800;
    margin-top: 7px;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(170px, 1fr));
    gap: 12px;
}}

.metric {{
    background: #0b1728;
    padding: 15px;
    border-radius: 12px;
}}

.metric-name {{
    color: #8ca4c2;
    font-size: 12px;
}}

.metric-value {{
    margin-top: 6px;
    font-size: 20px;
    font-weight: 700;
}}

.chart {{
    width: 100%;
    display: block;
    border-radius: 11px;
}}

.two-column {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(320px, 1fr));
    gap: 17px;
}}

.case-title {{
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 13px;
}}

ul {{
    margin: 0;
    padding-left: 20px;
}}

li {{
    margin-bottom: 11px;
    line-height: 1.45;
    color: #cbd9e9;
}}

.intel-grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(230px, 1fr));
    gap: 13px;
}}

.intel-card {{
    background: #0b1728;
    border-radius: 13px;
    padding: 17px;
}}

.intel-title {{
    font-weight: 800;
    font-size: 16px;
    margin-bottom: 12px;
    color: #62b8ff;
}}

.intel-item {{
    display: block;
    color: #d2dfef;
    text-decoration: none;
    padding: 9px 0;
    border-bottom: 1px solid #243852;
    line-height: 1.4;
}}

.intel-item:last-child {{
    border-bottom: none;
}}

.news-item {{
    display: block;
    color: inherit;
    text-decoration: none;
    padding: 14px 0;
    border-bottom: 1px solid #263a55;
}}

.news-title {{
    font-weight: 650;
    line-height: 1.4;
}}

.news-source {{
    color: #8099b8;
    font-size: 12px;
    margin-top: 5px;
}}

.component-row {{
    display: flex;
    justify-content: space-between;
    padding: 11px 0;
    border-bottom: 1px solid #263953;
    color: #cbd9e9;
}}

.component-score {{
    font-weight: 800;
    color: #62b8ff;
}}

.muted {{
    color: #7f98b7;
    line-height: 1.4;
}}

.disclaimer {{
    margin-top: 25px;
    color: #7189a8;
    font-size: 12px;
    line-height: 1.5;
}}

.footer {{
    text-align: center;
    color: #7189a8;
    font-size: 12px;
    margin-top: 25px;
}}

</style>

</head>

<body>

<div class="container">


<div class="title">
    V Stock Intelligence
</div>

<div class="subtitle">
    Micron Technology · NASDAQ: MU
</div>


<div class="hero">


<div class="card">

    <div class="label">
        Current Price
    </div>

    <div class="big">
        {format_money(price)}
    </div>

    <div class="{price_change_class}">
        {daily_change:+,.2f}
        ({daily_change_pct:+.2f}%)
    </div>

</div>


<div class="card">

    <div class="label">
        Overall Investment View
    </div>

    <div class="rating">
        {overall_rating}
    </div>

    <div class="small">
        Score:
        {overall_score}/100
    </div>

</div>


<div class="card">

    <div class="label">
        Analyst Consensus
    </div>

    <div class="rating">
        {escape_text(
            analysts["recommendation"]
        )}
    </div>

    <div class="small">
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

    <div class="small">
        Consensus price target
    </div>

</div>


</div>


<div class="card section">

<div class="section-title">
    Investment Time Horizon
</div>

<div class="view-grid">


<div class="view-card">

    <div class="label">
        Short-Term View
    </div>

    <div class="view-score">
        {short_term_score}/100
    </div>

    <div class="rating">
        {short_term_rating}
    </div>

    <div class="small">
        Technical + price momentum
    </div>

</div>


<div class="view-card">

    <div class="label">
        Long-Term Investment View
    </div>

    <div class="view-score">
        {long_term_score}/100
    </div>

    <div class="rating">
        {long_term_rating}
    </div>

    <div class="small">
        Fundamentals + analyst expectations
    </div>

</div>


<div class="view-card">

    <div class="label">
        Overall View
    </div>

    <div class="view-score">
        {overall_score}/100
    </div>

    <div class="rating">
        {overall_rating}
    </div>

    <div class="small">
        Weighted toward long-term investment
    </div>

</div>


</div>

</div>


<div class="card section">

<div class="section-title">
    Core Investment Scores
</div>

<div class="grid">


<div class="metric">

    <div class="metric-name">
        Technical
    </div>

    <div class="metric-value">
        {technical["score"]}/100
    </div>

    <div class="small">
        {score_description(
            technical["score"]
        )}
    </div>

</div>


<div class="metric">

    <div class="metric-name">
        Momentum
    </div>

    <div class="metric-value">
        {momentum["score"]}/100
    </div>

    <div class="small">
        {score_description(
            momentum["score"]
        )}
    </div>

</div>


<div class="metric">

    <div class="metric-name">
        Fundamentals
    </div>

    <div class="metric-value">
        {fundamentals["score"]}/100
    </div>

    <div class="small">
        {score_description(
            fundamentals["score"]
        )}
    </div>

</div>


</div>

</div>


<div class="card section">

<div class="section-title">
    Micron Intelligence
</div>

<div class="intel-grid">

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
    src="data:image/png;base64,{chart_base64}"
    alt="Micron price chart"
>

</div>


<div class="card section">

<div class="section-title">
    Fundamental Snapshot
</div>

<div class="grid">


<div class="metric">
<div class="metric-name">
Market Cap
</div>
<div class="metric-value">
{format_large_number(
fundamentals["market_cap"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Trailing P/E
</div>
<div class="metric-value">
{format_ratio(
fundamentals["trailing_pe"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Forward P/E
</div>
<div class="metric-value">
{format_ratio(
fundamentals["forward_pe"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
EPS
</div>
<div class="metric-value">
{format_money(
fundamentals["eps"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Revenue Growth
</div>
<div class="metric-value">
{format_percent(
fundamentals["revenue_growth"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Earnings Growth
</div>
<div class="metric-value">
{format_percent(
fundamentals["earnings_growth"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Gross Margin
</div>
<div class="metric-value">
{format_percent(
fundamentals["gross_margin"],
signed=False
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Operating Margin
</div>
<div class="metric-value">
{format_percent(
fundamentals["operating_margin"],
signed=False
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Return on Equity
</div>
<div class="metric-value">
{format_percent(
fundamentals["return_on_equity"],
signed=False
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Debt / Equity
</div>
<div class="metric-value">
{format_ratio(
fundamentals["debt_to_equity"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Current Ratio
</div>
<div class="metric-value">
{format_ratio(
fundamentals["current_ratio"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Price / Book
</div>
<div class="metric-value">
{format_ratio(
fundamentals["price_to_book"]
)}
</div>
</div>


</div>

</div>


<div class="card section">

<div class="section-title">
    Fundamental Score Breakdown
</div>

{score_component_rows(
fundamentals["components"]
)}

</div>


<div class="card section">

<div class="section-title">
    Technical & Momentum
</div>

<div class="grid">


<div class="metric">
<div class="metric-name">
RSI
</div>
<div class="metric-value">
{technical["rsi"]:.1f}
</div>
</div>


<div class="metric">
<div class="metric-name">
20 Day MA
</div>
<div class="metric-value">
{format_money(
technical["ma20"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
50 Day MA
</div>
<div class="metric-value">
{format_money(
technical["ma50"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
200 Day MA
</div>
<div class="metric-value">
{format_money(
technical["ma200"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
1 Week
</div>
<div class="metric-value">
{format_percent(
momentum["week_1"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
1 Month
</div>
<div class="metric-value">
{format_percent(
momentum["month_1"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
3 Months
</div>
<div class="metric-value">
{format_percent(
momentum["month_3"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
6 Months
</div>
<div class="metric-value">
{format_percent(
momentum["month_6"]
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Support
</div>
<div class="metric-value">
{format_money(
support
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
Resistance
</div>
<div class="metric-value">
{format_money(
resistance
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
52 Week Low
</div>
<div class="metric-value">
{format_money(
low_52
)}
</div>
</div>


<div class="metric">
<div class="metric-name">
52 Week High
</div>
<div class="metric-value">
{format_money(
high_52
)}
</div>
</div>


</div>

</div>


<div class="section two-column">


<div class="card">

<div class="case-title">
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

<div class="case-title">
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


<div class="disclaimer">

This dashboard is an automated research tool.
Scores are generated from market, technical,
fundamental and analyst data supplied by third-party
data sources and may occasionally be delayed or incomplete.
The investment ratings are not financial advice.

</div>


<div class="footer">

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
        / "index.html"
    )

    output_file.write_text(
        html_page,
        encoding="utf-8",
    )

    print(
        "Micron investment dashboard generated successfully."
    )


if __name__ == "__main__":
    main()
