from datetime import datetime, timezone
from pathlib import Path
import html
import re

from scanner import run_scanner


# ============================================================
# BASIC HELPERS
# ============================================================

def escape(value):
    if value is None:
        return ""

    return html.escape(
        str(value)
    )


def ticker_slug(ticker):
    """
    Convert tickers into safe folder names.

    MU -> mu
    U11.SI -> u11-si
    """
    value = ticker.lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "-",
        value,
    )

    return value.strip("-")


def stock_url(stock):
    return (
        "stocks/"
        + ticker_slug(
            stock["ticker"]
        )
        + "/"
    )


def format_price(
    price,
    market,
):
    if price is None:
        return "N/A"

    if market == "Singapore":
        return f"S${price:,.2f}"

    return f"${price:,.2f}"


def format_percent(value):
    if value is None:
        return "N/A"

    return (
        f"{value * 100:+.2f}%"
    )


def rating_class(value):
    return (
        value
        .lower()
        .replace(
            " ",
            "-",
        )
    )


def quality_class(score):
    if score >= 80:
        return "quality-good"

    if score >= 60:
        return "quality-medium"

    return "quality-low"


def quality_label(score):
    if score >= 80:
        return "High"

    if score >= 60:
        return "Medium"

    return "Limited"


def value_opportunity_score(stock):
    return round(
        stock["valuation"]
        * 0.50
        +
        stock["fundamental"]
        * 0.50
    )


# ============================================================
# TOP OPPORTUNITY CARDS
# ============================================================

def opportunity_cards(
    stocks,
    count=5,
):
    output = ""

    for stock in stocks[:count]:

        change_class = (
            "positive"
            if stock["daily_change"] >= 0
            else "negative"
        )

        css_rating = rating_class(
            stock["rating"]
        )

        quality_css = quality_class(
            stock["data_quality"]
        )

        output += f"""
        <a
            class="opportunity-card"
            href="{stock_url(stock)}"
        >

            <div class="opportunity-top">

                <div>

                    <div class="opportunity-ticker">
                        {escape(
                            stock["ticker"]
                        )}
                    </div>

                    <div class="opportunity-name">
                        {escape(
                            stock["name"]
                        )}
                    </div>

                    <div class="sector">
                        {escape(
                            stock["sector"]
                        )}
                    </div>

                </div>


                <div class="
                    rating-badge
                    {css_rating}
                ">
                    {escape(
                        stock["rating"]
                    )}
                </div>

            </div>


            <div class="opportunity-price">

                {format_price(
                    stock["price"],
                    stock["market"],
                )}

            </div>


            <div class="{change_class}">

                {format_percent(
                    stock["daily_change"]
                )}

            </div>


            <div class="score-row">

                <div>
                    Overall
                </div>

                <div>
                    {stock["overall"]}/100
                </div>

            </div>


            <div class="score-row">

                <div>
                    Technical
                </div>

                <div>
                    {stock["technical"]}
                </div>

            </div>


            <div class="score-row">

                <div>
                    Momentum
                </div>

                <div>
                    {stock["momentum"]}
                </div>

            </div>


            <div class="score-row">

                <div>
                    Fundamentals
                </div>

                <div>
                    {stock["fundamental"]}
                </div>

            </div>


            <div class="quality-row">

                <span>
                    Data quality
                </span>

                <span class="
                    quality-badge
                    {quality_css}
                ">
                    {quality_label(
                        stock["data_quality"]
                    )}
                </span>

            </div>

        </a>
        """

    return output


# ============================================================
# FULL RANKING TABLE
# ============================================================

