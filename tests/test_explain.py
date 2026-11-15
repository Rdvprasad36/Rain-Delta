"""
Tests for src/monsoon/explain.py

Fixed inputs must produce fixed sentences.
Banned words must never appear in any output.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from monsoon.explain import (
    explain_forecast,
    explain_revision,
    explain_disagreement,
    explain_all,
)
from monsoon.constants import BANNED_WORDS, DISCLAIMER


class TestExplainForecast:
    def test_deterministic(self):
        a = explain_forecast(7.0, 3.0, "Tue 06–12 UTC")
        b = explain_forecast(7.0, 3.0, "Tue 06–12 UTC")
        assert a == b

    def test_contains_values(self):
        s = explain_forecast(7.0, 3.0, "Tue 06–12 UTC")
        assert "7.0" in s
        assert "3.0" in s
        assert "moderate" in s   # 7.0 mm band
        assert "light" in s      # 3.0 mm band

    def test_no_banned_words(self):
        s = explain_forecast(25.0, 10.0, "Wed 12–18 UTC")
        for word in BANNED_WORDS:
            assert word not in s.lower()


class TestExplainRevision:
    def test_down(self):
        # PRD: latest_change=-3.0, range=6.0 → "less rain"
        s = explain_revision("down", -3.0, 6.0, 3)
        assert "less" in s
        assert "3.0" in s or "-3.0" in s
        assert "6.0" in s

    def test_up(self):
        s = explain_revision("up", 5.0, 7.0, 4)
        assert "more" in s
        assert "5.0" in s

    def test_steady(self):
        s = explain_revision("steady", 0.1, None, 3)
        assert "stable" in s or "steady" in s.lower() or "broadly" in s

    def test_insufficient(self):
        s = explain_revision("insufficient_data", None, None, 1)
        assert "one" in s.lower() or "not yet" in s.lower()

    def test_no_banned_words(self):
        for direction in ["up", "down", "steady", "insufficient_data"]:
            s = explain_revision(direction, -3.0, 6.0, 3)
            for word in BANNED_WORDS:
                assert word not in s.lower(), f"Banned word '{word}' in: {s!r}"


class TestExplainDisagreement:
    def test_ifs_wetter(self):
        s = explain_disagreement(4.0, "IFS", False)
        assert "IFS" in s
        assert "4.0" in s

    def test_close(self):
        s = explain_disagreement(0.5, "IFS", True)
        assert "broadly" in s or "agree" in s

    def test_no_banned_words(self):
        s = explain_disagreement(10.0, "AIFS", False)
        for word in BANNED_WORDS:
            assert word not in s.lower()


class TestExplainAll:
    def test_returns_all_keys(self):
        result = explain_all(
            latest_ifs_mm=7.0,
            latest_aifs_mm=3.0,
            direction="down",
            latest_change=-3.0,
            range_mm=6.0,
            n_runs=3,
            diff_mm=4.0,
            wetter_model="IFS",
            close=False,
            window_label="Tue 06–12 UTC",
        )
        assert set(result.keys()) == {"forecast", "revision", "disagreement", "disclaimer"}

    def test_disclaimer_present(self):
        result = explain_all(7.0, 3.0, "down", -3.0, 6.0, 3, 4.0, "IFS", False)
        assert result["disclaimer"] == DISCLAIMER

    def test_no_banned_words_anywhere(self):
        result = explain_all(7.0, 3.0, "down", -3.0, 6.0, 3, 4.0, "IFS", False)
        for key, text in result.items():
            if key == "disclaimer":
                continue  # disclaimer text is exempt
            for word in BANNED_WORDS:
                assert word not in text.lower(), f"Banned word '{word}' in {key}: {text!r}"
