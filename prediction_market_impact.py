"""Conditional stock-impact analysis. Reads existing scores; never changes them.

No fitted stock-return model, target prices, orders or Wealth Hub gate updates.
The rules explain scenarios and review triggers, not deterministic trade calls.
"""
from __future__ import annotations
import html
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

IMPACT_VERSION = 'stock-impact-scenarios-v1'
FRESH_HOURS = 72
MIN_DATA_QUALITY = 70
MIN_ACTIVITY = 100  # Review-quality floor within either supported $1-payout venue.
BANKS = {'JPM', 'BAC', 'D05.SI', 'U11.SI', 'O39.SI'}
CLOUD = {'MSFT', 'AMZN', 'GOOGL', 'ORCL'}
SOURCES = [
    {'label': 'FINRA: stock research and consensus estimates',
     'url': 'https://syndication.finra.org/content/stock-investing-and-due-diligence'},
    {'label': 'U.S. Bank: prediction prices as one information source',
     'url': 'https://www.usbank.com/investing/financial-perspectives/market-news/prediction-markets-vs-investing.html'},
]


def number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def fresh(value, now, hours=FRESH_HOURS):
    parsed = timestamp(value)
    return parsed is not None and 0 <= (now - parsed).total_seconds() <= hours * 3600


def has(pattern, text):
    return re.search(pattern, text, re.I) is not None


def read_context(root, now):
    """Use only the latest snapshot. Never substitute an older missing stock."""
    context = {'stocks': {}, 'as_of': None, 'fresh': False, 'errors': [], 'mu_signal': None}
    try:
        history = json.loads((root / 'docs/data/score-history.json').read_text())
        if not isinstance(history, list) or not history or not isinstance(history[-1], dict):
            raise ValueError('Invalid history')
        latest = history[-1]
        if not isinstance(latest.get('stocks'), dict):
            raise ValueError('Invalid stocks')
        context.update(stocks=latest['stocks'], as_of=latest.get('timestamp'),
                       fresh=fresh(latest.get('timestamp'), now))
    except (OSError, ValueError, TypeError):
        context['errors'].append('Existing dashboard snapshot unavailable or invalid.')
    try:
        mu = json.loads((root / 'docs/data/mu-signal.json').read_text())
        age = number(mu.get('max_age_hours')) if isinstance(mu, dict) else None
        if not isinstance(mu, dict) or mu.get('symbol') != 'MU':
            raise ValueError('Invalid MU signal')
        context['mu_signal'] = {
            'as_of': mu.get('generated_at'), 'fresh': fresh(mu.get('generated_at'), now, min(age or 72, 72)),
            'thesis': mu.get('thesis'), 'gate_hint': mu.get('gate_hint'),
            'short_term_rating': (mu.get('ratings') or {}).get('short_term'),
            'long_term_rating': (mu.get('ratings') or {}).get('long_term'),
        }
    except (OSError, ValueError, TypeError, AttributeError):
        context['errors'].append('Existing MU advisory signal unavailable or invalid.')
    return context


def profile(key, direction, mechanism, yes, no, hold, reduce, confirm, benchmark=False):
    return dict(key=key, direction=direction, mechanism=mechanism, if_yes=yes, if_no=no,
                hold_case=hold, reduce_review=reduce, confirmation=confirm, benchmark_required=benchmark)