def stock_rows(
    stocks,
    limit=25,
):
    output = ""

    for rank, stock in enumerate(
        stocks[:limit],
        start=1,
    ):

        change_class = (
            "positive"
            if stock["daily_change"] >= 0
            else "negative"
        )

        css_rating = rating_class(
            stock["rating"]
        )

        quality_css = quality_class(
            stock["data_quality"]
        )

        output += f"""
        <tr>

            <td>
                {rank}
            </td>

            <td>

                <a
                    class="stock-link"
                    href="{stock_url(stock)}"
                >

                    <div class="stock-name">
                        {escape(
                            stock["name"]
                        )}
                    </div>

                    <div class="ticker">
                        {escape(
                            stock["ticker"]
                        )}
                    </div>

                    <div class="sector">
                        {escape(
                            stock["sector"]
                        )}
                    </div>

                </a>

            </td>


            <td>
                {format_price(
                    stock["price"],
                    stock["market"],
                )}
            </td>


            <td class="{change_class}">
                {format_percent(
                    stock["daily_change"]
                )}
            </td>


            <td class="desktop-column">
                {stock["technical"]}
            </td>


            <td class="desktop-column">
                {stock["momentum"]}
            </td>


            <td class="desktop-column">
                {stock["fundamental"]}
            </td>


            <td class="desktop-column">
                {stock["valuation"]}
            </td>


            <td class="score">
                {stock["overall"]}
            </td>


            <td>

                <span class="
                    quality-badge
                    {quality_css}
                ">
                    {stock["data_quality"]}%
                </span>

            </td>


            <td>

                <span class="
                    rating-badge
                    {css_rating}
                ">
                    {escape(
                        stock["rating"]
                    )}
                </span>

            </td>

        </tr>
        """

    return output


# ============================================================
# MICRON FLAGSHIP
# ============================================================

def find_micron(us_results):
    for stock in us_results:

        if stock["ticker"] == "MU":
            return stock

    return None


def micron_focus(micron):

    if micron is None:

        return """
        <div class="muted">
            Micron data unavailable.
        </div>
        """

    change_class = (
        "positive"
        if micron["daily_change"] >= 0
        else "negative"
    )

    css_rating = rating_class(
        micron["rating"]
    )

    return f"""
    <div class="micron-layout">

        <div>

            <div class="micron-label">
                FLAGSHIP STOCK REPORT
            </div>

            <div class="micron-title">
                Micron Technology
            </div>

            <div class="muted">
                NASDAQ: MU
            </div>

        </div>


        <div>

            <div class="micron-price">
                {format_price(
                    micron["price"],
                    "US",
                )}
            </div>

            <div class="{change_class}">
                {format_percent(
                    micron["daily_change"]
                )}
            </div>

        </div>


        <div>

            <div class="micron-score">
                {micron["overall"]}/100
            </div>

            <span class="
                rating-badge
                {css_rating}
            ">
                {escape(
                    micron["rating"]
                )}
            </span>

        </div>


        <div>

            <a
                class="primary-button"
                href="micron/"
            >
                Open Full Micron Report →
            </a>

        </div>

    </div>
    """


# ============================================================
# OPPORTUNITY SCREENS
# ============================================================

def get_oversold(stocks):

    results = [
        stock
        for stock in stocks
        if (
            stock["rsi"] is not None
            and
            stock["rsi"] < 35
        )
    ]

    return sorted(
        results,
        key=lambda stock:
            stock["rsi"]
    )


def get_momentum_leaders(stocks):

    eligible = [
        stock
        for stock in stocks
        if (
            stock["fundamental"] >= 50
            and
            stock["data_quality"] >= 60
        )
    ]

    return sorted(
        eligible,
        key=lambda stock: (
            stock["momentum"],
            stock["overall"],
        ),
        reverse=True,
    )


def get_value_opportunities(stocks):

    eligible = [
        stock
        for stock in stocks
        if stock["data_quality"] >= 60
    ]

    return sorted(
        eligible,
        key=lambda stock:
            value_opportunity_score(
                stock
            ),
        reverse=True,
    )


def get_balanced_opportunities(stocks):

    eligible = [
        stock
        for stock in stocks
        if stock["data_quality"] >= 60
    ]

    return sorted(
        eligible,
        key=lambda stock:
            stock["balanced_score"],
        reverse=True,
    )


