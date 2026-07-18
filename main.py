import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone


TICKER = "MU"


def calculate_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])


def get_signal(
    price: float,
    ma20: float,
    ma50: float,
    ma200: float,
    rsi: float,
    macd: float,
    signal_line: float,
):
    score = 0
    reasons = []

    if price > ma20:
        score += 1
        reasons.append("Price is above the 20-day moving average.")
    else:
        score -= 1
        reasons.append("Price is below the 20-day moving average.")

    if price > ma50:
        score += 1
        reasons.append("Price is above the 50-day moving average.")
    else:
        score -= 1
        reasons.append("Price is below the 50-day moving average.")

    if price > ma200:
        score += 2
        reasons.append("Price is above the long-term 200-day moving average.")
    else:
        score -= 2
        reasons.append("Price is below the long-term 200-day moving average.")

    if macd > signal_line:
        score += 1
        reasons.append("MACD momentum is bullish.")
    else:
        score -= 1
        reasons.append("MACD momentum is bearish.")

    if rsi < 30:
        score += 2
        reasons.append("RSI suggests the stock may be oversold.")
    elif rsi > 70:
        score -= 1
        reasons.append("RSI suggests the stock may be overbought.")
    else:
        reasons.append("RSI is in a neutral range.")

    if score >= 4:
        signal = "STRONG BUY"
    elif score >= 2:
        signal = "BUY"
    elif score >= 0:
        signal = "HOLD"
    elif score >= -2:
        signal = "WATCH"
    else:
        signal = "CAUTION"

    return signal, score, reasons


def main():
    print("Downloading Micron market data...")

    stock = yf.Ticker(TICKER)

    history = stock.history(period="1y", interval="1d")

    if history.empty:
        raise RuntimeError("No market data returned for MU.")

    close = history["Close"]

    price = float(close.iloc[-1])
    previous_close = float(close.iloc[-2])

    daily_change = price - previous_close
    daily_change_pct = (daily_change / previous_close) * 100

    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1])
    ma200 = float(close.rolling(200).mean().iloc[-1])

    rsi = calculate_rsi(close)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    macd_series = ema12 - ema26
    signal_series = macd_series.ewm(span=9, adjust=False).mean()

    macd = float(macd_series.iloc[-1])
    signal_line = float(signal_series.iloc[-1])

    high_52 = float(history["High"].max())
    low_52 = float(history["Low"].min())

    support = float(history["Low"].tail(20).min())
    resistance = float(history["High"].tail(20).max())

    signal, score, reasons = get_signal(
        price,
        ma20,
        ma50,
        ma200,
        rsi,
        macd,
        signal_line,
    )

    updated = datetime.now(timezone.utc).strftime(
        "%d %B %Y, %H:%M UTC"
    )

    change_class = "positive" if daily_change >= 0 else "negative"

    html = f"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>V Stock Intelligence</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: #07111f;
    color: #eaf2ff;
    font-family:
        Arial,
        Helvetica,
        sans-serif;
}}

.container {{
    width: min(1200px, 94%);
    margin: 0 auto;
    padding: 30px 0 60px;
}}

.header {{
    margin-bottom: 28px;
}}

.title {{
    font-size: 34px;
    font-weight: 800;
    margin-bottom: 5px;
}}

.subtitle {{
    color: #8ba5c7;
    font-size: 15px;
}}

.hero {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(210px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
}}

.card {{
    background: #101d30;
    border: 1px solid #223653;
    border-radius: 16px;
    padding: 22px;
}}

.label {{
    color: #89a1c1;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

.price {{
    font-size: 38px;
    font-weight: 800;
    margin-top: 8px;
}}

.value {{
    font-size: 25px;
    font-weight: 700;
    margin-top: 10px;
}}

.positive {{
    color: #4ee1a0;
}}

.negative {{
    color: #ff6b7d;
}}

.signal {{
    font-size: 28px;
    font-weight: 800;
    color: #53b7ff;
    margin-top: 10px;
}}

.section {{
    margin-top: 20px;
}}

.section-title {{
    font-size: 21px;
    font-weight: 750;
    margin-bottom: 15px;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
}}

.metric {{
    background: #0b1728;
    border-radius: 12px;
    padding: 16px;
}}

.metric-name {{
    color: #8da4c2;
    font-size: 13px;
}}

.metric-value {{
    margin-top: 7px;
    font-size: 21px;
    font-weight: 700;
}}

.reason {{
    padding: 11px 0;
    border-bottom: 1px solid #21344f;
    color: #c9d8eb;
}}

.reason:last-child {{
    border-bottom: none;
}}

.footer {{
    text-align: center;
    color: #6f88aa;
    margin-top: 32px;
    font-size: 13px;
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

            <div class="price">
                ${price:,.2f}
            </div>

            <div class="{change_class}">
                {daily_change:+,.2f}
                ({daily_change_pct:+.2f}%)
            </div>

        </div>

        <div class="card">

            <div class="label">
                Technical Signal
            </div>

            <div class="signal">
                {signal}
            </div>

            <div class="subtitle">
                Score: {score}
            </div>

        </div>

        <div class="card">

            <div class="label">
                52 Week Range
            </div>

            <div class="value">
                ${low_52:,.2f}
            </div>

            <div class="subtitle">
                to ${high_52:,.2f}
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
                    {rsi:.1f}
                </div>

            </div>

            <div class="metric">

                <div class="metric-name">
                    20 Day MA
                </div>

                <div class="metric-value">
                    ${ma20:,.2f}
                </div>

            </div>

            <div class="metric">

                <div class="metric-name">
                    50 Day MA
                </div>

                <div class="metric-value">
                    ${ma50:,.2f}
                </div>

            </div>

            <div class="metric">

                <div class="metric-name">
                    200 Day MA
                </div>

                <div class="metric-value">
                    ${ma200:,.2f}
                </div>

            </div>

            <div class="metric">

                <div class="metric-name">
                    MACD
                </div>

                <div class="metric-value">
                    {macd:.2f}
                </div>

            </div>

            <div class="metric">

                <div class="metric-name">
                    MACD Signal
                </div>

                <div class="metric-value">
                    {signal_line:.2f}
                </div>

            </div>

        </div>

    </div>


    <div class="card section">

        <div class="section-title">
            Key Price Levels
        </div>

        <div class="grid">

            <div class="metric">

                <div class="metric-name">
                    Resistance
                </div>

                <div class="metric-value">
                    ${resistance:,.2f}
                </div>

            </div>

            <div class="metric">

                <div class="metric-name">
                    Current Price
                </div>

                <div class="metric-value">
                    ${price:,.2f}
                </div>

            </div>

            <div class="metric">

                <div class="metric-name">
                    Support
                </div>

                <div class="metric-value">
                    ${support:,.2f}
                </div>

            </div>

        </div>

    </div>


    <div class="card section">

        <div class="section-title">
            Why this signal?
        </div>

        {''.join(
            f'<div class="reason">{reason}</div>'
            for reason in reasons
        )}

    </div>


    <div class="footer">

        Last updated:
        {updated}

        <br><br>

        Research dashboard only.
        Not financial advice.

    </div>

</div>

</body>

</html>
"""

    output_folder = Path("docs")
    output_folder.mkdir(exist_ok=True)

    output_file = output_folder / "index.html"

    output_file.write_text(
        html,
        encoding="utf-8",
    )

    print(
        f"Dashboard successfully created at {output_file}"
    )


if __name__ == "__main__":
    main()
