"""Offline integration checks: no stock or prediction-market network requests."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import prediction_market_intelligence as pm

ROOT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def isolated_directory():
    previous = Path.cwd()
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        try:
            yield Path(directory)
        finally:
            os.chdir(previous)


def fixture_stock():
    return {
        "ticker": "MU", "name": "Micron Technology", "market": "US",
        "sector": "Semiconductors", "scoring_model": "Semiconductor",
        "price": 100.0, "daily_change": 1.5, "technical": 70,
        "momentum": 60, "fundamental": 80, "valuation": 50,
        "overall": 69, "balanced_score": 65, "rating": "Positive",
        "data_quality": 100, "rsi": 55,
    }


class PredictionMarketIntegrationTests(unittest.TestCase):
    def test_generation_preserves_existing_artifacts_in_success_and_failure(self):
        for fail in (False, True):
            with self.subTest(feed_failure=fail), isolated_directory() as root:
                protected = ("docs/index.html", "docs/micron/index.html",
                             "docs/data/mu-signal.json", "docs/data/score-history.json")
                for name in protected:
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"existing protected artifact\n")
                def fetch(_):
                    if fail:
                        raise OSError("offline")
                    return [{"source": "kalshi", "id": "1", "question": "Will interest rates change?",
                             "probability": .4, "volume_24hr": 100}]
                report = pm.build_report(fetch)
                with patch.object(pm, "build_report", return_value=report), contextlib.redirect_stdout(io.StringIO()):
                    pm.main()
                for name in protected:
                    self.assertEqual((root / name).read_bytes(), b"existing protected artifact\n")
                self.assertEqual({str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()},
                                 set(protected) | {str(pm.DATA_PATH), str(pm.PAGE_PATH)})
                result = json.loads(pm.DATA_PATH.read_text())
                self.assertEqual(result["status"], "unavailable" if fail else "ok")
                self.assertEqual(result["model_version"], pm.MODEL_VERSION)
                self.assertIn('href="../"', pm.PAGE_PATH.read_text())

    def test_dashboard_renders_navigation_without_prediction_feed_dependency(self):
        # Stub only the external scanner. Exercise the real dashboard generator,
        # scoring module, stock detail page, guide and score-history writer.
        scanner = types.ModuleType("scanner")
        scanner.run_scanner = lambda: {"us": [fixture_stock()], "singapore": []}
        spec = importlib.util.spec_from_file_location("dashboard_under_test", ROOT / "dashboard.py")
        dashboard = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"scanner": scanner}):
            spec.loader.exec_module(dashboard)
        with isolated_directory(), contextlib.redirect_stdout(io.StringIO()):
            signal = Path("docs/data/mu-signal.json")
            signal.parent.mkdir(parents=True)
            signal.write_text('{"protected": true}')
            dashboard.main()
            page = Path("docs/index.html").read_text()
            self.assertEqual(page.count('href="prediction-markets/"'), 1)
            self.assertIn("Micron Technology", page)
            self.assertTrue(Path("docs/stocks/mu/index.html").is_file())
            self.assertTrue(Path("docs/guide/index.html").is_file())
            self.assertEqual(signal.read_text(), '{"protected": true}')
            self.assertEqual(dashboard.SCORING_MODEL_VERSION, "v2-sector-specific")


if __name__ == "__main__":
    unittest.main()
