"""Read-only pdata.world prediction-market research panel for V Stock Intelligence.

No trading interfaces, credentials, orders, bets, or account data. Prediction-market
prices are contextual observations, not stock-return forecasts or trading signals.
The existing four-factor stock scores and MU Wealth Hub gate are unchanged.
"""

from __future__ import annotations

import ast
import html
import json
import math
import re
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from prediction_market_impact import enrich_report, render_impact

API_URL = "https://api.pdata.world/api/v1/markets"
DATA_PATH = Path("docs/data/prediction-market-intelligence.json")
PAGE_PATH = Path("docs/prediction-markets/index.html")
MODEL_VERSION = "prediction-market-shadow-v3"
ROOT = Path(__file__).resolve().parent
ALLOWED_SOURCES = {"kalshi", "polymarket"}
PAGE_SIZE = 60
MAX_PER_TOPIC = 6

# Only names and sectors from the existing dashboard universe are used. Loading
# the literal dictionaries avoids executing scanner.py or requesting stock prices.
ALIASES = {
    "MU": ("Micron",), "NVDA": ("Nvidia",), "AMD": ("AMD", "Advanced Micro Devices"),
    "JPM": ("JPMorgan", "JP Morgan", "JPMorgan Chase"),
    "D05.SI": ("DBS", "DBS Group"), "U11.SI": ("UOB", "United Overseas Bank"),
    "O39.SI": ("OCBC",), "TSM": ("TSMC", "Taiwan Semiconductor"),
    "GOOGL": ("Alphabet", "Google"), "META": ("Meta", "Meta Platforms", "Facebook"),
    "LULU": ("Lululemon",), "UA": ("Under Armour",), "UAA": ("Under Armour",),
}
BUSINESS = r"\b(earnings|revenue|profits?|sales|guidance|capex|capital expenditure|demand|shipments?|acquir(?:e|es|ed|ing)|acquisition|merger|bankruptcy|dividends?|buybacks?|antitrust|layoffs?|export controls?|export restrictions?|FDA|clinical trials?|product launch|production|deliveries)\b"
EXCLUDED = r"\b(next CEO|CEO (?:by|before|in)|president|presidential|election|nominee|nomination|world cup|super bowl|NBA|NFL|say during|mention|mentions|mentioned)\b"
PRICE_ONLY = r"\b(stock price|share price|market cap|market capitalization|closing price|close above|close below|largest company|most valuable company)\b"
SECTIONS = ("Company developments", "Sector & supply-chain risks", "Macro conditions")


def matches(pattern, text):
    return re.search(pattern, text, re.IGNORECASE) is not None


def load_companies(root=ROOT):
    tree = ast.parse((root / "scanner.py").read_text(encoding="utf-8"))
    static = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("US_STOCKS", "SINGAPORE_STOCKS"):
                    static[target.id] = ast.literal_eval(node.value)
    if set(static) != {"US_STOCKS", "SINGAPORE_STOCKS"}:
        raise ValueError("Expected static company dictionaries in scanner.py")
    portfolio = json.loads((root / "portfolio-universe.json").read_text(encoding="utf-8"))
    watch = json.loads((root / "watchlist.json").read_text(encoding="utf-8"))["tickers"]
    if not isinstance(watch, list) or not all(isinstance(t, str) for t in watch):
        raise ValueError("Invalid watchlist tickers")
    extras = {}
    for market in ("us", "singapore"):
        extras.update(portfolio[market])
    combined = {**static["US_STOCKS"], **static["SINGAPORE_STOCKS"], **extras}
    if set(watch) - combined.keys():
        raise ValueError("Watchlist contains companies without universe metadata")
    companies = {}
    for ticker, meta in combined.items():
        if not isinstance(meta, dict) or not meta.get("name") or not meta.get("sector"):
            raise ValueError(f"Invalid company metadata: {ticker}")
        aliases = ALIASES.get(ticker, (meta["name"],))
        companies[ticker] = {"ticker": ticker, "name": meta["name"], "sector": meta["sector"],
                             "aliases": aliases, "watchlist": ticker in watch,
                             "portfolio": ticker in extras}
    return companies


