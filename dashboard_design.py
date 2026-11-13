"""Presentation-only publishing pass; retains the original dashboard at /classic/.

Run after dashboard.py and prediction_market_intelligence.py. Reads their saved
artifacts without refreshing prices, changing scores, or writing signal feeds.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

from prediction_market_impact import render_impact

DESIGN_MARKER = 'data-dashboard-design="v1"'
CLASSIC_BAR = '<div id="classic-return" style="padding:12px 4%;background:#14233a;color:#e9effa;font:14px Arial,sans-serif"><a href="./" style="color:#9bcaff">← New Overview</a> · Old Dashboard layout · Updated with the same scheduled scans</div>'


def esc(value):
    return html.escape(str(value if value is not None else '—'), quote=True)


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def number(value, default=None):
    if isinstance(value, bool):
        return default
    try:
        result = float(value)
        return result if abs(result) != float('inf') and result == result else default
    except (ValueError, TypeError):
        return default


def sgt(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return 'Time unavailable'
        return parsed.astimezone(ZoneInfo('Asia/Singapore')).strftime('%d %b %Y · %H:%M SGT')
    except (ValueError, TypeError):
        return 'Time unavailable'


def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', str(value).lower()).strip('-')


def score(value):
    val = number(value)
    return '—' if val is None else f'{val:g}'


class ClassicRows(HTMLParser):
    """Read daily moves from the original generated table (not a new quote feed)."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.moves, self.cells, self.current, self.link = {}, None, None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr' and 'filterable-row' in attrs.get('class', '').split():
            self.cells, self.link = [], None
        if self.cells is not None:
            if tag == 'td':
                self.current = []
            if tag == 'a' and attrs.get('href', '').startswith('stocks/'):
                self.link = attrs['href'].split('/')[1]

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == 'td' and self.current is not None:
            self.cells.append(' '.join(''.join(self.current).split()))
            self.current = None
        if tag == 'tr' and self.cells is not None:
            if self.link and len(self.cells) > 3:
                self.moves[self.link] = self.cells[3]
            self.cells, self.current = None, None


def classic_page(original):
    if 'id="classic-return"' in original:
        return original
    if DESIGN_MARKER in original:
        raise ValueError('Refusing to archive the new layout as the old dashboard.')
    # The single base preserves every existing stock/report link and filter script.
    return original.replace('<head>', '<head>\n<base href="../">', 1).replace('<body>', '<body>\n' + CLASSIC_BAR, 1)


def navigation(active, prefix):
    links = [('Overview', prefix, 'overview'), ('Prediction Markets', prefix + 'prediction-markets/', 'predictions'),
             ('Micron Report', prefix + 'micron/', 'micron'), ('Guide', prefix + 'guide/', 'guide'),
             ('Old Dashboard', prefix + 'classic/', 'classic')]
    return '<nav class="vs-nav" aria-label="Main navigation">' + ''.join(
        f'<a href="{href}"{chr(32) + "aria-current=\"page\"" if key == active else ""}>{label}</a>'
        for label, href, key in links) + '</nav>'


