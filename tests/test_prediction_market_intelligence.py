import unittest
import io
import json
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import prediction_market_intelligence as pm


class PredictionMarketTests(unittest.TestCase):
    def test_normalizes_and_attributes(self):
        item = {
            "source": "kalshi", "id": "KX-FED-YES", "event_id": "KX-FED",
            "question": "Will Federal Reserve cut interest rates?", "event_title": "Fed decision",
            "probability": 0.67, "prob_24h_change": 0.08, "volume_24hr": 2000,
            "closed": False,
        }
        result = pm.normalize_market(item, pm.TOPICS[0][2])
        self.assertEqual(result["probability"], 0.67)
        self.assertEqual(result["change_24h"], 0.08)
        self.assertEqual(result["url"], "https://pdata.world/events/kalshi/KX-FED")

    def test_skips_irrelevant_closed_and_invalid(self):
        pattern = pm.TOPICS[0][2]
        base = {"source": "kalshi", "id": "1", "question": "Will interest rates change?", "probability": 0.4}
        self.assertIsNone(pm.normalize_market(dict(base, closed=True), pattern))
        self.assertIsNone(pm.normalize_market(dict(base, probability=1.2), pattern))
        self.assertIsNone(pm.normalize_market(dict(base, probability=float("nan")), pattern))
        self.assertIsNone(pm.normalize_market(dict(base, source="unknown"), pattern))
        self.assertIsNone(pm.normalize_market(dict(base, question="Will Arsenal win?"), pattern))

    def test_collects_without_changing_stock_scores(self):
        def fake_fetcher(q):
            return [{"source": "polymarket", "id": q, "event_id": "123", "question": f"Will {q} change?", "probability": 0.25, "volume_24hr": 500}]
        report = pm.build_report(fake_fetcher, now=datetime(2026, 11, 9, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["model_version"], "prediction-market-shadow-v1")
        self.assertEqual(len(report["topics"]), 4)
        self.assertNotIn("overall_score", report)

    def test_api_down_is_explicit_and_html_escapes(self):
        def failing(_):
            raise OSError("unavailable")
        report = pm.build_report(failing)
        self.assertEqual(report["status"], "unavailable")
        page = pm.render_html(report)
        self.assertIn("Feed unavailable", page)
        unsafe = {"source": "kalshi", "id": "abc", "question": "Will Federal Reserve <script>alert(1)</script>?", "probability": 0.3}
        normalized = pm.normalize_market(unsafe, pm.TOPICS[0][2])
        report["topics"][0]["markets"] = [normalized]
        page = pm.render_html(report)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_prob_delta_is_percentage_points(self):
        self.assertEqual(pm.fmt_delta(0.042), "+4.2 pp")
        self.assertEqual(pm.fmt_delta(-0.05), "-5.0 pp")
        self.assertEqual(pm.fmt_delta(None), "—")

    def test_probability_boundaries_and_invalid_numbers(self):
        base = {"source": "kalshi", "question": "Will interest rates change?"}
        for value in (None, True, False, "not a number", float("inf"), -0.1, 1.1, 10**1000):
            with self.subTest(value=repr(value)[:40]):
                self.assertIsNone(pm.normalize_market(dict(base, probability=value), pm.TOPICS[0][2]))
        for value in (0, 1, "0.5"):
            with self.subTest(value=value):
                self.assertIsNotNone(pm.normalize_market(dict(base, probability=value), pm.TOPICS[0][2]))

    def test_missing_activity_is_not_reported_as_zero(self):
        base = {"source": "kalshi", "question": "Will interest rates change?", "probability": .4}
        for value in (-1, None, float("nan"), True):
            result = pm.normalize_market(dict(base, volume_24hr=value, prob_24h_change=2), pm.TOPICS[0][2])
            self.assertIsNone(result["volume_24hr"])
            self.assertIsNone(result["change_24h"])
        self.assertEqual(pm.fmt_volume(None), "—")
        self.assertEqual(pm.fmt_volume(0), "0")

    def test_inactive_non_records_and_empty_titles_are_skipped(self):
        base = {"source": "kalshi", "question": "Will interest rates change?", "probability": .4}
        for item in (None, [], "invalid", dict(base, active=False), dict(base, question="")):
            self.assertIsNone(pm.normalize_market(item, pm.TOPICS[0][2]))

    def test_empty_feed_has_no_matches_state(self):
        report = pm.build_report(lambda _: [])
        self.assertEqual(report["status"], "no_matches")
        self.assertIn("No matching active contracts", pm.render_html(report))

    def test_partial_failure_keeps_successful_observations(self):
        def fetch(query):
            if query == "Federal Reserve":
                raise TimeoutError("request timed out")
            return [{"source": "kalshi", "id": "rates", "question": "Will interest rates change?", "probability": .4}]
        report = pm.build_report(fetch)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["successful_queries"], 9)
        self.assertEqual(len(report["failed_queries"]), 1)
        self.assertEqual(len(report["topics"][0]["markets"]), 1)
        self.assertIn("Partial update", pm.render_html(report))

    def test_bad_query_payload_is_explicit_failure(self):
        report = pm.build_report(lambda _: {"items": []})
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(len(report["failed_queries"]), 10)

    def test_deduplicates_by_venue_and_caps_each_topic(self):
        rows = [{"source": "kalshi", "id": str(i), "question": "Will interest rates change?",
                 "probability": .4, "volume_24hr": i} for i in range(12)]
        rows += [dict(rows[-1]), dict(rows[-1], source="polymarket")]
        report = pm.build_report(lambda _: rows)
        markets = report["topics"][0]["markets"]
        self.assertEqual(len(markets), pm.MAX_PER_TOPIC)
        self.assertEqual(len({(m["source"], m["market_id"]) for m in markets}), len(markets))
        self.assertEqual({m["source"] for m in markets if m["market_id"] == "11"}, {"kalshi", "polymarket"})

    def test_displays_outcome_and_source_timestamps_safely(self):
        item = {"source": "kalshi", "id": "1", "event": {"id": 'a/b?"'},
                "question": "Who will be the next CEO of NVIDIA?", "event_title": "NVIDIA CEO",
                "group_item_title": "Candidate <A>", "probability": .4,
                "updated_at": "2026-11-13T00:00:00Z", "end_date": "2028-12-31T00:00:00Z"}
        report = pm.build_report(lambda _: [item])
        market = report["topics"][2]["markets"][0]
        self.assertEqual(market["url"], "https://pdata.world/events/kalshi/a%2Fb%3F%22")
        page = pm.render_html(report)
        self.assertIn("Candidate &lt;A&gt;", page)
        self.assertIn("Source row updated: 2026-11-13T00:00:00Z", page)
        self.assertIn("Scheduled close: 2028-12-31T00:00:00Z", page)

    def test_http_request_and_response_contract(self):
        with patch.object(pm, "urlopen", return_value=io.StringIO('{"items": []}')) as request:
            self.assertEqual(pm.fetch_markets("Federal Reserve"), [])
        req = request.call_args.args[0]
        params = parse_qs(urlparse(req.full_url).query)
        self.assertEqual(params["source"], ["kalshi,polymarket"])
        self.assertEqual(params["active"], ["true"])
        self.assertEqual(params["closed"], ["false"])
        self.assertEqual(params["search"], ["Federal Reserve"])
        self.assertEqual(request.call_args.kwargs["timeout"], 8)
        for data in ({"data": []}, {"items": {}}, [], "broken JSON"):
            body = data if isinstance(data, str) else json.dumps(data)
            with patch.object(pm, "urlopen", return_value=io.StringIO(body)):
                with self.assertRaises(ValueError):
                    pm.fetch_markets("rates")


if __name__ == "__main__":
    unittest.main()
