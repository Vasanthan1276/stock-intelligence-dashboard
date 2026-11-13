"""Read-only pdata.world prediction-market research panel for V Stock Intelligence.

No trading interfaces, credentials, orders, bets, or account data. Prediction-market
prices are contextual observations, not stock-return forecasts or trading signals.
The existing four-factor stock scores and MU Wealth Hub gate are unchanged.
"""

from __future__ import annotations

import html
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.pdata.world/api/v1/markets"
DATA_PATH = Path("docs/data/prediction-market-intelligence.json")
PAGE_PATH = Path("docs/prediction-markets/index.html")
MODEL_VERSION = "prediction-market-shadow-v1"
ALLOWED_SOURCES = {"kalshi", "polymarket"}
PAGE_SIZE = 30
MAX_PER_TOPIC = 6

# Conservative, explainable themes. No generic 'AI' or 'Fed' substring search:
# those generate too many unrelated matches. Extend topics after manual review.
TOPICS = (
    ("Rates & monetary policy", ("Federal Reserve", "interest rates"),
     r"\b(federal reserve|fomc|fed funds|fed rate|interest rates?|rate cuts?|rate hikes?)\b"),
    ("Inflation & recession", ("inflation", "recession"),
     r"\b(inflation|cpi|pce|recession|economic downturn)\b"),
    ("AI & semiconductors", ("Micron", "semiconductor", "Nvidia", "artificial intelligence"),
     r"\b(micron|nvidia|semiconductors?|chipmakers?|artificial intelligence|ai infrastructure|hbm|dram|nand)\b"),
    ("Trade & Taiwan", ("Taiwan", "tariff"),
     r"\b(taiwan|tariffs?|trade restrictions?|export controls?)\b"),
)


def finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def fetch_markets(query):
    params = {
        "source": "kalshi,polymarket",
        "search": query,
        "closed": "false",
        "hide_ended": "true",
        "active": "true",
        "page_size": PAGE_SIZE,
        "sort": "-volume_24hr",
    }
    url = API_URL + "?" + urlencode(params)
    request = Request(url, headers={
        "User-Agent": "VStockIntelligence/1.0 (read-only research dashboard)",
        "Accept": "application/json",
    })
    with urlopen(request, timeout=8) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("pdata response missing 'items' list")
    return data["items"]


def normalize_market(item, pattern):
    if not isinstance(item, dict):
        return None
    source = str(item.get("source") or "").lower()
    probability = finite_number(item.get("probability"))
    if source not in ALLOWED_SOURCES or probability is None or not 0 <= probability <= 1:
        return None
    if item.get("closed") is True or item.get("active") is False:
        return None
    title = str(item.get("question") or item.get("event_title") or "").strip()
    event_title = str(item.get("event_title") or "").strip()
    if not title or not re.search(pattern, " ".join((title, event_title)), re.IGNORECASE):
        return None
    event_id = item.get("event_id")
    if event_id is None and isinstance(item.get("event"), dict):
        event_id = item["event"].get("id")
    market_id = item.get("id") or item.get("market_id") or title
    delta = finite_number(item.get("prob_24h_change"))
    if delta is not None and not -1 <= delta <= 1:
        delta = None
    volume_24hr = finite_number(item.get("volume_24hr"))
    if volume_24hr is not None and volume_24hr < 0:
        volume_24hr = None
    url = ("https://pdata.world/events/" + quote(source, safe="") + "/" +
           quote(str(event_id), safe="")) if event_id is not None else "https://pdata.world/"
    return {
        "source": source,
        "market_id": str(market_id),
        "event_id": str(event_id) if event_id is not None else None,
        "title": title[:240],
        "event_title": event_title[:240],
        "outcome": str(item.get("group_item_title") or "")[:240],
        "source_updated_at": str(item.get("updated_at") or "")[:64] or None,
        "end_date": str(item.get("end_date") or "")[:64] or None,
        "probability": round(probability, 5),
        "change_24h": round(delta, 5) if delta is not None else None,
        "volume_24hr": volume_24hr,
        "url": url,
    }


def build_report(fetcher=fetch_markets, now=None):
    now = now or datetime.now(timezone.utc)
    topics = []
    errors = []
    successful_queries = 0
    for label, queries, pattern in TOPICS:
        found = {}
        for query in queries:
            try:
                rows = fetcher(query)
                if not isinstance(rows, list):
                    raise ValueError("Expected list of markets")
                successful_queries += 1
            except (OSError, ValueError, TimeoutError, RuntimeError) as error:
                errors.append(f"{query}: {type(error).__name__}")
                continue
            for raw in rows:
                market = normalize_market(raw, pattern)
                if market is None:
                    continue
                key = (market["source"], market["market_id"])
                found[key] = market
        ranked = sorted(found.values(), key=lambda m: (
            m["volume_24hr"] if m["volume_24hr"] is not None else -1,
            abs(m["change_24h"] or 0),
        ), reverse=True)
        topics.append({"name": label, "markets": ranked[:MAX_PER_TOPIC]})
    status = ("unavailable" if successful_queries == 0 else
              "partial" if errors else
              "ok" if any(t["markets"] for t in topics) else "no_matches")
    return {
        "model_version": MODEL_VERSION,
        "status": status,
        "fetched_at_utc": now.isoformat(timespec="seconds"),
        "attribution": "pdata.world (CC BY 4.0); underlying venue terms also apply",
        "sources": sorted(ALLOWED_SOURCES),
        "successful_queries": successful_queries,
        "failed_queries": errors,
        "interpretation": "Advisory context only; not calibrated stock-return forecasts, stock ratings, or trading advice.",
        "topics": topics,
    }