def shell(title, active, body, prefix='./'):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | V Stock Intelligence</title>
<link rel="stylesheet" href="{prefix}assets/dashboard.css">
<script src="{prefix}assets/dashboard.js" defer></script></head>
<body><a class="skip-link" href="#main-content">Skip to content</a><div id="vstock-app" {DESIGN_MARKER}>
<header class="vs-top"><a class="vs-logo" href="{prefix}" aria-label="V Stock Intelligence overview">V</a>
<div><div class="vs-brand">V Stock Intelligence</div><div class="vs-meta">US &amp; Singapore · Your research dashboard</div></div></header>
{navigation(active, prefix)}<main class="vs-main" id="main-content">{body}</main>
<footer class="vs-foot"><span>V Stock Intelligence · Sector-specific quantitative research</span><span>Ratings and scenarios are research inputs, not trade instructions.</span></footer>
</div></body></html>'''


def heading(title, subtitle, timestamp, source):
    return f'<div class="vs-heading"><div><h1>{esc(title)}</h1><p class="vs-subtitle">{esc(subtitle)}</p></div><div class="vs-time">{esc(source)}<br><strong>{esc(sgt(timestamp))}</strong></div></div>'


def rating(value):
    return f'<span class="vs-badge {"vs-good" if value in ("Buy", "Strong Buy") else ""}">{esc(value)}</span>'


def move_text(value):
    css = 'vs-down' if value.startswith('-') else 'vs-up' if value.startswith('+') else ''
    return f'<span class="{css}">{esc(value)}</span>'


def price(stock):
    val = number(stock.get('price'))
    return '—' if val is None else ('S$' if stock.get('market') == 'Singapore' else 'US$') + f'{val:,.2f}'


def company_row(ticker, stock, moves):
    val = number(stock.get('overall'))
    bar = '' if val is None else f'<span class="vs-score-track" aria-hidden="true"><span style="width:{min(100,max(0,val))}%"></span></span>'
    return (f'<div class="vs-stock-row"><div><a href="stocks/{slug(ticker)}/"><strong>{esc(ticker)}</strong><span class="vs-stock-name">{esc(stock.get("name"))}</span></a></div>'
            f'<div class="vs-stock-score">{score(val)}{bar}</div><div class="vs-rating">{rating(stock.get("rating"))}</div>'
            f'<div class="vs-stock-change">{move_text(moves.get(slug(ticker), "—"))}</div></div>')


def markets(report):
    return [m for t in report.get('topics', []) for m in t.get('markets', [])]


def overview(history, watchlist, report, mu, moves):
    latest = history[-1] if history else {}
    stocks = latest.get('stocks', {})
    body = heading('Your market briefing', 'Your watchlist, notable changes and the events worth investigating.', latest.get('timestamp'), 'Stock snapshot')
    micron = stocks.get('MU', {})
    if micron:
        ratings = mu.get('ratings') or {}
        context = [('Dashboard model', f'{score(micron.get("overall"))} / 100 · {micron.get("rating", "Unavailable")}'),
                   ('Long-term thesis', ratings.get('long_term', 'Unavailable')),
                   ('Short-term view', ratings.get('short_term', 'Unavailable')),
                   ('Wealth Hub gate', mu.get('gate_hint', 'Unavailable'))]
        body += ('<article class="vs-feature"><div><div class="vs-eyebrow">Featured company · NASDAQ: MU</div><h2>Micron Technology</h2>'
                 f'<div class="vs-price">{esc(price(micron))} <span class="daily-move">{move_text(moves.get("mu", "—"))}</span></div>'
                 '<a href="micron/">Open full Micron report →</a>'
                 f'<p class="vs-meta">Thesis / gate snapshot: {esc(sgt(mu.get("generated_at")))}</p></div><div class="vs-models">' +
                 ''.join(f'<div class="vs-model"><span class="vs-meta">{esc(label)}</span><strong>{esc(value)}</strong></div>' for label, value in context) + '</div></article>')
    body += ('<section class="vs-watch"><div class="vs-section-head"><h2>Your watchlist</h2>'
             f'<span class="vs-meta">{len(watchlist)} configured companies · Dashboard scores</span></div>'
             '<div class="vs-stock-row vs-row-heading" aria-hidden="true"><span>Company</span><span>Score / 100</span><span class="vs-rating">Rating</span><span>Daily move</span></div>' +
             ''.join(company_row(t, stocks[t], moves) if t in stocks else f'<p class="vs-note">{esc(t)}: current stock data unavailable.</p>' for t in watchlist) + '</section>')
    prior = next((h for h in reversed(history[:-1]) if h.get('scoring_model_version') == latest.get('scoring_model_version')), {})
    changes = []
    for ticker, stock in stocks.items():
        old = prior.get('stocks', {}).get(ticker, {})
        a, b = number(old.get('overall')), number(stock.get('overall'))
        if a is not None and b is not None and a != b:
            changes.append((abs(b-a), ticker, stock, old, b-a))
    changes.sort(reverse=True, key=lambda c: (c[0], c[1]))
    change_rows = ''.join(f'<div class="vs-brief-row"><a href="stocks/{slug(t)}/">{esc(t)} · {esc(s.get("name"))}</a>'
                          f'<p><strong>{score(old.get("overall"))} → {score(s.get("overall"))} ({d:+g})</strong> · {esc(old.get("rating"))} → {esc(s.get("rating"))}</p></div>'
                          for _, t, s, old, d in changes[:4]) or '<p class="vs-note">No comparable score changes available.</p>'
    selected = markets(report)
    brief = []
    for m in selected:
        tickers = {c['ticker'] for c in m.get('related_stocks', [])}
        if not tickers.intersection(watchlist):
            continue
        brief.append(f'<div class="vs-brief-row"><strong>{esc(", ".join(sorted(tickers.intersection(watchlist))))}</strong><p>{esc(m["title"])}</p></div>')
        if len(brief) == 2:
            break
    body += ('<div class="vs-bottom-grid"><section class="vs-brief"><h2>Notable score changes</h2>' + change_rows +
             '<a class="vs-source-link" href="classic/">Full change report &amp; opportunity screens →</a></section><section class="vs-brief"><h2>Prediction market context</h2>' +
             (''.join(brief) or '<p class="vs-note">No selected watchlist markets available. Check the prediction page for feed status and company coverage.</p>') +
             f'<p class="vs-meta">Market snapshot: {esc(sgt(report.get("fetched_at_utc")))}</p><a class="vs-source-link" href="prediction-markets/">Explore {len(selected)} selected events →</a></section></div>')
    sectors = sorted({s.get('sector', 'Unknown') for s in stocks.values()})
    options = ''.join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in sectors)
    rows = []
    for ticker, stock in sorted(stocks.items(), key=lambda pair: (-(number(pair[1].get('overall'), -1)), pair[0])):
        rows.append(f'<tr data-stock-row data-ticker="{esc(ticker)}" data-score="{number(stock.get("overall"),-1)}" data-search="{esc(ticker + " " + str(stock.get("name", "")))}" data-market="{esc(stock.get("market"))}" data-sector="{esc(stock.get("sector"))}">'
                    f'<td><a href="stocks/{slug(ticker)}/"><strong>{esc(ticker)}</strong><span class="vs-stock-name">{esc(stock.get("name"))}</span></a></td>'
                    f'<td>{esc(price(stock))}</td><td>{score(stock.get("overall"))}</td><td>{rating(stock.get("rating"))}</td><td>{move_text(moves.get(slug(ticker),"—"))}</td>'
                    f'<td>{score(stock.get("data_quality"))}%</td><td>{esc(stock.get("sector"))}</td></tr>')
    body += f'''<section class="rankings"><details><summary>Explore all {len(stocks)} ranked stocks</summary>
