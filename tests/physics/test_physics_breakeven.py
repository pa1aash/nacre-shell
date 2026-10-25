"""breakeven_ratio: the ratio a_pm_sat / a_pm at which a tier-1 exclusion stops standing (PH-W4.9).

Every number is built from the constants module or the inputs of the case; no LiClO4 value is bound here.
"""
import math

import pytest

from nacre.physics import sink, stability
from nacre.physics.bindings import UNDETERMINED
from nacre.physics.constants import FARADAY, GAS_CONSTANT

T = 298.15
TWO_RT_F = 2.0 * GAS_CONSTANT * T / FARADAY


def test_zero_headroom_gives_one():
    assert sink.breakeven_ratio(4.2, 4.0, 0.2, T) == pytest.approx(1.0, rel=1e-12)


def test_one_decade_of_headroom_gives_ten():
    decade = math.log(10.0) * TWO_RT_F
    assert sink.breakeven_ratio(4.2, 4.0, 0.2 - decade, T) == pytest.approx(10.0, rel=1e-12)
    assert decade == pytest.approx(0.11832, abs=2e-5)       # 2 ln10 R T / F at 298.15 K


@pytest.mark.parametrize("headroom", [0.008, 0.054, 0.175])
def test_round_trip_with_m_sink(headroom):
    r = sink.breakeven_ratio(4.2, 4.0, 0.2 - headroom, T)
    assert r == pytest.approx(math.exp(headroom / TWO_RT_F), rel=1e-12)
    # at the break-even ratio the dilute-electrolyte edge E_c - m_expt - m_sink meets E_ub
    m_sink = stability.sink_margin(1.0, T, r, 1.0)
    assert 4.0 + (0.2 - headroom) + m_sink == pytest.approx(4.2, abs=1e-12)


def test_monotone_in_headroom_and_inverse_in_temperature():
    assert sink.breakeven_ratio(4.3, 4.0, 0.1, T) > sink.breakeven_ratio(4.2, 4.0, 0.1, T) > 1.0
    assert sink.breakeven_ratio(4.2, 4.0, 0.1, 350.0) < sink.breakeven_ratio(4.2, 4.0, 0.1, 250.0)


def test_negative_headroom_is_not_excluded_without_correction():
    r = sink.breakeven_ratio(4.2, 4.1, 0.2, T)
    assert r == sink.NOT_EXCLUDED_WITHOUT_CORRECTION == "not excluded without correction"


@pytest.mark.parametrize("args", [(None, 4.0, 0.1, T), (4.2, float("nan"), 0.1, T), (4.2, 4.0, None, T), (4.2, 4.0, 0.1, None)])
def test_a_gap_is_undetermined_never_a_number(args):
    assert sink.breakeven_ratio(*args) == UNDETERMINED
