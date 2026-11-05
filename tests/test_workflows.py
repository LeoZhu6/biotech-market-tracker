"""Exercise real Streamlit controls with deterministic external-service fixtures."""
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
MEMO = "### Sector Overview\nFixture research.\n### Key Findings\nPositive performance."


class Workflows(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(18)
        index = pd.bdate_range("2025-01-01", periods=260)
        self.prices = pd.DataFrame({t: 100 * np.exp(np.cumsum(rng.normal(.0004, .012, 260)))
                                    for t in ["PFE", "MRNA", "SPY"]}, index=index)
        stock = MagicMock()
        stock.info = {"symbol": "PFE", "regularMarketPrice": 100, "longName": "Pfizer",
                      "shortName": "Pfizer", "exchange": "NYSE", "quoteType": "EQUITY",
                      "website": "https://www.pfizer.com"}
        stock.news = []
        self.completions = MagicMock()
        self.completions.create.side_effect = lambda **kw: (
            iter([NS(choices=[NS(delta=NS(content=MEMO))])]) if kw.get("stream")
            else NS(choices=[NS(message=NS(content="Fixture answer"))]))
        client = NS(chat=NS(completions=self.completions))
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"quotes": [{"symbol": "PFE", "shortname": "Pfizer",
                                     "longname": "Pfizer", "exchange": "NYSE", "quoteType": "EQUITY"}]}
        for target, value in [("yfinance.download", self.prices), ("yfinance.Ticker", stock),
                              ("openai.OpenAI", client), ("requests.get", response)]:
            patcher = patch(target, return_value=value)
            mock = patcher.start()
            self.addCleanup(patcher.stop)
            if target == "yfinance.download":
                self.download = mock
        import streamlit as st
        st.cache_data.clear()
        self.a = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)

    def click(self, label):
        matches = [b for b in self.a.button if b.label == label]
        self.assertEqual(len(matches), 1, f"Expected one {label} button, got {len(matches)}")
        matches[0].click().run(timeout=30)
        self.healthy()

    def healthy(self):
        self.assertEqual([e.message for e in self.a.exception], [])
        self.assertEqual([e.value for e in self.a.error], [])

    def select(self):
        self.a.multiselect[0].select("PFE").run()
        self.healthy()

    def analyze(self):
        self.select()
        # Use the sidebar explicitly so duplicate-button regression is independent.
        self.a.button(key="sidebar_start_analysis").click().run(timeout=30)
        self.healthy()

    def report(self):
        self.analyze()
        self.click("Generate Report")
        self.assertIn("Sector Overview", self.a.session_state.ai_report)

    def test_clear_all_clears_widget_and_analysis(self):
        self.analyze()
        self.click("Clear All")
        self.assertEqual(self.a.multiselect[0].value, [])
        self.assertEqual(self.a.session_state.selected_tickers, [])
        self.assertFalse(self.a.session_state.analysis_started)
        self.assertEqual(len(self.a.get("plotly_chart")), 0)

    def test_only_one_start_button(self):
        self.select()
        self.assertEqual(len([b for b in self.a.button if b.label == "Start Analysis"]), 1)

    def test_favorites_load_restores_widget(self):
        self.select()
        self.click("Save to Favorites")
        self.click("Clear All")
        self.click("Load Favorites")
        self.assertEqual(self.a.multiselect[0].value, ["PFE"])
        self.assertEqual(self.a.session_state.selected_tickers, ["PFE"])
        self.click("Clear")
        self.assertEqual(self.a.session_state.favorite_tickers, [])

    def test_new_analysis_resets_report_and_returns_to_configuration(self):
        self.report()
        self.click("New Analysis")
        self.assertFalse(self.a.session_state.analysis_started)
        self.assertEqual(self.a.session_state.ai_report, "")
        self.assertEqual(self.a.session_state.chat_history, [])
        self.assertEqual(len(self.a.get("plotly_chart")), 0)
        self.assertEqual(self.a.multiselect[0].value, ["PFE"])

    def test_refresh_keeps_selection_and_period(self):
        self.analyze()
        next(s for s in self.a.selectbox if s.label == "Analysis period").select("6mo").run()
        self.click("Refresh")
        self.assertEqual(self.a.multiselect[0].value, ["PFE"])
        self.assertEqual(self.a.session_state.selected_time_range, "6mo")
        self.assertGreaterEqual(len(self.a.get("plotly_chart")), 5)

    def test_changing_selection_invalidates_report(self):
        self.report()
        self.a.multiselect[0].select("MRNA").run(timeout=30)
        self.assertEqual(self.a.session_state.ai_report, "")
        self.assertFalse(self.a.session_state.analysis_completed)

    def test_changing_period_invalidates_report(self):
        self.report()
        next(s for s in self.a.selectbox if s.label == "Analysis period").select("3mo").run(timeout=30)
        self.assertEqual(self.a.session_state.ai_report, "")

    def test_charts_ticker_switch_and_alerts(self):
        self.analyze()
        self.assertEqual(len(self.a.get("plotly_chart")), 5)
        self.a.multiselect[0].select("MRNA").run(timeout=30)
        tech = next(s for s in self.a.selectbox if s.label == "Select ticker for analysis")
        tech.select("MRNA").run(timeout=30)
        self.healthy()
        self.a.number_input[0].set_value(1).run()
        self.click("Add Alert")
        self.assertEqual(len(self.a.session_state.price_alerts), 1)
        self.assertTrue(any("ALERT:" in m.value for m in self.a.markdown))
        self.click("×")
        self.assertEqual(self.a.session_state.price_alerts, [])

    def test_report_chat_and_clear_history(self):
        self.report()
        for i in range(4):
            self.a.button(key=f"quick_q_{i}").click().run(timeout=30)
            self.healthy()
        question = next(t for t in self.a.text_input if t.label == "question")
        question.set_value("Compare risks").run()
        self.click("Send")
        self.assertEqual(len(self.a.session_state.chat_history), 10)
        self.click("Clear Chat History")
        self.assertEqual(self.a.session_state.chat_history, [])

    def test_report_and_chat_use_latest_deepseek_model(self):
        self.report()
        self.a.button(key="quick_q_0").click().run(timeout=30)
        self.healthy()
        self.assertGreaterEqual(self.completions.create.call_count, 2)
        for call in self.completions.create.call_args_list:
            self.assertEqual(call.kwargs["model"], "deepseek-flash")

    def test_chat_controls_are_complete_during_ai_request(self):
        self.report()
        observed = []
        original = self.completions.create.side_effect
        import streamlit as st
        rendered = set()
        original_button = st.button
        def button(*args, **kwargs):
            rendered.add(kwargs.get("key"))
            return original_button(*args, **kwargs)
        def respond(**kwargs):
            if not kwargs.get("stream"):
                observed.append(all(f"quick_q_{i}" in rendered for i in range(4)))
            return original(**kwargs)
        self.completions.create.side_effect = respond
        with patch("streamlit.button", side_effect=button):
            self.a.button(key="quick_q_0").click().run(timeout=30)
        self.healthy()
        self.assertEqual(observed, [True])
        self.assertEqual(len([b for b in self.a.button if b.key and b.key.startswith("quick_q_")]), 4)

    def test_empty_ai_response_is_not_saved_as_blank(self):
        self.report()
        self.completions.create.side_effect = lambda **kw: NS(choices=[NS(message=NS(content=""), finish_reason="length")])
        self.a.button(key="quick_q_1").click().run(timeout=30)
        self.healthy()
        self.assertTrue(self.a.session_state.chat_history[-1]["content"].strip())

    def test_followup_explicitly_requests_final_answer_mode(self):
        self.report()
        self.a.button(key="quick_q_1").click().run(timeout=30)
        self.assertEqual(self.completions.create.call_args.kwargs.get("extra_body"), {"thinking": {"type": "disabled"}})

    def test_chat_has_no_avatars_or_emoji_in_displayed_answers(self):
        self.report()
        self.completions.create.side_effect = lambda **kw: NS(choices=[NS(message=NS(content="# Outlook\n\n\U0001f916 Research notes \u2705\n\n- Pipeline review"))])
        self.a.button(key="quick_q_0").click().run(timeout=30)
        self.healthy()
        self.assertEqual(len(self.a.get("chat_message")), 0)
        rendered = "\n".join(m.value for m in self.a.markdown)
        self.assertNotIn("\U0001f916", rendered)
        self.assertNotIn("\u2705", rendered)
        self.assertIn("Research notes", rendered)

    def test_pdf_download_survives_rerun_and_csv_exists(self):
        self.report()
        self.click("Generate PDF")
        self.assertEqual(len(self.a.get("download_button")), 2)
        self.a.run()
        self.assertEqual(len(self.a.get("download_button")), 2)
        import fitz
        pdf = fitz.open(stream=self.a.session_state.pdf_report, filetype="pdf")
        self.assertGreaterEqual(len(pdf), 2)
        text = "".join(page.get_text() for page in pdf)
        self.assertIn("PFE", text)
        self.assertIn("Sector Overview", text)
        import io
        import streamlit as st
        with patch("streamlit.download_button", wraps=st.download_button) as download:
            self.a.run()
        csv_call = next(call for call in download.call_args_list if call.kwargs.get("label") == "Export CSV")
        metrics = pd.read_csv(io.StringIO(csv_call.kwargs["data"]))
        self.assertEqual(metrics["Ticker Code"].tolist(), ["PFE"])
        self.assertTrue(np.isfinite(metrics["Total Return (%)"]).all())

    def test_search_and_add(self):
        self.a.text_input(key="search_input").set_value("Pfizer").run(timeout=30)
        self.click("Add")
        self.assertIn("PFE", self.a.session_state.selected_tickers)

    def test_retry_reloads_market_data(self):
        self.select()
        self.download.return_value = pd.DataFrame()
        self.a.button(key="sidebar_start_analysis").click().run(timeout=30)
        self.download.return_value = self.prices
        self.click("Retry")
        self.assertGreaterEqual(len(self.a.get("plotly_chart")), 5)

    def test_all_periods_and_below_alert(self):
        self.analyze()
        for period in ["3mo", "6mo", "1y", "3y", "5y"]:
            next(s for s in self.a.selectbox if s.label == "Analysis period").select(period).run()
            self.healthy()
            self.assertEqual(len(self.a.get("plotly_chart")), 5)
        next(s for s in self.a.selectbox if s.label == "Type").select("Below").run()
        self.a.number_input[0].set_value(10000).run()
        self.click("Add Alert")
        self.assertTrue(any("ALERT:" in m.value and "below" in m.value for m in self.a.markdown))

    def test_report_connection_error_does_not_enable_chat(self):
        self.analyze()
        self.completions.create.side_effect = ConnectionError("Fixture offline")
        next(b for b in self.a.button if b.label == "Generate Report").click().run()
        self.assertEqual(len(self.a.exception), 0)
        self.assertTrue(any("Fixture offline" in e.value for e in self.a.error))
        self.assertFalse(self.a.session_state.analysis_completed)

    def test_refresh_disabled_without_selection(self):
        self.assertTrue(self.a.button(key="refresh_btn").disabled)

    def test_search_add_twice_does_not_duplicate(self):
        self.a.text_input(key="search_input").set_value("Pfizer").run()
        self.click("Add")
        self.click("Add")
        self.assertEqual(self.a.session_state.selected_tickers, ["PFE"])

    def test_known_chinese_name_works_without_search_provider(self):
        with patch("requests.get", side_effect=ConnectionError("offline")), patch("yfinance.Ticker", side_effect=ConnectionError("offline")):
            self.a.text_input(key="search_input").set_value("\u8f89\u745e").run(timeout=30)
            self.click("Add")
        self.assertEqual(self.a.session_state.selected_tickers, ["PFE"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
