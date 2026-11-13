"""Offline checks for the presentation layer and repeat scheduled generation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import dashboard_design as design

ROOT = Path(__file__).resolve().parents[1]


class DashboardDesignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'docs/data').mkdir(parents=True)
        self.original = '''<!doctype html><html><head><title>Original</title></head><body>
<input id="stockSearch"><a href="stocks/mu/">MU</a><a href="micron/">Micron</a>
<table><tr class="filterable-row"><td>1</td><td><a href="stocks/mu/">Micron</a></td><td>$100</td><td>-1.59%</td></tr></table>
<script>const originalFilters = true;</script></body></html>'''
        (self.root / 'docs/index.html').write_text(self.original)
        for name in ['docs/data/score-history.json', 'docs/data/mu-signal.json', 'docs/data/prediction-market-intelligence.json', 'watchlist.json']:
            (self.root / name).write_bytes((ROOT / name).read_bytes())
        (self.root / 'docs/micron').mkdir()
        (self.root / 'docs/micron/index.html').write_bytes(b'protected micron analysis')

    def test_original_layout_keeps_content_filters_and_resolved_links(self):
        design.publish(self.root)
        classic = (self.root / 'docs/classic/index.html').read_text()
        restored = classic.replace('\n<base href="../">', '', 1).replace('\n' + design.CLASSIC_BAR, '', 1)
        self.assertEqual(restored, self.original)
        self.assertIn('<base href="../">', classic)
        self.assertIn('href="./"', classic)
        self.assertIn('originalFilters', classic)

    def test_repeat_render_does_not_replace_classic_with_new_layout(self):
        design.publish(self.root)
        files = ['docs/index.html','docs/classic/index.html','docs/prediction-markets/index.html']
        before = {f:(self.root / f).read_bytes() for f in files}
        design.publish(self.root)
        self.assertEqual(before, {f:(self.root / f).read_bytes() for f in files})

    def test_fresh_scheduled_scan_refreshes_old_and_new_layout(self):
        design.publish(self.root)
        fresh = self.original.replace('-1.59%', '+2.50%')
        (self.root / 'docs/index.html').write_text(fresh)
        design.publish(self.root)
        for name in ['docs/index.html','docs/classic/index.html']:
            self.assertIn('+2.50%', (self.root / name).read_text())

    def test_protected_signals_history_and_report_are_byte_identical(self):
        protected = ['docs/micron/index.html','docs/data/score-history.json','docs/data/mu-signal.json','docs/data/prediction-market-intelligence.json','watchlist.json']
        before = {f:(self.root/f).read_bytes() for f in protected}
        design.publish(self.root)
        self.assertEqual(before, {f:(self.root/f).read_bytes() for f in protected})

    def test_navigation_order_and_all_data_survive(self):
        design.publish(self.root)
        overview = (self.root/'docs/index.html').read_text()
        prediction = (self.root/'docs/prediction-markets/index.html').read_text()
        history = json.loads((self.root/'docs/data/score-history.json').read_text())
        report = json.loads((self.root/'docs/data/prediction-market-intelligence.json').read_text())
        self.assertEqual(overview.count('data-stock-row '), len(history[-1]['stocks']))
        self.assertEqual(prediction.count('data-market-card '), len(design.markets(report)))
        for page, prefix in [(overview,'./'),(prediction,'../')]:
            nav=page.split('<nav ',1)[1].split('</nav>',1)[0]
            self.assertLess(nav.index('>Guide<'), nav.index('>Old Dashboard<'))
            self.assertIn(f'href="{prefix}classic/"', nav)
        self.assertEqual(prediction.count('<details class="vs-details">'), len(design.markets(report)))
        for market in design.markets(report):
            for group in market['impact']['groups']:
                self.assertIn(design.esc(group['hold_case']), prediction)
                self.assertIn(design.esc(group['reduce_review']), prediction)

    def test_missing_prediction_feed_is_visible_without_breaking_stocks(self):
        (self.root/'docs/data/prediction-market-intelligence.json').unlink()
        design.publish(self.root)
        self.assertIn('Feed unavailable', (self.root/'docs/prediction-markets/index.html').read_text())
        self.assertIn('Micron Technology', (self.root/'docs/index.html').read_text())

    def test_invalid_stock_snapshot_does_not_replace_existing_pages(self):
        (self.root/'docs/data/score-history.json').write_text('[]')
        with self.assertRaises(ValueError):
            design.publish(self.root)
        self.assertEqual((self.root/'docs/index.html').read_text(), self.original)
        self.assertFalse((self.root/'docs/classic/index.html').exists())

    def test_untrusted_labels_are_escaped_and_report_is_not_mutated(self):
        report=json.loads((ROOT/'docs/data/prediction-market-intelligence.json').read_text())
        report['topics'][0]['markets'][0]['title']='<script>alert(1)</script>'
        original=copy.deepcopy(report)
        result=design.predictions(report)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',result)
        self.assertNotIn('<script>alert(1)</script>',result)
        self.assertEqual(report,original)

    def test_no_match_and_partial_coverage_are_distinct(self):
        self.assertIn('No relevant market found',design.coverage_finding({}))
        self.assertEqual(design.coverage_finding({'search_incomplete':True}),'Search incomplete')
        self.assertIn('omitted by diversity/card limits',design.coverage_finding({'relevant_matches':2}))


if __name__ == '__main__':
    unittest.main()