def scenario(market, company):
    """Interpret explicit contract wording; ambiguity never becomes a direction."""
    text = market['title']
    low = text.lower()
    sector, ticker = company['sector'], company['ticker']
    unknown = profile('unclear', 'Unclear',
        'The contract does not establish a single, reliable earnings or valuation effect for this company.',
        'The selected outcome occurs; its financial significance still needs verification.',
        'The selected outcome does not occur; that alone does not imply the opposite share-price move.',
        'The independently assessed earnings thesis and valuation remain acceptable.',
        'Company evidence weakens the thesis, or the position exceeds your own allocation limit.',
        'Verify the exact settlement rules, company exposure and expectations already reflected in the share price.')
    # Avoid reversing polarity accidentally in compound, negated or unclear titles.
    checked = re.sub(r'no later than|not later than', '', low)
    if has(r"\b(not|never|avoid|prevent|unless|fail to)\b|n['’]t\b", checked):
        return unknown
    if has(r'\b(acquisition|acquir\w*|merger)\b', text):
        target = any(has(r'(?:acquisition of|acquire|acquires|acquiring)\s+(?:the\s+)?'+re.escape(a)+r'\b', text)
                     for a in company['aliases'])
        if target:
            return profile('deal_target', 'Potential upside, terms dependent',
                'A takeover offer above the unaffected share price could create a premium for the target. Announcement odds do not establish an offer price or completion odds.',
                'A confirmed premium offer could support the shares; cash/stock terms and approval risk determine value.',
                'The takeover catalyst is absent; value returns to the standalone business rather than automatically falling.',
                'The standalone business supports the holding even without a takeover.',
                'The holding relies mainly on takeover speculation, or an actual offer leaves little upside relative to deal risk.',
                'Check a company announcement, offer price, financing, conditions and standalone valuation.', True)
        return profile('deal_buyer', 'Mixed',
            'Acquisitions can add revenue and capabilities, but the purchase price, funding and integration can reduce returns for the buyer.',
            'Growth benefits could be offset by overpayment, dilution, debt or integration costs.',
            'No acquisition preserves capital but does not resolve the existing operating outlook.',
            'The core business remains sound and any announced deal has credible returns and manageable financing.',
            'An announced deal materially weakens returns, leverage or the original investment thesis.',
            'Assess actual deal terms and expected cash-flow returns; an acquisition of an unspecified company has no reliable price direction.', True)
    if has(r'\b(earnings|reporting|results)\b', text) and has(r'\b(postponed|delayed|delay)\b', text):
        return profile('report_delay', 'Potential downside / uncertainty',
            'Delayed financial reporting can increase uncertainty and postpone assessment of demand and margins. It does not prove deteriorating earnings.',
            'The shares could face uncertainty until management explains the delay and confirms the reporting timetable.',
            'One timing concern recedes; an on-time report can still disappoint on earnings or guidance.',
            'The delay has a credible administrative explanation and the earnings thesis remains intact.',
            'The company confirms accounting concerns, guidance deterioration or repeated unexplained delays.',
            'Check the investor-relations calendar, management explanation and the actual results.')
    if 'us_rates' in market['risk_keys']:
        if has(r'\b0\s*(?:bps|basis points)\b|maintain|unchanged|hold rates', text):
            return profile('rates_unchanged', 'No new rate impulse',
                'A zero-basis-point outcome means unchanged rates, even if the contract title uses the word hike.',
                'Current financing conditions persist; management guidance and the future rate path matter more.',
                'A different rate outcome occurs; this contract alone does not identify its direction or size.',
                'Current financing costs, credit quality and valuation support the existing thesis.',
                'Refinancing pressure or credit losses weaken the thesis despite unchanged policy rates.',
                'Check the full set of meeting outcomes and management sensitivity to rates.')
        cut = has(r'\b(cut|cuts|decrease|lower|reduce)\b', text)
        hike = has(r'\b(hike|hikes|increase|raise|higher)\b', text)
        if cut == hike:
            return unknown
        if ticker in BANKS:
            return profile('bank_rates', 'Mixed',
                'Lower rates can compress lending margins but ease borrower stress and funding costs; higher rates can reverse those effects. Loan mix and deposit repricing determine the net result.',
                'The stated rate move changes both margins and credit demand; it is not automatically bullish or bearish for this bank.',
                'An alternative rate outcome applies; do not infer a specific alternative from this one contract.',
                'Net interest income guidance, asset quality and capital remain resilient.',
                'Management cuts income guidance or credit costs rise enough to weaken the thesis.',
                'Check bank-specific margin guidance, deposit costs and credit losses; US-to-Singapore effects are indirect.')
        if sector in {'REIT', 'Property'}:
            return profile('property_cut' if cut else 'property_hike', 'Potential upside' if cut else 'Potential downside',
                'Lower financing costs and discount rates can support property cash flows and valuations; higher rates can pressure them. A weak economy can offset rate-cut benefits.',
                'A cut could ease refinancing pressure; a hike could raise it, depending on fixed-rate debt and maturity dates.',
                'The expected financing change may not arrive; assess the actual alternative policy outcome.',
                'Debt maturities, occupancy and recurring cash flow remain manageable.',
                'Refinancing costs, falling occupancy or distribution cuts materially weaken the thesis.',
                'Check debt hedges, maturities and occupancy, not only the Fed outcome.')
        return unknown
    if 'chip_trade' in market['risk_keys']:
        easing = has(r'\b(lift|lifts|lifted|remove|removed|ease|eased|repeal)\b', text)
        tightening = has(r'\b(restrictions?|ban|banned|blocking|sanctions?|tariffs?)\b', text)
        if not tightening:
            return unknown
        return profile('chip_easing' if easing else 'chip_controls', 'Potential upside' if easing else 'Potential downside',
            'Rules affecting covered chips or equipment can change available customers, licences and shipment timing. The effect depends on this company\'s actual product and geographic exposure.',
            'Easier rules could reopen affected sales.' if easing else 'Tighter rules could restrict affected revenue, delay shipments or increase compliance costs.',
            'Existing rules remain a constraint; failure of this proposal does not remove all other restrictions.',
            'Management confirms limited exposure or credible offsets, with earnings guidance intact.',
            'Confirmed restrictions produce a material guidance cut or remove a key source of expected earnings.',
            'Verify the legal scope, affected products, revenue exposure and company guidance. Sector linkage alone is not proof of material exposure.')
    if 'taiwan_supply' in market['risk_keys']:
        return profile('taiwan_disruption', 'Potential downside',
            'A military or fabrication disruption could interrupt semiconductor production and customer deliveries. Exposure varies with sourcing, inventory and alternative capacity.',
            'Lost production and risk repricing could pressure exposed shares, potentially before reported earnings change.',
            'This particular disruption does not occur; other operational and valuation risks remain.',
            'Supply continuity is supported by credible operating information and position size remains within your limits.',
            'Confirmed disruption materially threatens supply, earnings or your acceptable concentration risk.',
            'Check verified operational reports, supplier exposure and inventory; low odds do not eliminate a severe downside scenario.')
    if 'us_economy' in market['risk_keys'] and has(r'\brecession\b', text):
        defensive = sector in {'Healthcare', 'Consumer Staples', 'Telecom'}
        bank = ticker in BANKS
        return profile('recession_defensive' if defensive else 'recession_bank' if bank else 'recession_cyclical',
            'Mixed / relatively defensive' if defensive else 'Potential downside',
            'Essential demand can be more resilient, but valuation and company-specific risks remain.' if defensive else
            'Weaker growth can reduce loan demand and increase defaults, pressuring bank earnings.' if bank else
            'Weaker demand can reduce sales, capacity use and margins; risk aversion can also pressure valuation multiples.',
            'Relative resilience is possible, not immunity from a falling share price.' if defensive else 'Earnings expectations and valuation could come under pressure.',
            'Avoiding the defined recession removes one risk, but does not guarantee earnings growth or higher shares.',
            'Demand, cash flow and balance-sheet resilience continue to support the thesis through a slowdown.',
            'Confirmed demand deterioration, guidance cuts or financial stress undermine expected earnings.',
            'Check company guidance and customer demand alongside the recession definition and time horizon.')
    if 'ai_spending' in market['risk_keys']:
        if ticker in CLOUD:
            return profile('cloud_capex', 'Mixed',
                'AI infrastructure investment can support future cloud revenue but uses cash now and increases depreciation. Returns depend on utilisation and monetisation.',
                'Higher spending can create future capacity while pressuring near-term free cash flow.',
                'Lower spending can protect cash but may signal weaker demand or reduce growth capacity.',
                'Utilisation, revenue growth and returns on investment justify the spending.',
                'Capital spending persistently outruns monetisation or materially weakens cash-flow expectations.',
                'Compare capex, cloud demand, depreciation and free-cash-flow guidance.')
        increasing = has(r'\b(increase|grow|rise|higher|double|exceed|above)\b', text)
        decreasing = has(r'\b(cut|decline|decrease|fall|lower|below)\b', text)
        if increasing == decreasing:
            return unknown
        return profile('ai_supplier_up' if increasing else 'ai_supplier_down', 'Potential upside' if increasing else 'Potential downside',
            'Customer infrastructure spending can translate into chip and equipment orders, subject to product share, lead times and pricing.',
            'The stated spending outcome could change order expectations; the effect depends on whether it surprises existing expectations.',
            'Failure to meet the selected outcome does not establish the size of any order change.',
            'Orders, shipments and margins confirm the expected demand and valuation remains reasonable.',
            'Customers cut spending or orders enough to weaken earnings guidance.',
            'Check customer commitments, company guidance and the spending benchmark already priced in.', True)
    if 'memory_demand' in market['risk_keys']:
        return profile('memory_cycle', 'Benchmark dependent',
            'Memory revenue depends on both shipment volume and selling prices. Stronger demand can help pricing, while added industry supply can offset it; revenue growth alone need not improve margins.',
            'The stated demand, supply or price outcome could change the memory earnings cycle; its direction depends on which measure changed and by how much.',
            'The selected condition is not met; this does not establish an opposite demand or pricing trend.',
            'Memory pricing, demand and gross-margin guidance support the earnings thesis.',
            'Confirmed price weakness, inventory build or excess supply materially reduces expected earnings.',
            'Verify the metric, industry supply and company pricing/margin guidance against expectations.', True)
    if 'energy_supply' in market['risk_keys']:
        return profile('energy_transport' if sector == 'Transport' else 'energy_producer', 'Mixed',
            'A supply disruption can raise fuel costs for transport operators; hedges and fare increases may offset them.' if sector == 'Transport' else
            'Tighter supply can support commodity prices, but a producer may also lose output or face operating disruption. Higher prices do not automatically mean higher cash flow.',
            'Assess the resulting commodity price and company-specific volumes, hedges and costs.',
            'This supply event is absent; demand and other supply changes still determine prices.',
            'Cash-flow guidance remains resilient after allowing for fuel costs, output and hedging.',
            'Confirmed cost increases or lost production materially weaken cash flow.',
            'Check commodity prices, operating exposure, volumes and hedges rather than assigning one direction to all energy-linked shares.')
    if has(r'\b(revenue|sales|earnings|profits?)\b', text):
        negative_threshold = has(r'(above|exceed|over|below|under)\s+(?:\$\s*)?-\d', text)
        below = has(r'\b(below|under|less than|miss)\b', text)
        return profile('financial_threshold', 'Benchmark dependent',
            ('Clearing a negative growth threshold can still mean shrinking sales. ' if negative_threshold else '') +
            'The threshold is a contract condition, not necessarily analyst consensus or company guidance. Stock prices respond to the surprise, margins and forward outlook.',
            'A below-threshold result could pressure shares if it also misses expectations; the contract does not establish that comparison.' if below else
            'A result above expectations with sound margins could support the shares; clearing this threshold alone does not establish that.',
            'Avoiding a below-threshold result is not necessarily an earnings beat.' if below else
            'Missing this threshold could disappoint, but the actual market benchmark and forward guidance determine the significance.',
            'Reported demand, margins and forward guidance support the thesis at the current valuation.',
            'Results or guidance materially miss a verified benchmark and weaken the earnings thesis.',
            'Verify the metric, fiscal period, unit, company guidance and matching consensus estimate. No matched benchmark is available in this dataset.', True)
    return unknown