def mini_list(
    stocks,
    mode,
    limit=6,
):

    if not stocks:

        return """
        <div class="muted">
            No stocks currently meet this screen.
        </div>
        """

    output = ""

    for stock in stocks[:limit]:

        if mode == "oversold":

            main_detail = (
                f'RSI '
                f'{stock["rsi"]:.1f}'
            )

            secondary = (
                f'Overall '
                f'{stock["overall"]}/100'
            )


        elif mode == "momentum":

            main_detail = (
                f'Momentum '
                f'{stock["momentum"]}/100'
            )

            secondary = (
                f'Fundamentals '
                f'{stock["fundamental"]}/100'
            )


        elif mode == "value":

            main_detail = (
                f'Value Opportunity '
                f'{value_opportunity_score(stock)}/100'
            )

            secondary = (
                f'Valuation '
                f'{stock["valuation"]}'
                f' · Fundamentals '
                f'{stock["fundamental"]}'
            )


        else:

            main_detail = (
                f'Balance '
                f'{stock["balanced_score"]}/100'
            )

            secondary = (
                f'Overall '
                f'{stock["overall"]}'
                f' · Data '
                f'{stock["data_quality"]}%'
            )


        output += f"""
        <a
            class="mini-row"
            href="{stock_url(stock)}"
        >

            <div>

                <div class="mini-ticker">
                    {escape(
                        stock["ticker"]
                    )}
                </div>

                <div class="mini-name">
                    {escape(
                        stock["name"]
                    )}
                </div>

                <div class="sector">
                    {escape(
                        stock["sector"]
                    )}
                </div>

            </div>


            <div class="mini-right">

                <div class="mini-score">
                    {main_detail}
                </div>

                <div class="mini-secondary">
                    {secondary}
                </div>

            </div>

        </a>
        """

    return output


# ============================================================
# INDIVIDUAL STOCK DETAIL PAGES
# ============================================================

def score_commentary(
    score,
    category,
):

    if score >= 80:
        return (
            f"{category} conditions are currently strong."
        )

    if score >= 65:
        return (
            f"{category} conditions are currently positive."
        )

    if score >= 50:
        return (
            f"{category} conditions are broadly neutral."
        )

    if score >= 35:
        return (
            f"{category} conditions are currently weak."
        )

    return (
        f"{category} conditions are currently very weak."
    )


def generate_stock_detail_page(
    stock,
    updated,
):

    css_rating = rating_class(
        stock["rating"]
    )

    quality_css = quality_class(
        stock["data_quality"]
    )

    change_class = (
        "positive"
        if stock["daily_change"] >= 0
        else "negative"
    )

    value_score = (
        value_opportunity_score(
            stock
        )
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
    V Stock Intelligence ·
    {escape(stock["ticker"])}
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
    width: min(1100px, 94%);
    margin: auto;
    padding: 30px 0 60px;
}}

.back {{
    color: #68b9ff;
    text-decoration: none;
    font-size: 13px;
}}

.header {{
    margin-top: 24px;
}}

.title {{
    font-size: 34px;
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
    padding: 21px;
}}

.section {{
    margin-top: 20px;
}}

.hero {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(190px, 1fr));
    gap: 14px;
    margin-top: 24px;
}}

.label {{
    color: #8ba4c3;
    font-size: 11px;
    text-transform: uppercase;
}}

.big {{
    font-size: 32px;
    font-weight: 800;
    margin-top: 7px;
}}

.rating {{
    color: #65baff;
    font-size: 27px;
    font-weight: 800;
    margin-top: 7px;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(180px, 1fr));
    gap: 13px;
}}

.metric {{
    background: #0b1728;
    border-radius: 12px;
    padding: 17px;
}}

.metric-value {{
    font-size: 25px;
    font-weight: 800;
    margin-top: 7px;
}}

.section-title {{
    font-size: 21px;
    font-weight: 800;
    margin-bottom: 15px;
}}