def fmt_probability(value):
    return f"{value * 100:.1f}%"


def fmt_delta(value):
    return "—" if value is None else f"{value * 100:+.1f} pp"


def fmt_volume(value):
    return "—" if value is None else f"{value:,.0f}"


def render_html(report):
    esc = lambda value: html.escape(str(value), quote=True)
    sections = []
    for topic in report["topics"]:
        cards = []
        for m in topic["markets"]:
            delta = m["change_24h"]
            change_class = "up" if delta is not None and delta > 0 else "down" if delta is not None and delta < 0 else "flat"
            units = "contracts" if m["source"] == "kalshi" else "shares"
            context = " · ".join(value for value in (m["event_title"], m["outcome"])
                                 if value and value != m["title"])
            cards.append(
                '<article class="market">'
                f'<div class="meta">{esc(m["source"].title())}</div>'
                f'<a href="{esc(m["url"])}" target="_blank" rel="noopener noreferrer">{esc(m["title"])}</a>'
                f'<div class="meta">{esc(context)}</div>'
                f'<div class="stats"><span><b>{esc(fmt_probability(m["probability"]))}</b> implied</span>'
                f'<span class="{change_class}">{esc(fmt_delta(delta))} / 24h</span></div>'
                f'<div class="meta">24h volume: {esc(fmt_volume(m["volume_24hr"]))} {units}</div>'
                f'<div class="meta">Source row updated: {esc(m["source_updated_at"] or "Unknown")}</div>'
                f'<div class="meta">Scheduled close: {esc(m["end_date"] or "Unknown")}</div>'
                '</article>'
            )
        cards_html = '\n'.join(cards) if cards else '<p class="empty">No relevant markets with usable probabilities in this sample.</p>'
        sections.append(f'<section><h2>{esc(topic["name"])}</h2><div class="cards">{cards_html}</div></section>')
    banner = {
        "unavailable": "Feed unavailable. No live prediction-market readings were retrieved.",
        "partial": "Partial update: some queries failed. This is not a complete market view.",
        "no_matches": "No matching active contracts were found in the queried sample.",
    }.get(report["status"], "")
    warning = f'<div class="warning">{esc(banner)}</div>' if banner else ''
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prediction Market Intelligence | V Stock Intelligence</title>
<style>
:root{{color-scheme:dark}} *{{box-sizing:border-box}} body{{margin:0;background:#07111f;color:#edf4ff;font-family:Arial,Helvetica,sans-serif;line-height:1.5}}
main{{width:min(1150px,94%);margin:30px auto 70px}} a{{color:#67b8fa}} h1{{font-size:30px;margin-bottom:3px}} h2{{font-size:20px;margin:28px 0 12px}}
.subtitle,.meta,.note{{color:#98acc9;font-size:13px}} .intro,.warning{{background:#111e31;border:1px solid #29415e;border-radius:14px;padding:18px;margin:18px 0}}
.warning{{border-color:#c59b57}} .cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
.market{{background:#111e31;border:1px solid #263c5b;border-radius:12px;padding:17px;min-height:172px;overflow-wrap:anywhere}} .market a{{display:block;font-weight:700;margin:9px 0;line-height:1.35;text-decoration:none}}
.stats{{display:flex;gap:12px;flex-wrap:wrap;margin:13px 0 8px;font-size:13px}} .stats b{{font-size:21px}} .up{{color:#51e0a0}} .down{{color:#ff8797}} .flat{{color:#a0b5d0}} .empty{{font-size:13px;color:#8ea9c9}}
@media(max-width:900px){{.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:650px){{.cards{{grid-template-columns:1fr}}h1{{font-size:25px}}}}
</style></head><body><main>
<a href="../">← Back to V Stock Intelligence</a>
<h1>Prediction Market Intelligence</h1><div class="subtitle">Independent read-only context · Shadow model v1 · {esc(report["status"])}</div>
<div class="intro">Data: <a href="https://pdata.world/" target="_blank" rel="noopener noreferrer">pdata.world</a> (CC BY 4.0), aggregating Kalshi and Polymarket. Fetched: {esc(report["fetched_at_utc"])}. These are event-contract implied probabilities, <strong>not</strong> probabilities of a stock rising. No positions or bets are placed. Existing stock scores are unchanged.</div>
{warning}
{''.join(sections)}
<p class="note">Source row timestamps are supplied by pdata and may reflect derived-field updates, not the time of the last trade. Unknown timestamps do not establish freshness. Volume is activity, not order-book depth; inspect the linked event's rules and liquidity before interpreting a price.</p>
<p class="note">Contracts are selected using fixed research queries, topic checks and a capped first page of search results; coverage is not exhaustive. A 24-hour change is shown in percentage points, not percent. Volumes are venue-reported in contracts (Kalshi) or shares (Polymarket), not directly equivalent liquidity. Low or zero activity and wide spreads can distort prices. A market may have multiple mutually exclusive outcomes. Do not combine or average probabilities across unrelated questions or venues. Refresh occurs only when the GitHub workflow runs.</p>
</main></body></html>'''


def main():
    report = build_report()
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    PAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    PAGE_PATH.write_text(render_html(report), encoding="utf-8")
    print(f"Prediction-market panel: {report['status']}; {report['successful_queries']} successful queries; "
          f"{sum(len(x['markets']) for x in report['topics'])} selected contracts")


if __name__ == "__main__":
    main()