<div class="stock-controls"><label>Search company<input id="stock-search" type="search" placeholder="Ticker or company"></label>
<label>Market<select id="stock-market"><option value="">All markets</option><option>US</option><option>Singapore</option></select></label>
<label>Sector<select id="stock-sector"><option value="">All sectors</option>{options}</select></label>
<label>Sort<select id="stock-sort"><option value="score">Highest score</option><option value="ticker">Ticker A–Z</option></select></label>
<button type="button" id="stock-reset">Clear filters</button></div><p id="stock-count" class="vs-meta" aria-live="polite">Showing {len(stocks)} stocks</p>
<div class="table-scroll"><table><thead><tr><th scope="col">Company</th><th scope="col">Price</th><th scope="col">Score / 100</th><th scope="col">Rating</th><th scope="col">Daily move</th><th scope="col">Data quality</th><th scope="col">Sector</th></tr></thead><tbody id="stock-body">{''.join(rows)}</tbody></table></div>
</details></section><p class="vs-note">Scoring methodology: {esc(latest.get('scoring_model_version','Unavailable'))}. Prices and ratings reflect the saved scan, not live quotes. <a href="classic/">Old Dashboard</a> retains the full original layout, screens and filters.</p>'''
    return shell('Overview', 'overview', body)


def coverage_finding(c):
    if c.get('direct_matches'):
        finding = f'{c["direct_matches"]} direct company match(es)'
    elif c.get('relevant_matches'):
        finding = 'No direct company market found; related risk context available'
    else:
        finding = 'Search incomplete' if c.get('search_incomplete') else 'No relevant market found in the searched sample'
    if c.get('relevant_matches') and not c.get('displayed_matches'):
        finding += '; omitted by diversity/card limits'
    if c.get('search_incomplete') and finding != 'Search incomplete':
        finding += '; search incomplete'
    return finding


def market_card(m):
    impact = m.get('impact') or {}
    groups = impact.get('groups', [])
    stances = list(dict.fromkeys(s['stance'] for g in groups for s in g['stocks']))
    state = stances[0] if len(stances) == 1 else 'Stock-specific reviews' if stances else 'Insufficient evidence'
    gaps = impact.get('evidence_gaps', [])
    tickers = [c['ticker'] for c in m.get('related_stocks', [])]
    badges = ''.join(f'<span class="vs-ticker">{esc(t)}</span>' for t in tickers[:6])
    if len(tickers) > 6:
        badges += f'<details class="more-tickers"><summary>+{len(tickers)-6} related stocks</summary>' + ''.join(f'<span class="vs-ticker">{esc(t)}</span>' for t in tickers[6:]) + '</details>'
    effects = ''.join(f'<div><span class="vs-label">{esc(", ".join(s["ticker"] for s in g["stocks"][:6]))}{" + others" if len(g["stocks"])>6 else ""}</span><strong>{esc(g["direction"])}</strong></div>' for g in groups)
    probability = number(m.get('probability'))
    prob = '—' if probability is None else f'{probability*100:.1f}%'
    delta = number(m.get('change_24h'))
    delta_text = '24h change unavailable' if delta is None else f'{delta*100:+.1f} pp / 24h'
    volume = number(m.get('volume_24hr'))
    units = 'contracts' if m.get('source') == 'kalshi' else 'shares'
    volume_text = '24h activity unavailable' if volume is None else f'{volume:,.0f} {units} / 24h'
    evidence = '<ul class="evidence-list">' + ''.join(f'<li>{esc(g)}</li>' for g in gaps) + '</ul>' if gaps else '<p class="vs-evidence">Spreads and order-book depth unavailable.</p>'
    details = render_impact(m)
    # The outer disclosure is closed; full existing scenarios remain unchanged inside it.
    return f'''<article class="vs-event" data-market-card data-companies="{esc(' '.join(tickers))}">
