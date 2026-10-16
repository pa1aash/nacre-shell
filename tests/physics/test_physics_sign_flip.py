"""Sign-flip tests (contract sign_flips SF1, SF2): a sign slip would be caught.

SF1: under the registered Young convention a water-displacement cost Delta_gamma_w > 0
raises theta, f and the heterogeneous barrier; flipping its sign reverses the inequality.
The deck form (gamma_eff in the denominator) reverses it on the wetting side.
SF2 (contract v2, uniform chemical potential): Delta_G_seq reaches the barrier only through
Delta_gamma_ads in gamma_sl, so at fixed gamma_sl0 and gamma_sn stronger binding (Delta_G_seq
more negative) lowers cos(theta) and RAISES the barrier; Omega stays Omega_bulk. The
rejected local-ideal alternative (contract v1: Omega_local = E_enr Omega_bulk) has the
opposite sign; it is kept as the demonstration and its old SF2 tests now witness it.
SF3 (lane note N3): lowering gamma_nl lowers f only on the wetting side (gamma_sl > gamma_sn);
on the other side it raises f, and at gamma_sl = gamma_sn it leaves f = 1/2.
"""
import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from nacre.physics.constants import GAS_CONSTANT
from nacre.physics.nucleation import heterogeneous_barrier_from_saturation, homogeneous_barrier_from_saturation
from nacre.physics import template
from nacre.physics.devtools.wrong_variants import local_ideal_barrier
from nacre.physics.sequestration import adsorption_interfacial_energy_change, enrichment_factor, site_occupancy
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
    """REJECTED local-ideal bookkeeping: DG_hom at Omega_local = E_enr Omega_bulk."""
    omega_local = enrichment_factor(dg, t) * omega_bulk
    return homogeneous_barrier_from_saturation(1.0, 1e-5, omega_local, t)


def test_sf2_alternative_witness_local_ideal_lowers_the_barrier_with_binding():
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
def test_sf2_alternative_ordering_at_random_points(inputs):
    omega_bulk, x, t = inputs
    dg = x * GAS_CONSTANT * t
    b0 = _barrier_with_enrichment(0.0, omega_bulk, t)
    assert _barrier_with_enrichment(-dg, omega_bulk, t) < b0 < _barrier_with_enrichment(+dg, omega_bulk, t)


def test_sf2_alternative_derivative_identity():
    # d DG_hom(Omega_local) / d Delta_G_seq = 2 DG_hom / (R T ln Omega_local).
    t, ob, dg = 300.0, 5.0, -100.0
    h = 1e-3
    num = (_barrier_with_enrichment(dg + h, ob, t) - _barrier_with_enrichment(dg - h, ob, t)) / (2 * h)
    om = enrichment_factor(dg, t) * ob
    assert num == pytest.approx(2 * _barrier_with_enrichment(dg, ob, t) / (GAS_CONSTANT * t * np.log(om)), rel=1e-6)


# ---------------------------------------------------------------- SF2 registered (contract v2)

T_UNIT = 1.0 / GAS_CONSTANT        # R T = 1, as in the contract witness (R_gas = 1, T = 1)
SF2_WITNESS = dict(gamma_sl0=3.0, gamma_sn0=2.0, Delta_gamma_w=0.0, gamma_nl=4.0, V_m=1e-5, T=T_UNIT,
                   c_bulk=1.0, Gamma_s=1.0, delta_s=1.0, a_Ca=2.0, a_CO3=1.0, K_sp=1.0)   # Omega_bulk = 2


def _registered_barrier(dg, **over):
    d = dict(SF2_WITNESS, **over)
    return template.template_heterogeneous_barrier(*[dg if a == "Delta_G_seq" else d[a] for a in template.COMPOSITE_ARGS])


def test_sf2_registered_witness_binding_raises_the_barrier():
    q = 0.25                           # Delta_G_seq = +-1/4 with R T = 1
    assert _registered_barrier(+q) < _registered_barrier(0.0) < _registered_barrier(-q)


def test_sf2_registered_and_rejected_forms_disagree_in_sign():
    q = 0.25
    w = dict(SF2_WITNESS, a_Ca=10.0)    # Omega_bulk = 10 keeps the local-ideal Omega above 1
    at = lambda dg: [dg if a == "Delta_G_seq" else w[a] for a in template.COMPOSITE_ARGS]
    reg = template.template_heterogeneous_barrier(*at(-q)) - template.template_heterogeneous_barrier(*at(+q))
    alt = local_ideal_barrier(*at(-q)) - local_ideal_barrier(*at(+q))
    assert reg > 0 > alt               # binding raises the registered barrier, lowers the rejected one


