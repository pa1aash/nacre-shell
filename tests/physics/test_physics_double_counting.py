"""Double-counting demonstration (C3 item 13) and the channel separation of the contract.

The contract barrier counts the template's Ca2+ binding once, through Omega_local. The
deliberately wrong variants (nacre.physics.devtools.wrong_variants) count it again as a
shift Gamma_s Delta_G_seq of an interfacial energy inside Young, or count the water-
displacement cost twice (inside the deck's gamma_eff and in gamma_sn). Each gives a
different barrier from the contract implementation.

Documented directions (partial wetting, enrichment Delta_G_seq < 0):
  * shift on gamma_sn: the wrong barrier is LOWER than the contract barrier, i.e. double
    counting overstates the template's benefit; reversed for Delta_G_seq > 0;
  * shift on gamma_sl (Gibbs-adsorption-like): the wrong barrier is HIGHER;
  * water cost twice (Delta_gamma_w > 0, wetting numerator gamma_sl - gamma_sn > 0): the
    wrong barrier is LOWER (gamma_eff < gamma_nl shrinks DG_hom and raises cos theta).
"""
import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from nacre.physics import template
from nacre.physics.devtools.wrong_variants import (
    double_counted_sequestration_barrier,
    double_counted_water_barrier,
)

# Synthetic inputs (exact mathematics, no literature values).
BASE = dict(gamma_sl=0.6, gamma_sn0=0.4, Delta_gamma_w=0.05, gamma_nl=0.5, V_m=1e-5, T=300.0,
            Delta_G_seq=-5e3, c_bulk=1.0, Gamma_s=5e-6, delta_s=1e-9, a_Ca=1e-2, a_CO3=1e-2, K_sp=1e-6)


def _args(d):
    return [d[a] for a in template.COMPOSITE_ARGS]


def test_sn_double_counting_lowers_the_barrier_under_enrichment():
    right = template.template_heterogeneous_barrier(*_args(BASE))
    wrong = double_counted_sequestration_barrier(*_args(BASE), interface="sn")
    assert wrong < right
    assert (right - wrong) / right > 1e-3


def test_sn_double_counting_raises_the_barrier_under_depletion():
    d = dict(BASE, Delta_G_seq=+1e3)
    assert double_counted_sequestration_barrier(*_args(d), interface="sn") > \
        template.template_heterogeneous_barrier(*_args(d))


def test_sl_double_counting_shifts_the_other_way():
    assert double_counted_sequestration_barrier(*_args(BASE), interface="sl") > \
        template.template_heterogeneous_barrier(*_args(BASE))


def test_water_cost_counted_twice_lowers_the_barrier_on_the_wetting_side():
    right = template.template_heterogeneous_barrier(*_args(BASE))
    wrong = double_counted_water_barrier(*_args(BASE))
    assert wrong < right


def test_without_a_template_effect_the_variants_coincide_with_the_contract():
    d = dict(BASE, Delta_G_seq=0.0, Delta_gamma_w=0.0)
    right = template.template_heterogeneous_barrier(*_args(d))
    assert double_counted_sequestration_barrier(*_args(d), interface="sn") == pytest.approx(right, rel=1e-14)
    assert double_counted_water_barrier(*_args(d)) == pytest.approx(right, rel=1e-14)


@given(st.floats(min_value=0.0, max_value=0.5), st.floats(min_value=0.1, max_value=1.0),
       st.floats(min_value=1e-7, max_value=1e-5), st.floats(min_value=-2e4, max_value=-10.0))
def test_sn_direction_holds_across_partial_wetting(excess, nl, gamma_s, dg):
    d = dict(BASE, gamma_sl=0.4 + 0.05 + excess, gamma_nl=nl, Gamma_s=gamma_s, Delta_G_seq=dg)
    shift = gamma_s * dg
    for num in (excess, excess - shift):
        assume(abs(num / nl) < 1)
    assume(abs(shift) > 1e-9)
    right = template.template_heterogeneous_barrier(*_args(d))
    wrong = double_counted_sequestration_barrier(*_args(d), interface="sn")
    assert wrong < right


def test_each_template_input_enters_exactly_one_channel():
    def channels(d):
        theta = template.wetting_channel(d["gamma_sl"], d["gamma_sn0"], d["Delta_gamma_w"], d["gamma_nl"])
        omega = template.enrichment_channel(d["Delta_G_seq"], d["T"], d["c_bulk"], d["Gamma_s"],
                                            d["delta_s"], d["a_Ca"], d["a_CO3"], d["K_sp"])
        return theta, omega

    t0, o0 = channels(BASE)
    for name in template.TEMPLATE_DEPENDENT:
        d = dict(BASE)
        d[name] = BASE[name] * 1.01 if BASE[name] else 1e-3
        t1, o1 = channels(d)
        moved = (t1 != t0, o1 != o0)
        assert sum(moved) == 1, (name, moved)