<div class="vs-event-main"><div class="vs-event-top">{badges}<span class="vs-source">{esc(m.get('source','').title())} · {esc(m.get('relevance'))}</span></div>
<span class="vs-badge {'vs-warning' if gaps or state == 'Insufficient evidence' else ''}">{esc(state)}</span>
<h3 class="vs-event-title">{esc(m['title'])}</h3><p class="vs-contract">{esc(m.get('event_title'))} · Outcome: {esc(m.get('outcome'))}</p>
<div class="vs-prob"><div><span class="vs-prob-value">{prob}</span><span class="vs-prob-label">Event-implied probability</span></div><span class="vs-delta">{delta_text}</span></div>
<div class="vs-track" aria-hidden="true"><div class="vs-fill" style="width:{min(100,max(0,(probability or 0)*100))}%"></div></div>
<p class="vs-why"><strong class="vs-label">WHY THIS MATTERS</strong>{esc(m['why_this_matters'])}</p>
<div class="vs-impact"><span class="vs-label">POTENTIAL STOCK EFFECT</span>{effects or 'Insufficient evidence'}</div>
<p class="vs-evidence">{volume_text}</p>{evidence}</div>
<details class="vs-details"><summary>Scenarios &amp; holding criteria</summary><div class="vs-detail-body">{details}
<p class="vs-meta">Source row updated: {esc(sgt(m.get('source_updated_at')))}<br>Contract close: {esc(sgt(m.get('end_date')))}</p>
<a class="vs-source-link" href="{esc(m['url'])}" target="_blank" rel="noopener noreferrer">Read full contract on pdata.world ↗</a></div></details></article>'''


def predictions(report):
    selected = markets(report)
    body = heading('Prediction Market Intelligence', 'Events that matter to your stocks — company developments, business risks and thesis implications.', report.get('fetched_at_utc'), 'Market snapshot')
    watch = [c for c in report.get('coverage', []) if c.get('watchlist')]
    mu = report.get('existing_mu_advisory') or {}
    body += f'''<div class="vs-summary"><div><span class="vs-meta">Markets selected</span><strong class="vs-number">{len(selected)}</strong><span class="vs-meta">Company, sector &amp; macro events</span></div>