def baseline_for(ticker, context):
    raw = context['stocks'].get(ticker)
    if not isinstance(raw, dict):
        return {'rating': 'Unavailable', 'fresh': False, 'as_of': context['as_of'], 'data_quality': None}
    result = {k: number(raw.get(k)) for k in ('overall', 'technical', 'momentum', 'fundamental', 'valuation', 'data_quality')}
    result = {k: v if v is not None and 0 <= v <= 100 else None for k, v in result.items()}
    result.update(rating=str(raw.get('rating') or 'Unavailable'), fresh=context['fresh'], as_of=context['as_of'])
    return result


def evidence(market, fetched_at, now):
    gaps = []
    if not fresh(fetched_at, now):
        gaps.append('Prediction snapshot is stale or its timestamp is unknown.')
    if not fresh(market.get('source_updated_at'), now):
        gaps.append('Source row is stale or its timestamp is unknown.')
    volume = number(market.get('volume_24hr'))
    if volume is None:
        gaps.append('Recent trading activity is unknown.')
    elif volume == 0:
        gaps.append('Zero reported 24-hour activity; this price has no recent trading confirmation.')
    elif volume < MIN_ACTIVITY:
        gaps.append('Limited reported 24-hour activity; treat the price as a weak signal.')
    delta = number(market.get('change_24h'))
    if delta is not None and abs(delta) > .25:
        gaps.append('The reported move exceeds 25 percentage points; verify its history before treating it as a trend.')
    return gaps


