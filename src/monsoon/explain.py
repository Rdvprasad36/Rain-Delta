"""
MonsoonDelta plain-language explanation engine.

Template-based and deterministic: given fixed numeric inputs, the
same sentence is always returned. No free-form AI generation.

All generated strings are tested against the BANNED_WORDS list in constants.py.
Every output includes the disclaimer anchor.
"""

from __future__ import annotations

from monsoon.compute import precip_band
from monsoon.constants import BANNED_WORDS, DISAGREE_CLOSE_MM, DISCLAIMER


def _check_banned(text: str) -> str:
    """Raise ValueError if any banned word appears (case-insensitive)."""
    lower = text.lower()
    for word in BANNED_WORDS:
        if word in lower:
            raise ValueError(
                f"Generated text contains banned word '{word}': {text!r}"
            )
    return text


def explain_forecast(
    latest_ifs_mm: float,
    latest_aifs_mm: float,
    window_label: str = "this 6-hour period",
) -> str:
    """
    One sentence about the latest forecast values from both models.

    Example:
        latest_ifs_mm=7.0, latest_aifs_mm=3.0, window_label="Tue 06–12 UTC"
        → "For Tue 06–12 UTC, IFS expects moderate rain (7.0 mm)
            and AIFS expects light rain (3.0 mm)."
    """
    ifs_band = precip_band(latest_ifs_mm)
    aifs_band = precip_band(latest_aifs_mm)

    text = (
        f"For {window_label}, IFS expects {ifs_band} rain ({latest_ifs_mm:.1f}\u202fmm) "
        f"and AIFS expects {aifs_band} rain ({latest_aifs_mm:.1f}\u202fmm)."
    )
    return _check_banned(text)


def explain_revision(
    direction: str,
    latest_change: float | None,
    range_mm: float | None,
    n_runs: int,
) -> str:
    """
    One sentence about how the forecast for a window has changed across runs.

    direction: "up" | "down" | "steady" | "insufficient_data"
    """
    if direction == "insufficient_data" or n_runs < 2:
        text = "Only one model run covers this period, so trend information is not yet available."
    elif direction == "steady":
        text = (
            f"The forecast for this period has remained broadly stable across "
            f"the last {n_runs} runs (change\u202f<\u202f{abs(latest_change):.1f}\u202fmm)."
        )
    elif direction == "up":
        text = (
            f"The newest run expects more rain than the previous one for this period "
            f"(+{latest_change:.1f}\u202fmm). "
            f"The range across the last {n_runs} runs is {range_mm:.1f}\u202fmm."
        )
    else:  # down
        text = (
            f"The newest run expects less rain than the previous one for this period "
            f"({latest_change:.1f}\u202fmm). "
            f"The range across the last {n_runs} runs is {range_mm:.1f}\u202fmm."
        )
    return _check_banned(text)


def explain_disagreement(
    diff_mm: float,
    wetter_model: str,
    close: bool,
) -> str:
    """
    One sentence about how much IFS and AIFS disagree.

    close: True when |diff| < DISAGREE_CLOSE_MM
    """
    abs_diff = abs(diff_mm)
    if wetter_model == "equal" or close:
        text = (
            f"The two models broadly agree for this period "
            f"(difference\u202f<\u202f{DISAGREE_CLOSE_MM:.0f}\u202fmm)."
        )
    else:
        text = (
            f"The two models differ by {abs_diff:.1f}\u202fmm for this period — "
            f"{wetter_model} is wetter."
        )
    return _check_banned(text)


def explain_all(
    latest_ifs_mm: float,
    latest_aifs_mm: float,
    direction: str,
    latest_change: float | None,
    range_mm: float | None,
    n_runs: int,
    diff_mm: float,
    wetter_model: str,
    close: bool,
    window_label: str = "this period",
) -> dict[str, str]:
    """
    Return all three explanation sentences plus the disclaimer link.

    Returns
    -------
    dict with keys: forecast, revision, disagreement, disclaimer
    """
    return {
        "forecast": explain_forecast(latest_ifs_mm, latest_aifs_mm, window_label),
        "revision": explain_revision(direction, latest_change, range_mm, n_runs),
        "disagreement": explain_disagreement(diff_mm, wetter_model, close),
        "disclaimer": DISCLAIMER,
    }
