from datetime import datetime, timezone
from pathlib import Path
import html

from scanner import run_scanner


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

        return (
            f"S${price:,.2f}"
        )

    return (
        f"${price:,.2f}"
    )


def format_percent(value):

    if value is None:
        return "N/A"

    return (
        f"{value * 100:+.2f}%"
    )


def rating_class(
    value,
):

    return (

        value
        .lower()
        .replace(
            " ",
            "-",
        )

    )


def opportunity_cards(
    stocks,
    count=5,
):

    output = ""


    for stock in stocks[:count]:

        change_class = (

            "positive"

            if stock[
                "daily_change"
            ] >= 0

            else

            "negative"

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
                    stock[
                        "daily_change"
                    ]
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


def stock_rows(
    stocks,
    limit=20,
):

    output = ""


    for rank, stock in enumerate(

        stocks[:limit],

        start=1,

    ):


        change_class = (

            "positive"

            if stock[
                "daily_change"
            ] >= 0

            else

            "negative"

        )


        css_rating = rating_class(
            stock["rating"]
        )


        output += f"""

        <tr>


            <td>
                {rank}
            </td>


            <td>


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


            </td>


            <td>

                {format_price(

                    stock["price"],

                    stock["market"],

                )}

            </td>


            <td class="{change_class}">

                {format_percent(
                    stock[
                        "daily_change"
                    ]
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

        <div class="muted">

            Micron data unavailable.

        </div>

        """


    change_class = (

        "positive"

        if micron[
            "daily_change"
        ] >= 0

        else

        "negative"

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

                    micron[
                        "daily_change"
                    ]

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


def main():


    print(

        "Running stock scanner..."

    )


    scan_data = run_scanner()


    us_results = scan_data[
        "us"
    ]


    singapore_results = scan_data[
        "singapore"
    ]


    micron = find_micron(
        us_results
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

    box-sizing:
        border-box;

}}


body {{

    margin:
        0;

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
        auto;

    padding:
        28px 0
        60px;

}}


.header {{

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        flex-end;

    margin-bottom:
        24px;

}}


.main-title {{

    font-size:
        36px;

    font-weight:
        800;

}}


.subtitle,
.muted {{

    color:
        #8ca5c4;

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

    margin-top:
        4px;

    margin-bottom:
        16px;

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

}}


.micron-title {{

    font-size:
        27px;

    font-weight:
        800;

    margin:
        7px 0;

}}


.micron-price,
.micron-score {{

    font-size:
        32px;

    font-weight:
        800;

}}


.primary-button {{

    display:
        inline-block;

    background:
        #55a8fa;

    color:
        #06111f;

    font-weight:
        800;

    text-decoration:
        none;

    padding:
        14px 18px;

    border-radius:
        10px;

}}


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
        4px;

    min-height:
        30px;

}}


.opportunity-price {{

    font-size:
        23px;

    font-weight:
        800;

    margin-top:
        18px;

}}


.score-row {{

    display:
        flex;

    justify-content:
        space-between;

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


.rating-badge {{

    display:
        inline-block;

    padding:
        5px 8px;

    border-radius:
        7px;

    font-size:
        10px;

    font-weight:
        800;

}}


.strong-buy {{

    color:
        #51e5a0;

    background:
        rgba(
            55,
            219,
            143,
            0.15
        );

}}


.buy {{

    color:
        #66bdff;

    background:
        rgba(
            86,
            184,
            255,
            0.15
        );

}}


.hold {{

    color:
        #f4cd69;

}}


.watch {{

    color:
        #ffa165;

}}


.caution {{

    color:
        #ff7183;

}}


.positive {{

    color:
        #51e0a0;

}}


.negative {{

    color:
        #ff7183;

}}


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


th,
td {{

    padding:
        13px 10px;

    text-align:
        left;

    border-bottom:
        1px solid
        #20344f;

}}


th {{

    color:
        #7892b1;

    font-size:
        11px;

}}


td {{

    font-size:
        13px;

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

}}


.footer {{

    text-align:
        center;

    color:
        #6f88a8;

    margin-top:
        30px;

    font-size:
        12px;

}}


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

}}


@media (
    max-width: 720px
) {{

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


    .opportunity-grid,
    .micron-layout {{

        grid-template-columns:
            1fr;

    }}


    .desktop-column {{

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

        Highest-ranked stocks in the current US watch universe

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

        Highest-ranked SGX stocks in the current Singapore watch universe

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

        US Stock Rankings

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


<div class="
    card
    section
">


    <div class="section-title">

        Singapore Stock Rankings

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

    Ratings are research indicators
    and are not financial advice.

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

        "Main dashboard generated successfully."

    )


if __name__ == "__main__":

    main()