def review_stance(scenario, baseline, market, gaps):
    direction = scenario['direction']
    weak = (baseline.get('data_quality') is None or baseline['data_quality'] < MIN_DATA_QUALITY or
            baseline.get('overall') is None or baseline['rating'].casefold() not in {'strong buy', 'buy', 'hold', 'watch', 'caution'})
    if gaps or not baseline['fresh'] or weak:
        reason = '; '.join(gaps) if gaps else 'Dashboard context is stale, missing or below the 70% data-quality review floor.'
        return 'Insufficient evidence', reason
    if scenario['benchmark_required'] or direction in {'Unclear', 'Benchmark dependent'}:
        return 'Wait for confirmation', scenario['confirmation']
    if baseline['rating'].casefold() in {'watch', 'caution'}:
        return 'Review existing weak thesis', 'The existing dashboard already flags Watch or Caution. This event does not clear that concern; reassess the original thesis and valuation.'
    p = market['probability']
    delta = market.get('change_24h')
    adverse = direction.startswith('Potential downside')
    if adverse and (p >= .5 or (delta is not None and delta >= .05)):
        return 'Review downside exposure', 'The adverse event is at least 50% implied or rose by at least 5 percentage points. Check the stated sell-review conditions; this is not a sell instruction.'
    if adverse:
        return 'Monitor downside risk', 'The adverse outcome is below 50% implied without a rise of at least 5 percentage points. Low odds do not make the potential loss immaterial.'
    if direction == 'Potential upside' and p >= .5 and baseline['rating'].casefold() in {'buy', 'strong buy'}:
        return 'Hold case supported — conditional', 'The existing dashboard is constructive and the supportive event is at least 50% implied. Confirm company exposure and valuation before acting.'
    return 'Hold / monitor — conditional', 'This event alone does not justify changing the holding. Use the company-specific hold and reduce-review conditions below.'


