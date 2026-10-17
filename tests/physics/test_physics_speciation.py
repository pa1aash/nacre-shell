"""Carbonate speciation of contract v3: mass balances, limits, the ion-pair bound and the I_val refusal.

All inputs are synthetic round numbers chosen only to exercise the algebra (no literature value).
"""
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from nacre.physics import speciation as sp
from nacre.physics.constants import STANDARD_MOLALITY

BASE = dict(pH=11.0, C_T=10.0, Ca_T=2.0, I_ionic=0.05, rho_water=1000.0, pK1_carbonic=6.0, pK2_carbonic=10.0,
            K_CaCO3_aq=1e3, K_CaHCO3=1e1, K_CaOH=1e-13, a_w=1.0, A_DH=0.5, b_D=0.3, I_val=0.5)


def test_standard_molality_is_one_mole_per_kilogram():
    assert STANDARD_MOLALITY == 1.0


def test_davies_is_ideal_at_zero_ionic_strength_and_charge_two_is_fourth_power():
    assert sp.activity_coefficient_charge_one(0.5, 0.0, 0.3) == 1.0
    g1 = sp.activity_coefficient_charge_one(0.5, 0.1, 0.3)
    assert sp.activity_coefficient_charge_two(0.5, 0.1, 0.3) == pytest.approx(g1 ** 4, rel=1e-14)
    assert 0 < g1 < 1


def test_unrepresentable_coefficient_is_refused():
    with pytest.raises(ValueError):
        sp.activity_coefficient_charge_two(50.0, 1e6, 50.0)


@settings(max_examples=200, deadline=None)
@given(ph=st.floats(8.0, 13.5), lct=st.floats(-1.0, 2.0), lca=st.floats(-3.0, 2.0), li=st.floats(-4.0, -0.4),
       lk0=st.floats(0.0, 4.0), lkh=st.floats(0.0, 2.0))
def test_both_mass_balances_close(ph, lct, lca, li, lk0, lkh):
    x = dict(BASE, pH=ph, C_T=10 ** lct, Ca_T=10 ** lca, I_ionic=10 ** li, K_CaCO3_aq=10 ** lk0, K_CaHCO3=10 ** lkh)
    r = sp.speciate(**x)
    y, a = r["a_CO3"], r["a_Ca"]
    assert y > 0 and a > 0
    # carbon: m_CT = A y + P y a_Ca; calcium: m_CaT = a_Ca (D + P y)
    assert r["A_carb"] * y + r["P_pair"] * y * a == pytest.approx(r["m_CT"], rel=1e-10)
    assert a * (r["D_Ca"] + r["P_pair"] * y) == pytest.approx(r["m_CaT"], rel=1e-10)
    # ion pairs can only lower the free carbonate
    assert y <= r["m_CT"] / r["A_carb"] * (1 + 1e-12)


def test_without_pairs_and_ideal_the_carbonate_system_alone():
    x = dict(BASE, K_CaCO3_aq=0.0, K_CaHCO3=0.0, K_CaOH=0.0, I_ionic=0.0, A_DH=0.0)
    r = sp.speciate(**x)
    a_carb = 10 ** (6.0 + 10.0 - 22.0) + 10 ** (10.0 - 11.0) + 1.0
    assert r["a_CO3"] == pytest.approx(x["C_T"] / 1000.0 / a_carb, rel=1e-14)
    assert r["a_Ca"] == pytest.approx(x["Ca_T"] / 1000.0, rel=1e-14)
    assert r["c_Ca_free"] == pytest.approx(x["Ca_T"], rel=1e-14)


def test_root_is_accurate_on_both_branches_of_the_linear_coefficient():
    # B = A D + P (m_CaT - m_CT) < 0 when calcium exceeds carbon strongly with pairing; the lower form is used
    for ca_t in (1e-3, 1e3):
        r = sp.speciate(**dict(BASE, Ca_T=ca_t, K_CaCO3_aq=1e6))
        y = r["a_CO3"]
        resid = r["A_carb"] * r["P_pair"] * y * y + (r["A_carb"] * r["D_Ca"] + r["P_pair"] * (r["m_CaT"] - r["m_CT"])) * y \
            - r["m_CT"] * r["D_Ca"]
        assert abs(resid) <= 1e-12 * r["m_CT"] * r["D_Ca"]


def test_ionic_strength_above_the_validity_bound_is_refused():
    with pytest.raises(sp.ActivityModelRange):
        sp.speciate(**dict(BASE, I_ionic=0.6, I_val=0.5))


def test_free_carbonate_rises_with_pH_at_fixed_totals():
    lo = sp.speciate(**dict(BASE, pH=9.0))["a_CO3"]
    hi = sp.speciate(**dict(BASE, pH=12.0))["a_CO3"]
    assert hi > lo


def test_vectorised_over_draws():
    ph = np.linspace(9, 13, 7)
    r = sp.speciate(**dict(BASE, pH=ph))
    assert r["a_CO3"].shape == (7,)
    for i, p in enumerate(ph):
        assert r["a_CO3"][i] == pytest.approx(sp.speciate(**dict(BASE, pH=float(p)))["a_CO3"], rel=1e-14)
