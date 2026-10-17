"""Double-counting demonstration (C3 item 13) and the single channel of contract v2.

Contract v2 (uniform chemical potential): the template acts on the barrier only through
theta; its Ca2+ binding enters once, through Delta_gamma_ads in gamma_sl, and Omega is
Omega_bulk. The deliberately wrong or rejected forms (nacre.physics.devtools.wrong_variants)
count the binding twice (Delta_gamma_ads AND the local-ideal Omega), count it in the wrong
channel (contract v1: Ca-free gamma_sl0 and the local-ideal Omega), or count the water-
displacement cost twice (inside the deck's gamma_eff and in gamma_sn).

Documented directions, partial wetting:
  * binding counted twice, enrichment (Omega_local_ideal > Omega_bulk): the wrong barrier is
    LOWER than the contract barrier (double counting overstates the template); depletion
    reverses it. Theta is the same in both, so the error is purely the credited driving force;
  * rejected v1 bookkeeping with net binding (Delta_gamma_ads < 0): LOWER, because it omits
    the rise of theta from adsorption and raises Omega;
  * water cost twice (Delta_gamma_w > 0, wetting numerator gamma_sl - gamma_sn > 0): LOWER.
"""
import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from nacre.physics import template
from nacre.physics.devtools.wrong_variants import (
    double_counted_sequestration_barrier,
    double_counted_water_barrier,
    local_ideal_barrier,
)
from nacre.physics.sequestration import adsorption_interfacial_energy_change

# Synthetic inputs (exact mathematics, no literature values). c_max = Gamma_s / delta_s = 5000
# keeps the layer far from saturation, so enrichment raises the local-ideal Omega.
BASE = dict(gamma_sl0=0.6, gamma_sn0=0.4, Delta_gamma_w=0.05, gamma_nl=0.5, V_m=1e-5, T=300.0,
            Delta_G_seq=-5e3, c_bulk=1.0, Gamma_s=5e-6, delta_s=1e-9, a_Ca=1e-2, a_CO3=1e-2, K_sp=1e-6)


def _args(d):
    return [d[a] for a in template.COMPOSITE_ARGS]


def test_binding_counted_twice_lowers_the_barrier_under_enrichment():
    right = template.template_heterogeneous_barrier(*_args(BASE))
    wrong = double_counted_sequestration_barrier(*_args(BASE))
    assert wrong < right
    assert (right - wrong) / right > 1e-3


def test_binding_counted_twice_raises_the_barrier_under_depletion():
    d = dict(BASE, Delta_G_seq=+1e3)
    assert double_counted_sequestration_barrier(*_args(d)) > template.template_heterogeneous_barrier(*_args(d))


def test_rejected_v1_bookkeeping_lowers_the_barrier_with_net_binding():
    assert adsorption_interfacial_energy_change(BASE["Delta_G_seq"], BASE["T"], BASE["c_bulk"],
                                                BASE["Gamma_s"], BASE["delta_s"]) < 0
    assert local_ideal_barrier(*_args(BASE)) < template.template_heterogeneous_barrier(*_args(BASE))


def test_water_cost_counted_twice_lowers_the_barrier_on_the_wetting_side():
    right = template.template_heterogeneous_barrier(*_args(BASE))
    wrong = double_counted_water_barrier(*_args(BASE))
    assert wrong < right


def test_without_a_template_effect_the_variants_coincide_with_the_contract():
    # no binding free energy, an unsaturable layer (c_max >> c_bulk) and no displacement cost
    d = dict(BASE, Delta_G_seq=0.0, Delta_gamma_w=0.0, Gamma_s=1.0, delta_s=1e-9)
    right = template.template_heterogeneous_barrier(*_args(d))
    assert double_counted_sequestration_barrier(*_args(d)) == pytest.approx(right, rel=1e-6)
    assert double_counted_water_barrier(*_args(d)) == pytest.approx(right, rel=1e-14)