def enrich_report(report, companies, root, now=None):
    now = now or datetime.now(timezone.utc)
    context = read_context(Path(root), now)
    report['impact_method'] = {'version': IMPACT_VERSION, 'analyzed_at_utc': now.isoformat(timespec='seconds'),
        'stock_snapshot_at': context['as_of'], 'context_errors': context['errors'],
        'freshness_hours': FRESH_HOURS, 'minimum_data_quality': MIN_DATA_QUALITY,
        'minimum_activity': MIN_ACTIVITY, 'sources': SOURCES,
        'limits': 'Conditional scenarios and review prompts only; no calibrated stock-return probability, price target or personalised sell threshold.'}
    report['existing_mu_advisory'] = context['mu_signal']
    for topic in report['topics']:
        for market in topic['markets']:
            gaps = evidence(market, report['fetched_at_utc'], now)
            groups = {}
            for related in market['related_stocks']:
                ticker = related['ticker']
                analysis = scenario(market, companies[ticker])
                baseline = baseline_for(ticker, context)
                stance, reason = review_stance(analysis, baseline, market, gaps)
                group = groups.setdefault(analysis['key'], {**analysis, 'stocks': []})
                group['stocks'].append({'ticker': ticker, 'name': related['name'], 'baseline': baseline,
                                        'stance': stance, 'stance_reason': reason})
            market['impact'] = {'groups': list(groups.values()), 'evidence_gaps': gaps,
                'probability_meaning': f"{market['probability'] * 100:.1f}% is the implied probability of this selected contract outcome, not of any related share price rising.",
                'horizon': 'Near-term sentiment can react before resolution; earnings effects depend on the stated fiscal period or implementation date. Scheduled contract close: ' + (market.get('end_date') or 'unknown'),
                'confidence': 'Limited: qualitative scenario mapping; no calibrated return forecast. Source updates do not prove recent trades, and spreads/depth are unavailable.'}
    return report


