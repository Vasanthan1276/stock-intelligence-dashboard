import base64
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
# HELPER FUNCTIONS
# ============================================================

def safe_number(value, default=None):
    try:
        if value is None:
            return default

        if isinstance(value, float) and math.isnan(value):
            return default

        return float(value)

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


def format_percent(value):
    value = safe_number(value)

    if value is None:
        return "N/A"

    return f"{value * 100:+.1f}%"


def calculate_rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi


def score_label(score, maximum=10):
    percentage = score / maximum

    if percentage >= 0.75:
        return "STRONG"

    if percentage >= 0.55:
        return "POSITIVE"

    if percentage >= 0.40:
        return "NEUTRAL"

    return "WEAK"


def get_overall_rating(score):
    if score >= 75:
        return "STRONG BUY"

    if score >= 60:
        return "BUY"

    if score >= 45:
        return "HOLD"

    if score >= 30:
        return "WATCH"

    return "CAUTION"


# ============================================================
# TECHNICAL ANALYSIS
# ============================================================

def analyze_technical(history):
    close = history["Close"]

    latest_price = float(close.iloc[-1])

    ma20_series = close.rolling(20).mean()
    ma50_series = close.rolling(50).mean()
    ma200_series = close.rolling(200).mean()

    ma20 = float(ma20_series.iloc[-1])
    ma50 = float(ma50_series.iloc[-1])
    ma200 = float(ma200_series.iloc[-1])

    rsi_series = calculate_rsi(close)
    rsi = float(rsi_series.iloc[-1])

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    macd_series = ema12 - ema26
    signal_series = macd_series.ewm(
        span=9,
        adjust=False,
    ).mean()

    macd = float(macd_series.iloc[-1])
    macd_signal = float(signal_series.iloc[-1])

    technical_score = 0
    reasons = []

    if latest_price > ma20:
        technical_score += 2
        reasons.append(
            "Price is above the 20-day moving average."
        )
    else:
        reasons.append(
            "Price is below the 20-day moving average."
        )

    if latest_price > ma50:
        technical_score += 2
        reasons.append(
            "Price is above the 50-day moving average."
        )
    else:
        reasons.append(
            "Price is below the 50-day moving average."
        )

    if latest_price > ma200:
        technical_score += 3
        reasons.append(
            "The long-term trend remains above the 200-day moving average."
        )
    else:
        reasons.append(
            "Price is below the long-term 200-day moving average."
        )

    if macd > macd_signal:
        technical_score += 2
        reasons.append(
            "MACD momentum is currently bullish."
        )
    else:
        reasons.append(
            "MACD momentum is currently bearish."
        )

    if 40 <= rsi <= 65:
        technical_score += 1
        reasons.append(
            "RSI is in a relatively healthy range."
        )

    elif rsi < 30:
        technical_score += 1
        reasons.append(
            "RSI indicates oversold conditions."
        )

    elif rsi > 70:
        reasons.append(
            "RSI indicates potentially overbought conditions."
        )

    else:
        reasons.append(
            "RSI is outside the preferred momentum range."
        )

    return {
        "price": latest_price,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "technical_score": technical_score,
        "technical_label": score_label(
            technical_score
        ),
        "technical_reasons": reasons,
        "ma20_series": ma20_series,
        "ma50_series": ma50_series,
        "ma200_series": ma200_series,
    }


# ============================================================
# MOMENTUM ANALYSIS
# ============================================================

def calculate_return(close, days):
    if len(close) <= days:
        return None

    old_price = float(close.iloc[-days - 1])
    latest_price = float(close.iloc[-1])

    return (
        (latest_price / old_price) - 1
    )


def analyze_momentum(history):
    close = history["Close"]

    one_week = calculate_return(
        close,
        5,
    )

    one_month = calculate_return(
        close,
        21,
    )

    three_month = calculate_return(
        close,
        63,
    )

    six_month = calculate_return(
        close,
        126,
    )

    momentum_score = 0

    returns = [
        one_week,
        one_month,
        three_month,
        six_month,
    ]

    for value in returns:
        if value is None:
            continue

        if value > 0:
            momentum_score += 2

    if (
        three_month is not None
        and three_month > 0.10
    ):
        momentum_score += 1

    if (
        six_month is not None
        and six_month > 0.20
    ):
        momentum_score += 1

    momentum_score = min(
        momentum_score,
        10,
    )

    return {
        "one_week": one_week,
        "one_month": one_month,
        "three_month": three_month,
        "six_month": six_month,
        "momentum_score": momentum_score,
        "momentum_label": score_label(
            momentum_score
        ),
    }


