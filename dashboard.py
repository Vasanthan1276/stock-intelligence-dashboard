from datetime import datetime, timezone
from pathlib import Path
import html

from scanner import run_scanner


# ============================================================
# GENERAL HELPERS
# ============================================================

def escape(value):
    if value is None:
        return ""

    return html.escape(
        str(value)
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


def format_percent(
    value,
):
    if value is None:
        return "N/A"

    return f"{value * 100:+.2f}%"


def rating_class(
    rating,
):
    rating = (
        rating
        .lower()
        .replace(
            " ",
            "-",
        )
    )

    return rating


# ============================================================
# STOCK TABLE
# ============================================================

def stock_rows(
    stocks,
    limit=10,
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

        ticker = escape(
            stock["ticker"]
        )

        name = escape(
            stock["name"]
        )

        rating = escape(
            stock["rating"]
        )

        css_rating = rating_class(
            stock["rating"]
        )

        output += f"""
        <tr>

            <td class="rank">
                {rank}
            </td>

            <td>

                <div class="stock-name">
                    {name}
                </div>

                <div class="ticker">
                    {ticker}
                </div>

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

            <td>

                <div class="score">
                    {stock["overall"]}
                </div>

            </td>

            <td>

                <span class="
                    rating-badge
                    {css_rating}
                ">
                    {rating}
                </span>

            </td>

        </tr>
        """

    return output


# ============================================================
# OPPORTUNITY CARDS
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

        output += f"""
        <div class="opportunity-card">

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
                    Score
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

        </div>
        """

    return output


# ============================================================
# FILTERED STOCK LISTS
# ============================================================

def get_oversold(
    stocks,
):
    results = [
        stock
        for stock in stocks
        if (
            stock["rsi"] is not None
            and stock["rsi"] < 35
        )
    ]

    results.sort(
        key=lambda item: item[
            "rsi"
        ]
    )

    return results


def get_momentum_leaders(
    stocks,
):
    results = sorted(
        stocks,
        key=lambda item: item[
            "momentum"
        ],
        reverse=True,
    )

    return results


def get_value_opportunities(
    stocks,
):
    results = sorted(
        stocks,
        key=lambda item: (
            item["valuation"]
            * 0.50
            +
            item["fundamental"]
            * 0.50
        ),
        reverse=True,
    )

    return results


def mini_list(
    stocks,
    metric,
    limit=5,
):
    if not stocks:
        return """
        <div class="empty">
            No stocks currently meet this screen.
        </div>
        """

    output = ""

    for stock in stocks[:limit]:

        if metric == "rsi":

            detail = (
                f'RSI {stock["rsi"]:.1f}'
                if stock["rsi"] is not None
                else "RSI N/A"
            )

        elif metric == "momentum":

            detail = (
                f'Momentum '
                f'{stock["momentum"]}/100'
            )

        else:

            detail = (
                f'Value '
                f'{stock["valuation"]}/100'
            )

        output += f"""
        <div class="mini-row">

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

            </div>

            <div class="mini-score">
                {detail}
            </div>

        </div>
        """

    return output


# ============================================================
# MICRON SUMMARY
# ============================================================

def find_micron(
    us_results,
):
    for stock in us_results:

        if stock[
            "ticker"
        ] == "MU":

            return stock

    return None


def micron_focus(
    micron,
):
    if micron is None:

        return """
        <div class="empty">
            Micron market data is currently unavailable.
        </div>
        """

    change_class = (
        "positive"
        if micron["daily_change"] >= 0
        else "negative"
    )

    rating_css = rating_class(
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

            <div class="micron-ticker">
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
                {rating_css}
            ">
                {escape(
                    micron["rating"]
                )}
            </span>

        </div>


        <div class="micron-button-wrapper">

            <a
                class="primary-button"
                href="micron/"
            >
                Open Full Micron Report
                →
            </a>

        </div>


    </div>
    """


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Running US and Singapore stock scanner..."
    )

    scan_data = run_scanner()

    us_results = scan_data[
        "us"
    ]

    singapore_results = scan_data[
        "singapore"
    ]

    all_results = (
        us_results
        +
        singapore_results
    )

    all_results.sort(
        key=lambda item: item[
            "overall"
        ],
        reverse=True,
    )

    micron = find_micron(
        us_results
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

    updated = datetime.now(
        timezone.utc
    ).strftime(
        "%d %B %Y, %H:%M UTC"
    )


    page = f"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="
        width=device-width,
        initial-scale=1.0
    "
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

    background:
        #07111f;

    color:
        #edf4ff;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

}}


.container {{

    width:
        min(
            1380px,
            95%
        );

    margin:
        0 auto;

    padding:
        28px 0
        70px;

}}


.header {{

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        flex-end;

    gap:
        20px;

    margin-bottom:
        25px;

}}


.main-title {{

    font-size:
        36px;

    font-weight:
        800;

}}


.subtitle {{

    color:
        #91a8c6;

    margin-top:
        6px;

}}


.updated {{

    color:
        #748dab;

    font-size:
        12px;

    text-align:
        right;

}}


.card {{

    background:
        #111e31;

    border:
        1px solid
        #263c5b;

    border-radius:
        16px;

    padding:
        21px;

}}


.section {{

    margin-top:
        20px;

}}


.section-header {{

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        center;

    gap:
        15px;

    margin-bottom:
        17px;

}}


.section-title {{

    font-size:
        22px;

    font-weight:
        800;

}}


.section-subtitle {{

    color:
        #8098b6;

    font-size:
        13px;

}}


/* ==========================================
   MICRON
========================================== */


.micron-card {{

    background:
        linear-gradient(
            135deg,
            #122540,
            #101d30
        );

}}


.micron-layout {{

    display:
        grid;

    grid-template-columns:
        1.5fr
        1fr
        0.8fr
        1.2fr;

    gap:
        25px;

    align-items:
        center;

}}


.micron-label {{

    color:
        #62b8ff;

    font-size:
        11px;

    font-weight:
        800;

    letter-spacing:
        1px;

}}


.micron-title {{

    font-size:
        27px;

    font-weight:
        800;

    margin-top:
        7px;

}}


.micron-ticker {{

    color:
        #8ca5c4;

    margin-top:
        5px;

}}


.micron-price {{

    font-size:
        32px;

    font-weight:
        800;

}}


.micron-score {{

    font-size:
        29px;

    font-weight:
        800;

    margin-bottom:
        7px;

}}


.micron-button-wrapper {{

    text-align:
        right;

}}


.primary-button {{

    display:
        inline-block;

    background:
        #3a9df8;

    color:
        #06111f;

    font-weight:
        800;

    text-decoration:
        none;

    padding:
        13px
        17px;

    border-radius:
        10px;

}}


/* ==========================================
   OPPORTUNITY CARDS
========================================== */


.opportunity-grid {{

    display:
        grid;

    grid-template-columns:
        repeat(
            5,
            1fr
        );

    gap:
        13px;

}}


.opportunity-card {{

    background:
        #0b1728;

    border-radius:
        13px;

    padding:
        16px;

}}


.opportunity-top {{

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        flex-start;

    gap:
        8px;

}}


.opportunity-ticker {{

    font-size:
        20px;

    font-weight:
        800;

}}


.opportunity-name {{

    color:
        #829bb9;

    font-size:
        12px;

    margin-top:
        3px;

    min-height:
        30px;

}}


.opportunity-price {{

    font-size:
        23px;

    font-weight:
        800;

    margin-top:
        19px;

}}


.score-row {{

    display:
        flex;

    justify-content:
        space-between;

    gap:
        12px;

    padding:
        8px 0;

    border-bottom:
        1px solid
        #223650;

    font-size:
        12px;

    color:
        #a1b5cf;

}}


.score-row:last-child {{

    border-bottom:
        none;

}}


/* ==========================================
   RATINGS
========================================== */


.rating-badge {{

    display:
        inline-block;

    padding:
        5px
        8px;

    border-radius:
        7px;

    font-size:
        10px;

    font-weight:
        800;

    white-space:
        nowrap;

}}


.strong-buy {{

    background:
        rgba(
            55,
            219,
            143,
            0.15
        );

    color:
        #51e5a0;

}}


.buy {{

    background:
        rgba(
            86,
            184,
            255,
            0.15
        );

    color:
        #66bdff;

}}


.hold {{

    background:
        rgba(
            245,
            195,
            70,
            0.15
        );

    color:
        #f4cd69;

}}


.watch {{

    background:
        rgba(
            255,
            149,
            77,
            0.15
        );

    color:
        #ffa165;

}}


.caution {{

    background:
        rgba(
            255,
            96,
            111,
            0.15
        );

    color:
        #ff7183;

}}


/* ==========================================
   TABLE
========================================== */


.table-wrapper {{

    overflow-x:
        auto;

}}


table {{

    width:
        100%;

    border-collapse:
        collapse;

}}


th {{

    text-align:
        left;

    color:
        #7992b1;

    font-size:
        11px;

    text-transform:
        uppercase;

    padding:
        12px
        10px;

    border-bottom:
        1px solid
        #2a3f5d;

}}


td {{

    padding:
        14px
        10px;

    border-bottom:
        1px solid
        #20344f;

    font-size:
        13px;

}}


tr:last-child td {{

    border-bottom:
        none;

}}


.rank {{

    color:
        #7891b0;

    font-weight:
        700;

}}


.stock-name {{

    font-weight:
        700;

}}


.ticker {{

    color:
        #738caa;

    font-size:
        11px;

    margin-top:
        3px;

}}


.score {{

    font-weight:
        800;

    font-size:
        16px;

}}


/* ==========================================
   SCREENERS
========================================== */


.screen-grid {{

    display:
        grid;

    grid-template-columns:
        repeat(
            3,
            1fr
        );

    gap:
        15px;

}}


.screen-card {{

    background:
        #0b1728;

    border-radius:
        13px;

    padding:
        17px;

}}


.screen-title {{

    font-size:
        17px;

    font-weight:
        800;

    margin-bottom:
        12px;

}}


.mini-row {{

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        center;

    gap:
        10px;

    padding:
        11px 0;

    border-bottom:
        1px solid
        #223650;

}}


.mini-row:last-child {{

    border-bottom:
        none;

}}


.mini-ticker {{

    font-weight:
        800;

}}


.mini-name {{

    font-size:
        11px;

    color:
        #7891b0;

    margin-top:
        3px;

}}


.mini-score {{

    font-size:
        12px;

    font-weight:
        700;

    color:
        #62b8ff;

    text-align:
        right;

}}


.empty {{

    color:
        #8199b7;

    font-size:
        13px;

    padding:
        10px 0;

}}


.positive {{

    color:
        #51e0a0;

}}


.negative {{

    color:
        #ff7183;

}}


.footer {{

    text-align:
        center;

    color:
        #6f88a8;

    font-size:
        12px;

    margin-top:
        30px;

    line-height:
        1.6;

}}


/* ==========================================
   RESPONSIVE
========================================== */


@media (
    max-width: 1100px
) {{

    .opportunity-grid {{

        grid-template-columns:
            repeat(
                2,
                1fr
            );

    }}


    .micron-layout {{

        grid-template-columns:
            repeat(
                2,
                1fr
            );

    }}


    .micron-button-wrapper {{

        text-align:
            left;

    }}

}}


@media (
    max-width: 720px
) {{

    .container {{

        width:
            94%;

    }}


    .header {{

        display:
            block;

    }}


    .updated {{

        text-align:
            left;

        margin-top:
            10px;

    }}


    .main-title {{

        font-size:
            29px;

    }}


    .micron-layout {{

        grid-template-columns:
            1fr;

    }}


    .opportunity-grid {{

        grid-template-columns:
            1fr;

    }}


    .screen-grid {{

        grid-template-columns:
            1fr;

    }}


    .desktop-column {{

        display:
            none;

    }}


    th.desktop-column {{

        display:
            none;

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


<!-- ========================================
     MICRON FOCUS
========================================= -->


<div class="
    card
    micron-card
">

    {micron_focus(
        micron
    )}

</div>


<!-- ========================================
     US TOP OPPORTUNITIES
========================================= -->


<div class="
    card
    section
">

    <div class="section-header">

        <div>

            <div class="section-title">
                🇺🇸 US Top Opportunities
            </div>

            <div class="section-subtitle">
                Highest-ranked stocks in the current US watch universe
            </div>

        </div>

    </div>


    <div class="opportunity-grid">

        {opportunity_cards(
            us_results,
            5,
        )}

    </div>

</div>


<!-- ========================================
     SINGAPORE TOP OPPORTUNITIES
========================================= -->


<div class="
    card
    section
">

    <div class="section-header">

        <div>

            <div class="section-title">
                🇸🇬 Singapore Top Opportunities
            </div>

            <div class="section-subtitle">
                Highest-ranked SGX stocks in the current watch universe
            </div>

        </div>

    </div>


    <div class="opportunity-grid">

        {opportunity_cards(
            singapore_results,
            5,
        )}

    </div>

</div>


<!-- ========================================
     MARKET SCREENS
========================================= -->


<div class="
    card
    section
">

    <div class="section-title">
        Market Opportunity Screens
    </div>


    <div class="screen-grid">


        <div class="screen-card">

            <div class="screen-title">
                Oversold Watch
            </div>

            {mini_list(
                oversold,
                "rsi",
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


    </div>

</div>


<!-- ========================================
     US FULL TABLE
========================================= -->


<div class="
    card
    section
">

    <div class="section-header">

        <div>

            <div class="section-title">
                US Stock Rankings
            </div>

            <div class="section-subtitle">
                Ranked using technical, momentum, fundamental and valuation factors
            </div>

        </div>

    </div>


    <div class="table-wrapper">

        <table>

            <thead>

                <tr>

                    <th>
                        #
                    </th>

                    <th>
                        Company
                    </th>

                    <th>
                        Price
                    </th>

                    <th>
                        Day
                    </th>

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

                    <th>
                        Score
                    </th>

                    <th>
                        Rating
                    </th>

                </tr>

            </thead>


            <tbody>

                {stock_rows(
                    us_results,
                    20,
                )}

            </tbody>

        </table>

    </div>

</div>


<!-- ========================================
     SG FULL TABLE
========================================= -->


<div class="
    card
    section
">

    <div class="section-header">

        <div>

            <div class="section-title">
                Singapore Stock Rankings
            </div>

            <div class="section-subtitle">
                Ranked across the selected SGX stock universe
            </div>

        </div>

    </div>


    <div class="table-wrapper">

        <table>

            <thead>

                <tr>

                    <th>
                        #
                    </th>

                    <th>
                        Company
                    </th>

                    <th>
                        Price
                    </th>

                    <th>
                        Day
                    </th>

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

                    <th>
                        Score
                    </th>

                    <th>
                        Rating
                    </th>

                </tr>

            </thead>


            <tbody>

                {stock_rows(
                    singapore_results,
                    20,
                )}

            </tbody>

        </table>

    </div>

</div>


<div class="footer">

    Automated quantitative research dashboard.

    <br>

    Ratings are generated from third-party market and fundamental data
    and should not be treated as financial advice.

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
        page,
        encoding="utf-8",
    )

    print(
        "Main stock intelligence dashboard generated successfully."
    )


if __name__ == "__main__":
    main()