@st.composite
def enriched_partial_wetting(draw):
    """Composite inputs with |cos theta| < 0.9 and Omega_local_ideal > Omega_bulk > 1, by construction.

    Delta_G_seq < 0 gives E_enr > 1; c_max >= 10 E_enr c_bulk keeps the layer unsaturated
    so c_local / c_bulk > 1; gamma_sl0 is set so that cos theta (with Delta_gamma_ads) is c0.
    """
    t = draw(st.floats(min_value=280.0, max_value=320.0))
    dg = -draw(st.floats(min_value=2e3, max_value=2e4))
    cb = draw(st.floats(min_value=1e-2, max_value=10.0))
    ds = draw(st.floats(min_value=1e-10, max_value=1e-8))
    e = np.exp(-dg / (8.314462618 * t))
    gs = 10.0 * e * cb * ds * draw(st.floats(min_value=1.0, max_value=100.0))
    nl = draw(st.floats(min_value=0.05, max_value=1.0))
    sn0 = draw(st.floats(min_value=0.0, max_value=1.0))
    dw = draw(st.floats(min_value=0.0, max_value=0.2))
    c0 = draw(st.floats(min_value=-0.9, max_value=0.9))
    sl0 = c0 * nl + sn0 + dw - adsorption_interfacial_energy_change(dg, t, cb, gs, ds)
    return dict(gamma_sl0=sl0, gamma_sn0=sn0, Delta_gamma_w=dw, gamma_nl=nl, V_m=1e-5, T=t, Delta_G_seq=dg,
                c_bulk=cb, Gamma_s=gs, delta_s=ds, a_Ca=1e-2, a_CO3=1e-2, K_sp=1e-5)


@given(enriched_partial_wetting())
def test_double_counting_direction_holds_across_partial_wetting(d):
    right = template.template_heterogeneous_barrier(*_args(d))
    wrong = double_counted_sequestration_barrier(*_args(d))
    assert wrong < right


def test_template_inputs_enter_only_the_theta_channel_and_binding_only_through_gamma_sl():
    theta_args = ("gamma_sl0", "gamma_sn0", "Delta_gamma_w", "gamma_nl", "Delta_G_seq", "T", "c_bulk",
                  "Gamma_s", "delta_s")

    def channels(d):
        return (template.wetting_channel(*[d[a] for a in theta_args]),
                template.omega_channel(d["a_Ca"], d["a_CO3"], d["K_sp"]))

    t0, o0 = channels(BASE)
    for name in template.TEMPLATE_DEPENDENT:
        d = dict(BASE)
        d[name] = BASE[name] * 1.01 if BASE[name] else 1e-3
        t1, o1 = channels(d)
        assert t1 != t0 and o1 == o0, name                     # theta moves, Omega never does
    for name in ("a_Ca", "a_CO3", "K_sp"):
        d = dict(BASE, **{name: BASE[name] * 1.01})
        t1, o1 = channels(d)
        assert t1 == t0 and o1 != o0, name
    # the binding inputs act only through gamma_sl = gamma_sl0 + Delta_gamma_ads: compensating
    # gamma_sl0 for a change of Delta_G_seq leaves theta unchanged
    d = dict(BASE, Delta_G_seq=BASE["Delta_G_seq"] - 1e3)
    shift = (adsorption_interfacial_energy_change(d["Delta_G_seq"], d["T"], d["c_bulk"], d["Gamma_s"], d["delta_s"])
             - adsorption_interfacial_energy_change(BASE["Delta_G_seq"], d["T"], d["c_bulk"], d["Gamma_s"], d["delta_s"]))
    d["gamma_sl0"] = BASE["gamma_sl0"] - shift
    assert channels(d)[0] == pytest.approx(t0, rel=1e-12)


def test_in_situ_gamma_sl_adds_nothing():
    sl = template.template_liquid_energy_in_situ(BASE["gamma_sl0"], BASE["Delta_G_seq"], BASE["T"], BASE["c_bulk"],
                                                 BASE["Gamma_s"], BASE["delta_s"])
    a = template.template_heterogeneous_barrier(*_args(BASE))
    b = template.template_heterogeneous_barrier_in_situ(sl, BASE["gamma_sn0"], BASE["Delta_gamma_w"], BASE["gamma_nl"],
                                                        BASE["V_m"], BASE["T"], BASE["a_Ca"], BASE["a_CO3"], BASE["K_sp"])
    assert a == pytest.approx(b, rel=1e-14)