# ============================================================
# FUNDAMENTAL ANALYSIS
# ============================================================

def analyze_fundamentals(info):
    market_cap = safe_number(
        info.get("marketCap")
    )

    trailing_pe = safe_number(
        info.get("trailingPE")
    )

    forward_pe = safe_number(
        info.get("forwardPE")
    )

    eps = safe_number(
        info.get("trailingEps")
    )

    revenue_growth = safe_number(
        info.get("revenueGrowth")
    )

    earnings_growth = safe_number(
        info.get("earningsGrowth")
    )

    return_on_equity = safe_number(
        info.get("returnOnEquity")
    )

    debt_to_equity = safe_number(
        info.get("debtToEquity")
    )

    fundamental_score = 0
    reasons = []

    if revenue_growth is not None:

        if revenue_growth > 0.20:
            fundamental_score += 3
            reasons.append(
                "Revenue growth is currently strong."
            )

        elif revenue_growth > 0:
            fundamental_score += 2
            reasons.append(
                "Revenue is growing."
            )

        else:
            reasons.append(
                "Revenue growth is currently negative."
            )

    if earnings_growth is not None:

        if earnings_growth > 0.20:
            fundamental_score += 3
            reasons.append(
                "Earnings growth is currently strong."
            )

        elif earnings_growth > 0:
            fundamental_score += 2
            reasons.append(
                "Earnings are growing."
            )

        else:
            reasons.append(
                "Earnings growth is currently negative."
            )

    if forward_pe is not None:

        if 0 < forward_pe <= 20:
            fundamental_score += 2
            reasons.append(
                "Forward valuation appears relatively reasonable."
            )

        elif forward_pe <= 35:
            fundamental_score += 1
            reasons.append(
                "Forward valuation is elevated but not extreme."
            )

        else:
            reasons.append(
                "Forward valuation appears relatively high."
            )

    if return_on_equity is not None:

        if return_on_equity > 0.15:
            fundamental_score += 1

    if debt_to_equity is not None:

        if debt_to_equity < 100:
            fundamental_score += 1

    fundamental_score = min(
        fundamental_score,
        10,
    )

    return {
        "market_cap": market_cap,
        "trailing_pe": trailing_pe,
        "forward_pe": forward_pe,
        "eps": eps,
        "revenue_growth": revenue_growth,
        "earnings_growth": earnings_growth,
        "return_on_equity": return_on_equity,
        "debt_to_equity": debt_to_equity,
        "fundamental_score": fundamental_score,
        "fundamental_label": score_label(
            fundamental_score
        ),
        "fundamental_reasons": reasons,
    }


# ============================================================
# ANALYST DATA
# ============================================================

def analyze_analysts(info, current_price):
    target_mean = safe_number(
        info.get("targetMeanPrice")
    )

    target_high = safe_number(
        info.get("targetHighPrice")
    )

    target_low = safe_number(
        info.get("targetLowPrice")
    )

    recommendation = info.get(
        "recommendationKey"
    )

    analyst_count = info.get(
        "numberOfAnalystOpinions"
    )

    upside = None

    if (
        target_mean is not None
        and current_price > 0
    ):
        upside = (
            target_mean / current_price
        ) - 1

    if recommendation:
        recommendation = (
            recommendation
            .replace("_", " ")
            .upper()
        )
    else:
        recommendation = "N/A"

    return {
        "target_mean": target_mean,
        "target_high": target_high,
        "target_low": target_low,
        "recommendation": recommendation,
        "analyst_count": analyst_count,
        "upside": upside,
    }


# ============================================================
# NEWS
# ============================================================

def get_news(stock):
    news_items = []

    try:
        raw_news = stock.news

    except Exception:
        raw_news = []

    for item in raw_news[:6]:

        content = item.get(
            "content",
            item,
        )

        title = content.get(
            "title",
            "Micron news update",
        )

        provider = content.get(
            "provider",
            {}
        )

        publisher = provider.get(
            "displayName",
            ""
        )

        canonical_url = content.get(
            "canonicalUrl",
            {}
        )

        url = canonical_url.get(
            "url",
            "#",
        )

        news_items.append(
            {
                "title": title,
                "publisher": publisher,
                "url": url,
            }
        )

    return news_items


# ============================================================
# PRICE CHART
# ============================================================

