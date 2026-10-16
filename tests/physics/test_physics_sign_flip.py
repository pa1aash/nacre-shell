"""Sign-flip tests (contract sign_flips SF1, SF2): a sign slip would be caught.

SF1: under the registered Young convention a water-displacement cost Delta_gamma_w > 0
raises theta, f and the heterogeneous barrier; flipping its sign reverses the inequality.
The deck form (gamma_eff in the denominator) reverses it on the wetting side.
SF2: Delta_G_seq < 0 enriches Ca2+, raises Omega_local and lowers the barrier; Delta_G_seq > 0
reverses both.
"""
import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from nacre.physics.constants import GAS_CONSTANT
from nacre.physics.nucleation import heterogeneous_barrier_from_saturation, homogeneous_barrier_from_saturation
from nacre.physics.sequestration import enrichment_factor
from nacre.physics.wetting import (
    contact_angle_cosine_deck,
    contact_angle_cosine_young,
    contact_angle_young,
    shape_factor_from_cos,
)

# Witness of the contract (exact small numbers, synthetic): gamma_sl = 3, gamma_sn0 = 2, gamma_nl = 4.
SL, SN0, NL, D = 3.0, 2.0, 4.0, 0.5


def f_registered(dw):
    return shape_factor_from_cos(contact_angle_cosine_young(SL, SN0, dw, NL))


def f_deck(dw):
    return shape_factor_from_cos(contact_angle_cosine_deck(SL, SN0, NL, dw))


def test_sf1_witness_registered_convention():
    assert f_registered(+D) > f_registered(0.0) > f_registered(-D)


def test_sf1_witness_deck_form_reverses_the_inequality():
    assert f_deck(+D) < f_deck(0.0)


def cost_raises_barrier(young):
    """The registered statement: a displacement cost does not lower the heterogeneous barrier."""
    def barrier(dw):
        theta = math.acos(young(SL, SN0, dw, NL))
        return heterogeneous_barrier_from_saturation(theta, NL, 1e-5, 10.0, 300.0)
    return barrier(+D) >= barrier(0.0)


def test_sf1_statement_holds_for_the_implementation():
    assert cost_raises_barrier(contact_angle_cosine_young)


def test_sf1_statement_catches_a_sign_slip():
    slipped = lambda sl, sn0, dw, nl: (sl - sn0 + dw) / nl
    assert not cost_raises_barrier(slipped)


# The generators below build only inputs inside the domain of the relation under test, by
# construction (lane note N9): no assume() filtering and no health-check suppression. The
# margin keeps the Young ratio a rounding error away from |cos theta| = 1, where the
# physics functions raise by design.
_MARGIN = 1e-9
positive_energies = st.floats(min_value=0.05, max_value=1.0)
cost_fractions = st.floats(min_value=1e-3, max_value=0.5)
ratios = st.floats(min_value=-(1 - _MARGIN), max_value=1 - _MARGIN)


@st.composite
def registered_young_inputs(draw):
    """(sl, sn0, nl, dw) with |sl - sn0 - d| / nl < 1 for every d in {dw, -dw, 0}.

    nl is drawn first, the cost as a fraction of it (dw = r nl, 0 < r <= 1/2), and the
    reference numerator m = sl - sn0 as a fraction of the room nl - dw left after the cost.
    """
    nl = draw(positive_energies)
    dw = draw(cost_fractions) * nl
    m = draw(ratios) * (nl - dw)
    sn0 = draw(st.floats(min_value=-1.0, max_value=1.0))
    return sn0 + m, sn0, nl, dw


@given(registered_young_inputs())
def test_sf1_flipping_the_cost_sign_reverses_the_barrier_inequality(inputs):
    sl, sn0, nl, dw = inputs
    barrier = lambda d: heterogeneous_barrier_from_saturation(
        contact_angle_young(sl, sn0, d, nl), nl, 1e-5, 10.0, 300.0)
    b0 = barrier(0.0)
    assert barrier(+dw) >= b0 * (1 - 1e-12)
    assert barrier(-dw) <= b0 * (1 + 1e-12)


@st.composite
def deck_wetting_side_inputs(draw):
    """(excess, sn0, nl, dw) on the wetting side with the deck ratio strictly inside (0, 1).

    The deck ratio is excess / (nl - dw). nl is drawn first, then the cost as a fraction of
    it (0 < dw < nl, so gamma_eff > 0), then the deck ratio c in (0, 1); excess = c (nl - dw)
    is positive (gamma_sl > gamma_sn0) and the deck ratio cannot leave [-1, 1].
    """
    nl = draw(positive_energies)
    dw = draw(st.floats(min_value=1e-3, max_value=0.9)) * nl
    c = draw(st.floats(min_value=1e-3, max_value=1 - _MARGIN))
    sn0 = draw(st.floats(min_value=0.0, max_value=1.0))
    return c * (nl - dw), sn0, nl, dw