.comment {{
    color: #aebfd4;
    font-size: 13px;
    line-height: 1.5;
    margin-top: 8px;
}}

.positive {{
    color: #51e0a0;
}}

.negative {{
    color: #ff7183;
}}

.rating-badge,
.quality-badge {{
    display: inline-block;
    padding: 5px 8px;
    border-radius: 7px;
    font-size: 10px;
    font-weight: 800;
}}

.strong-buy {{
    color: #51e5a0;
    background: rgba(55, 219, 143, 0.15);
}}

.buy {{
    color: #66bdff;
    background: rgba(86, 184, 255, 0.15);
}}

.hold {{
    color: #f4cd69;
}}

.watch {{
    color: #ffa165;
}}

.caution {{
    color: #ff7183;
}}

.quality-good {{
    color: #55dea0;
}}

.quality-medium {{
    color: #f3c968;
}}

.quality-low {{
    color: #ff7a87;
}}

.footer {{
    text-align: center;
    color: #6f88a8;
    margin-top: 30px;
    font-size: 12px;
}}

</style>

</head>

<body>

<div class="container">


<a
    class="back"
    href="../../"
>
    ← Back to Market Dashboard
</a>


<div class="header">

    <div class="title">
        {escape(
            stock["name"]
        )}
    </div>

    <div class="subtitle">

        {escape(
            stock["ticker"]
        )}

        ·

        {escape(
            stock["sector"]
        )}

        ·

        {escape(
            stock["market"]
        )}

    </div>

</div>


<div class="hero">


<div class="card">

    <div class="label">
        Current Price
    </div>

    <div class="big">
        {format_price(
            stock["price"],
            stock["market"],
        )}
    </div>

    <div class="{change_class}">
        {format_percent(
            stock["daily_change"]
        )}
    </div>

</div>


<div class="card">

    <div class="label">
        Overall Score
    </div>

    <div class="big">
        {stock["overall"]}/100
    </div>

    <div style="margin-top:8px;">

        <span class="
            rating-badge
            {css_rating}
        ">
            {escape(
                stock["rating"]
            )}
        </span>

    </div>

</div>


<div class="card">

    <div class="label">
        Value Opportunity
    </div>

    <div class="big">
        {value_score}/100
    </div>

    <div class="comment">
        Valuation + fundamentals
    </div>

</div>


<div class="card">

    <div class="label">
        Data Quality
    </div>

    <div class="big">
        {stock["data_quality"]}%
    </div>

    <div style="margin-top:8px;">

        <span class="
            quality-badge
            {quality_css}
        ">
            {quality_label(
                stock["data_quality"]
            )}
        </span>

    </div>

</div>


</div>


