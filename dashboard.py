from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import html
import json
import re

from scanner import run_scanner


# ============================================================
# HISTORY + WATCHLIST SETTINGS
# ============================================================

HISTORY_PATH = Path("docs/data/score-history.json")
WATCHLIST_PATH = Path("watchlist.json")
MAX_HISTORY_SNAPSHOTS = 365

DEFAULT_WATCHLIST = [
    "MU",
    "NVDA",
    "AMD",
    "JPM",
    "D05.SI",
    "U11.SI",
]


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


def format_percent(
    value,
    signed=True,
):
    if value is None:
        return "N/A"

    if signed:
        return f"{value * 100:+.2f}%"

    return f"{value * 100:.1f}%"


def format_large_number(value):
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

    return f"${value:,.0f}"


def format_number(
    value,
    decimals=1,
):
    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}"


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


def score_commentary(
    score,
    category,
):
    if score >= 80:
        return (
            f"{category} conditions "
            f"are currently strong."
        )

    if score >= 65:
        return (
            f"{category} conditions "
            f"are currently positive."
        )

    if score >= 50:
        return (
            f"{category} conditions "
            f"are broadly neutral."
        )

    if score >= 35:
        return (
            f"{category} conditions "
            f"are currently weak."
        )

    return (
        f"{category} conditions "
        f"are currently very weak."
    )


# ============================================================
# HISTORY + WATCHLIST HELPERS
# ============================================================

def load_watchlist():

    if not WATCHLIST_PATH.exists():
        return DEFAULT_WATCHLIST

    try:

        data = json.loads(
            WATCHLIST_PATH.read_text(
                encoding="utf-8"
            )
        )

        tickers = data.get(
            "tickers",
            [],
        )

        if not isinstance(
            tickers,
            list,
        ):
            return DEFAULT_WATCHLIST

        return [
            str(ticker)
            .strip()
            .upper()

            for ticker
            in tickers

            if str(ticker)
            .strip()
        ]

    except Exception as error:

        print(
            "Could not read "
            "watchlist.json: "
            f"{error}"
        )

        return DEFAULT_WATCHLIST