def company_priority(company):
    return 2 if company["watchlist"] else 1 if company["portfolio"] else 0


def company_matches(company, text):
    # Short bare tickers such as MU, W, V and UA are never treated as names.
    return any(matches(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text)
               for alias in company["aliases"]) or matches(
                   r"\$" + re.escape(company["ticker"]) + r"(?!\w)", text)


# These are qualitative research links, not measured exposure or price forecasts.
# Each rule requires BOTH a specific subject and a business/economic event.
RISK_RULES = (
    ("memory_demand", "Sector & supply-chain risks", '"HBM" or "DRAM" or "NAND"',
     r"\b(HBM|DRAM|NAND|memory chips?)\b", r"\b(demand|supply|shortage|prices?|production|capacity|spending)\b",
     lambda c: c["ticker"] == "MU",
     "Memory demand, supply or pricing is relevant to Micron's memory business; this does not estimate its earnings impact."),
    ("ai_spending", "Sector & supply-chain risks", '"AI spending" or "AI capex" or "data center spending"',
     r"\b(AI|artificial intelligence|data cent(?:er|re)s?)\b", r"\b(spending|capex|capital expenditure|investment|demand|capacity)\b",
     lambda c: c["ticker"] in {"MU", "NVDA", "AMD", "AVGO", "TSM", "MSFT", "AMZN", "GOOGL", "ORCL", "AMAT", "LRCX", "KLAC", "ASML"},
     "AI infrastructure spending can affect demand for chips and equipment and the capital needs of cloud operators. Direction and size vary by company."),
    ("chip_trade", "Sector & supply-chain risks", '"chip export" or "semiconductor tariff" or "Nvidia China"',
     r"\b(chips?|semiconductors?|Nvidia|AMD|Micron)\b", r"\b(export|exports|tariffs?|trade restrictions?|sanctions?|ban|banned)\b",
     lambda c: "Semiconductor" in c["sector"],
     "Chip trade restrictions can affect addressable markets and semiconductor supply chains; the named companies' exposure differs."),
    ("taiwan_supply", "Sector & supply-chain risks", '"Taiwan invasion" or "Taiwan blockade" or "Taiwan conflict"',
     r"\bTaiwan\b", r"\b(invad(?:e|es)|invasion|blockade|military conflict|war|fab disruption)\b",
     lambda c: "Semiconductor" in c["sector"],
     "A Taiwan supply disruption could affect semiconductor fabrication and downstream chip availability. A political headline alone does not qualify."),
    ("us_rates", "Macro conditions", '"Fed rate" or "Federal Reserve" or "FOMC"',
     r"\b(Fed|Federal Reserve|FOMC|US|U\.S\.)\b", r"\b(rates?|bps|basis points|cut|cuts|hike|hikes)\b",
     lambda c: c["sector"] in {"Banks", "Financials", "Financial Services", "Financial Technology", "REIT", "Property"},
     "US rate changes provide context for funding costs, credit demand and property financing, including indirect effects in Singapore. They do not determine a bank's margins."),
    ("us_economy", "Macro conditions", '"US recession" or "US inflation" or "US CPI"',
     r"\b(US|U\.S\.|United States|American)\b", r"\b(recession|inflation|CPI|PCE)\b",
     lambda c: True,
     "US growth and inflation are broad demand and financing context for the tracked companies. This is a macro link, not a company-specific forecast."),
    ("energy_supply", "Sector & supply-chain risks", '"oil supply" or "OPEC production" or "Strait of Hormuz"',
     r"\b(oil|OPEC|Strait of Hormuz)\b", r"\b(supply|production|output|cut|cuts|blockade|closed|closure)\b",
     lambda c: c["sector"] in {"Energy", "Transport"},
     "Energy supply conditions can influence producer revenue and transport fuel costs in different directions; this is a sector research link."),
)