<div><span class="vs-meta">Your watchlist</span><strong class="vs-number">{len(watch)} stocks</strong><span class="vs-meta">Prioritised in selection</span></div>
<div><span class="vs-meta">Micron / Wealth Hub context</span><strong class="vs-context">Long term: {esc(mu.get('long_term_rating','Unavailable'))}</strong><span class="vs-meta">Short term: {esc(mu.get('short_term_rating','Unavailable'))} · Existing gate: {esc(mu.get('gate_hint','Unavailable'))}<br>{esc(sgt(mu.get('as_of')))} · {'Current at analysis' if mu.get('fresh') else 'Stale / unverified'}</span></div></div>'''
    banner = {'unavailable':'Feed unavailable. No prediction-market readings were retrieved.', 'partial':'Partial update: some queries failed. Coverage is incomplete.', 'no_matches':'No relevant market found in the searched sample.'}.get(report.get('status'))
    if banner:
        body += f'<p class="feed-warning">{esc(banner)}</p>'
    method = report.get('impact_method') or {}
    for error in method.get('context_errors', []):
        body += f'<p class="feed-warning">{esc(error)}</p>'
    options = ''.join(f'<option value="{esc(c["ticker"])}">{esc(c["ticker"])} · {esc(c["name"])}</option>' for c in report.get('coverage', []))
    body += f'<div class="market-controls"><label>Related company<select id="market-company"><option value="">All companies</option>{options}</select></label><label>Event type<select id="market-topic"><option value="">All event types</option>' + ''.join(f'<option value="{i}">{esc(t["name"])}</option>' for i, t in enumerate(report.get('topics', []))) + '</select></label><button id="market-reset" type="button">Clear filters</button><span id="market-count" class="vs-meta" aria-live="polite">' + str(len(selected)) + ' selected markets</span></div>'
    body += '<p class="probability-note">These are event probabilities, <strong>not probabilities of a stock rising</strong>. Effects and review labels are conditional scenarios; existing stock ratings and Wealth Hub signals are unchanged.</p>'
    for index, topic in enumerate(report.get('topics', [])):
        body += f'<section class="market-section" data-topic="{index}"><h2>{esc(topic["name"])}</h2><div class="vs-market-grid">' + ''.join(market_card(m) for m in topic.get('markets', [])) + '</div></section>'
    body += '<p id="market-empty" class="feed-warning" hidden>No selected markets match these filters. Check company coverage below.</p><section class="coverage"><h2>Your company coverage</h2><p id="selected-coverage" class="vs-note" aria-live="polite"></p>'
    def coverage_table(companies):
        return '<div class="table-scroll"><table><thead><tr><th scope="col">Company</th><th scope="col">Coverage in the searched sample</th></tr></thead><tbody>' + ''.join(f'<tr data-coverage-ticker="{esc(c["ticker"])}" data-finding="{esc(coverage_finding(c))}"><td><strong>{esc(c["ticker"])}</strong><br>{esc(c["name"])}</td><td>{esc(coverage_finding(c))}</td></tr>' for c in companies) + '</tbody></table></div>'
    body += coverage_table(watch) + '<details><summary>View other tracked companies</summary>' + coverage_table([c for c in report.get('coverage', []) if not c.get('watchlist')]) + '</details></section>'
    sources = ' · '.join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["label"])}</a>' for s in method.get('sources', []))
    body += f'''<details class="methodology"><summary>Data quality, sources &amp; methodology</summary>
