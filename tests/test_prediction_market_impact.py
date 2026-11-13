import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import prediction_market_impact as impact
import prediction_market_intelligence as pm

NOW = datetime(2026, 11, 13, 8, tzinfo=timezone.utc)


def market(title, risks=(), probability=.7, volume=1000, delta=.01):
    return dict(title=title, risk_keys=list(risks), probability=probability,
                volume_24hr=volume, change_24h=delta, source_updated_at=NOW.isoformat(), end_date='2027-01-01T00:00:00Z')


def company(ticker, name, sector):
    return dict(ticker=ticker, name=name, sector=sector, aliases=(name,))


MU = company('MU', 'Micron', 'Semiconductors')
DBS = company('D05.SI', 'DBS', 'Banks')
REIT = company('A17U.SI', 'CapitaLand Ascendas REIT', 'REIT')
GOOD = dict(rating='Buy', overall=70, data_quality=100, fresh=True, as_of=NOW.isoformat())


class StockImpactTests(unittest.TestCase):
    def test_same_rate_cut_has_different_bank_and_property_effects(self):
        m = market('Will the Fed decrease interest rates by 25 bps?', ['us_rates'])
        self.assertEqual(impact.scenario(m, DBS)['direction'], 'Mixed')
        self.assertEqual(impact.scenario(m, REIT)['direction'], 'Potential upside')
        self.assertIn('margins', impact.scenario(m, DBS)['mechanism'])
        self.assertIn('financing', impact.scenario(m, REIT)['mechanism'])

    def test_zero_bps_is_not_a_rate_hike(self):
        p = impact.scenario(market('Will the Fed Hike rates by 0bps?', ['us_rates']), REIT)
        self.assertEqual(p['direction'], 'No new rate impulse')

    def test_acquisition_buyer_and_target_are_not_both_bullish(self):
        m = market('Will Meta announce acquisition of Pinterest?')
        buyer = impact.scenario(m, company('META','Meta','Communication Services'))
        target = impact.scenario(m, company('PINS','Pinterest','Communication Services'))
        self.assertEqual(buyer['direction'], 'Mixed')
        self.assertIn('terms dependent', target['direction'])
        self.assertTrue(target['benchmark_required'])
        self.assertIn('standalone', target['hold_case'])

    def test_negative_sales_threshold_is_not_an_earnings_beat(self):
        m = market('Will Lululemon report Above -9% comparable sales growth?', probability=.99)
        p = impact.scenario(m, company('LULU','Lululemon','Consumer'))
        self.assertIn('shrinking sales', p['mechanism'])
        self.assertEqual(p['direction'], 'Benchmark dependent')
        self.assertEqual(impact.review_stance(p, GOOD, m, [])[0], 'Wait for confirmation')

    def test_below_threshold_yes_is_not_described_as_above_threshold(self):
        p = impact.scenario(market('Will Micron revenue be below $20B?'), MU)
        self.assertIn('below-threshold', p['if_yes'])
        self.assertTrue(p['benchmark_required'])

    def test_revenue_probability_is_not_stock_return_or_buy_signal(self):
        m = market('Will Micron revenue exceed $20B?', probability=.99)
        p = impact.scenario(m, MU)
        stance, _ = impact.review_stance(p, GOOD, m, [])
        self.assertEqual(stance, 'Wait for confirmation')
        self.assertNotIn('price_target', p)
        self.assertNotIn('return_probability', p)

    def test_zero_activity_and_unknown_or_stale_dates_block_stance(self):
        m = market('Will chip export restrictions become law?', ['chip_trade'], volume=0)
        p = impact.scenario(m, MU)
        gaps = impact.evidence(m, NOW.isoformat(), NOW)
        self.assertEqual(impact.review_stance(p, GOOD, m, gaps)[0], 'Insufficient evidence')
        self.assertTrue(any('Zero reported' in g for g in gaps))
        for stamp in (None, 'bad', (NOW-timedelta(hours=73)).isoformat(), (NOW+timedelta(hours=1)).isoformat()):
            gaps = impact.evidence(dict(m, volume_24hr=1000, source_updated_at=stamp), NOW.isoformat(), NOW)
            self.assertTrue(gaps)
        self.assertTrue(impact.evidence(dict(m, volume_24hr=1000), 'bad', NOW))

    def test_large_reported_move_requires_verification(self):
        m = market('Will chip export restrictions become law?', ['chip_trade'], delta=.61)
        gaps = impact.evidence(m, NOW.isoformat(), NOW)
        self.assertTrue(any('25 percentage' in g for g in gaps))
        self.assertEqual(impact.review_stance(impact.scenario(m, MU), GOOD, m, gaps)[0], 'Insufficient evidence')

    def test_adverse_probability_is_a_review_prompt_not_sell_order(self):
        m = market('Will chip export restrictions become law?', ['chip_trade'], probability=.6)
        stance, reason = impact.review_stance(impact.scenario(m,MU), GOOD,m,[])
        self.assertEqual(stance, 'Review downside exposure')
        self.assertIn('not a sell instruction', reason)
        low = dict(m, probability=.06, change_24h=-.05)
        self.assertEqual(impact.review_stance(impact.scenario(low,MU),GOOD,low,[])[0], 'Monitor downside risk')

    def test_low_quality_or_missing_dashboard_does_not_support_a_hold(self):
        m = market('Will the Fed cut interest rates?', ['us_rates'])
        p = impact.scenario(m,REIT)
        for b in (dict(GOOD,data_quality=35), dict(GOOD,fresh=False), dict(GOOD,overall=None), dict(GOOD,rating='Unknown')):
            self.assertEqual(impact.review_stance(p,b,m,[])[0], 'Insufficient evidence')
        self.assertEqual(impact.review_stance(p,GOOD,m,[])[0], 'Hold case supported — conditional')
        self.assertEqual(impact.review_stance(p,dict(GOOD,rating='Watch'),m,[])[0], 'Review existing weak thesis')

    def test_negated_and_ambiguous_contracts_abstain(self):
        for title in ('Will chip export restrictions NOT become law?', 'Will China avoid a Taiwan invasion?',
                      'Will the Fed cut rates unless inflation rises?', "Will the Fed's cut fail to happen?"):
            self.assertEqual(impact.scenario(market(title,['chip_trade','taiwan_supply','us_rates']),MU)['direction'], 'Unclear')

    def test_restriction_removal_is_not_tightening(self):
        m = market('Will chip export restrictions be lifted?', ['chip_trade'])
        self.assertEqual(impact.scenario(m,MU)['direction'], 'Potential upside')

    def test_ai_operator_and_supplier_have_different_mechanisms(self):
        m = market('Will AI spending increase?', ['ai_spending'])
        operator = impact.scenario(m,company('MSFT','Microsoft','Technology'))
        supplier = impact.scenario(m,MU)
        self.assertEqual(operator['direction'], 'Mixed')
        self.assertEqual(supplier['direction'], 'Potential upside')
        self.assertIn('free cash flow', operator['if_yes'])

    def test_latest_context_only_and_signal_never_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            data=root/'docs/data';data.mkdir(parents=True)
            history=[{'timestamp':(NOW-timedelta(days=1)).isoformat(),'stocks':{'MU':GOOD}},
                     {'timestamp':NOW.isoformat(),'stocks':{'AMD':GOOD}}]
            (data/'score-history.json').write_text(json.dumps(history))
            signal={'symbol':'MU','generated_at':NOW.isoformat(),'max_age_hours':72,'thesis':'positive','gate_hint':'defer',
                    'ratings':{'short_term':'Watch','long_term':'Strong Buy'}}
            (data/'mu-signal.json').write_text(json.dumps(signal))
            before={p.name:p.read_bytes() for p in data.iterdir()}
            context=impact.read_context(root,NOW)
            self.assertEqual(impact.baseline_for('MU',context)['rating'],'Unavailable')
            self.assertEqual(context['mu_signal']['gate_hint'],'defer')
            self.assertEqual(context['mu_signal']['short_term_rating'],'Watch')
            self.assertEqual(before,{p.name:p.read_bytes() for p in data.iterdir()})
            (data/'score-history.json').write_text('{}')
            self.assertTrue(impact.read_context(root,NOW)['errors'])

    def test_out_of_range_baseline_values_are_not_trusted(self):
        c={'stocks':{'MU':dict(GOOD,overall=1000,data_quality=200)},'fresh':True,'as_of':NOW.isoformat()}
        b=impact.baseline_for('MU',c)
        self.assertIsNone(b['overall'])
        self.assertIsNone(b['data_quality'])

    def test_enrichment_is_separate_and_all_user_facing_fields_are_escaped(self):
        c=pm.load_companies()
        raw={'source':'kalshi','id':'x','question':'Will Micron revenue exceed <script>bad</script>?','probability':.7,'volume_24hr':1000,
             'updated_at':NOW.isoformat(),'end_date':'2027-01-01T00:00:00Z'}
        r=pm.build_report(lambda _:[raw],NOW,{'MU':c['MU']})
        m=r['topics'][0]['markets'][0]
        self.assertIn('not of any related share price rising',m['impact']['probability_meaning'])
        m['impact']['groups'][0]['stocks'][0]['stance_reason']='<img src=x onerror=bad>'
        rendered=pm.render_html(r)
        self.assertNotIn('<script>bad',rendered)
        self.assertNotIn('<img src=x',rendered)
        self.assertIn('Consider a reduce / sell review',rendered)
        self.assertIn('Holding remains reasonable',rendered)
        self.assertIn('Existing Micron / Wealth Hub context',rendered)
        self.assertNotIn('stock_return_probability',r)


if __name__=='__main__':
    unittest.main()