<div class="card section">

    <div class="section-title">
        Core Investment Scores
    </div>

    <div class="grid">


        <div class="metric">

            <div class="label">
                Technical
            </div>

            <div class="metric-value">
                {stock["technical"]}/100
            </div>

            <div class="comment">
                {score_commentary(
                    stock["technical"],
                    "Technical"
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Momentum
            </div>

            <div class="metric-value">
                {stock["momentum"]}/100
            </div>

            <div class="comment">
                {score_commentary(
                    stock["momentum"],
                    "Momentum"
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Fundamentals
            </div>

            <div class="metric-value">
                {stock["fundamental"]}/100
            </div>

            <div class="comment">
                {score_commentary(
                    stock["fundamental"],
                    "Fundamental"
                )}
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Valuation
            </div>

            <div class="metric-value">
                {stock["valuation"]}/100
            </div>

            <div class="comment">
                {score_commentary(
                    stock["valuation"],
                    "Valuation"
                )}
            </div>

        </div>


    </div>

</div>


<div class="card section">

    <div class="section-title">
        Opportunity Signals
    </div>

    <div class="grid">


        <div class="metric">

            <div class="label">
                RSI
            </div>

            <div class="metric-value">

                {
                    f'{stock["rsi"]:.1f}'
                    if stock["rsi"] is not None
                    else "N/A"
                }

            </div>

            <div class="comment">

                {
                    "Oversold territory."
                    if (
                        stock["rsi"] is not None
                        and
                        stock["rsi"] < 35
                    )
                    else
                    "Not currently in the oversold screen."
                }

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Balanced Score
            </div>

            <div class="metric-value">
                {stock["balanced_score"]}/100
            </div>

            <div class="comment">
                Rewards strength across multiple factors
                while penalising large score differences.
            </div>

        </div>


        <div class="metric">

            <div class="label">
                Value Opportunity
            </div>

            <div class="metric-value">
                {value_score}/100
            </div>

            <div class="comment">

                Valuation:
                {stock["valuation"]}/100

                ·

                Fundamentals:
                {stock["fundamental"]}/100

            </div>

        </div>


    </div>

</div>


<div class="footer">

    Last updated:
    {updated}

    <br><br>

    Automated quantitative research tool.
    Not financial advice.

</div>


</div>

</body>

</html>
"""

    output_folder = (
        Path("docs")
        /
        "stocks"
        /
        ticker_slug(
            stock["ticker"]
        )
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
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


def generate_all_stock_pages(
    stocks,
    updated,
):

    for stock in stocks:

        generate_stock_detail_page(
            stock,
            updated,
        )

    print(
        f"Generated "
        f"{len(stocks)} "
        f"stock detail pages."
    )


# ============================================================
# MAIN DASHBOARD
# ============================================================

def main():

    print(
        "Running stock scanner..."
    )

    scan_data = run_scanner()

    us_results = scan_data["us"]

    singapore_results = scan_data[
        "singapore"
    ]

    micron = find_micron(
        us_results
    )

    all_results = (
        us_results
        +
        singapore_results
    )

    oversold = get_oversold(
        all_results
    )

    momentum_leaders = (
        get_momentum_leaders(
            all_results
        )
    )

    value_opportunities = (
        get_value_opportunities(
            all_results
        )
    )

    balanced_opportunities = (
        get_balanced_opportunities(
            all_results
        )
    )

    updated = datetime.now(
        timezone.utc
    ).strftime(
        "%d %B %Y, %H:%M UTC"
    )


    # Generate a lightweight page
    # for every scanned stock.

    generate_all_stock_pages(
        all_results,
        updated,
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
V Stock Intelligence
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
    width: min(1380px, 95%);
    margin: auto;
    padding: 28px 0 60px;
}}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 24px;
}}

.main-title {{
    font-size: 36px;
    font-weight: 800;
}}

.subtitle,
.muted {{
    color: #8ca5c4;
}}

.updated {{
    color: #748dab;
    font-size: 12px;
    text-align: right;
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

.section-title {{
    font-size: 22px;
    font-weight: 800;
}}

.section-subtitle {{
    color: #8098b6;
    font-size: 13px;
    margin-top: 4px;
    margin-bottom: 16px;
}}

.micron-layout {{
    display: grid;
    grid-template-columns:
        1.5fr
        1fr
        0.8fr
        1.2fr;
    gap: 25px;
    align-items: center;
}}

.micron-label {{
    color: #62b8ff;
    font-size: 11px;
    font-weight: 800;
}}

.micron-title {{
    font-size: 27px;
    font-weight: 800;
    margin: 7px 0;
}}

.micron-price,
.micron-score {{
    font-size: 32px;
    font-weight: 800;
}}

.primary-button {{
    display: inline-block;
    background: #55a8fa;
    color: #06111f;
    font-weight: 800;
    text-decoration: none;
    padding: 14px 18px;
    border-radius: 10px;
}}

.opportunity-grid {{
    display: grid;
    grid-template-columns:
        repeat(5, 1fr);
    gap: 13px;
}}

.opportunity-card {{
    display: block;
    background: #0b1728;
    border-radius: 13px;
    padding: 16px;
    text-decoration: none;
    color: inherit;
}}

.opportunity-card:hover {{
    background: #10203a;
}}

.opportunity-top {{
    display: flex;
    justify-content: space-between;
    gap: 8px;
}}

.opportunity-ticker {{
    font-size: 20px;
    font-weight: 800;
}}

.opportunity-name {{
    color: #829bb9;
    font-size: 12px;
    margin-top: 4px;
}}

.sector {{
    color: #607c9f;
    font-size: 10px;
    margin-top: 4px;
}}

.opportunity-price {{
    font-size: 23px;
    font-weight: 800;
    margin-top: 18px;
}}

.score-row,
.quality-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #223650;
    font-size: 12px;
    color: #a1b5cf;
}}

.quality-row {{
    border-bottom: none;
}}

.rating-badge,
.quality-badge {{
    display: inline-block;
    padding: 5px 8px;
    border-radius: 7px;
    font-size: 10px;
    font-weight: 800;
}}

.strong-buy {{
    color: #51e5a0;
    background: rgba(55, 219, 143, 0.15);
}}

.buy {{
    color: #66bdff;
    background: rgba(86, 184, 255, 0.15);
}}

.hold {{
    color: #f4cd69;
}}

.watch {{
    color: #ffa165;
}}

.caution {{
    color: #ff7183;
}}

.quality-good {{
    color: #55dea0;
}}

.quality-medium {{
    color: #f3c968;
}}

.quality-low {{
    color: #ff7a87;
}}

.positive {{
    color: #51e0a0;
}}

.negative {{
    color: #ff7183;
}}

.screen-grid {{
    display: grid;
    grid-template-columns:
        repeat(4, 1fr);
    gap: 14px;
}}

.screen-card {{
    background: #0b1728;
    border-radius: 13px;
    padding: 17px;
}}

.screen-title {{
    font-size: 17px;
    font-weight: 800;
    margin-bottom: 12px;
}}

.mini-row {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 11px 0;
    border-bottom: 1px solid #223650;
    text-decoration: none;
    color: inherit;
}}

.mini-row:hover {{
    background: rgba(255,255,255,0.02);
}}

.mini-row:last-child {{
    border-bottom: none;
}}

.mini-ticker {{
    font-weight: 800;
}}

.mini-name {{
    color: #7b95b5;
    font-size: 11px;
    margin-top: 3px;
}}

.mini-right {{
    text-align: right;
}}

.mini-score {{
    color: #62b8ff;
    font-size: 12px;
    font-weight: 700;
}}

.mini-secondary {{
    color: #708aa9;
    font-size: 10px;
    margin-top: 4px;
}}

.table-wrapper {{
    overflow-x: auto;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th,
td {{
    padding: 13px 10px;
    text-align: left;
    border-bottom: 1px solid #20344f;
}}

th {{
    color: #7892b1;
    font-size: 11px;
}}

td {{
    font-size: 13px;
}}

.stock-link {{
    color: inherit;
    text-decoration: none;
}}

.stock-link:hover .stock-name {{
    color: #62b8ff;
}}

.stock-name {{
    font-weight: 700;
}}

.ticker {{
    color: #738caa;
    font-size: 11px;
    margin-top: 3px;
}}

.score {{
    font-weight: 800;
}}

.footer {{
    text-align: center;
    color: #6f88a8;
    margin-top: 30px;
    font-size: 12px;
}}

@media (
    max-width: 1100px
) {{

    .opportunity-grid {{
        grid-template-columns:
            repeat(2, 1fr);
    }}

    .screen-grid {{
        grid-template-columns:
            repeat(2, 1fr);
    }}

    .micron-layout {{
        grid-template-columns:
            repeat(2, 1fr);
    }}

}}

@media (
    max-width: 720px
) {{

    .header {{
        display: block;
    }}

    .updated {{
        text-align: left;
        margin-top: 10px;
    }}

    .opportunity-grid,
    .screen-grid,
    .micron-layout {{
        grid-template-columns: 1fr;
    }}

    .desktop-column {{
        display: none;
    }}

}}

</style>

</head>

<body>

<div class="container">


<div class="header">

    <div>

        <div class="main-title">
            V Stock Intelligence
        </div>

        <div class="subtitle">
            US & Singapore Market Opportunity Dashboard
        </div>

    </div>

    <div class="updated">

        Last updated

        <br>

        {updated}

    </div>

</div>


<div class="card">

    {micron_focus(
        micron
    )}

</div>


<div class="
    card
    section
">

    <div class="section-title">
        US Top Opportunities
    </div>

    <div class="section-subtitle">
        Click any stock to open its individual analysis
    </div>

    <div class="opportunity-grid">

        {opportunity_cards(
            us_results,
            5,
        )}

    </div>

</div>


<div class="
    card
    section
">

    <div class="section-title">
        Singapore Top Opportunities
    </div>

    <div class="section-subtitle">
        Click any stock to open its individual analysis
    </div>

    <div class="opportunity-grid">

        {opportunity_cards(
            singapore_results,
            5,
        )}

    </div>

</div>


<div class="
    card
    section
">

    <div class="section-title">
        Market Opportunity Screens
    </div>

    <div class="section-subtitle">
        Component scores are shown to explain each ranking
    </div>

    <div class="screen-grid">


        <div class="screen-card">

            <div class="screen-title">
                Oversold Watch
            </div>

            {mini_list(
                oversold,
                "oversold",
            )}

        </div>


        <div class="screen-card">

            <div class="screen-title">
                Momentum Leaders
            </div>

            {mini_list(
                momentum_leaders,
                "momentum",
            )}

        </div>


        <div class="screen-card">

            <div class="screen-title">
                Value Opportunities
            </div>

            {mini_list(
                value_opportunities,
                "value",
            )}

        </div>


        <div class="screen-card">

            <div class="screen-title">
                Best Balanced
            </div>

            {mini_list(
                balanced_opportunities,
                "balanced",
            )}

        </div>


    </div>

</div>


<div class="
    card
    section
">

    <div class="section-title">
        US Stock Rankings
    </div>

    <div class="section-subtitle">
        Click a company name to open its analysis
    </div>

    <div class="table-wrapper">

        <table>

            <thead>

                <tr>

                    <th>#</th>

                    <th>Company</th>

                    <th>Price</th>

                    <th>Day</th>

                    <th class="desktop-column">
                        Tech
                    </th>

                    <th class="desktop-column">
                        Momentum
                    </th>

                    <th class="desktop-column">
                        Fundamental
                    </th>

                    <th class="desktop-column">
                        Value
                    </th>

                    <th>Score</th>

                    <th>Data</th>

                    <th>Rating</th>

                </tr>

            </thead>

            <tbody>

                {stock_rows(
                    us_results,
                    25,
                )}

            </tbody>

        </table>

    </div>

</div>


<div class="
    card
    section
">

    <div class="section-title">
        Singapore Stock Rankings
    </div>

    <div class="section-subtitle">
        Click a company name to open its analysis
    </div>

    <div class="table-wrapper">

        <table>

            <thead>

                <tr>

                    <th>#</th>

                    <th>Company</th>

                    <th>Price</th>

                    <th>Day</th>

                    <th class="desktop-column">
                        Tech
                    </th>

                    <th class="desktop-column">
                        Momentum
                    </th>

                    <th class="desktop-column">
                        Fundamental
                    </th>

                    <th class="desktop-column">
                        Value
                    </th>

                    <th>Score</th>

                    <th>Data</th>

                    <th>Rating</th>

                </tr>

            </thead>

            <tbody>

                {stock_rows(
                    singapore_results,
                    25,
                )}

            </tbody>

        </table>

    </div>

</div>


<div class="footer">

    Automated quantitative research dashboard.

    <br>

    Individual stock pages use the same scoring engine
    as the main market rankings.

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
        "Main dashboard generated successfully."
    )


if __name__ == "__main__":
    main()
