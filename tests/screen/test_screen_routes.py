"""Route evaluators of theory/claims_redirect.md Section 9 (PH-W4.2a): every row of tables H1 to H4, F1r to F4r,
B1 to B4, the wetting form of ruling C3 with both limits, the framing labels of 9d and the rules M1 to M4, L1 to L3."""
import math

import numpy as np
import pytest

from nacre.screen import routes

ROWS = [{"key": "k6", "pH": 6.0, "ca_mM": 0.0, "T": 296.0, "k": (4e-8, 6e-8)},
        {"key": "k6ca", "pH": 6.0, "ca_mM": 1.0, "T": 296.0, "k": (1.5e-7, 2.5e-7)},
        {"key": "k8", "pH": 8.0, "ca_mM": 0.0, "T": 296.0, "k": (4e-8, 6e-8)},
        {"key": "k8ca", "pH": 8.0, "ca_mM": 1.0, "T": 296.0, "k": (3e-7, 5e-7)}]
STATE = {"pH": 7.0, "T": 298.0, "ca_mM": 0.0}


def h(state=None, t_wet=3600.0, tau=(0.5, 3.0), f_min=0.9, t_tol=5.0, rows=ROWS):
    return routes.hydrolysis_descriptor(dict(STATE, **(state or {})), rows, tau, t_wet, f_min, t_tol, route="R1")


# ------------------------------------------------------------------ K2h
@pytest.mark.parametrize("state, why", [({"pH": 5.0}, "pH"), ({"pH": 9.0}, "pH"), ({"T": 320.0}, "temperature"),
                                        ({"ca_mM": 5.0}, "Ca2+"), ({"drying": True}, "drying"),
                                        ({"pit": True}, "pit")])
def test_h1_outside_data_is_undetermined_and_never_gates(state, why):
    r = h(state)
    assert (r["row"], r["verdict"], r["gates"]) == ("H1", "undetermined", False)
    assert why in r["coverage"]["reason"]


def test_h1_without_a_temperature_tolerance():
    r = h(t_tol=None)
    assert r["row"] == "H1" and "tolerance" in r["coverage"]["reason"]


def test_h2_falsifies_only_at_the_slowest_rate():
    # k_slow = 0.5 * 4e-8 = 2e-8 s^-1: f_cond(slow) < 0.9 needs t_wet > ln(1/0.9)/2e-8 ~ 5.3e6 s
    r = h(t_wet=1e7)
    assert (r["row"], r["verdict"], r["gates"]) == ("H2", "falsified", True)
    assert r["f_cond_slow"] < 0.9 and r["k_slow"] == pytest.approx(2e-8)


def test_h3_not_gating_at_the_fastest_rate():
    r = h(t_wet=600.0)
    assert (r["row"], r["verdict"], r["gates"]) == ("H3", "not gating", False)
    assert r["f_cond_fast"] >= 0.9 and r["k_fast"] == pytest.approx(3.0 * 6e-8)


def test_h4_inconclusive_with_both_flip_values():
    t = 1e6     # f(slow) = exp(-0.02) > 0.9, f(fast) = exp(-0.18) < 0.9
    r = h(t_wet=t)
    assert (r["row"], r["verdict"], r["gates"]) == ("H4", "inconclusive", False)
    assert r["t_wet_max_slow"] == pytest.approx(math.log(1 / 0.9) / 2e-8)
    assert r["t_wet_max_fast"] == pytest.approx(math.log(1 / 0.9) / 1.8e-7)
    assert r["t_wet_max_fast"] < t < r["t_wet_max_slow"]


def test_ca_present_uses_only_the_ca_rows():
    r = h({"ca_mM": 0.5}, t_wet=600.0)
    assert set(r["coverage"]["rows"]) == {"k6ca", "k8ca"}
    assert r["k_fast"] == pytest.approx(3.0 * 5e-7)


def test_exact_ph_uses_one_row_and_interpolation_two():
    assert h({"pH": 6.0})["coverage"]["rows"] == ["k6"]
    assert set(h({"pH": 7.0})["coverage"]["rows"]) == {"k6", "k8"}


def test_covered_state_with_a_missing_registration_is_undetermined():
    r = h(f_min=None)
    assert r["verdict"] == "undetermined" and "f_min" in r["label"] and not r["gates"]


def test_evidence_grade_is_printed_beside_every_verdict():
    r = routes.hydrolysis_descriptor(STATE, ROWS, (0.5, 3.0), 600.0, 0.9, 5.0,
                                     grades={"k6": "single-source", "hydrolysis_transfer_factor": "gap"}, route="R1")
    assert r["evidence"]["k6"] == "single-source" and r["evidence"]["hydrolysis_transfer_factor"] == "gap"
    assert r["evidence"]["k8"] == "gap"


# ------------------------------------------------------------------ R1
N = 4000
RNG = np.random.default_rng(0)


