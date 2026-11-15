"""
Tests for src/monsoon/compute.py

All expected values are hand-computed from PRD §2.2, §2.3, §2.4.
No network access; no file downloads.
"""

import sys
import os
import pytest
import numpy as np

# Make sure the src layout is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from monsoon.compute import (
    to_mm,
    window_totals,
    revision,
    disagreement,
    precip_band,
    area_mean,
)


# ═══════════════════════════════════════════════════════════════════════════════
# to_mm — unit conversion
# ═══════════════════════════════════════════════════════════════════════════════

class TestToMm:
    def test_metres_scalar(self):
        # PRD §2.2 hand example: 0.002 m → 2.0 mm
        result = to_mm([0.002], "m")
        assert result[0] == pytest.approx(2.0, abs=1e-9)

    def test_metres_pair(self):
        # 0.005 m → 5.0 mm
        result = to_mm([0.002, 0.005], "m")
        np.testing.assert_allclose(result, [2.0, 5.0], atol=1e-9)

    def test_kgm2_no_change(self):
        # PRD §2.2: 2.0 kg m**-2 → 2.0 mm
        result = to_mm([2.0, 5.0], "kg m**-2")
        np.testing.assert_allclose(result, [2.0, 5.0], atol=1e-9)

    def test_kgm2_alternate_spelling(self):
        result = to_mm([3.0], "kg m-2")
        assert result[0] == pytest.approx(3.0, abs=1e-9)

    def test_mm_passthrough(self):
        result = to_mm([7.5], "mm")
        assert result[0] == pytest.approx(7.5, abs=1e-9)

    def test_unknown_units_raises(self):
        with pytest.raises(ValueError, match="Unknown tp units"):
            to_mm([1.0], "kg/m2")

    def test_unknown_units_raises_other(self):
        with pytest.raises(ValueError):
            to_mm([1.0], "inch")


# ═══════════════════════════════════════════════════════════════════════════════
# window_totals — accumulation → 6-hour windows
# ═══════════════════════════════════════════════════════════════════════════════

class TestWindowTotals:
    def test_prd_hand_example_ifs(self):
        """PRD §2.2: steps 12 and 18, values 2.0 and 5.0 mm → window(18)=3.0 mm"""
        # steps 12 and 18 present; step 6 not given (not needed here)
        result = window_totals([2.0, 5.0], steps=[12, 18], window=6)
        # step 12: 2.0 - 0 (no step 6 provided, but step 6 must be in steps for it to appear)
        # Actually step 12 looks back to step 6 which is NOT in this list,
        # so tp(6) = 0 (not in dict → default 0 is WRONG).
        # To be precise: we only provide steps 12 and 18 here.
        # tp(12) = 2.0, tp(6) not in dict → 0, so window(12) = 2.0
        # tp(18) = 5.0, tp(12) = 2.0, so window(18) = 3.0
        step18 = next(r for r in result if r["step_end"] == 18)
        assert step18["total_mm"] == pytest.approx(3.0, abs=1e-6)

    def test_prd_hand_example_aifs(self):
        """PRD §2.2: AIFS 2.0 and 5.0 kg m**-2 → window(18) = 3.0 mm"""
        # Already converted to mm; same arithmetic
        result = window_totals([2.0, 5.0], steps=[12, 18], window=6)
        step18 = next(r for r in result if r["step_end"] == 18)
        assert step18["total_mm"] == pytest.approx(3.0, abs=1e-6)

    def test_step6_uses_zero_base(self):
        """For step=6, tp(0)=0, so window(6) = tp(6) itself."""
        result = window_totals([2.0], steps=[6], window=6)
        assert len(result) == 1
        assert result[0]["step_end"] == 6
        assert result[0]["step_start"] == 0
        assert result[0]["total_mm"] == pytest.approx(2.0, abs=1e-9)

    def test_non_multiple_steps_skipped(self):
        """Steps not multiples of window should be ignored (IFS 3-h steps)."""
        # Steps 3, 6, 9, 12 → windows at 6 and 12 only
        result = window_totals([0.5, 1.0, 1.5, 2.5], steps=[3, 6, 9, 12], window=6)
        step_ends = [r["step_end"] for r in result]
        assert 3 not in step_ends
        assert 9 not in step_ends
        assert 6 in step_ends
        assert 12 in step_ends

    def test_negative_large_raises(self):
        """A large negative difference must raise ValueError."""
        # tp(18) < tp(12) by more than tolerance
        with pytest.raises(ValueError, match="below the clamping tolerance"):
            window_totals([5.0, 2.0], steps=[12, 18], window=6)

    def test_tiny_negative_clamped(self):
        """A tiny negative (packing artefact) is clamped to 0.0."""
        # -0.01 mm is above NEGATIVE_CLAMP_TOLERANCE_MM (-0.05)
        result = window_totals([2.0, 2.0 - 0.01], steps=[12, 18], window=6)
        step18 = next(r for r in result if r["step_end"] == 18)
        assert step18["total_mm"] == pytest.approx(0.0, abs=1e-9)