def load_history():

    if not HISTORY_PATH.exists():
        return []

    try:

        data = json.loads(
            HISTORY_PATH.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(
            data,
            list,
        ):
            return data

    except Exception as error:

        print(
            "Could not read "
            "score history: "
            f"{error}"
        )

    return []


def make_history_snapshot(
    stocks,
    updated_iso,
):

    stock_data = {}

    for stock in stocks:

        stock_data[
            stock["ticker"]
        ] = {

            "name":
                stock["name"],

            "market":
                stock["market"],

            "sector":
                stock["sector"],

            "overall":
                stock["overall"],

            "technical":
                stock["technical"],

            "momentum":
                stock["momentum"],

            "fundamental":
                stock["fundamental"],

            "valuation":
                stock["valuation"],

            "balanced_score":
                stock[
                    "balanced_score"
                ],

            "rating":
                stock["rating"],

            "price":
                round(
                    stock["price"],
                    4,
                ),
        }

    return {

        "timestamp":
            updated_iso,

        "stocks":
            stock_data,
    }


def save_history(
    history,
    snapshot,
):

    history.append(
        snapshot
    )

    history = history[
        -MAX_HISTORY_SNAPSHOTS:
    ]

    HISTORY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    HISTORY_PATH.write_text(

        json.dumps(
            history,
            indent=2,
        ),

        encoding="utf-8",
    )

    return history


def previous_snapshot(history):

    if not history:
        return None

    return history[-1]


def get_stock_changes(
    stocks,
    previous,
):

    if not previous:
        return []

    old_stocks = previous.get(
        "stocks",
        {},
    )

    changes = []

    for stock in stocks:

        old = old_stocks.get(
            stock["ticker"]
        )

        if not old:

            changes.append({

                "stock":
                    stock,

                "type":
                    "new",

                "overall_change":
                    0,

                "rating_changed":
                    True,

                "old_rating":
                    "NEW",
            })

            continue


        overall_change = (

            stock["overall"]

            -

            old.get(
                "overall",
                stock["overall"],
            )
        )


        rating_changed = (

            stock["rating"]

            !=

            old.get(
                "rating",
                stock["rating"],
            )
        )


        component_changes = {

            "Technical":

                stock["technical"]

                -

                old.get(
                    "technical",
                    stock["technical"],
                ),


            "Momentum":

                stock["momentum"]

                -

                old.get(
                    "momentum",
                    stock["momentum"],
                ),


            "Fundamentals":

                stock["fundamental"]

                -

                old.get(
                    "fundamental",
                    stock["fundamental"],
                ),


            "Valuation":

                stock["valuation"]

                -

                old.get(
                    "valuation",
                    stock["valuation"],
                ),
        }


        if (

            overall_change != 0

            or

            rating_changed

            or

            any(

                value != 0

                for value

                in component_changes.values()

            )

        ):

            changes.append({

                "stock":
                    stock,

                "type":
                    "changed",

                "overall_change":
                    overall_change,

                "rating_changed":
                    rating_changed,

                "old_rating":

                    old.get(
                        "rating",
                        "N/A",
                    ),

                "old_overall":

                    old.get(
                        "overall"
                    ),

                "component_changes":
                    component_changes,
            })


    changes.sort(

        key=lambda item: (

            item[
                "rating_changed"
            ],

            abs(
                item[
                    "overall_change"
                ]
            ),

            max(

                [

                    abs(value)

                    for value

                    in item.get(
                        "component_changes",
                        {},
                    ).values()

                ]

                or

                [0]

            ),

        ),

        reverse=True,
    )


    return changes


def get_watchlist_stocks(
    stocks,
    watchlist_tickers,
):

    stock_map = {

        stock[
            "ticker"
        ].upper():

        stock

        for stock

        in stocks
    }


    return [

        stock_map[
            ticker
        ]

        for ticker

        in watchlist_tickers

        if ticker

        in stock_map
    ]


def change_arrow(value):

    if value > 0:
        return "↑"

    if value < 0:
        return "↓"

    return "→"


def signed_score_change(value):

    if value > 0:
        return f"+{value}"

    return str(value)


def changes_panel(
    changes,
    previous,
    limit=8,
):

    if not previous:

        return """
        <div class="empty-state">

            Score history starts with this run.

            The next dashboard update will show
            what changed.

        </div>
        """


    if not changes:

        return """
        <div class="empty-state">

            No score or rating changes were
            detected since the previous scan.

        </div>
        """


    output = ""


    for item in changes[
        :limit
    ]:

        stock = item[
            "stock"
        ]

        overall_change = item[
            "overall_change"
        ]


        direction_class = (

            "positive"

            if overall_change > 0

            else

            "negative"

            if overall_change < 0

            else

            "muted"
        )


        if item[
            "type"
        ] == "new":

            summary = (
                "Newly added to "
                "the tracked universe"
            )

        else:

            old_overall = item.get(
                "old_overall"
            )

            summary = (

                f'Overall '
                f'{old_overall} '
                f'→ '
                f'{stock["overall"]} '

                f'('
                f'{signed_score_change(overall_change)}'
                f')'
            )


        rating_line = ""


        if item.get(
            "rating_changed"
        ):

            rating_line = (

                '<div class="change-rating">'

                'Rating: '

                f'{escape(item.get("old_rating", "N/A"))}'

                ' → '

                f'{escape(stock["rating"])}'

                '</div>'
            )


        components = item.get(
            "component_changes",
            {},
        )


        component_text = (
            " · ".join(

                f'{name} '
                f'{change_arrow(value)} '
                f'{signed_score_change(value)}'

                for name, value

                in components.items()

                if value != 0
            )
        )


        output += f"""
        <a
            class="change-card"
            href="{stock_url(stock)}"
        >

            <div class="change-top">

                <div>

                    <div class="change-ticker">
                        {escape(
                            stock["ticker"]
                        )}
                    </div>

                    <div class="change-name">
                        {escape(
                            stock["name"]
                        )}
                    </div>

                </div>


                <div class="
                    change-score
                    {direction_class}
                ">

                    {change_arrow(
                        overall_change
                    )}

                    {signed_score_change(
                        overall_change
                    )}

                </div>

            </div>


            <div class="change-summary">
                {summary}
            </div>


            {rating_line}


            <div class="change-components">

                {
                    escape(
                        component_text
                    )

                    if component_text

                    else

                    "Component scores unchanged"
                }

            </div>

        </a>
        """


    return output


# ============================================================
# TOOLTIPS
# ============================================================

TOOLTIPS = {

    "overall":

        "The combined dashboard score. "
        "It uses Technical 25%, Momentum 20%, "
        "Fundamentals 40% and Valuation 15%.",


    "technical":

        "Measures the stock's current price trend "
        "using moving averages, RSI and MACD. "
        "A higher score indicates stronger "
        "technical conditions.",


    "momentum":

        "Measures recent share-price performance "
        "across approximately 1 week, 1 month, "
        "3 months and 6 months.",


    "fundamental":

        "Measures available business strength "
        "using revenue growth, earnings growth, "
        "margins, return on equity, debt "
        "and liquidity.",


    "valuation":

        "Measures how attractively the stock "
        "appears priced using available valuation "
        "indicators such as forward P/E "
        "and price-to-book.",


    "data_quality":

        "Shows how much of the fundamental scoring "
        "model had usable data. Lower data quality "
        "means the score should be interpreted "
        "more cautiously.",


    "oversold":

        "Stocks with RSI below 35. "
        "This indicates weak recent price momentum, "
        "but does not guarantee that the stock "
        "will rebound.",


    "momentum_leaders":

        "Stocks with strong recent price performance "
        "that also meet minimum fundamental "
        "and data-quality requirements.",


    "value_opportunity":

        "An equal combination of the Fundamental "
        "Score and Valuation Score.",


    "balanced":

        "Rewards stocks that perform consistently "
        "across Technical, Momentum, Fundamentals "
        "and Valuation while penalising large "
        "score differences.",


    "dashboard_rating":

        "An automated quantitative rating generated "
        "by V Stock Intelligence. It is not an "
        "analyst recommendation and is not "
        "financial advice.",
}


def info_icon(key):

    text = TOOLTIPS.get(
        key,
        "",
    )

    return f"""
    <span
        class="info-wrap"
        tabindex="0"
        aria-label="{escape(text)}"
    >

        ⓘ

        <span class="tooltip">
            {escape(text)}
        </span>

    </span>
    """


# ============================================================
# OPPORTUNITY / RANKING HELPERS
# ============================================================

def opportunity_cards(
    stocks,
    count=5,
):

    output = ""


    for stock in stocks[
        :count
    ]:

        change_class = (

            "positive"

            if stock[
                "daily_change"
            ] >= 0

            else

            "negative"
        )


        css_rating = rating_class(
            stock[
                "rating"
            ]
        )


        quality_css = quality_class(
            stock[
                "data_quality"
            ]
        )


        output += f"""
        <a
            class="
                opportunity-card
                filterable-card
            "

            href="{stock_url(stock)}"

            data-market="
                {escape(stock["market"])}
            "

            data-sector="
                {escape(stock["sector"])}
            "

            data-search="
                {
                    escape(
                        (
                            stock["ticker"]
                            +
                            " "
                            +
                            stock["name"]
                        ).lower()
                    )
                }
            "
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
                    stock[
                        "price"
                    ],
                    stock[
                        "market"
                    ],
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
                    Overall
                </div>

                <div>
                    {stock[
                        "overall"
                    ]}/100
                </div>

            </div>


            <div class="score-row">

                <div>
                    Technical
                </div>

                <div>
                    {stock[
                        "technical"
                    ]}
                </div>

            </div>


            <div class="score-row">

                <div>
                    Momentum
                </div>

                <div>
                    {stock[
                        "momentum"
                    ]}
                </div>

            </div>


            <div class="score-row">

                <div>
                    Fundamentals
                </div>

                <div>
                    {stock[
                        "fundamental"
                    ]}
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
                        stock[
                            "data_quality"
                        ]
                    )}

                </span>

            </div>

        </a>
        """


    return output


def stock_rows(
    stocks,
    limit=100,
):

    output = ""


    for rank, stock in enumerate(

        stocks[
            :limit
        ],

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
            stock[
                "rating"
            ]
        )


        quality_css = quality_class(
            stock[
                "data_quality"
            ]
        )


        search_text = escape(

            (

                stock[
                    "ticker"
                ]

                +

                " "

                +

                stock[
                    "name"
                ]

            ).lower()

        )


        output += f"""
        <tr
            class="filterable-row"

            data-market="
                {escape(stock["market"])}
            "

            data-sector="
                {escape(stock["sector"])}
            "

            data-search="
                {search_text}
            "
        >

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

                    stock[
                        "price"
                    ],

                    stock[
                        "market"
                    ],

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
                {stock[
                    "technical"
                ]}
            </td>


            <td class="desktop-column">
                {stock[
                    "momentum"
                ]}
            </td>


            <td class="desktop-column">
                {stock[
                    "fundamental"
                ]}
            </td>


            <td class="desktop-column">
                {stock[
                    "valuation"
                ]}
            </td>


            <td class="score">
                {stock[
                    "overall"
                ]}
            </td>


            <td>

                <span class="
                    quality-badge
                    {quality_css}
                ">

                    {stock[
                        "data_quality"
                    ]}%

                </span>

            </td>


            <td>

                <span class="
                    rating-badge
                    {css_rating}
                ">

                    {escape(
                        stock[
                            "rating"
                        ]
                    )}

                </span>

            </td>

        </tr>
        """


    return output


def find_micron(us_results):

    for stock in us_results:

        if stock[
            "ticker"
        ] == "MU":

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

        if micron[
            "daily_change"
        ] >= 0

        else

        "negative"
    )


    css_rating = rating_class(
        micron[
            "rating"
        ]
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
                    micron[
                        "price"
                    ],
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
                {micron[
                    "overall"
                ]}/100
            </div>

            <span class="
                rating-badge
                {css_rating}
            ">

                {escape(
                    micron[
                        "rating"
                    ]
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


def get_oversold(stocks):

    results = [

        stock

        for stock

        in stocks

        if (

            stock[
                "rsi"
            ] is not None

            and

            stock[
                "rsi"
            ] < 35

        )

    ]


    return sorted(

        results,

        key=lambda stock:

            stock[
                "rsi"
            ],

    )


def get_momentum_leaders(stocks):

    eligible = [

        stock

        for stock

        in stocks

        if (

            stock[
                "fundamental"
            ] >= 50

            and

            stock[
                "data_quality"
            ] >= 60

        )

    ]


    return sorted(

        eligible,

        key=lambda stock: (

            stock[
                "momentum"
            ],

            stock[
                "overall"
            ],

        ),

        reverse=True,

    )


def get_value_opportunities(stocks):

    eligible = [

        stock

        for stock

        in stocks

        if stock[
            "data_quality"
        ] >= 60

    ]


    return sorted(

        eligible,

        key=value_opportunity_score,

        reverse=True,

    )


def get_balanced_opportunities(stocks):

    eligible = [

        stock

        for stock

        in stocks

        if stock[
            "data_quality"
        ] >= 60

    ]


    return sorted(

        eligible,

        key=lambda stock:

            stock[
                "balanced_score"
            ],

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


    for stock in stocks[
        :limit
    ]:


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

                f'{
                    value_opportunity_score(
                        stock
                    )
                }/100'

            )

            secondary = (

                f'Valuation '
                f'{stock["valuation"]}'

                f' · '

                f'Fundamentals '
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

                f' · '

                f'Data '
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
# PRICE CHART
# ============================================================

def chart_svg(stock):

    prices = stock.get(
        "chart_prices"
    ) or []


    if len(
        prices
    ) < 2:

        return """
        <div class="muted">
            Chart data unavailable.
        </div>
        """


    width = 900

    height = 260

    padding = 18


    minimum = min(
        prices
    )

    maximum = max(
        prices
    )


    price_range = (
        maximum
        -
        minimum
    )


    if price_range == 0:
        price_range = 1


    points = []


    for index, value in enumerate(
        prices
    ):

        x = (

            padding

            +

            index

            *

            (

                (
                    width
                    -
                    padding
                    * 2
                )

                /

                (
                    len(prices)
                    -
                    1
                )

            )

        )


        y = (

            height

            -

            padding

            -

            (

                (
                    value
                    -
                    minimum
                )

                /

                price_range

            )

            *

            (
                height
                -
                padding
                * 2
            )

        )


        points.append(
            f"{x:.1f},{y:.1f}"
        )


    points_string = " ".join(
        points
    )


    return f"""
    <svg
        class="price-chart"
        viewBox="
            0
            0
            {width}
            {height}
        "
        preserveAspectRatio="none"
        role="img"
        aria-label="Six month closing price trend"
    >

        <polyline
            points="{points_string}"
            fill="none"
            stroke="#63b8ff"
            stroke-width="3"
        />

    </svg>

    <div class="chart-scale">

        <span>
            Low:
            {format_price(
                minimum,
                stock[
                    "market"
                ],
            )}
        </span>

        <span>
            Latest:
            {format_price(
                prices[-1],
                stock[
                    "market"
                ],
            )}
        </span>

        <span>
            High:
            {format_price(
                maximum,
                stock[
                    "market"
                ],
            )}
        </span>

    </div>
    """


# ============================================================
# STOCK DETAIL PAGE
# ============================================================

def generate_stock_detail_page(
    stock,
    updated,
):

    css_rating = rating_class(
        stock[
            "rating"
        ]
    )


    quality_css = quality_class(
        stock[
            "data_quality"
        ]
    )


    change_class = (

        "positive"

        if stock[
            "daily_change"
        ] >= 0

        else

        "negative"
    )


    value_score = value_opportunity_score(
        stock
    )


    analyst_upside_class = (

        "positive"

        if (
            stock.get(
                "analyst_upside"
            )
            or 0
        ) >= 0

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
    content="
        width=device-width,
        initial-scale=1.0
    "
>

<title>

V Stock Intelligence ·
{escape(stock["ticker"])}

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
            1180px,
            94%
        );

    margin:
        auto;

    padding:
        30px 0 60px;
}}

.top-nav {{
    display:
        flex;

    gap:
        20px;

    flex-wrap:
        wrap;
}}

.top-nav a {{
    color:
        #68b9ff;

    text-decoration:
        none;

    font-size:
        13px;
}}

.header {{
    margin-top:
        24px;
}}

.title {{
    font-size:
        34px;

    font-weight:
        800;
}}

.subtitle {{
    color:
        #8ca5c4;

    margin-top:
        6px;
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

.hero {{
    display:
        grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                190px,
                1fr
            )
        );

    gap:
        14px;

    margin-top:
        24px;
}}

.label {{
    color:
        #8ba4c3;

    font-size:
        11px;

    text-transform:
        uppercase;
}}

.big {{
    font-size:
        32px;

    font-weight:
        800;

    margin-top:
        7px;
}}

.grid {{
    display:
        grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                180px,
                1fr
            )
        );

    gap:
        13px;
}}