def create_chart(
    history,
    technical,
):
    plt.figure(
        figsize=(12, 5.2)
    )

    plt.plot(
        history.index,
        history["Close"],
        linewidth=2,
        label="MU Price",
    )

    plt.plot(
        history.index,
        technical["ma20_series"],
        linewidth=1,
        label="20 Day MA",
    )

    plt.plot(
        history.index,
        technical["ma50_series"],
        linewidth=1,
        label="50 Day MA",
    )

    plt.plot(
        history.index,
        technical["ma200_series"],
        linewidth=1,
        label="200 Day MA",
    )

    plt.title(
        "Micron Technology · 1 Year Price Trend"
    )

    plt.xlabel("")

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

    chart_base64 = base64.b64encode(
        buffer.read()
    ).decode("utf-8")

    return chart_base64


# ============================================================
# INVESTMENT VIEW
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

    price = technical["price"]

    if price > technical["ma200"]:
        bull_points.append(
            "The longer-term price trend remains above the 200-day moving average."
        )
    else:
        bear_points.append(
            "The share price is trading below its 200-day moving average."
        )

    if technical["rsi"] < 30:
        bull_points.append(
            "The stock is technically oversold, which can create rebound potential."
        )

    if technical["macd"] < technical["macd_signal"]:
        bear_points.append(
            "Short-term MACD momentum remains bearish."
        )
    else:
        bull_points.append(
            "MACD currently supports positive short-term momentum."
        )

    revenue_growth = fundamentals[
        "revenue_growth"
    ]

    if revenue_growth is not None:

        if revenue_growth > 0:
            bull_points.append(
                "Recent revenue growth remains positive."
            )

        else:
            bear_points.append(
                "Recent reported revenue growth is negative."
            )

    earnings_growth = fundamentals[
        "earnings_growth"
    ]

    if earnings_growth is not None:

        if earnings_growth > 0:
            bull_points.append(
                "Recent earnings growth is positive."
            )

        else:
            bear_points.append(
                "Recent earnings growth is negative."
            )

    upside = analysts[
        "upside"
    ]

    if upside is not None:

        if upside > 0.10:
            bull_points.append(
                "The current analyst consensus target implies meaningful upside."
            )

        elif upside < -0.05:
            bear_points.append(
                "The current price is above the analyst consensus target."
            )

    watch_points.extend(
        [
            "HBM demand and Micron's ability to expand high-bandwidth memory supply.",
            "DRAM and NAND pricing trends and industry inventory levels.",
            "AI data-center demand and capital spending by hyperscale customers.",
            "Micron gross margin progression and manufacturing cost reductions.",
            "Changes in analyst earnings estimates and price targets.",
        ]
    )

    if not bull_points:
        bull_points.append(
            "No strong quantitative bull signal is currently detected."
        )

    if not bear_points:
        bear_points.append(
            "No major quantitative bear signal is currently detected."
        )

    return {
        "bull_points": bull_points,
        "bear_points": bear_points,
        "watch_points": watch_points,
    }


# ============================================================
# HTML HELPERS
# ============================================================

def list_html(items):
    return "".join(
        f"<li>{item}</li>"
        for item in items
    )