def query_plan(companies):
    ordered = sorted(companies.values(), key=lambda c: (-company_priority(c), c["ticker"]))
    plan = []
    for i in range(0, len(ordered), 4):
        group = ordered[i:i + 4]
        terms = dict.fromkeys(a for c in group for a in c["aliases"])
        plan.append({"query": " or ".join('"' + a.replace('"', '') + '"' for a in terms),
                     "tickers": [c["ticker"] for c in group], "kind": "company"})
    for key, _, query, _, _, eligible, _ in RISK_RULES:
        tickers = [t for t, c in companies.items() if eligible(c)]
        if tickers:
            plan.append({"query": query, "tickers": tickers, "kind": key})
    return plan


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
    # Retry one transient transport failure; a persistent failure stays explicit.
    for attempt in range(2):
        try:
            with urlopen(request, timeout=15) as response:
                data = json.load(response)
            break
        except (OSError, TimeoutError):
            if attempt:
                raise
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("pdata response missing 'items' list")
    return data["items"]


def normalize_market(item, now=None):
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
    if not title:
        return None
    now = now or datetime.now(timezone.utc)
    end_date = item.get("end_date")
    if end_date:
        try:
            end = datetime.fromisoformat(str(end_date).replace("Z", "+00:00"))
            if end.tzinfo is not None and end <= now:
                return None
        except ValueError:
            pass  # Unparseable timestamps remain explicitly unknown, not fresh.
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


def assess_relevance(market, companies):
    text = " ".join((market["title"], market["event_title"]))
    if matches(EXCLUDED, text) or matches(PRICE_ONLY, text):
        return None
    related = {}
    direct = [t for t, c in companies.items() if company_matches(c, text)]
    reasons = []
    if direct and matches(BUSINESS, text):
        for ticker in direct:
            related[ticker] = "Direct company"
        if matches(r"\b(postponed|postponement|delayed)\b", text):
            reason = "Reporting delays affect when investors can assess operating results and guidance. A delay alone does not establish weaker performance."
        elif matches(r"\b(acquir\w*|acquisition|merger)\b", text):
            reason = "An acquisition or merger can change the business mix, capital requirements and integration risk. The outcome alone does not establish whether the deal creates value."
        elif matches(r"\b(FDA|clinical trials?)\b", text):
            reason = "Clinical or regulatory milestones can affect product availability, development costs and the timing of potential revenue."
        elif matches(r"\b(earnings|revenue|profits?|sales|guidance)\b", text):
            reason = "Revenue, earnings or guidance provides context for operating demand and profitability. Read the contract's metric, threshold and reporting period before comparing it with the stock analysis."
        elif matches(r"\b(dividends?|buybacks?)\b", text):
            reason = "Capital-return decisions affect cash allocation between shareholders, investment and the balance sheet."
        else:
            reason = "The operating or regulatory development can affect business execution, costs or market access. Its financial impact requires separate company analysis."
        reasons.append("For " + ", ".join(direct) + ": " + reason)
    risk_keys = []
    section = None
    for key, topic, _, subject, event, eligible, explanation in RISK_RULES:
        if matches(subject, text) and matches(event, text):
            tickers = [t for t, c in companies.items() if eligible(c)]
            if tickers:
                risk_keys.append(key)
                section = section or topic
                reasons.append(explanation)
                for ticker in tickers:
                    related.setdefault(ticker, "Macro context" if topic == "Macro conditions" else "Sector risk")
    if not related:
        return None
    is_direct = any(v == "Direct company" for v in related.values())
    section = SECTIONS[0] if is_direct else section
    stocks = [dict(ticker=t, name=companies[t]["name"], relationship=relationship)
              for t, relationship in related.items()]
    stocks.sort(key=lambda c: (c["relationship"] != "Direct company",
                              -company_priority(companies[c["ticker"]]), c["ticker"]))
    return {**market, "section": section, "relevance": "Direct company" if is_direct else
            "Macro context" if section == "Macro conditions" else "Sector risk",
            "related_stocks": stocks, "why_this_matters": " ".join(reasons),
            "risk_keys": risk_keys,
            "priority": max(company_priority(companies[c["ticker"]]) for c in stocks)}


