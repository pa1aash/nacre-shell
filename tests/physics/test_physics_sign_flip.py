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
from hypothesis import assume, given
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


energies = st.floats(min_value=-1.0, max_value=1.0)
positive_energies = st.floats(min_value=0.05, max_value=1.0)
costs = st.floats(min_value=1e-4, max_value=0.5)


@given(energies, energies, positive_energies, costs)
def test_sf1_flipping_the_cost_sign_reverses_the_barrier_inequality(sl, sn0, nl, dw):
    for d in (dw, -dw, 0.0):
        assume(abs((sl - sn0 - d) / nl) <= 1)
    barrier = lambda d: heterogeneous_barrier_from_saturation(
        contact_angle_young(sl, sn0, d, nl), nl, 1e-5, 10.0, 300.0)
    b0 = barrier(0.0)
    assert barrier(+dw) >= b0 * (1 - 1e-12)
    assert barrier(-dw) <= b0 * (1 + 1e-12)


@given(st.floats(min_value=0.05, max_value=1.0), st.floats(min_value=0.0, max_value=1.0),
       positive_energies, costs)
def test_sf1_deck_form_lowers_the_barrier_on_the_wetting_side(excess, sn0, nl, dw):
    sl = sn0 + excess          # gamma_sl > gamma_sn0: the wetting side
    assume(dw < nl)
    assume(abs(excess / (nl - dw)) <= 1)
    assert shape_factor_from_cos(contact_angle_cosine_deck(sl, sn0, nl, dw)) < \
        shape_factor_from_cos(contact_angle_cosine_deck(sl, sn0, nl, 0.0))


def _barrier_with_enrichment(dg, omega_bulk=2.0, t=300.0):
    omega_local = enrichment_factor(dg, t) * omega_bulk
    return homogeneous_barrier_from_saturation(1.0, 1e-5, omega_local, t)


def test_sf2_witness_sequestration_sign_orders_the_barrier():
    q = GAS_CONSTANT * 300.0 / 4      # Delta_G_seq = +-RT/4, the contract witness
    assert _barrier_with_enrichment(+q) > _barrier_with_enrichment(0.0) > _barrier_with_enrichment(-q)


@given(st.floats(min_value=1.5, max_value=1e3), st.floats(min_value=1e-3, max_value=2.0),
       st.floats(min_value=100.0, max_value=1000.0))
def test_sf2_flipping_the_sequestration_sign_reverses_the_inequality(omega_bulk, x, t):
    dg = x * GAS_CONSTANT * t
    assume(omega_bulk * math.exp(-x) > 1 + 1e-6)
    b0 = _barrier_with_enrichment(0.0, omega_bulk, t)
    assert _barrier_with_enrichment(-dg, omega_bulk, t) < b0 < _barrier_with_enrichment(+dg, omega_bulk, t)


def test_sf2_derivative_identity():
    # d DG_hom(Omega_local) / d Delta_G_seq = 2 DG_hom / (R T ln Omega_local).
    t, ob, dg = 300.0, 5.0, -100.0
    h = 1e-3
    num = (_barrier_with_enrichment(dg + h, ob, t) - _barrier_with_enrichment(dg - h, ob, t)) / (2 * h)
    om = enrichment_factor(dg, t) * ob
    assert num == pytest.approx(2 * _barrier_with_enrichment(dg, ob, t) / (GAS_CONSTANT * t * np.log(om)), rel=1e-6)