@st.composite
def template_inputs(draw):
    """Composite inputs with cos(theta) inside (-0.9, 0.9) over Delta_G_seq in [-d, d], by construction.

    |d cos / d Delta_G_seq| = Gamma_s Theta / gamma_nl <= Gamma_s / gamma_nl, so with
    d <= 0.4 gamma_nl / Gamma_s the cosine moves by at most 0.4 from its value c0 at
    Delta_G_seq = 0; gamma_sl0 is set so that this value is c0 in (-0.5, 0.5).
    """
    t = draw(st.floats(min_value=250.0, max_value=400.0))
    nl = draw(st.floats(min_value=0.05, max_value=2.0))
    gs = draw(st.floats(min_value=1e-7, max_value=1e-5))
    ds = draw(st.floats(min_value=1e-10, max_value=1e-8))
    cb = draw(st.floats(min_value=1e-2, max_value=1e2))
    sn0 = draw(st.floats(min_value=-1.0, max_value=1.0))
    dw = draw(st.floats(min_value=0.0, max_value=0.5))
    c0 = draw(st.floats(min_value=-0.5, max_value=0.5))
    d = draw(st.floats(min_value=1e-3, max_value=1.0)) * min(0.4 * nl / gs, 3e4)
    d_ads0 = adsorption_interfacial_energy_change(0.0, t, cb, gs, ds)
    sl0 = c0 * nl + sn0 + dw - d_ads0
    return dict(gamma_sl0=sl0, gamma_sn0=sn0, Delta_gamma_w=dw, gamma_nl=nl, V_m=1e-5, T=t, c_bulk=cb,
                Gamma_s=gs, delta_s=ds, a_Ca=1.0, a_CO3=1.0, K_sp=0.1), d


@given(template_inputs())
def test_sf2_registered_ordering_at_random_points(inputs):
    d_in, d = inputs
    barrier = lambda dg: template.template_heterogeneous_barrier(
        *[dg if a == "Delta_G_seq" else d_in[a] for a in template.COMPOSITE_ARGS])
    b0 = barrier(0.0)
    assert barrier(-d) >= b0 * (1 - 1e-12)
    assert barrier(+d) <= b0 * (1 + 1e-12)


@given(template_inputs())
def test_sf2_registered_derivative_identity(inputs):
    # d cos(theta) / d Delta_G_seq = Gamma_s Theta / gamma_nl; Omega does not depend on Delta_G_seq.
    # cos theta moves by exactly Delta(Delta_gamma_ads) / gamma_nl; the derivative is taken on
    # Delta_gamma_ads itself, free of the O(1) offset gamma_sl0 that would swamp a difference of cos.
    d_in, _ = inputs
    bind = (d_in["T"], d_in["c_bulk"], d_in["Gamma_s"], d_in["delta_s"])
    args = lambda dg: [d_in[a] for a in ("gamma_sl0", "gamma_sn0", "Delta_gamma_w", "gamma_nl")] + [dg, *bind]
    dg, h = -2000.0, 1.0
    d_ads = adsorption_interfacial_energy_change(dg + h, *bind) - adsorption_interfacial_energy_change(dg - h, *bind)
    d_cos = template.contact_angle_cosine_template(*args(dg + h)) - template.contact_angle_cosine_template(*args(dg - h))
    scale = (abs(d_in["gamma_sl0"]) + abs(d_in["gamma_sn0"]) + abs(d_in["Delta_gamma_w"]) + 1.0) / d_in["gamma_nl"]
    assert d_cos == pytest.approx(d_ads / d_in["gamma_nl"], abs=1e-14 * scale)
    want = d_in["Gamma_s"] * site_occupancy(dg, *bind)
    assert d_ads / (2 * h) == pytest.approx(want, rel=1e-5, abs=1e-18)
    assert template.omega_channel(d_in["a_Ca"], d_in["a_CO3"], d_in["K_sp"]) == d_in["a_Ca"] * d_in["a_CO3"] / d_in["K_sp"]


# ---------------------------------------------------------------- SF3 (lane note N3)

def _f_at(excess, nl, sn0=2.0, dw=0.0):
    return shape_factor_from_cos(contact_angle_cosine_young(sn0 + dw + excess, sn0, dw, nl))


def test_sf3_witness():
    assert _f_at(+1.0, 2.0) < _f_at(+1.0, 3.0)      # wetting side: lowering gamma_nl lowers f
    assert _f_at(-1.0, 2.0) > _f_at(-1.0, 3.0)      # other side: lowering gamma_nl raises f
    assert _f_at(0.0, 2.0) == _f_at(0.0, 3.0) == 0.5


@given(st.floats(min_value=1e-3, max_value=1.0), st.floats(min_value=1e-3, max_value=1.0),
       st.floats(min_value=-1.0, max_value=1.0), st.floats(min_value=0.0, max_value=0.5))
def test_sf3_direction_follows_the_sign_of_gamma_sl_minus_gamma_sn(u, v, sn0, dw):
    nl = u + v                         # reparametrisation keeps |cos theta| = u / (u + v) < 1
    h = 1e-6 * nl
    up_wet = _f_at(+u, nl + h, sn0, dw) - _f_at(+u, nl, sn0, dw)
    up_dry = _f_at(-u, nl + h, sn0, dw) - _f_at(-u, nl, sn0, dw)
    assert up_wet > 0 and up_dry < 0