def render_impact(market):
    impact = market.get('impact')
    if not impact:
        return '<p class="impact-warning">Stock implications unavailable: insufficient evidence.</p>'
    esc = lambda x: html.escape(str(x), quote=True)
    def stock_row(stock):
        b = stock['baseline']
        score = '—' if b.get('overall') is None else f"{b['overall']:g}/100"
        factors = ' · '.join(label + ' ' + ('—' if b.get(key) is None else f'{b[key]:g}')
                             for key, label in [('fundamental','Fundamentals'),('valuation','Valuation'),('technical','Technical'),('momentum','Momentum')])
        quality = 'unknown' if b.get('data_quality') is None else f"{b['data_quality']:g}%"
        age = '' if b['fresh'] else ' · stale/missing'
        return (f'<tr><td><b>{esc(stock["ticker"])}</b></td>'
                f'<td>{esc(b["rating"])} · {esc(score)}<br><span class="meta">{esc(factors)}<br>Data quality: {esc(quality + age)}</span></td>'
                f'<td><strong>{esc(stock["stance"])}</strong><br><span class="meta">{esc(stock["stance_reason"])}</span></td></tr>')
    groups = []
    for index, group in enumerate(impact['groups']):
        stocks = group['stocks']
        tickers = ', '.join(s['ticker'] for s in stocks[:6]) + (f' +{len(stocks)-6}' if len(stocks)>6 else '')
        rows = ''.join(stock_row(s) for s in stocks[:6])
        more = ''
        if len(stocks)>6:
            more = f'<details><summary>Assess {len(stocks)-6} other stocks in this group</summary><table class="impact-table"><thead><tr><th>Stock</th><th>Existing dashboard</th><th>Current review</th></tr></thead><tbody>{"".join(stock_row(s) for s in stocks[6:])}</tbody></table></details>'
        block = (f'<table class="impact-table"><thead><tr><th>Stock</th><th>Existing dashboard</th><th>Current review</th></tr></thead><tbody>{rows}</tbody></table>{more}'
                 f'<p class="mechanism">{esc(group["mechanism"])}</p>'
                 f'<dl class="impact-scenarios"><dt>If this outcome happens</dt><dd>{esc(group["if_yes"])}</dd>'
                 f'<dt>If it does not happen</dt><dd>{esc(group["if_no"])}</dd>'
                 f'<dt>Holding remains reasonable if…</dt><dd>{esc(group["hold_case"])}</dd>'
                 f'<dt>Consider a reduce / sell review if…</dt><dd>{esc(group["reduce_review"])}</dd>'
                 f'<dt>What to verify next</dt><dd>{esc(group["confirmation"])}</dd></dl>')
        groups.append(f'<details class="impact-group" {"open" if index==0 else ""}><summary>{esc(tickers)} — {esc(group["direction"])}</summary>{block}</details>')
    gaps = ''.join(f'<li>{esc(g)}</li>' for g in impact['evidence_gaps'])
    warning = f'<div class="impact-warning"><strong>Evidence gaps</strong><ul>{gaps}</ul></div>' if gaps else ''
    return (f'<div class="impact-panel"><h3>How this could affect your stocks</h3>'
            f'<p class="probability-note">{esc(impact["probability_meaning"])}</p>{warning}{"".join(groups)}'
            f'<p class="meta">{esc(impact["horizon"])}</p><p class="meta">{esc(impact["confidence"])}</p></div>')