@given(deck_wetting_side_inputs())
def test_sf1_deck_form_lowers_the_barrier_on_the_wetting_side(inputs):
    excess, sn0, nl, dw = inputs
    sl = sn0 + excess          # gamma_sl > gamma_sn0: the wetting side
    assert shape_factor_from_cos(contact_angle_cosine_deck(sl, sn0, nl, dw)) < \
        shape_factor_from_cos(contact_angle_cosine_deck(sl, sn0, nl, 0.0))


# Regression case of lane note N9 (the failing example of --hypothesis-seed=19 under the old
# filtering strategy): excess / (nl - dw) = 1 exactly, and sl - sn0 rounds to just above
# excess, so the deck ratio is 1 + 2.2e-16.
SEED19 = dict(excess=0.5, sn0=0.698451471401042, nl=1.0, dw=0.5)


def test_sf1_seed19_case_is_a_domain_error_in_the_physics():
    sl = SEED19["sn0"] + SEED19["excess"]
    ratio = contact_angle_cosine_deck(sl, SEED19["sn0"], SEED19["nl"], SEED19["dw"])
    assert ratio > 1.0                                   # complete spreading, by rounding
    with pytest.raises(ValueError, match="cos_theta must lie in"):
        shape_factor_from_cos(ratio)


def test_sf1_seed19_case_is_clipped_and_counted_only_in_the_screen():
    from nacre.screen.boundary import clip_cos_theta
    sl = SEED19["sn0"] + SEED19["excess"]
    ratio = contact_angle_cosine_deck(sl, SEED19["sn0"], SEED19["nl"], SEED19["dw"])
    cos_theta, mass = clip_cos_theta([ratio])
    assert cos_theta[0] == 1.0                           # theta = 0
    assert shape_factor_from_cos(cos_theta[0]) == 0.0     # f = 0: no barrier
    assert (mass.n_finite, mass.n_spread, mass.n_nonwetting) == (1, 1, 0)


def _barrier_with_enrichment(dg, omega_bulk=2.0, t=300.0):
    omega_local = enrichment_factor(dg, t) * omega_bulk
    return homogeneous_barrier_from_saturation(1.0, 1e-5, omega_local, t)


def test_sf2_witness_sequestration_sign_orders_the_barrier():
    q = GAS_CONSTANT * 300.0 / 4      # Delta_G_seq = +-RT/4, the contract witness
    assert _barrier_with_enrichment(+q) > _barrier_with_enrichment(0.0) > _barrier_with_enrichment(-q)


@st.composite
def depletion_inputs(draw):
    """(omega_bulk, x, t) with the depleted state still supersaturated: Omega_bulk e^-x > 1.

    x = Delta_G_seq / RT is drawn as a fraction of the room ln(Omega_bulk) leaves, capped
    at 2, so Omega_bulk e^-x >= Omega_bulk^0.1 > 1 by construction.
    """
    omega_bulk = draw(st.floats(min_value=1.5, max_value=1e3))
    room = min(2.0, 0.9 * math.log(omega_bulk))
    x = draw(st.floats(min_value=1e-3, max_value=1.0)) * room
    t = draw(st.floats(min_value=100.0, max_value=1000.0))
    return omega_bulk, x, t


@given(depletion_inputs())
def test_sf2_flipping_the_sequestration_sign_reverses_the_inequality(inputs):
    omega_bulk, x, t = inputs
    dg = x * GAS_CONSTANT * t
    b0 = _barrier_with_enrichment(0.0, omega_bulk, t)
    assert _barrier_with_enrichment(-dg, omega_bulk, t) < b0 < _barrier_with_enrichment(+dg, omega_bulk, t)


def test_sf2_derivative_identity():
    # d DG_hom(Omega_local) / d Delta_G_seq = 2 DG_hom / (R T ln Omega_local).
    t, ob, dg = 300.0, 5.0, -100.0
    h = 1e-3
    num = (_barrier_with_enrichment(dg + h, ob, t) - _barrier_with_enrichment(dg - h, ob, t)) / (2 * h)
    om = enrichment_factor(dg, t) * ob
    assert num == pytest.approx(2 * _barrier_with_enrichment(dg, ob, t) / (GAS_CONSTANT * t * np.log(om)), rel=1e-6)