def news_html(news_items):
    if not news_items:
        return """
        <div class="empty-message">
            No recent news was returned by the data provider.
        </div>
        """

    html = ""

    for item in news_items:

        html += f"""
        <a
            class="news-item"
            href="{item['url']}"
            target="_blank"
            rel="noopener noreferrer"
        >

            <div class="news-title">
                {item['title']}
            </div>

            <div class="news-source">
                {item['publisher']}
            </div>

        </a>
        """

    return html


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

    info = stock.info

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

    close = history["Close"]

    price = float(
        close.iloc[-1]
    )

    previous_close = float(
        close.iloc[-2]
    )

    daily_change = (
        price - previous_close
    )

    daily_change_pct = (
        daily_change
        / previous_close
    ) * 100

    high_52 = float(
        history["High"].max()
    )

    low_52 = float(
        history["Low"].min()
    )

    recent_history = history.tail(
        60
    )

    support = float(
        recent_history["Low"].min()
    )

    resistance = float(
        recent_history["High"].max()
    )

    technical_score_pct = (
        technical["technical_score"]
        * 10
    )

    momentum_score_pct = (
        momentum["momentum_score"]
        * 10
    )

    fundamental_score_pct = (
        fundamentals[
            "fundamental_score"
        ]
        * 10
    )

    overall_score = round(

        technical_score_pct
        * 0.35

        +

        momentum_score_pct
        * 0.20

        +

        fundamental_score_pct
        * 0.45

    )

    overall_rating = get_overall_rating(
        overall_score
    )

    updated = datetime.now(
        timezone.utc
    ).strftime(
        "%d %B %Y, %H:%M UTC"
    )

    change_class = (
        "positive"
        if daily_change >= 0
        else "negative"
    )

    analyst_upside = (
        format_percent(
            analysts["upside"]
        )
    )

    html = f"""
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

    font-family:
        Arial,
        Helvetica,
        sans-serif;
}}

.container {{
    width: min(
        1250px,
        94%
    );

    margin: 0 auto;

    padding:
        30px 0
        60px;
}}

.header {{
    margin-bottom: 25px;
}}

.title {{
    font-size: 35px;

    font-weight: 800;
}}

.subtitle {{
    color: #90a8c7;

    margin-top: 6px;
}}

.hero {{
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                220px,
                1fr
            )
        );

    gap: 15px;
}}

.card {{
    background: #111e31;

    border:
        1px solid
        #263b59;

    border-radius: 16px;

    padding: 21px;
}}

.label {{
    color: #90a8c7;

    text-transform: uppercase;

    letter-spacing: 0.8px;

    font-size: 12px;
}}

.big-number {{
    font-size: 38px;

    font-weight: 800;

    margin-top: 7px;
}}

.rating {{
    font-size: 30px;

    color: #5db7ff;

    font-weight: 800;

    margin-top: 8px;
}}

.score {{
    color: #96aecb;

    margin-top: 3px;
}}

.positive {{
    color: #51e0a0;
}}

.negative {{
    color: #ff7185;
}}

.section {{
    margin-top: 19px;
}}

.section-title {{
    font-size: 21px;

    font-weight: 800;

    margin-bottom: 16px;
}}

.grid {{
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                170px,
                1fr
            )
        );

    gap: 12px;
}}

.metric {{
    background: #0b1728;

    border-radius: 12px;

    padding: 15px;
}}

.metric-name {{
    font-size: 12px;

    color: #8da5c3;
}}

.metric-value {{
    font-size: 20px;

    font-weight: 700;

    margin-top: 6px;
}}

.scores {{
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                200px,
                1fr
            )
        );

    gap: 13px;
}}

.score-card {{
    background: #0b1728;

    border-radius: 13px;

    padding: 18px;
}}

.score-number {{
    font-size: 30px;

    font-weight: 800;

    margin-top: 8px;
}}

.score-label {{
    color: #60b9ff;

    margin-top: 3px;

    font-weight: 700;
}}

.chart {{
    width: 100%;

    border-radius: 12px;

    display: block;
}}

.two-column {{
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                320px,
                1fr
            )
        );

    gap: 17px;
}}

.case-title {{
    font-size: 18px;

    font-weight: 800;

    margin-bottom: 12px;
}}

ul {{
    margin: 0;

    padding-left: 20px;
}}

li {{
    margin-bottom: 11px;

    color: #cbd9ea;

    line-height: 1.45;
}}

.news-item {{
    display: block;

    padding:
        15px 0;

    border-bottom:
        1px solid
        #263954;

    color: inherit;

    text-decoration: none;
}}

.news-item:last-child {{
    border-bottom: none;
}}

.news-title {{
    font-size: 16px;

    line-height: 1.4;

    font-weight: 650;
}}

.news-source {{
    margin-top: 5px;

    font-size: 12px;

    color: #829bb9;
}}

.empty-message {{
    color: #8da4c2;
}}

.disclaimer {{
    margin-top: 28px;

    padding: 18px;

    border:
        1px solid
        #233954;

    border-radius: 12px;

    color: #7e97b7;

    font-size: 12px;

    line-height: 1.5;
}}

.footer {{
    text-align: center;

    color: #7188a7;

    margin-top: 25px;

    font-size: 12px;
}}

@media (
    max-width: 650px
) {{

    .title {{
        font-size: 28px;
    }}

    .big-number {{
        font-size: 32px;
    }}

}}

</style>

</head>

<body>

<div class="container">


<div class="header">

    <div class="title">
        V Stock Intelligence
    </div>

    <div class="subtitle">
        Micron Technology · NASDAQ: MU
    </div>

</div>


<div class="hero">

    <div class="card">

        <div class="label">
            Current Price
        </div>

        <div class="big-number">
            {format_money(price)}
        </div>

        <div class="{change_class}">

            {daily_change:+,.2f}

            ({daily_change_pct:+.2f}%)

        </div>

    </div>


    <div class="card">

        <div class="label">
            Overall Assessment
        </div>

        <div class="rating">
            {overall_rating}
        </div>

        <div class="score">
            Combined Score:
            {overall_score}/100
        </div>

    </div>


    <div class="card">

        <div class="label">
            Analyst Consensus
        </div>

        <div class="rating">
            {analysts["recommendation"]}
        </div>

        <div class="score">
            Target:
            {format_money(
                analysts["target_mean"]
            )}
        </div>

    </div>


    <div class="card">

        <div class="label">
            Analyst Target Upside
        </div>

        <div class="big-number">
            {analyst_upside}
        </div>

        <div class="score">
            Based on consensus target
        </div>

    </div>

</div>


<div class="card section">

    <div class="section-title">
        Investment Scores
    </div>

    <div class="scores">


        <div class="score-card">

            <div class="label">
                Technical
            </div>

            <div class="score-number">
                {technical_score_pct}/100
            </div>

            <div class="score-label">
                {technical["technical_label"]}
            </div>

        </div>


        <div class="score-card">

            <div class="label">
                Momentum
            </div>

            <div class="score-number">
                {momentum_score_pct}/100
            </div>

            <div class="score-label">
                {momentum["momentum_label"]}
            </div>

        </div>


        <div class="score-card">

            <div class="label">
                Fundamental
            </div>

            <div class="score-number">
                {fundamental_score_pct}/100
            </div>

            <div class="score-label">
                {fundamentals["fundamental_label"]}
            </div>

        </div>


        <div class="score-card">

            <div class="label">
                Combined
            </div>

            <div class="score-number">
                {overall_score}/100
            </div>

            <div class="score-label">
                {overall_rating}
            </div>

        </div>


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
        Market & Fundamental Snapshot
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
                {
                    f'{fundamentals["trailing_pe"]:.1f}'
                    if fundamentals["trailing_pe"] is not None
                    else "N/A"
                }
            </div>

        </div>


        <div class="metric">

            <div class="metric-name">
                Forward P/E
            </div>

            <div class="metric-value">
                {
                    f'{fundamentals["forward_pe"]:.1f}'
                    if fundamentals["forward_pe"] is not None
                    else "N/A"
                }
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


<div class="card section">

    <div class="section-title">
        Technical Analysis
    </div>

    <div class="grid">


        <div class="metric">

            <div class="metric-name">
                RSI (14)
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
                MACD
            </div>

            <div class="metric-value">
                {technical["macd"]:.2f}
            </div>

        </div>


        <div class="metric">

            <div class="metric-name">
                MACD Signal
            </div>

            <div class="metric-value">
                {technical["macd_signal"]:.2f}
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


    </div>

</div>


<div class="card section">

    <div class="section-title">
        Price Momentum
    </div>

    <div class="grid">


        <div class="metric">

            <div class="metric-name">
                1 Week
            </div>

            <div class="metric-value">
                {format_percent(
                    momentum["one_week"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="metric-name">
                1 Month
            </div>

            <div class="metric-value">
                {format_percent(
                    momentum["one_month"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="metric-name">
                3 Months
            </div>

            <div class="metric-value">
                {format_percent(
                    momentum["three_month"]
                )}
            </div>

        </div>


        <div class="metric">

            <div class="metric-name">
                6 Months
            </div>

            <div class="metric-value">
                {format_percent(
                    momentum["six_month"]
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
            {
                list_html(
                    investment_view[
                        "bull_points"
                    ]
                )
            }
        </ul>

    </div>


    <div class="card">

        <div class="case-title">
            Bear Case
        </div>

        <ul>
            {
                list_html(
                    investment_view[
                        "bear_points"
                    ]
                )
            }
        </ul>

    </div>


</div>


<div class="card section">

    <div class="section-title">
        What to Watch
    </div>

    <ul>
        {
            list_html(
                investment_view[
                    "watch_points"
                ]
            )
        }
    </ul>

</div>


<div class="card section">

    <div class="section-title">
        Latest Micron Headlines
    </div>

    {
        news_html(
            news_items
        )
    }

</div>


<div class="disclaimer">

    The rating shown on this page is generated from
    quantitative technical, momentum and fundamental
    indicators. It is intended as a research aid and does
    not constitute financial advice. Analyst estimates and
    fundamental information may be delayed or incomplete
    depending on the underlying data provider.

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
        html,
        encoding="utf-8",
    )

    print(
        "Dashboard successfully created."
    )


if __name__ == "__main__":
    main()