# ═══════════════════════════════════════════════════════════════════════════════
# revision — across-run statistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestRevision:
    def test_prd_hand_example(self):
        """PRD §2.3: [4.0, 10.0, 7.0] → change=-3.0 mm (down), range=6.0 mm"""
        r = revision([4.0, 10.0, 7.0])
        # latest_change = 7.0 - 10.0 = -3.0
        assert r["latest_change"] == pytest.approx(-3.0, abs=1e-6)
        assert r["range_mm"] == pytest.approx(6.0, abs=1e-6)
        assert r["direction"] == "down"
        assert r["n_runs"] == 3
        assert r["latest"] == pytest.approx(7.0, abs=1e-6)
        assert r["previous"] == pytest.approx(10.0, abs=1e-6)

    def test_direction_up(self):
        r = revision([2.0, 3.0, 8.0])
        assert r["direction"] == "up"
        assert r["latest_change"] == pytest.approx(5.0, abs=1e-6)

    def test_direction_steady(self):
        r = revision([5.0, 5.3, 5.2], tolerance=0.5)
        # 5.2 - 5.3 = -0.1 → within 0.5 tolerance
        assert r["direction"] == "steady"

    def test_none_runs_skipped(self):
        """Runs returning None (window not covered) must be skipped, not zero-filled."""
        # PRD §2.3: "a run that does not cover V is skipped"
        r = revision([4.0, None, 10.0, 7.0])
        assert r["n_runs"] == 3
        assert r["valid_values"] == [4.0, 10.0, 7.0]

    def test_all_none(self):
        r = revision([None, None])
        assert r["direction"] == "insufficient_data"
        assert r["n_runs"] == 0

    def test_single_value(self):
        r = revision([5.0])
        assert r["direction"] == "insufficient_data"
        assert r["range_mm"] is None

    def test_min_max(self):
        r = revision([4.0, 10.0, 7.0])
        assert r["min_mm"] == pytest.approx(4.0)
        assert r["max_mm"] == pytest.approx(10.0)


# ═══════════════════════════════════════════════════════════════════════════════
# disagreement — IFS vs AIFS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDisagreement:
    def test_prd_hand_example(self):
        """PRD §2.4: ifs=7.0, aifs=3.0 → diff=+4.0, IFS wetter"""
        d = disagreement(7.0, 3.0)
        assert d["diff_mm"] == pytest.approx(4.0, abs=1e-6)
        assert d["abs_diff_mm"] == pytest.approx(4.0, abs=1e-6)
        assert d["wetter_model"] == "IFS"
        assert d["close"] is False

    def test_aifs_wetter(self):
        d = disagreement(3.0, 7.0)
        assert d["wetter_model"] == "AIFS"
        assert d["diff_mm"] == pytest.approx(-4.0, abs=1e-6)

    def test_equal(self):
        d = disagreement(5.0, 5.0)
        assert d["wetter_model"] == "equal"

    def test_both_tiny_no_percent(self):
        """PRD §2.4: both under 1 mm → percent must be None."""
        d = disagreement(0.3, 0.5)
        assert d["percent"] is None

    def test_one_large_has_percent(self):
        d = disagreement(7.0, 3.0)
        assert d["percent"] is not None
        # 4/7 * 100 ≈ 57.1 %
        assert d["percent"] == pytest.approx(100.0 * 4.0 / 7.0, abs=0.2)

    def test_close_flag(self):
        d = disagreement(5.0, 5.5)
        # diff = 0.5, DISAGREE_CLOSE_MM = 2.0
        assert d["close"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# precip_band
# ═══════════════════════════════════════════════════════════════════════════════

class TestPrecipBand:
    @pytest.mark.parametrize("mm,expected", [
        (0.0, "negligible"),
        (0.9, "negligible"),
        (1.0, "light"),
        (4.9, "light"),
        (5.0, "moderate"),
        (14.9, "moderate"),
        (15.0, "heavy"),
        (29.9, "heavy"),
        (30.0, "very heavy"),
        (100.0, "very heavy"),
    ])
    def test_bands(self, mm, expected):
        assert precip_band(mm) == expected