def r1(a_al, ksp, beta=None, state="oxide-equilibrium"):
    return routes.r1_at_state(np.full(N, a_al), np.full(N, 1e-2), 1.0, 3.0, 0.9, K_sp_AlPP=ksp, beta_AlPP=beta,
                              a_al_state=state)


def test_f1r_gap_prints_the_flip_value():
    r = r1(1e-10, None)
    assert (r["row"], r["verdict"]) == ("F1r", "undetermined")
    assert r["flip_K_sp"]["median"] == pytest.approx(1e-10 * 1e-6)


def test_f2r_f3r_f4r():
    iap = 1e-16
    assert r1(1e-10, iap * 10)["row"] == "F2r"
    assert r1(1e-10, iap * 10)["verdict"] == "falsified"
    r = r1(1e-10, iap / 10, beta=np.zeros(N))
    assert (r["row"], r["verdict"]) == ("F3r", "not excluded") and "optimistic" not in r["label"]
    mixed = routes.r1_at_state(np.where(np.arange(N) % 2 == 0, 1e-9, 1e-11), np.full(N, 1e-2), 1.0, 3.0, 0.9,
                               K_sp_AlPP=iap, beta_AlPP=np.zeros(N))
    assert (mixed["row"], mixed["verdict"]) == ("F4r", "inconclusive")


def test_complexation_gap_is_flagged_and_not_excluded_is_optimistic():
    r = r1(1e-10, 1e-17)
    assert "complexation gap" in r["flags"] and "optimistic" in r["label"]
    f = r1(1e-10, 1e-15)
    assert f["verdict"] == "falsified" and "complexation gap" in f["flags"]


def test_complexation_lowers_the_free_ligand():
    free = r1(1e-10, 1e-17, beta=np.zeros(N))["IAP_AlPP"]["median"]
    bound = r1(1e-10, 1e-17, beta=np.full(N, 1e10))["IAP_AlPP"]["median"]
    assert bound < free


def test_r1_states_are_labelled_and_never_combined():
    out = routes.formation_accessibility("R1", 0.9, r1={"states": {
        "oxide-equilibrium": {"a_Al": np.full(N, 1e-12), "a_PP_tot": 1e-2, "nu_Al": 1.0, "nu_PP": 3.0, "K_sp_AlPP": 1e-16,
                              "beta_AlPP": np.zeros(N)},
        "pit-state": {"a_Al": np.full(N, 1e-4), "a_PP_tot": 1e-2, "nu_Al": 1.0, "nu_PP": 3.0, "K_sp_AlPP": 1e-16,
                      "beta_AlPP": np.zeros(N)}}})
    assert out["by_a_Al_state"]["oxide-equilibrium"]["verdict"] == "falsified"
    assert out["by_a_Al_state"]["pit-state"]["verdict"] == "not excluded"
    assert out["verdict"] == "falsified" and out["governing_state"] == "oxide-equilibrium"
    assert out["falsifying_only"] and "hypothesis" in out["hypothesis"]
    with pytest.raises(routes.RouteInputError):
        routes.r1_at_state(1e-9, 1e-2, 1.0, 3.0, 0.9, a_al_state="bulk")


def test_r3_has_no_formation_criterion():
    assert routes.formation_accessibility("R3", 0.9)["verdict"] == "not applicable"


# ------------------------------------------------------------------ R2
MAP = {"covered": {"Ca_T": [1.0, 50.0], "P_T": [1.0, 50.0]}, "two_phase": {"Ca_T": [4.0, 50.0]}}


def r2(ca, cmap=MAP):
    return routes.r2_at_state({"Ca_T": np.asarray(ca, dtype=float), "P_T": np.full(np.size(ca), 10.0)}, cmap, 0.9)


def test_b1_gap_and_outside_coverage():
    assert r2([10.0], cmap=None)["row"] == "B1"
    r = r2(np.r_[np.full(99, 10.0), 100.0])
    assert r["row"] == "B1" and r["fraction_covered"] == pytest.approx(0.99)


def test_b2_b3_b4():
    assert (r2(np.full(10, 2.0))["row"], r2(np.full(10, 2.0))["verdict"]) == ("B2", "falsified")
    assert (r2(np.full(10, 10.0))["row"], r2(np.full(10, 10.0))["verdict"]) == ("B3", "not excluded")
    assert r2(np.r_[np.full(5, 2.0), np.full(5, 10.0)])["row"] == "B4"


# ------------------------------------------------------------------ K4 route form (C3)
def test_wetting_undetermined_without_the_site_free_difference():
    r = routes.liquid_precursor_wetting(0.9, 0.0, gamma_nl_c=np.full(10, 1e-4))
    assert r["verdict"] == "undetermined" and r["flip_Dgamma"]["median"] == pytest.approx(1e-4)
    r = routes.liquid_precursor_wetting(0.9, 0.0)
    assert r["verdict"] == "undetermined" and "gap" in r["flip_Dgamma"]


