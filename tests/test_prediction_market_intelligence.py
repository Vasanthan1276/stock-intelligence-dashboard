import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import prediction_market_intelligence as pm

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)


def companies():
    all_companies = pm.load_companies()
    return {t: all_companies[t] for t in ('MU', 'NVDA', 'AMD', 'JPM', 'D05.SI', 'U11.SI', 'LRCX', 'MRNA', 'W')}


def row(title='Will Micron revenue exceed guidance?', **kwargs):
    return dict(source='kalshi', id='one', event_id='event', question=title,
                probability=.4, volume_24hr=100, **kwargs)


def relevance(title, universe=None):
    return pm.assess_relevance(pm.normalize_market(row(title), NOW), universe or companies())


class PredictionMarketTests(unittest.TestCase):
    def report(self, rows=(), fetcher=None):
        return pm.build_report(fetcher or (lambda _: list(rows)), now=NOW, companies=companies())

    def test_company_scope_comes_from_repository_without_importing_scanner(self):
        loaded = pm.load_companies()
        self.assertEqual({t for t, c in loaded.items() if c['watchlist']},
                         set(json.loads((pm.ROOT / 'watchlist.json').read_text())['tickers']))
        self.assertTrue(loaded['MRNA']['portfolio'])
        self.assertEqual(loaded['MU']['sector'], 'Semiconductors')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'scanner.py').write_text("raise RuntimeError('must not execute')\nUS_STOCKS={'NEW': {'name':'Newco','sector':'Energy'}}\nSINGAPORE_STOCKS={}")
            (root/'portfolio-universe.json').write_text('{"us":{},"singapore":{}}')
            (root/'watchlist.json').write_text('{"tickers":["NEW"]}')
            self.assertEqual(set(pm.load_companies(root)), {'NEW'})
            (root/'watchlist.json').write_text('{"tickers":["MISSING"]}')
            with self.assertRaises(ValueError):
                pm.load_companies(root)

    def test_queries_follow_actual_companies(self):
        original = pm.query_plan(companies())
        reduced = {t: c for t, c in companies().items() if t != 'MRNA'}
        self.assertTrue(any('Moderna' in q['query'] for q in original))
        self.assertFalse(any('Moderna' in q['query'] for q in pm.query_plan(reduced)))
        self.assertTrue(all(set(q['tickers']) <= set(reduced) for q in pm.query_plan(reduced)))

    def test_company_requires_business_relevance_and_safe_name_match(self):
        for title in ('Who will be the next CEO of NVIDIA?', 'Will Taiwan local elections happen?',
                      'Will Arsenal win?', 'Will W win the race?', 'Will Nvidia stock price exceed $500?',
                      'Will a museum increase revenue?', 'Will Micron sponsor the world cup?',
                      'What will NVIDIA say during their next earnings call?'):
            with self.subTest(title=title):
                self.assertIsNone(relevance(title))
        result = relevance('Will Micron revenue exceed guidance?')
        self.assertEqual(result['relevance'], 'Direct company')
        self.assertEqual([c['ticker'] for c in result['related_stocks']], ['MU'])
        self.assertIsNone(relevance('Will Unknownco revenue exceed guidance?'))
        self.assertEqual(relevance('Will $MU revenue grow?')['related_stocks'][0]['ticker'], 'MU')

    def test_explicit_business_risk_intersects_real_universe(self):
        result = relevance('Will HBM demand double?')
        self.assertEqual([c['ticker'] for c in result['related_stocks']], ['MU'])
        self.assertIsNone(pm.assess_relevance(pm.normalize_market(row('Will HBM demand double?'), NOW),
                                            {'MRNA': companies()['MRNA']}))
        result = relevance('Will China invade Taiwan?')
        self.assertEqual({c['ticker'] for c in result['related_stocks']}, {'MU','NVDA','AMD','LRCX'})
        result = relevance('Will the Federal Reserve cut rates?')
        self.assertEqual({c['ticker'] for c in result['related_stocks']}, {'JPM','D05.SI','U11.SI'})
        self.assertEqual(result['relevance'], 'Macro context')
        self.assertIsNone(relevance('Will Brazil interest rates rise?'))

    def test_direct_business_and_sector_explanations_can_coexist(self):
        result = relevance('Will Nvidia chip exports to China be banned?')
        direct = [c['ticker'] for c in result['related_stocks'] if c['relationship'] == 'Direct company']
        # Exports are classified as sector risk unless the explicit business cue matches.
        self.assertIn('NVDA', [c['ticker'] for c in result['related_stocks']])
        result = relevance('Will Nvidia export restrictions reduce revenue?')
        self.assertEqual(result['relevance'], 'Direct company')
        self.assertIn('chip_trade', result['risk_keys'])
        self.assertIn('trade restrictions', result['why_this_matters'])

    def test_probability_and_record_validation(self):
        for value in (None, True, False, 'broken', float('inf'), float('nan'), -.1, 1.1, 10**1000):
            self.assertIsNone(pm.normalize_market(dict(row(), probability=value), NOW))
        for value in (0, 1, '0.5'):
            self.assertIsNotNone(pm.normalize_market(dict(row(), probability=value), NOW))
        for item in (None, [], 'bad', dict(row(), active=False), dict(row(), closed=True),
                     dict(row(), source='unknown'), dict(row(), question=''),
                     dict(row(), end_date='2026-11-12T00:00:00Z')):
            self.assertIsNone(pm.normalize_market(item, NOW))

    def test_missing_activity_is_not_zero_and_delta_is_percentage_points(self):
        for value in (-1, None, float('nan'), True):
            result = pm.normalize_market(dict(row(), volume_24hr=value, prob_24h_change=2), NOW)
            self.assertIsNone(result['volume_24hr'])
            self.assertIsNone(result['change_24h'])
        self.assertEqual(pm.fmt_volume(None), '—')
        self.assertEqual(pm.fmt_volume(0), '0')
        self.assertEqual(pm.fmt_delta(.042), '+4.2 pp')
        self.assertEqual(pm.fmt_delta(None), '—')

    def test_relevance_and_watchlist_priority_rank_before_activity(self):
        low = relevance('Will Micron revenue grow?')
        high = dict(relevance('Will the Federal Reserve cut rates?'), market_id='rates', volume_24hr=999999)
        portfolio = dict(relevance('Will Moderna revenue grow?'), market_id='mrna', volume_24hr=999999)
        self.assertEqual(pm.rank_markets([high, portfolio, low])[0]['market_id'], low['market_id'])

    def test_event_outcomes_cross_venue_duplicates_and_company_cap(self):
        rows = []
        for i in range(8):
            rows.append(dict(row(f'Will Micron revenue exceed {i} billion?'), id=str(i),
                             event_id='same', event_title='Micron earnings', group_item_title=str(i)))
        rows.append(dict(rows[0], source='polymarket'))
        report = self.report(rows)
        self.assertEqual(len(report['topics'][0]['markets']), 1)
        rows = [dict(row(f'Will Micron revenue grow in year {i}?'), id=str(i), event_id=str(i)) for i in range(8)]
        report = self.report(rows)
        self.assertEqual(len(report['topics'][0]['markets']), 2)
        self.assertEqual(next(c for c in report['coverage'] if c['ticker']=='MU')['direct_matches'], 8)

    def test_risk_family_and_section_limits(self):
        rows = [dict(row(f'Will the Federal Reserve cut rates in year {i}?'), id=str(i), event_id=str(i)) for i in range(8)]
        report = self.report(rows)
        self.assertEqual(len(report['topics'][2]['markets']), 2)
        self.assertTrue(all(len(t['markets']) <= pm.MAX_PER_TOPIC for t in report['topics']))

    def test_no_matches_and_related_only_are_honest(self):
        report = self.report()
        self.assertEqual(report['status'], 'no_matches')
        self.assertIn('No relevant market found', pm.render_html(report))
        report = self.report([row('Will HBM demand double?')])
        mu = next(c for c in report['coverage'] if c['ticker'] == 'MU')
        self.assertEqual(mu['direct_matches'], 0)
        self.assertEqual(mu['relevant_matches'], 1)
        self.assertIn('No direct company market found; related risk context available', pm.render_html(report))

    def test_failed_search_is_not_no_matches(self):
        def failing(_):
            raise OSError('offline')
        report = self.report(fetcher=failing)
        self.assertEqual(report['status'], 'unavailable')
        self.assertTrue(all(c['search_incomplete'] for c in report['coverage']))
        page = pm.render_html(report)
        self.assertIn('Feed unavailable', page)
        self.assertNotIn('No relevant market found', page)
        report = self.report(fetcher=lambda _: {'items': []})
        self.assertEqual(report['status'], 'unavailable')

    def test_partial_failure_retains_successes_and_scoped_coverage(self):
        plan = pm.query_plan(companies())
        failing_query = next(q['query'] for q in plan if q['kind'] == 'memory_demand')
        def fetch(query):
            if query == failing_query:
                raise TimeoutError('offline')
            return [row()]
        report = self.report(fetcher=fetch)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['successful_queries'], len(plan)-1)
        self.assertTrue(next(c for c in report['coverage'] if c['ticker']=='MU')['search_incomplete'])
        self.assertFalse(next(c for c in report['coverage'] if c['ticker']=='MRNA')['search_incomplete'])
        self.assertIn('Partial update', pm.render_html(report))

    def test_html_escapes_all_external_fields_and_links(self):
        item = dict(row('Will Micron revenue exceed <script>alert(1)</script>?'),
                    event_id='a/b?"', group_item_title='Outcome <A>', updated_at='2026-11-13T00:00:00Z',
                    end_date='2028-12-31T00:00:00Z')
        report = self.report([item])
        market = report['topics'][0]['markets'][0]
        self.assertEqual(market['url'], 'https://pdata.world/events/kalshi/a%2Fb%3F%22')
        market['related_stocks'][0]['name'] = '<img onerror="bad">'
        market['why_this_matters'] += '<script>bad</script>'
        page = pm.render_html(report)
        self.assertNotIn('<script>', page)
        self.assertNotIn('<img ', page)
        for text in ('Outcome &lt;A&gt;', 'Related stocks', 'Why this matters',
                     'Source row updated: 2026-11-13T00:00:00Z', 'Scheduled close: 2028-12-31T00:00:00Z'):
            self.assertIn(text, page)

    def test_reasons_explain_specific_business_connection(self):
        earnings = relevance('Will Micron revenue beat guidance?')['why_this_matters']
        merger = relevance('Will JPMorgan announce an acquisition?')['why_this_matters']
        self.assertIn('profitability', earnings)
        self.assertIn('integration risk', merger)
        self.assertNotEqual(earnings, merger)

    def test_transport_retry_is_bounded(self):
        with patch.object(pm, 'urlopen', side_effect=[OSError('temporary'), io.StringIO('{"items": []}')]) as request:
            self.assertEqual(pm.fetch_markets('Micron'), [])
            self.assertEqual(request.call_count, 2)
        with patch.object(pm, 'urlopen', side_effect=OSError('persistent')) as request:
            with self.assertRaises(OSError):
                pm.fetch_markets('Micron')
            self.assertEqual(request.call_count, 2)

    def test_coverage_does_not_call_hidden_matches_missing(self):
        rows = [dict(row(f'Will {c["aliases"][0]} revenue beat guidance?'), id=t, event_id=t)
                for t, c in companies().items()]
        report = self.report(rows)
        self.assertEqual(len(report['topics'][0]['markets']), pm.MAX_PER_TOPIC)
        hidden = [c for c in report['coverage'] if c['direct_matches'] and not c['displayed_matches']]
        self.assertTrue(hidden)
        self.assertIn('omitted by diversity/card limits', pm.render_html(report))

    def test_http_request_and_response_contract(self):
        with patch.object(pm, 'urlopen', return_value=io.StringIO('{"items": []}')) as request:
            self.assertEqual(pm.fetch_markets('Micron'), [])
        params = parse_qs(urlparse(request.call_args.args[0].full_url).query)
        self.assertEqual(params['source'], ['kalshi,polymarket'])
        self.assertEqual(params['active'], ['true'])
        self.assertEqual(params['closed'], ['false'])
        self.assertEqual(params['search'], ['Micron'])
        self.assertEqual(params['page_size'], [str(pm.PAGE_SIZE)])
        self.assertEqual(request.call_args.kwargs['timeout'], 15)
        for data in ({'data': []}, {'items': {}}, [], 'broken JSON'):
            body = data if isinstance(data, str) else json.dumps(data)
            with patch.object(pm, 'urlopen', return_value=io.StringIO(body)):
                with self.assertRaises(ValueError):
                    pm.fetch_markets('rates')


if __name__ == '__main__':
    unittest.main()