def rank_markets(markets):
    # Activity is compared only within the same venue, AFTER relevance/priority.
    activity = {}
    for source in sorted(ALLOWED_SOURCES):
        venue = sorted((m for m in markets if m["source"] == source),
                       key=lambda m: (-(m["volume_24hr"] if m["volume_24hr"] is not None else -1), m["market_id"]))
        for i, m in enumerate(venue):
            activity[(source, m["market_id"])] = i / max(1, len(venue))
    levels = {"Direct company": 0, "Sector risk": 1, "Macro context": 2}
    return sorted(markets, key=lambda m: (levels[m["relevance"]], -m["priority"],
                  activity[(m["source"], m["market_id"])], m["source"], m["market_id"]))


def select_markets(markets):
    selected = {name: [] for name in SECTIONS}
    events, titles, counts = set(), set(), {}
    for market in rank_markets(markets):
        topic = market["section"]
        event = (market["source"], market["event_id"] or market["market_id"])
        title = re.sub(r"[^a-z0-9]+", " ", (market["event_title"] or market["title"]).lower()).strip()
        # One representative outcome per event, and at most two events per
        # company or risk family. Probabilities are never combined.
        families = (["company:" + c["ticker"] for c in market["related_stocks"]
                     if c["relationship"] == "Direct company"] or market["risk_keys"])
        if len(selected[topic]) >= MAX_PER_TOPIC or event in events or title in titles:
            continue
        if any(counts.get(family, 0) >= 2 for family in families):
            continue
        selected[topic].append(market)
        events.add(event)
        titles.add(title)
        for family in families:
            counts[family] = counts.get(family, 0) + 1
    return [{"name": name, "markets": selected[name]} for name in SECTIONS]


def build_report(fetcher=fetch_markets, now=None, companies=None):
    now = now or datetime.now(timezone.utc)
    companies = load_companies() if companies is None else companies
    plan = query_plan(companies)
    errors, found, failed_tickers = [], {}, set()

    def fetch(plan_item):
        try:
            rows = fetcher(plan_item["query"])
            if not isinstance(rows, list):
                raise ValueError("Expected list of markets")
            return rows, None
        except (OSError, ValueError, TimeoutError, RuntimeError) as error:
            return [], type(error).__name__

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, plan))
    for plan_item, (rows, error) in zip(plan, results):
        if error:
            errors.append(f"{plan_item['query']}: {error}")
            failed_tickers.update(plan_item["tickers"])
        for raw in rows:
            market = normalize_market(raw, now)
            if market is not None:
                relevant = assess_relevance(market, companies)
                if relevant:
                    found[(market["source"], market["market_id"])] = relevant
    topics = select_markets(list(found.values()))
    shown = [m for t in topics for m in t["markets"]]
    coverage = []
    for ticker, company in sorted(companies.items(), key=lambda pair: (-company_priority(pair[1]), pair[0])):
        candidates = [m for m in found.values() if any(c["ticker"] == ticker for c in m["related_stocks"])]
        direct = sum(any(c["ticker"] == ticker and c["relationship"] == "Direct company"
                         for c in m["related_stocks"]) for m in candidates)
        displayed = sum(any(c["ticker"] == ticker for c in m["related_stocks"]) for m in shown)
        coverage.append({"ticker": ticker, "name": company["name"], "watchlist": company["watchlist"],
                         "portfolio": company["portfolio"], "direct_matches": direct,
                         "relevant_matches": len(candidates), "displayed_matches": displayed,
                         "search_incomplete": ticker in failed_tickers})
    successes = len(plan) - len(errors)
    status = ("unavailable" if successes == 0 else "partial" if errors else
              "ok" if shown else "no_matches")
    report = {
        "model_version": MODEL_VERSION, "status": status,
        "fetched_at_utc": now.isoformat(timespec="seconds"),
        "attribution": "pdata.world (CC BY 4.0); underlying venue terms also apply",
        "sources": sorted(ALLOWED_SOURCES), "successful_queries": successes,
        "failed_queries": errors, "query_plan": plan, "sample_limit_per_query": PAGE_SIZE,
        "universe_size": len(companies), "coverage": coverage,
        "interpretation": "Qualitative company and risk links only; not calibrated stock-return forecasts, stock ratings, or trading advice.",
        "topics": topics,
    }
    return enrich_report(report, companies, ROOT, now)