def test_wetting_negligible_limit_reduces_to_the_preference():
    good = routes.liquid_precursor_wetting(0.9, 0.0, np.full(N, 0.07), np.full(N, 0.05))
    assert good["verdict"] == "feasible" and "negligible" in good["limit_used"]
    bad = routes.liquid_precursor_wetting(0.9, 0.0, np.full(N, 0.05), np.full(N, 0.07))
    assert bad["verdict"] == "inconclusive"            # no closure route: a falsification cannot be stated
    bad_c = routes.liquid_precursor_wetting(0.9, 0.0, np.full(N, 0.05), np.full(N, 0.07), closure_good=np.zeros(N))
    assert bad_c["verdict"] == "falsified"
    rescued = routes.liquid_precursor_wetting(0.9, 0.0, np.full(N, 0.05), np.full(N, 0.07), closure_good=np.ones(N))
    assert rescued["verdict"] == "feasible"


def test_wetting_comparable_limit_branches():
    l0, n0 = np.full(N, 0.0505), np.full(N, 0.05)
    partial = routes.liquid_precursor_wetting(0.9, 0.0, l0, n0, gamma_nl_c=np.full(N, 1e-3), closure_good=np.zeros(N))
    assert partial["branches"]["partial_theta_below_pi_2"] == 1.0
    assert partial["verdict"] == "falsified"            # S = 5e-4 - 1e-3 < 0 although theta < pi/2: not gating
    complete = routes.liquid_precursor_wetting(0.9, 0.0, l0, n0, gamma_nl_c=np.full(N, 1e-4))
    assert complete["branches"]["complete_wetting"] == 1.0 and complete["verdict"] == "feasible"


def test_wetting_from_a_measured_contact_angle():
    r = routes.liquid_precursor_wetting(0.9, 0.0, gamma_nl_c=np.full(N, 1e-3), cos_theta_meas=np.full(N, 1.0))
    assert r["Dgamma_source"].startswith("measured") and r["verdict"] == "feasible"


def test_wetting_admissibility_refuses_and_counts():
    site = {"T": 298.15, "Gamma_P": 2e-6, "K_P": 1e4, "a_P": 1e-2, "delta_P": 5e-10, "Pi_osm": 0.0}
    # ln(1 + 100) RT Gamma ~ 0.0229 J m^-2: a site-free contact of 0.01 gives a negative gamma_sn
    l0 = np.full(N, 0.07)
    n0 = np.where(np.arange(N) < N // 4, 0.01, 0.05)
    r = routes.liquid_precursor_wetting(0.9, 0.0, l0, n0, site=site)
    assert r["retained_mass"]["M_adm"] == pytest.approx(0.75) and r["retained_mass"]["n_refused"] == N // 4
    assert r["n_used"] == N - N // 4


# ------------------------------------------------------------------ framings, matrix, baselines
def test_route_framing_amorphous_governs_and_labels():
    r = routes.route_framing("feasible", "falsified")
    assert r["verdict"] == "falsified" and "requires crystallisation" in r["labels"]
    assert routes.route_framing("falsified", "feasible")["verdict"] == "feasible"
    b = routes.route_framing("feasible", "falsified", baked=True)
    assert b["verdict"] is None and b["labels"] == ["structure unspecified"]


def test_matrix_rungs_never_gate():
    m1 = routes.matrix_entry("chitosan", [{"class": "A", "E_svc": 3.9}], 4.3, 0.1)
    assert m1["row"] == "M1" and m1["ceiling"] == 3.9 and not m1["gates"]
    assert routes.matrix_entry("chitosan", [{"class": "B", "E_svc": 4.5}], 4.3, 0.1)["row"] == "M2"
    assert routes.matrix_entry("pda", [{"class": "C", "E_svc": 3.0}], 4.3, 0.1)["row"] == "M3"
    m3 = routes.matrix_entry("pda", [], 4.3, 0.1, thermal_budget=True)
    assert m3["row"] == "M3" and m3["row_thermal"] == "M4" and "stated_risk" in m3


def test_baseline_k2_rules():
    assert routes.baseline_k2("x")["row"] == "L2"
    hq = routes.baseline_k2("hq", hydro_quebec=True)
    assert hq["row"] == "L3" and hq["verdict"] == "undetermined" and "inference from chemistry" in hq["label"]
    l1 = routes.baseline_k2("x", solubility={"verdict": "falsified"})
    assert l1["row"] == "L1" and l1["label"] == "composition-based"


def test_thresholds_structure_slots_are_provisional():
    t = routes.thresholds_ph({"m_S": 0.0, "p_cred": 0.9})
    assert t["provisional"] and t["K4_route"]["slots"]["m_S"] == 0.0 and t["K1_amorphous"]["slots"]["m_1"] == "pending"


def test_grade_of():
    assert routes.grade_of(None) == "gap"
    assert routes.grade_of({"status": "single-source", "prior": {"family": "fixed"}}) == "single-source"
    assert routes.grade_of({"status": "gap", "prior": {"family": "none"}}) == "gap"
    assert routes.grade_of({"status": "sourced", "prior": {"family": "uniform"}}, mock=True) == "mock"