<p>Data: <a href="https://pdata.world/" target="_blank" rel="noopener noreferrer">pdata.world</a> (CC BY 4.0), aggregating Kalshi and Polymarket. Model: {esc(report.get('model_version'))} · Status: {esc(report.get('status'))}.</p>
<p>Stock snapshot: {esc(sgt(method.get('stock_snapshot_at')))}. Scenario analysis: {esc(sgt(method.get('analyzed_at_utc')))}. No positions or bets are placed.</p>
<p>Selection prioritises company developments, sector risks, then macro context; watchlist companies precede portfolio companies. One representative outcome per event; no more than two events per company or risk family. Related stocks are qualitative links, not measured exposure. A missing direct market is not replaced with an unrelated question.</p>
<p>Review labels are conditional prompts, not orders or calibrated return forecasts. Freshness limit: 72 hours; dashboard data-quality floor: 70%; activity floor: 100 venue units. Adverse-event flags use 50% implied odds or a +5 percentage-point change after evidence checks. Moves over 25 percentage points require history verification. These rules are not backtested trading thresholds. Position size, cost basis, tax and personal sale limits are unavailable.</p>
<p>Source-row timestamps can reflect derived-field updates rather than recent trades. Unknown timestamps do not establish freshness. Volume is activity, not order-book depth. Kalshi contracts and Polymarket shares are not interchangeable liquidity measures. Do not combine or average probabilities.</p>
<p>{report.get('universe_size',0)} configured companies; up to {report.get('sample_limit_per_query',0)} results per query. Coverage is not exhaustive. Personal politics, CEO succession, word-mention bets and stock-price-only questions are excluded. Relevance ranks before within-venue activity. Exact duplicate event titles are suppressed, but semantic duplicates may remain. Refresh occurs when the scheduled workflow runs.</p><p>Research principles: {sources}</p></details>'''
    return shell('Prediction Markets', 'predictions', body, '../')


def publish(root=Path('.')):
    root = Path(root)
    docs = root / 'docs'
    current = (docs / 'index.html').read_text(encoding='utf-8')
    classic = docs / 'classic/index.html'
    original = classic.read_text(encoding='utf-8') if DESIGN_MARKER in current else current
    history = read_json(docs / 'data/score-history.json', [])
    if not isinstance(history, list) or not history or not isinstance(history[-1].get('stocks'), dict):
        raise ValueError('Valid saved stock history is required; existing pages were not replaced.')
    report = read_json(docs / 'data/prediction-market-intelligence.json', {'status':'unavailable','topics':[], 'coverage':[]})
    if not isinstance(report, dict) or not isinstance(report.get('topics'), list):
        report = {'status':'unavailable','topics':[], 'coverage':[]}
    watchlist = read_json(root / 'watchlist.json', [])
    if isinstance(watchlist, dict):
        watchlist = watchlist.get('tickers', watchlist.get('watchlist', []))
    if not isinstance(watchlist, list):
        watchlist = []
    parser = ClassicRows()
    parser.feed(original)
    # Prepare every page before writing, so a rendering error preserves the prior site.
    pages = {classic: classic_page(original), docs / 'index.html': overview(history, watchlist, report, read_json(docs / 'data/mu-signal.json', {}), parser.moves),
             docs / 'prediction-markets/index.html': predictions(report)}
    for path, contents in pages.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding='utf-8')
    print(f'Design published locally: Overview, {len(markets(report))} prediction cards, and preserved Old Dashboard.')


if __name__ == '__main__':
    publish()