def fmt_probability(value):
    return f"{value * 100:.1f}%"


def fmt_delta(value):
    return "—" if value is None else f"{value * 100:+.1f} pp"


def fmt_volume(value):
    return "—" if value is None else f"{value:,.0f}"


def impact_context_html(report):
    esc = lambda value: html.escape(str(value), quote=True)
    method = report.get("impact_method", {})
    mu = report.get("existing_mu_advisory")
    context = f'<p class="note">Existing dashboard scores as of {esc(method.get("stock_snapshot_at") or "Unavailable")}. Scenario analysis prepared {esc(method.get("analyzed_at_utc") or "Unknown")}.</p>'
    if mu:
        status = "current" if mu["fresh"] else "stale / unverified"
        context += (f'<div class="intro"><strong>Existing Micron / Wealth Hub context</strong><br>'
                    f'Long-term rating: {esc(mu["long_term_rating"])} · Short-term: {esc(mu["short_term_rating"])} · '
                    f'Thesis: {esc(mu["thesis"])} · Existing gate hint: {esc(mu["gate_hint"])}.<br>'
                    f'<span class="meta">As of {esc(mu["as_of"])} · {status}. Read-only reference; the prediction panel does not change this signal.</span></div>')
    if method.get("context_errors"):
        context += '<div class="warning">' + esc(' '.join(method["context_errors"])) + '</div>'
    links = ' · '.join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["label"])}</a>' for s in method.get("sources", []))
    context += '<details><summary>How to read the stock implications</summary><p class="note">Each group separates the event scenario, possible business effect and conditions for holding or reviewing a reduction. Existing scores are read unchanged. Event odds do not measure share-price upside or downside. A threshold result needs a matching expectations benchmark.</p><p class="note">Research principles: ' + links + '</p></details>'
    return context