.metric {{
    background:
        #0b1728;

    border-radius:
        12px;

    padding:
        17px;
}}

.metric-value {{
    font-size:
        24px;

    font-weight:
        800;

    margin-top:
        7px;
}}

.section-title {{
    font-size:
        21px;

    font-weight:
        800;

    margin-bottom:
        15px;
}}

.comment {{
    color:
        #aebfd4;

    font-size:
        13px;

    line-height:
        1.5;

    margin-top:
        8px;
}}

.positive {{
    color:
        #51e0a0;
}}

.negative {{
    color:
        #ff7183;
}}

.rating-badge,
.quality-badge {{
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

.quality-good {{
    color:
        #55dea0;
}}

.quality-medium {{
    color:
        #f3c968;
}}

.quality-low {{
    color:
        #ff7a87;
}}

.price-chart {{
    width:
        100%;

    height:
        300px;

    background:
        #0b1728;

    border-radius:
        12px;

    display:
        block;
}}

.chart-scale {{
    display:
        flex;

    justify-content:
        space-between;

    gap:
        12px;

    color:
        #718ba9;

    font-size:
        11px;

    margin-top:
        9px;

    flex-wrap:
        wrap;
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

    line-height:
        1.6;
}}

</style>

</head>


<body>

<div class="container">


<div class="top-nav">

    <a href="../../">
        ← Back to Market Dashboard
    </a>

    <a href="../../guide/">
        How to Read This Dashboard
    </a>

</div>


<div class="header">

    <div class="title">
        {escape(
            stock[
                "name"
            ]
        )}
    </div>

    <div class="subtitle">

        {escape(
            stock[
                "ticker"
            ]
        )}

        ·

        {escape(
            stock[
                "sector"
            ]
        )}

        ·

        {escape(
            stock[
                "market"
            ]
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

            stock[
                "price"
            ],

            stock[
                "market"
            ],

        )}

    </div>

    <div class="{change_class}">

        {format_percent(
            stock[
                "daily_change"
            ]
        )}

    </div>

</div>


<div class="card">

    <div class="label">
        Dashboard Rating
    </div>

    <div class="big">
        {stock[
            "overall"
        ]}/100
    </div>

    <div style="margin-top:8px;">

        <span class="
            rating-badge
            {css_rating}
        ">

            {escape(
                stock[
                    "rating"
                ]
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
        {stock[
            "data_quality"
        ]}%
    </div>

    <div style="margin-top:8px;">

        <span class="
            quality-badge
            {quality_css}
        ">

            {quality_label(
                stock[
                    "data_quality"
                ]
            )}

        </span>

    </div>

</div>


</div>


<div class="card section">

    <div class="section-title">
        Six-Month Price Trend
    </div>

    {chart_svg(
        stock
    )}

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
                {stock[
                    "technical"
                ]}/100
            </div>

            <div class="comment">

                {score_commentary(

                    stock[
                        "technical"
                    ],

                    "Technical",

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Momentum
            </div>

            <div class="metric-value">
                {stock[
                    "momentum"
                ]}/100
            </div>

            <div class="comment">

                {score_commentary(

                    stock[
                        "momentum"
                    ],

                    "Momentum",

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Fundamentals
            </div>

            <div class="metric-value">
                {stock[
                    "fundamental"
                ]}/100
            </div>

            <div class="comment">

                {score_commentary(

                    stock[
                        "fundamental"
                    ],

                    "Fundamental",

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Valuation
            </div>

            <div class="metric-value">
                {stock[
                    "valuation"
                ]}/100
            </div>

            <div class="comment">

                {score_commentary(

                    stock[
                        "valuation"
                    ],

                    "Valuation",

                )}

            </div>

        </div>


    </div>

</div>


<div class="card section">

    <div class="section-title">
        Price & Technical Context
    </div>

    <div class="grid">


        <div class="metric">

            <div class="label">
                RSI
            </div>

            <div class="metric-value">

                {format_number(
                    stock.get(
                        "rsi"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                20 Day MA
            </div>

            <div class="metric-value">

                {format_price(

                    stock.get(
                        "ma20"
                    ),

                    stock[
                        "market"
                    ],

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                50 Day MA
            </div>

            <div class="metric-value">

                {format_price(

                    stock.get(
                        "ma50"
                    ),

                    stock[
                        "market"
                    ],

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                200 Day MA
            </div>

            <div class="metric-value">

                {format_price(

                    stock.get(
                        "ma200"
                    ),

                    stock[
                        "market"
                    ],

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                52 Week Low
            </div>

            <div class="metric-value">

                {format_price(

                    stock.get(
                        "low_52"
                    ),

                    stock[
                        "market"
                    ],

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                52 Week High
            </div>

            <div class="metric-value">

                {format_price(

                    stock.get(
                        "high_52"
                    ),

                    stock[
                        "market"
                    ],

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Support
            </div>

            <div class="metric-value">

                {format_price(

                    stock.get(
                        "support"
                    ),

                    stock[
                        "market"
                    ],

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Resistance
            </div>

            <div class="metric-value">

                {format_price(

                    stock.get(
                        "resistance"
                    ),

                    stock[
                        "market"
                    ],

                )}

            </div>

        </div>


    </div>

</div>


<div class="card section">

    <div class="section-title">
        Recent Performance
    </div>

    <div class="grid">


        <div class="metric">

            <div class="label">
                1 Month
            </div>

            <div class="metric-value">

                {format_percent(
                    stock.get(
                        "return_1m"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                3 Months
            </div>

            <div class="metric-value">

                {format_percent(
                    stock.get(
                        "return_3m"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                6 Months
            </div>

            <div class="metric-value">

                {format_percent(
                    stock.get(
                        "return_6m"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Balanced Score
            </div>

            <div class="metric-value">

                {stock[
                    "balanced_score"
                ]}/100

            </div>

        </div>


    </div>

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

            <div class="metric-value">

                {format_large_number(
                    stock.get(
                        "market_cap"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Trailing P/E
            </div>

            <div class="metric-value">

                {format_number(
                    stock.get(
                        "trailing_pe"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Forward P/E
            </div>

            <div class="metric-value">

                {format_number(
                    stock.get(
                        "forward_pe"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Price / Book
            </div>

            <div class="metric-value">

                {format_number(
                    stock.get(
                        "price_to_book"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Revenue Growth
            </div>

            <div class="metric-value">

                {format_percent(
                    stock.get(
                        "revenue_growth"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Earnings Growth
            </div>

            <div class="metric-value">

                {format_percent(
                    stock.get(
                        "earnings_growth"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Gross Margin
            </div>

            <div class="metric-value">

                {format_percent(

                    stock.get(
                        "gross_margin"
                    ),

                    signed=False,

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Operating Margin
            </div>

            <div class="metric-value">

                {format_percent(

                    stock.get(
                        "operating_margin"
                    ),

                    signed=False,

                )}

            </div>

        </div>


    </div>

</div>


<div class="card section">

    <div class="section-title">
        Analyst View
    </div>

    <div class="grid">


        <div class="metric">

            <div class="label">
                Consensus
            </div>

            <div class="metric-value">

                {escape(

                    stock.get(
                        "analyst_recommendation"
                    )

                    or

                    "N/A"

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Mean Target
            </div>

            <div class="metric-value">

                {format_price(

                    stock.get(
                        "analyst_target"
                    ),

                    stock[
                        "market"
                    ],

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Target Upside / Downside
            </div>

            <div class="
                metric-value
                {analyst_upside_class}
            ">

                {format_percent(
                    stock.get(
                        "analyst_upside"
                    )
                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Analyst Opinions
            </div>

            <div class="metric-value">

                {escape(

                    stock.get(
                        "analyst_count"
                    )

                    or

                    "N/A"

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                Low Target
            </div>

            <div class="metric-value">

                {format_price(

                    stock.get(
                        "analyst_low"
                    ),

                    stock[
                        "market"
                    ],

                )}

            </div>

        </div>


        <div class="metric">

            <div class="label">
                High Target
            </div>

            <div class="metric-value">

                {format_price(

                    stock.get(
                        "analyst_high"
                    ),

                    stock[
                        "market"
                    ],

                )}

            </div>

        </div>


    </div>

</div>


<div class="footer">

    Last updated:
    {updated}

    <br><br>

    Dashboard ratings are automated
    quantitative indicators.

    They are not analyst recommendations
    or financial advice.

</div>


</div>

</body>

</html>
"""


    output_folder = (

        Path(
            "docs"
        )

        /

        "stocks"

        /

        ticker_slug(
            stock[
                "ticker"
            ]
        )

    )


    output_folder.mkdir(

        parents=True,

        exist_ok=True,

    )


    (

        output_folder

        /

        "index.html"

    ).write_text(

        page,

        encoding="utf-8",

    )


# ============================================================
# GUIDE PAGE
# ============================================================

def generate_guide_page(updated):

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
V Stock Intelligence · Guide
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
            1000px,
            94%
        );

    margin:
        auto;

    padding:
        30px 0 70px;
}}

.back {{
    color:
        #68b9ff;

    text-decoration:
        none;

    font-size:
        13px;
}}

.title {{
    font-size:
        36px;

    font-weight:
        800;

    margin-top:
        28px;
}}

.subtitle {{
    color:
        #8ca5c4;

    margin-top:
        8px;

    line-height:
        1.5;
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
        23px;

    margin-top:
        20px;
}}

.section-title {{
    font-size:
        22px;

    font-weight:
        800;

    margin-bottom:
        18px;
}}

.term {{
    padding:
        15px 0;

    border-bottom:
        1px solid
        #263a55;
}}

.term:last-child {{
    border-bottom:
        none;
}}

.term-name {{
    font-size:
        17px;

    font-weight:
        800;
}}

.term-description {{
    color:
        #afc0d5;

    line-height:
        1.55;

    margin-top:
        6px;
}}

.score-table {{
    width:
        100%;

    border-collapse:
        collapse;
}}

.score-table td {{
    padding:
        12px 8px;

    border-bottom:
        1px solid
        #263a55;
}}

.weight {{
    color:
        #68b9ff;

    font-weight:
        800;

    text-align:
        right;
}}

.note {{
    background:
        #0b1728;

    border-radius:
        12px;

    padding:
        17px;

    color:
        #afc0d5;

    line-height:
        1.6;
}}

.footer {{
    text-align:
        center;

    color:
        #7089a8;

    margin-top:
        30px;

    font-size:
        12px;
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


<div class="title">
    How to Read V Stock Intelligence
</div>


<div class="subtitle">

    This guide explains the terminology,
    scores and opportunity screens used
    throughout the dashboard.

</div>


<div class="card">

    <div class="section-title">
        Dashboard Rating
    </div>

    <div class="note">

        Ratings such as Strong Buy,
        Buy, Hold, Watch and Caution are
        automated quantitative ratings
        created by this dashboard.

        <br><br>

        They are not analyst recommendations
        and should be used as a starting point
        for further research rather than as
        instructions to buy or sell a stock.

    </div>

</div>


<div class="card">

    <div class="section-title">
        Overall Score Methodology
    </div>

    <table class="score-table">

        <tr>
            <td>
                Technical Score
            </td>

            <td class="weight">
                25%
            </td>
        </tr>

        <tr>
            <td>
                Momentum Score
            </td>

            <td class="weight">
                20%
            </td>
        </tr>

        <tr>
            <td>
                Fundamental Score
            </td>

            <td class="weight">
                40%
            </td>
        </tr>

        <tr>
            <td>
                Valuation Score
            </td>

            <td class="weight">
                15%
            </td>
        </tr>

    </table>

</div>


<div class="card">

    <div class="section-title">
        Core Investment Scores
    </div>


    <div class="term">

        <div class="term-name">
            Technical Score
        </div>

        <div class="term-description">

            Measures the current share-price
            trend using indicators such as
            moving averages, RSI and MACD.

        </div>

    </div>


    <div class="term">

        <div class="term-name">
            Momentum Score
        </div>

        <div class="term-description">

            Measures recent price performance
            across several time periods.

        </div>

    </div>


    <div class="term">

        <div class="term-name">
            Fundamental Score
        </div>

        <div class="term-description">

            Evaluates available business and
            financial information including
            growth, margins and balance-sheet
            measures.

        </div>

    </div>


    <div class="term">

        <div class="term-name">
            Valuation Score
        </div>

        <div class="term-description">

            Estimates how attractively a stock
            appears priced using available
            valuation metrics.

        </div>

    </div>


    <div class="term">

        <div class="term-name">
            Data Quality
        </div>

        <div class="term-description">

            Shows how much of the scoring model
            had usable fundamental information.

        </div>

    </div>


</div>


<div class="card">

    <div class="section-title">
        Market Opportunity Screens
    </div>


    <div class="term">

        <div class="term-name">
            Oversold Watch
        </div>

        <div class="term-description">

            Shows stocks with RSI below 35.

            Being oversold does not mean that
            a share price will automatically
            recover.

        </div>

    </div>


    <div class="term">

        <div class="term-name">
            Momentum Leaders
        </div>

        <div class="term-description">

            Highlights stocks with stronger
            recent price performance while
            requiring minimum fundamental
            strength and sufficient data quality.

        </div>

    </div>


    <div class="term">

        <div class="term-name">
            Value Opportunities
        </div>

        <div class="term-description">

            Combines the Valuation Score and
            Fundamental Score equally.

        </div>

    </div>


    <div class="term">

        <div class="term-name">
            Best Balanced
        </div>

        <div class="term-description">

            Looks for stocks that perform
            consistently across Technical,
            Momentum, Fundamentals and Valuation.

        </div>

    </div>


</div>


<div class="card">

    <div class="section-title">
        Score History & What's Changed
    </div>

    <div class="term">

        <div class="term-name">
            Score History
        </div>

        <div class="term-description">

            Each successful dashboard scan saves
            the current scores for every tracked
            stock.

            Up to 365 scan snapshots are retained.

        </div>

    </div>


    <div class="term">

        <div class="term-name">
            What's Changed
        </div>

        <div class="term-description">

            Compares the latest dashboard scan
            against the previous saved scan.

            It highlights changes in the Overall,
            Technical, Momentum, Fundamental and
            Valuation scores, as well as changes
            in Dashboard Rating.

        </div>

    </div>

</div>


<div class="card">

    <div class="section-title">
        Important Limitations
    </div>

    <div class="note">

        The dashboard uses automated
        third-party market and financial data.

        Data may occasionally be delayed,
        incomplete or inconsistent.

        <br><br>

        Quantitative scores cannot fully capture
        company-specific risks, future events,
        management quality, macroeconomic
        conditions or sudden changes in
        market sentiment.

        <br><br>

        Always conduct additional research
        before making an investment decision.

    </div>

</div>


<div class="footer">

    Last updated:
    {updated}

</div>


</div>

</body>

</html>
"""


    output_folder = (

        Path(
            "docs"
        )

        /

        "guide"

    )


    output_folder.mkdir(

        parents=True,

        exist_ok=True,

    )


    (

        output_folder

        /

        "index.html"

    ).write_text(

        page,

        encoding="utf-8",

    )


# ============================================================
# MAIN DASHBOARD
# ============================================================

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


    all_results = (

        us_results

        +

        singapore_results

    )


    # ========================================================
    # HISTORY AND WATCHLIST
    # ========================================================

    history = load_history()


    previous = previous_snapshot(
        history
    )


    changes = get_stock_changes(

        all_results,

        previous,

    )


    watchlist_tickers = (
        load_watchlist()
    )


    watchlist_stocks = (
        get_watchlist_stocks(

            all_results,

            watchlist_tickers,

        )
    )


    # ========================================================
    # OPPORTUNITY SCREENS
    # ========================================================

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


    # ========================================================
    # SINGAPORE TIME
    # ========================================================

    now_sgt = datetime.now(
        ZoneInfo(
            "Asia/Singapore"
        )
    )


    updated = now_sgt.strftime(
        "%d %B %Y, %H:%M SGT"
    )


    updated_iso = (
        now_sgt.isoformat()
    )


    # Save the current scan
    # after comparing with the previous one.

    snapshot = make_history_snapshot(

        all_results,

        updated_iso,

    )


    save_history(

        history,

        snapshot,

    )


    # ========================================================
    # GENERATE DETAIL PAGES
    # ========================================================

    for stock in all_results:

        generate_stock_detail_page(

            stock,

            updated,

        )


    generate_guide_page(
        updated
    )


    sectors = sorted({

        stock[
            "sector"
        ]

        for stock

        in all_results

    })


    sector_options = "".join(

        f'<option value="{escape(sector)}">'
        f'{escape(sector)}'
        f'</option>'

        for sector

        in sectors

    )


    watchlist_html = "".join(

        f"""
        <a
            class="watch-card"
            href="{stock_url(stock)}"
        >

            <div class="watch-ticker">
                {escape(
                    stock["ticker"]
                )}
            </div>

            <div class="watch-name">
                {escape(
                    stock["name"]
                )}
            </div>

            <div class="watch-score">
                {stock[
                    "overall"
                ]}/100
            </div>

            <div class="watch-meta">

                <span>
                    {escape(
                        stock[
                            "rating"
                        ]
                    )}
                </span>

                <span>
                    {format_percent(
                        stock[
                            "daily_change"
                        ]
                    )}
                </span>

            </div>

        </a>
        """

        for stock

        in watchlist_stocks

    )


    if not watchlist_html:

        watchlist_html = """
        <div class="empty-state">

            No watchlist stocks were found
            in the current scan.

        </div>
        """


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
        28px 0 60px;
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

    gap:
        20px;
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

.nav {{
    margin-top:
        10px;
}}

.nav a {{
    color:
        #68b9ff;

    text-decoration:
        none;

    font-size:
        13px;

    font-weight:
        700;
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
        5px;

    margin-bottom:
        16px;

    line-height:
        1.4;
}}

.filter-bar {{
    display:
        grid;

    grid-template-columns:
        2fr
        1fr
        1fr
        auto;

    gap:
        12px;

    align-items:
        center;

    margin-bottom:
        20px;
}}

.filter-bar input,
.filter-bar select {{
    width:
        100%;

    background:
        #0b1728;

    border:
        1px solid
        #2b4363;

    color:
        #edf4ff;

    border-radius:
        10px;

    padding:
        12px;

    font-size:
        14px;
}}

.filter-bar button {{
    background:
        #203653;

    border:
        1px solid
        #345477;

    color:
        #dce9f9;

    border-radius:
        10px;

    padding:
        12px 16px;

    font-weight:
        700;

    cursor:
        pointer;
}}

.filter-status {{
    color:
        #7892b1;

    font-size:
        12px;

    margin-top:
        10px;
}}

.info-wrap {{
    position:
        relative;

    display:
        inline-block;

    margin-left:
        5px;

    color:
        #68b9ff;

    cursor:
        help;

    font-size:
        14px;

    outline:
        none;
}}

.tooltip {{
    visibility:
        hidden;

    opacity:
        0;

    position:
        absolute;

    z-index:
        100;

    left:
        50%;

    top:
        25px;

    transform:
        translateX(
            -50%
        );

    width:
        280px;

    background:
        #020912;

    color:
        #d9e5f5;

    border:
        1px solid
        #345274;

    border-radius:
        10px;

    padding:
        12px;

    font-size:
        12px;

    font-weight:
        normal;

    line-height:
        1.45;

    text-align:
        left;
}}

.info-wrap:hover
.tooltip,
.info-wrap:focus
.tooltip {{
    visibility:
        visible;

    opacity:
        1;
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

.watchlist-grid {{
    display:
        grid;

    grid-template-columns:
        repeat(
            6,
            1fr
        );

    gap:
        12px;
}}

.watch-card {{
    display:
        block;

    background:
        #0b1728;

    border-radius:
        12px;

    padding:
        15px;

    text-decoration:
        none;

    color:
        inherit;
}}

.watch-card:hover {{
    background:
        #10203a;
}}

.watch-ticker {{
    font-size:
        18px;

    font-weight:
        800;
}}

.watch-name {{
    color:
        #7f98b7;

    font-size:
        11px;

    margin-top:
        3px;

    min-height:
        28px;
}}

.watch-score {{
    font-size:
        24px;

    font-weight:
        800;

    margin-top:
        12px;
}}

.watch-meta {{
    display:
        flex;

    justify-content:
        space-between;

    gap:
        8px;

    margin-top:
        8px;

    color:
        #8ba4c3;

    font-size:
        11px;
}}

.changes-grid {{
    display:
        grid;

    grid-template-columns:
        repeat(
            4,
            1fr
        );

    gap:
        12px;
}}

.change-card {{
    display:
        block;

    background:
        #0b1728;

    border-radius:
        12px;

    padding:
        15px;

    text-decoration:
        none;

    color:
        inherit;
}}

.change-card:hover {{
    background:
        #10203a;
}}

.change-top {{
    display:
        flex;

    justify-content:
        space-between;

    gap:
        12px;
}}

.change-ticker {{
    font-weight:
        800;

    font-size:
        18px;
}}

.change-name {{
    color:
        #7f98b7;

    font-size:
        11px;

    margin-top:
        3px;
}}

.change-score {{
    font-size:
        18px;

    font-weight:
        800;
}}

.change-summary {{
    font-size:
        12px;

    margin-top:
        12px;
}}

.change-rating {{
    font-size:
        11px;

    color:
        #f3c968;

    margin-top:
        6px;
}}

.change-components {{
    font-size:
        10px;

    color:
        #718ba9;

    margin-top:
        7px;

    line-height:
        1.4;
}}

.empty-state {{
    background:
        #0b1728;

    border-radius:
        12px;

    padding:
        18px;

    color:
        #8da5c2;

    font-size:
        13px;
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
    display:
        block;

    background:
        #0b1728;

    border-radius:
        13px;

    padding:
        16px;

    text-decoration:
        none;

    color:
        inherit;
}}

.opportunity-card:hover {{
    background:
        #10203a;
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
}}

.sector {{
    color:
        #607c9f;

    font-size:
        10px;

    margin-top:
        4px;
}}

.opportunity-price {{
    font-size:
        23px;

    font-weight:
        800;

    margin-top:
        18px;
}}

.score-row,
.quality-row {{
    display:
        flex;

    justify-content:
        space-between;

    align-items:
        center;

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

.quality-row {{
    border-bottom:
        none;
}}

.rating-badge,
.quality-badge {{
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

.quality-good {{
    color:
        #55dea0;
}}

.quality-medium {{
    color:
        #f3c968;
}}

.quality-low {{
    color:
        #ff7a87;
}}

.positive {{
    color:
        #51e0a0;
}}

.negative {{
    color:
        #ff7183;
}}

.screen-grid {{
    display:
        grid;

    grid-template-columns:
        repeat(
            4,
            1fr
        );

    gap:
        14px;
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
        5px;
}}

.screen-description {{
    color:
        #718ba9;

    font-size:
        11px;

    line-height:
        1.4;

    min-height:
        48px;

    margin-bottom:
        8px;
}}

.mini-row {{
    display:
        flex;

    justify-content:
        space-between;

    gap:
        12px;

    padding:
        11px 0;

    border-bottom:
        1px solid
        #223650;

    text-decoration:
        none;

    color:
        inherit;
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
    color:
        #7b95b5;

    font-size:
        11px;

    margin-top:
        3px;
}}

.mini-right {{
    text-align:
        right;
}}

.mini-score {{
    color:
        #62b8ff;

    font-size:
        12px;

    font-weight:
        700;
}}

.mini-secondary {{
    color:
        #708aa9;

    font-size:
        10px;

    margin-top:
        4px;
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

.stock-link {{
    color:
        inherit;

    text-decoration:
        none;
}}

.stock-link:hover
.stock-name {{
    color:
        #62b8ff;
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

.hidden-by-filter {{
    display:
        none
        !important;
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

    line-height:
        1.6;
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

    .screen-grid {{
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

    .filter-bar {{
        grid-template-columns:
            1fr
            1fr;
    }}

    .watchlist-grid {{
        grid-template-columns:
            repeat(
                3,
                1fr
            );
    }}

    .changes-grid {{
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
    .screen-grid,
    .micron-layout,
    .filter-bar,
    .watchlist-grid,
    .changes-grid {{
        grid-template-columns:
            1fr;
    }}

    .desktop-column {{
        display:
            none;
    }}

    .tooltip {{
        width:
            240px;
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

        <div class="nav">

            <a href="guide/">
                How to Read This Dashboard →
            </a>

        </div>

    </div>


    <div class="updated">

        Last updated

        <br>

        {updated}

    </div>

</div>


<div class="card">

    <div class="filter-bar">


        <input
            id="stockSearch"
            type="search"
            placeholder="
                Search ticker or company...
            "
            aria-label="
                Search ticker or company
            "
        >


        <select
            id="marketFilter"
            aria-label="
                Filter by market
            "
        >

            <option value="All">
                All Markets
            </option>

            <option value="US">
                US
            </option>

            <option value="Singapore">
                Singapore
            </option>

        </select>


        <select
            id="sectorFilter"
            aria-label="
                Filter by sector
            "
        >

            <option value="All">
                All Sectors
            </option>

            {sector_options}

        </select>


        <button
            id="clearFilters"
            type="button"
        >

            Clear Filters

        </button>


    </div>


    <div
        id="filterStatus"
        class="filter-status"
    >

        Showing all ranked stocks.

    </div>

</div>


<div class="card section">

    {micron_focus(
        micron
    )}

</div>


<div class="card section">

    <div class="section-title">
        V's Watchlist
    </div>

    <div class="section-subtitle">

        Your selected stocks remain visible
        here regardless of their market ranking.

        Edit
        <strong>
            watchlist.json
        </strong>
        to change this list.

    </div>


    <div class="watchlist-grid">

        {watchlist_html}

    </div>

</div>


<div class="card section">

    <div class="section-title">

        What Changed Since the Previous Scan?

    </div>


    <div class="section-subtitle">

        Highlights the largest score movements,
        component changes and rating changes
        since the last saved dashboard run.

    </div>


    <div class="changes-grid">

        {changes_panel(

            changes,

            previous,

            8,

        )}

    </div>

</div>


<div class="card section">

    <div class="section-title">

        US Top Opportunities

        {info_icon(
            "overall"
        )}

    </div>

    <div class="section-subtitle">

        Highest-ranked US stocks using
        the dashboard's combined
        quantitative score.

    </div>

    <div class="opportunity-grid">

        {opportunity_cards(
            us_results,
            5,
        )}

    </div>

</div>


<div class="card section">

    <div class="section-title">

        Singapore Top Opportunities

        {info_icon(
            "overall"
        )}

    </div>

    <div class="section-subtitle">

        Highest-ranked SGX stocks using
        the same quantitative scoring
        methodology.

    </div>

    <div class="opportunity-grid">

        {opportunity_cards(
            singapore_results,
            5,
        )}

    </div>

</div>


<div class="card section">

    <div class="section-title">
        Market Opportunity Screens
    </div>

    <div class="section-subtitle">

        Alternative ways of finding potential
        opportunities.

        These screens may rank stocks differently
        from the main Overall Score.

    </div>


    <div class="screen-grid">


        <div class="screen-card">

            <div class="screen-title">

                Oversold Watch

                {info_icon(
                    "oversold"
                )}

            </div>

            <div class="screen-description">

                Stocks with RSI below 35
                that have experienced unusually
                weak recent price momentum.

            </div>

            {mini_list(
                oversold,
                "oversold",
            )}

        </div>


        <div class="screen-card">

            <div class="screen-title">

                Momentum Leaders

                {info_icon(
                    "momentum_leaders"
                )}

            </div>

            <div class="screen-description">

                Strong recent price performers
                that also meet minimum fundamental
                and data-quality requirements.

            </div>

            {mini_list(
                momentum_leaders,
                "momentum",
            )}

        </div>


        <div class="screen-card">

            <div class="screen-title">

                Value Opportunities

                {info_icon(
                    "value_opportunity"
                )}

            </div>

            <div class="screen-description">

                Stocks combining relatively
                attractive valuation with
                stronger underlying fundamentals.

            </div>

            {mini_list(
                value_opportunities,
                "value",
            )}

        </div>


        <div class="screen-card">

            <div class="screen-title">

                Best Balanced

                {info_icon(
                    "balanced"
                )}

            </div>

            <div class="screen-description">

                Stocks showing more consistent
                strength across all four
                major scoring categories.

            </div>

            {mini_list(
                balanced_opportunities,
                "balanced",
            )}

        </div>


    </div>

</div>


<div class="card section">

    <div class="section-title">
        US Stock Rankings
    </div>

    <div class="section-subtitle">

        Search and filters above apply to
        this table and the Singapore table below.

    </div>


    <div class="table-wrapper">

        <table>

            <thead>

                <tr>

                    <th>#</th>

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

                        Technical

                        {info_icon(
                            "technical"
                        )}

                    </th>

                    <th class="desktop-column">

                        Momentum

                        {info_icon(
                            "momentum"
                        )}

                    </th>

                    <th class="desktop-column">

                        Fundamental

                        {info_icon(
                            "fundamental"
                        )}

                    </th>

                    <th class="desktop-column">

                        Value

                        {info_icon(
                            "valuation"
                        )}

                    </th>

                    <th>

                        Overall

                        {info_icon(
                            "overall"
                        )}

                    </th>

                    <th>

                        Data

                        {info_icon(
                            "data_quality"
                        )}

                    </th>

                    <th>

                        Dashboard Rating

                        {info_icon(
                            "dashboard_rating"
                        )}

                    </th>

                </tr>

            </thead>


            <tbody>

                {stock_rows(
                    us_results,
                    100,
                )}

            </tbody>

        </table>

    </div>

</div>


<div class="card section">

    <div class="section-title">
        Singapore Stock Rankings
    </div>

    <div class="section-subtitle">

        Search by ticker or company,
        or filter by market and sector.

    </div>


    <div class="table-wrapper">

        <table>

            <thead>

                <tr>

                    <th>#</th>

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

                        Technical

                        {info_icon(
                            "technical"
                        )}

                    </th>

                    <th class="desktop-column">

                        Momentum

                        {info_icon(
                            "momentum"
                        )}

                    </th>

                    <th class="desktop-column">

                        Fundamental

                        {info_icon(
                            "fundamental"
                        )}

                    </th>

                    <th class="desktop-column">

                        Value

                        {info_icon(
                            "valuation"
                        )}

                    </th>

                    <th>

                        Overall

                        {info_icon(
                            "overall"
                        )}

                    </th>

                    <th>

                        Data

                        {info_icon(
                            "data_quality"
                        )}

                    </th>

                    <th>

                        Dashboard Rating

                        {info_icon(
                            "dashboard_rating"
                        )}

                    </th>

                </tr>

            </thead>


            <tbody>

                {stock_rows(
                    singapore_results,
                    100,
                )}

            </tbody>

        </table>

    </div>

</div>


<div class="footer">

    V Stock Intelligence uses
    automated quantitative scoring.

    <br>

    Dashboard ratings are not
    analyst recommendations
    and are not financial advice.

</div>


</div>


<script>

(function() {{

    const searchInput =
        document.getElementById(
            "stockSearch"
        );


    const marketFilter =
        document.getElementById(
            "marketFilter"
        );


    const sectorFilter =
        document.getElementById(
            "sectorFilter"
        );


    const clearButton =
        document.getElementById(
            "clearFilters"
        );


    const status =
        document.getElementById(
            "filterStatus"
        );


    function applyFilters() {{

        const search =
            searchInput
            .value
            .trim()
            .toLowerCase();


        const market =
            marketFilter.value;


        const sector =
            sectorFilter.value;


        const rows =
            Array.from(

                document
                .querySelectorAll(
                    ".filterable-row"
                )

            );


        let visibleRows = 0;


        rows.forEach(
            row => {{

                const rowSearch = (

                    row
                    .dataset
                    .search

                    ||

                    ""

                ).toLowerCase();


                const rowMarket = (

                    row
                    .dataset
                    .market

                    ||

                    ""

                );


                const rowSector = (

                    row
                    .dataset
                    .sector

                    ||

                    ""

                );


                const searchMatch = (

                    !search

                    ||

                    rowSearch.includes(
                        search
                    )

                );


                const marketMatch = (

                    market === "All"

                    ||

                    rowMarket === market

                );


                const sectorMatch = (

                    sector === "All"

                    ||

                    rowSector === sector

                );


                const visible = (

                    searchMatch

                    &&

                    marketMatch

                    &&

                    sectorMatch

                );


                row.classList.toggle(

                    "hidden-by-filter",

                    !visible,

                );


                if (visible) {{
                    visibleRows += 1;
                }}

            }}
        );


        const topCards =
            Array.from(

                document
                .querySelectorAll(
                    ".filterable-card"
                )

            );


        topCards.forEach(
            card => {{

                const cardSearch = (

                    card
                    .dataset
                    .search

                    ||

                    ""

                ).toLowerCase();


                const cardMarket = (

                    card
                    .dataset
                    .market

                    ||

                    ""

                );


                const cardSector = (

                    card
                    .dataset
                    .sector

                    ||

                    ""

                );


                const searchMatch = (

                    !search

                    ||

                    cardSearch.includes(
                        search
                    )

                );


                const marketMatch = (

                    market === "All"

                    ||

                    cardMarket === market

                );


                const sectorMatch = (

                    sector === "All"

                    ||

                    cardSector === sector

                );


                card.classList.toggle(

                    "hidden-by-filter",

                    !(

                        searchMatch

                        &&

                        marketMatch

                        &&

                        sectorMatch

                    ),

                );

            }}
        );


        if (

            !search

            &&

            market === "All"

            &&

            sector === "All"

        ) {{

            status.textContent =
                "Showing all ranked stocks.";

        }}

        else {{

            status.textContent =

                `Showing ${{visibleRows}} `

                +

                `matching ranked stock${{
                    visibleRows === 1
                    ?
                    ""
                    :
                    "s"
                }}.`;

        }}

    }}


    searchInput.addEventListener(

        "input",

        applyFilters,

    );


    marketFilter.addEventListener(

        "change",

        applyFilters,

    );


    sectorFilter.addEventListener(

        "change",

        applyFilters,

    );


    clearButton.addEventListener(

        "click",

        function() {{

            searchInput.value =
                "";

            marketFilter.value =
                "All";

            sectorFilter.value =
                "All";

            applyFilters();

            searchInput.focus();

        }},

    );

}})();

</script>


</body>

</html>
"""


    output_folder = Path(
        "docs"
    )


    output_folder.mkdir(
        exist_ok=True
    )


    (

        output_folder

        /

        "index.html"

    ).write_text(

        page,

        encoding="utf-8",

    )


    print(

        "Main dashboard, watchlist, "
        "score history, change tracking, "
        "guide and stock detail pages "
        "generated successfully."

    )


if __name__ == "__main__":
    main()