def render_html(report):
    esc = lambda value: html.escape(str(value), quote=True)
    def coverage_row(c):
        if c["direct_matches"]:
            finding = f'{c["direct_matches"]} direct company match(es)'
        elif c["relevant_matches"]:
            finding = "No direct company market found; related risk context available"
        else:
            finding = "Search incomplete" if c["search_incomplete"] else "No relevant market found"
        if c["relevant_matches"] and not c["displayed_matches"]:
            finding += "; omitted by diversity/card limits"
        if c["search_incomplete"] and finding != "Search incomplete":
            finding += "; search incomplete"
        return f'<tr><td><b>{esc(c["ticker"])}</b><br>{esc(c["name"])}</td><td>{esc(finding)}</td></tr>'
    watch_rows = ''.join(coverage_row(c) for c in report["coverage"] if c["watchlist"])
    other_rows = ''.join(coverage_row(c) for c in report["coverage"] if not c["watchlist"])
    coverage_html = (f'<section><h2>Your company coverage</h2><p class="note">{report["universe_size"]} companies from the dashboard universe, portfolio list and watchlist. Findings refer to this searched sample. A missing direct market is not replaced with an unrelated question.</p>'
                     f'<table><thead><tr><th>Watchlist company</th><th>Coverage</th></tr></thead><tbody>{watch_rows}</tbody></table>'
                     f'<details><summary>View other tracked companies</summary><table><thead><tr><th>Company</th><th>Coverage</th></tr></thead><tbody>{other_rows}</tbody></table></details></section>')
    sections = []
    for topic in report["topics"]:
        cards = []
        for m in topic["markets"]:
            delta = m["change_24h"]
            change_class = "up" if delta is not None and delta > 0 else "down" if delta is not None and delta < 0 else "flat"
            units = "contracts" if m["source"] == "kalshi" else "shares"
            context = " · ".join(value for value in (m["event_title"], m["outcome"])
                                 if value and value != m["title"])
            badges = [f'<span class="badge" title="{esc(c["name"])} · {esc(c["relationship"])}">{esc(c["ticker"])}</span>'
                      for c in m["related_stocks"]]
            stocks = ''.join(badges[:6])
            if len(badges) > 6:
                stocks += f'<details><summary>+{len(badges) - 6} related stocks</summary>{"".join(badges[6:])}</details>'
            cards.append(
                '<article class="market">'
                f'<div class="meta">{esc(m["source"].title())} · {esc(m["relevance"])}</div>'
                f'<a href="{esc(m["url"])}" target="_blank" rel="noopener noreferrer">{esc(m["title"])}</a>'
                f'<div class="meta">{esc(context)}</div>'
                f'<div class="related"><strong>Related stocks</strong><div>{stocks}</div></div>'
                f'<p class="reason"><strong>Why this matters</strong><br>{esc(m["why_this_matters"])}</p>'
                f'<div class="stats"><span><b>{esc(fmt_probability(m["probability"]))}</b> implied</span>'
                f'<span class="{change_class}">{esc(fmt_delta(delta))} / 24h</span></div>'
                f'<div class="meta">24h volume: {esc(fmt_volume(m["volume_24hr"]))} {units}</div>'
                f'<div class="meta">Source row updated: {esc(m["source_updated_at"] or "Unknown")}</div>'
                f'<div class="meta">Scheduled close: {esc(m["end_date"] or "Unknown")}</div>'
                + render_impact(m) + '</article>'
            )
        empty = "Search incomplete: no relevant market retrieved." if report["failed_queries"] else "No relevant market found in the searched sample."
        cards_html = '\n'.join(cards) if cards else f'<p class="empty">{empty}</p>'
        sections.append(f'<section><h2>{esc(topic["name"])}</h2><div class="cards">{cards_html}</div></section>')
    banner = {
        "unavailable": "Feed unavailable. No live prediction-market readings were retrieved.",
        "partial": "Partial update: some queries failed. This is not a complete market view.",
        "no_matches": "No relevant market found in the searched sample.",
    }.get(report["status"], "")
    warning = f'<div class="warning">{esc(banner)}</div>' if banner else ''
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prediction Market Intelligence | V Stock Intelligence</title>
<style>
:root{{color-scheme:dark}} *{{box-sizing:border-box}} body{{margin:0;background:#07111f;color:#edf4ff;font-family:Arial,Helvetica,sans-serif;line-height:1.5}}
main{{width:min(1150px,94%);margin:30px auto 70px}} a{{color:#67b8fa}} h1{{font-size:30px;margin-bottom:3px}} h2{{font-size:20px;margin:28px 0 12px}}
.subtitle,.meta,.note{{color:#98acc9;font-size:13px}} .intro,.warning{{background:#111e31;border:1px solid #29415e;border-radius:14px;padding:18px;margin:18px 0}}
.warning{{border-color:#c59b57}} .cards{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
.market{{background:#111e31;border:1px solid #263c5b;border-radius:12px;padding:17px;min-height:172px;overflow-wrap:anywhere}} .market a{{display:block;font-weight:700;margin:9px 0;line-height:1.35;text-decoration:none}}
.stats{{display:flex;gap:12px;flex-wrap:wrap;margin:13px 0 8px;font-size:13px}} .stats b{{font-size:21px}} .up{{color:#51e0a0}} .down{{color:#ff8797}} .flat{{color:#a0b5d0}} .empty{{font-size:13px;color:#8ea9c9}}
.related,.reason{{font-size:13px;margin:14px 0}} .reason{{color:#e2ecfa;font-size:14px}} .badge{{display:inline-block;padding:3px 7px;margin:4px 4px 0 0;background:#19334e;border-radius:5px;color:#b9ddff;font-size:12px}} details{{margin:10px 0}} summary{{cursor:pointer;color:#67b8fa;font-size:13px}} table{{width:100%;border-collapse:collapse;font-size:13px}} th,td{{text-align:left;padding:10px;border-bottom:1px solid #263c5b;vertical-align:top}} th{{color:#98acc9}} td:first-child{{width:32%}}

.impact-panel{{border-top:1px solid #365577;margin-top:18px;padding-top:12px}} .impact-panel h3{{font-size:17px;margin:0 0 10px;color:#d8ecff}} .impact-panel p,.impact-scenarios{{font-size:14px}} .impact-group>summary{{font-size:14px;font-weight:bold;color:#c3e2ff;padding:8px 0}} .impact-scenarios dt{{font-weight:bold;color:#b9ddff;margin-top:12px}} .impact-scenarios dd{{margin:4px 0 0;color:#edf4ff}} .impact-warning{{border-left:3px solid #c59b57;background:#272333;padding:10px 12px;font-size:13px;margin:12px 0}} .impact-warning ul{{padding-left:18px;margin:6px 0 0}} .impact-table{{font-size:12px}} .impact-table th,.impact-table td{{padding:8px 5px}} .impact-table td:first-child{{width:13%}} .impact-table td:nth-child(2){{width:35%}} .impact-table .meta{{font-size:12px}} .probability-note{{color:#b6cde7}} .method-note{{font-size:13px;color:#b6cde7}}
@media(max-width:900px){{.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:650px){{.cards{{grid-template-columns:1fr}}h1{{font-size:25px}}}}
</style></head><body><main>
<a href="../">← Back to V Stock Intelligence</a>
<h1>Prediction Market Intelligence</h1><div class="subtitle">Company &amp; business-risk relevance · Shadow model v3 · {esc(report["status"])}</div>
<div class="intro">Data: <a href="https://pdata.world/" target="_blank" rel="noopener noreferrer">pdata.world</a> (CC BY 4.0), aggregating Kalshi and Polymarket. Fetched: {esc(report["fetched_at_utc"])}. These are event-contract implied probabilities, <strong>not</strong> probabilities of a stock rising. No positions or bets are placed. Existing stock scores are unchanged.</div>
{warning}
{impact_context_html(report)}
<p class="note">Selection: company developments first, then sector risks, then macro context. Watchlist companies have priority, followed by portfolio companies. Each event appears once; no more than two events per company or risk family. Related stocks are qualitative research links, not measured exposure.</p>
{''.join(sections)}
{coverage_html}
<p class="method-note">Review labels are conditional prompts, not orders or calibrated return forecasts. Freshness limit: 72 hours; dashboard data-quality floor: 70%; activity floor: 100 venue units. Adverse-event review flags use 50% implied odds or a +5 percentage-point change, after evidence checks. Moves over 25 percentage points require history verification. These are transparent review rules, not backtested trading thresholds. Position size, cost basis, tax and personal sale limits are not available here.</p>
<p class="note">Source row timestamps are supplied by pdata and may reflect derived-field updates, not the time of the last trade. Unknown timestamps do not establish freshness. Volume is activity, not order-book depth; inspect the linked event's rules and liquidity before interpreting a price.</p>
<p class="note">Searches use the configured company names plus explicit business-risk rules, with up to {report["sample_limit_per_query"]} results per query; coverage is not exhaustive. Personal politics, CEO succession, word-mention bets and stock-price-only questions are excluded. Relevance ranks before within-venue activity. One representative outcome is shown per event; exact duplicate event titles across venues are suppressed, but semantic duplicates may remain. A 24-hour change is shown in percentage points. Volumes are contracts (Kalshi) or shares (Polymarket), not interchangeable liquidity. Do not combine or average probabilities. Refresh occurs only when the GitHub workflow runs.</p>
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
