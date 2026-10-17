"""Per-link evaluators and the study-level rule: the cp2 block with the cp3 rulings.

The rule is read from configs/preprint/thresholds.yaml (the copy of theory/thresholds.md).
Every number fed to it here is synthetic, chosen so that the expected verdict is known by
construction; the parameter-table keys are the ones the block names.
"""
from pathlib import Path

import numpy as np
import pytest

from nacre.screen import decision as dc
from nacre.screen import thresholds as thr
from screen_helpers import P, synthetic_resolver as _resolver

ROOT = Path(__file__).resolve().parents[2]
RULE = thr.load_thresholds(ROOT / thr.COPY)["rule"]


def _test(claim, tid):
    return next(t for t in RULE["links"][claim]["tests"] if t["id"] == tid)


def test_band_mass_verdicts_at_the_credible_level():
    assert dc.verdict_from_mass(0.95, P) == "feasible"
    assert dc.verdict_from_mass(0.05, P) == "falsified"
    assert dc.verdict_from_mass(0.5, P) == "inconclusive"
    assert dc.verdict_from_mass(0.9, P) == "feasible"         # P_good >= p
    assert dc.verdict_from_mass(None, P) == "inconclusive"
    with pytest.raises(dc.RuleError):
        dc.verdict_from_mass(0.6, 0.5)
    m = dc.band_mass([1.0, 2.0, 3.0, np.nan], ">", 1.5)
    assert m["P_good"] == pytest.approx(2 / 3) and m["P_bad"] == pytest.approx(1 / 3)
    assert (m["n_used"], m["n_excluded"]) == (3, 1)
    assert dc.half_width(0.5, 10000) == pytest.approx(0.01)


def test_block_conventions_stand_in_for_unset_registrations():
    r = dc.Resolver({"thresholds.decision.credible_level": None})
    assert dc.credible_level(RULE, r) == 0.9                   # cp2 primary convention
    assert dc.degrade_mass(RULE, r, 0.9) == pytest.approx(0.1)  # p_deg = 1 - p_cred
    assert dc.degrade_mass(RULE, r, 0.99) == pytest.approx(0.01)


# ------------------------------------------------------------------ C1


def test_c1_per_termination_verdicts_and_the_ignorance_mixture():
    r = _resolver()
    t = _test("C1", "C1")
    w = np.linspace(-1.0, 1.0, 2001)
    rec = dc.evaluate_test(RULE, t, {"W_adh_wet": w}, r)
    assert rec["edge"] == 0.1 and rec["P_good"] == pytest.approx(np.mean(w > 0.1))
    assert rec["verdict"] == "inconclusive"
    good, bad = {"W_adh_wet": np.full(10, 1.0)}, {"W_adh_wet": np.full(10, -1.0)}
    rec = dc.evaluate_test(RULE, t, None, r, mixture={"t1": good, "t2": bad})
    # weights 3 : 1 in the table are never used as a point weight: the simplex spans [0, 1]
    assert rec["by_termination"]["t1"]["verdict"] == "feasible"
    assert rec["by_termination"]["t2"]["verdict"] == "falsified"
    assert rec["P_good_range"] == [0.0, 1.0] and rec["verdict"] == "inconclusive"
    rec = dc.evaluate_test(RULE, t, None, r, mixture={"t1": good, "t2": good})
    assert rec["verdict"] == "feasible"
    rec = dc.evaluate_test(RULE, t, None, r, mixture={"t1": bad, "t2": bad})
    assert rec["verdict"] == "falsified"


# ------------------------------------------------------------------ C2


def test_c2_is_a_descriptor_with_the_premise_finding():
    r = _resolver()
    out = dc.evaluate_c2(RULE, {"s": {"Delta_G_seq": np.full(100, 500.0)}}, r)
    assert out["role"] == "descriptor" and out["verdict"] == "descriptor"
    assert out["finding"]["statement"] == "the sequestration premise fails"
    out = dc.evaluate_c2(RULE, {"s": {"Delta_G_seq": np.full(100, -5000.0)}}, r)
    assert out["finding"]["statement"] == "the sequestration premise holds"
    assert out["tests"]["C2m"]["verdict"] == "feasible" and out["tests"]["C2m"]["edge"] == -1000.0
    assert "C2" not in RULE["study"]["gating_links"]


# ------------------------------------------------------------------ C3


def test_c3_wetting_edge_is_one_half():
    r = _resolver()
    assert dc._edge(_test("C3", "C3a")["edge"], _test("C3", "C3a")["params"], r, rule=RULE) == 0.5


def test_c3b_required_density_is_the_poisson_rule():
    r = _resolver(**{"regimes.R-slurry.parameters.patch_area": (2.0, "m^2")})
    assert dc.required_density(RULE, _test("C3", "C3b"), r, 0.9) == pytest.approx(np.log(10.0) / 2.0)
    assert dc.required_density(RULE, _test("C3", "C3b"), r, 0.99) == pytest.approx(np.log(100.0) / 2.0)


def test_c3_accessibility_sums_over_states_and_the_missing_state_rule():
    r = _resolver()                                             # N_req = 10
    s1 = {"f_theta": np.full(10, 0.2), "N_nuc": np.full(10, 6.0)}
    s2 = {"f_theta": np.full(10, 0.3), "N_nuc": np.full(10, 6.0)}
    out = dc.evaluate_link(RULE, "C3", {"slurry": s1, "drying": s2}, r)
    assert out["tests"]["C3a"]["verdict"] == "feasible" and out["tests"]["C3b"]["verdict"] == "feasible"
    assert out["tests"]["C3b"]["N_req"] == pytest.approx(10.0) and out["verdict"] == "feasible"
    out = dc.evaluate_link(RULE, "C3", {"slurry": s1}, r)       # both states registered, one evaluated
    assert out["tests"]["C3b"]["verdict"] == "falsified"       # nothing registered beyond it
    out = dc.evaluate_link(RULE, "C3", {"slurry": s1}, r, registered_states=["slurry", "drying"])
    assert out["tests"]["C3b"]["verdict"] == "inconclusive"     # a shortfall cannot falsify (R7(4))
    assert out["tests"]["C3b"]["states_missing"] == ["drying"]
    big = {"f_theta": np.full(10, 0.2), "N_nuc": np.full(10, 20.0)}
    out = dc.evaluate_link(RULE, "C3", {"slurry": big}, r, registered_states=["slurry", "drying"])
    assert out["tests"]["C3b"]["verdict"] == "feasible"         # a pass stands


def test_c3_worst_state_governs_the_wetting_part():
    r = _resolver()
    good = {"f_theta": np.full(10, 0.2), "N_nuc": np.full(10, 20.0)}
    bad = {"f_theta": np.full(10, 0.8), "N_nuc": np.full(10, 20.0)}
    out = dc.evaluate_link(RULE, "C3", {"a": good, "b": bad}, r)
    assert out["tests"]["C3a"]["verdict"] == "falsified" and "b of 2" in out["tests"]["C3a"]["aggregation"]


# ------------------------------------------------------------------ C4


def _c4(s, n_nuc, cos):
    return {"S_spread": np.full(10, s), "N_nuc": np.full(10, n_nuc), "cos_theta": np.full(10, cos),
            "gamma_sl_minus_nl": np.full(10, s)}


def test_c4_or_rule_of_cp3():
    r = _resolver()
    d_max = dc.admissible_thickness(_test("C4", "C4s"), r)
    edge90 = 1.0 / (2 * d_max ** 2)                             # tan^2(pi/4) = 1
    closes = dc.evaluate_link(RULE, "C4", {"s": _c4(-1.0, 2 * edge90, 0.0)}, r)
    assert closes["tests"]["C4"]["verdict"] == "falsified" and closes["tests"]["C4s"]["verdict"] == "feasible"
    assert closes["verdict"] == "feasible"                      # closure alone suffices under R3
    open_ = dc.evaluate_link(RULE, "C4", {"s": _c4(-1.0, 0.5 * edge90, 0.0)}, r)
    assert open_["verdict"] == "falsified"                      # both fail at p
    spreads = dc.evaluate_link(RULE, "C4", {"s": _c4(0.5, 0.0, 1.0)}, r)
    assert spreads["verdict"] == "feasible" and spreads["P_gamma_sl_gt_gamma_nl"] == 1.0
    half = _c4(-1.0, 0.5 * edge90, 0.0)
    half["N_nuc"][:5] = 2 * edge90
    assert dc.evaluate_link(RULE, "C4", {"s": half}, r)["verdict"] == "inconclusive"


def test_c4s_propagates_the_material_priors_and_flags_central_values():
    vals = {"regimes.R-cell.parameters.rho_e": {"value": 1e9, "unit": "Ohm m",
                                                "prior": {"family": "loguniform", "low": 1e8, "high": 1e10}}}
    r = _resolver(**vals)
    rng = np.random.default_rng(3)
    d, flags = dc.d_max_draws(_test("C4", "C4s"), r, 4000, rng)
    assert d.shape == (4000,) and np.std(d) > 0
    assert any("phi_B at its central value" in f for f in flags)
    assert not any(f.startswith("rho_e") for f in flags)
    d2, flags2 = dc.d_max_draws(_test("C4", "C4s"), r, 10, rng, design={"R_A_max": 10.0, "j_req": 1.0})
    assert not any(f.startswith("R_A_max") for f in flags2)
    assert np.max(d2) > np.max(d) * 0.99                        # a larger R_A_max admits a thicker film


# ------------------------------------------------------------------ joint mass (R7(1))


def test_falsified_mass_is_joint_draw_by_draw():
    r = _resolver()
    n = 1000
    f = np.where(np.arange(n) < n // 2, 0.2, 0.8)               # C3a bad on the second half
    nn = np.where(np.arange(n) < n // 2, 1.0, 100.0)            # C3b bad on the first half
    out = dc.evaluate_link(RULE, "C3", {"s": {"f_theta": f, "N_nuc": nn}}, r)
    assert out["tests"]["C3a"]["P_bad"] == pytest.approx(0.5) and out["tests"]["C3b"]["P_bad"] == pytest.approx(0.5)
    assert out["falsified_mass"] == pytest.approx(1.0)          # OR, not the max 0.5
    d_max = dc.admissible_thickness(_test("C4", "C4s"), r)
    e = 1.0 / (2 * d_max ** 2)
    s = {"S_spread": np.where(np.arange(n) < n // 2, -1.0, 1.0), "N_nuc": np.where(np.arange(n) < n // 2, 2 * e, 0.0),
         "cos_theta": np.zeros(n), "gamma_sl_minus_nl": np.zeros(n)}
    out = dc.evaluate_link(RULE, "C4", {"s": s}, r)
    assert out["falsified_mass"] == pytest.approx(0.0)          # AND on disjoint bad sets, not the min 0.5


# ------------------------------------------------------------------ gaps and refusals


def test_missing_parameter_key_is_an_explicit_named_gap():
    r = dc.Resolver({"thresholds.decision.credible_level": P})
    out = dc.evaluate_link(RULE, "C1", {"s": {"W_adh_wet": np.ones(3)}}, r)
    assert out["verdict"] == "inconclusive"
    assert "thresholds.C1.margin_W_adh_wet" in out["tests"]["C1"]["gap"]


def test_forbidden_quantities_never_enter_a_verdict():
    bad = dict(_test("C1", "C1"), quantity="E_enr")
    with pytest.raises(dc.RuleError, match="forbidden"):
        dc.evaluate_test(RULE, bad, {"E_enr": np.ones(3)}, _resolver())


# ------------------------------------------------------------------ C5 R-slurry (R1)


def _design(points):
    return {pid: {"axes": {"Ca_T": i}, "Omega_bulk": np.asarray(om, float)} for i, (pid, om) in enumerate(points.items())}


def test_c5_omega_dose_window_and_falsifiability_control():
    dissolves = {"axes": {"pH": 6.3}, "Omega_bulk": np.full(100, 0.01)}
    stable = {"lo": np.full(100, 5.0), "hi": np.full(100, 50.0)}
    rec = dc.evaluate_c5_slurry_omega(_design(stable), P, control=dissolves)
    assert rec["verdict"] == "feasible" and rec["control"]["fails_where_it_must"]
    assert rec["dose_window"]["feasible_points"] == ["hi", "lo"]
    # a control that does not report dissolution where it must forbids a pass
    rec = dc.evaluate_c5_slurry_omega(_design(stable), P, control={"axes": {}, "Omega_bulk": np.full(100, 3.0)})
    assert rec["verdict"] == "inconclusive" and not rec["control"]["fails_where_it_must"]
    assert dc.evaluate_c5_slurry_omega(_design(stable), P)["verdict"] == "inconclusive"
    # the window is design-dependent when low doses dissolve
    mixed = {"low": np.full(100, 0.1), "high": np.full(100, 10.0)}
    rec = dc.evaluate_c5_slurry_omega(_design(mixed), P, control=dissolves)
    assert rec["design_dependent"] and rec["verdict"] == "inconclusive"
    assert rec["dose_window"]["feasible_points"] == ["high"]
    assert rec["dose_window"]["points"]["low"]["verdict"] == "falsified"
    allbad = dc.evaluate_c5_slurry_omega(_design({"a": np.full(10, 0.5)}), P, control=dissolves)
    assert allbad["verdict"] == "falsified"


def _stability(calcite_grid):
    return {"kind": "pourbaix", "reference_electrode": "SHE", "temperature_K": 300.0,
            "axes": {"pH": [1.0, 2.0, 3.0], "E_V": [-1.0, 0.0, 1.0]},
            "states": {"bulk": {"conditions": {"a_Ca": 1.0, "a_CO3": 1.0}, "phases": [], "domains": {"index_grid": [[0]]},
                                "decomposition_energy": {"calcite": {"units": "eV/atom", "formula": "CaCO3",
                                                                     "grid": calcite_grid}}}}}


def test_c5_competing_phase_test_keeps_its_dft_tolerance():
    r = _resolver()
    grid = [[9.0, 0.01, 0.02], [9.0, 0.0, 0.03], [9.0, 9.0, 9.0]]   # region: pH 2-3, E -1..0
    out = dc.evaluate_c5_slurry_phase(_test("C5", "C5s"), _stability(grid), r, "calcite")
    assert out["verdict"] == "feasible"
    assert out["value"] == pytest.approx(0.03 * 5 / 2) and out["edge"] == pytest.approx(0.05 * 5 / 2)
    grid[1][2] = 0.06
    assert dc.evaluate_c5_slurry_phase(_test("C5", "C5s"), _stability(grid), r, "calcite")["verdict"] == "falsified"


# ------------------------------------------------------------------ C5 R-cell (R2)


def _cell(kind, ox_by_scheme, red=1.0):
    lim = lambda v: ({"status": "ok", "value_V": v, "reaction": "r", "reason": ""} if v is not None
                     else {"status": "undetermined", "value_V": None, "reaction": "", "reason": "missing"})
    ox = {s: lim(v) for s, v in ox_by_scheme.items()}
    return {"kind": "window", "reference_electrode": "Li+/Li", "temperature_K": 300.0,
            "sink_assumption": {"active": kind, "statement": "x", "kind": kind},
            "windows": {"CaCO3": {"reduction": lim(red), "oxidation": ox.get("expt", lim(None)),
                                  "oxidation_by_scheme": ox}}}


def _cell_eval(cells, cuts, **kw):
    return dc.evaluate_c5_cell(cells, _resolver(), ["CaCO3"], "oxidation", cuts, "thresholds.C5.margin_expt", **kw)


def test_c5_cell_expt_governs_and_dft_schemes_are_comparators():
    # janaf above and mp below the cutoff do not decide; the expt route does
    cells = {"LiX": _cell("solid_salt", {"expt": 3.9, "janaf": 4.6, "mp": 3.5})}
    rec = _cell_eval(cells, {"4.3": 4.3})
    assert rec["verdict"] == "falsified"                        # 3.9 + 0.1 < 4.3; a solid-salt falsification stands
    roles = {(r["scheme"], r["role"]) for r in rec["scheme_table"]}
    assert ("expt", "governing") in roles and ("janaf", "comparator") in roles and ("mp", "comparator") in roles
    cells = {"LiX": _cell("solid_salt", {"expt": 4.5, "mp": 3.0})}
    assert _cell_eval(cells, {"4.3": 4.3})["verdict"] == "inconclusive"   # solid-salt pass is an upper bound
    cells["solvated"] = _cell("solvated", {"expt": 4.6})
    assert _cell_eval(cells, {"4.3": 4.3})["verdict"] == "feasible"       # the solvated sink passes


def test_c5_cell_cutoff_axis_margin_and_undetermined_limits():
    cells = {"solvated": _cell("solvated", {"expt": 4.0})}
    rec = _cell_eval(cells, {"LFP": 3.6, "NMC": 4.3})
    assert rec["cutoff_axis"]["LFP"]["verdict"] == "feasible" and rec["cutoff_axis"]["NMC"]["verdict"] == "falsified"
    assert rec["design_dependent"] and rec["verdict"] == "inconclusive"
    assert _cell_eval(cells, {"x": 4.05})["verdict"] == "inconclusive"     # within the margin
    cells = {"solvated": _cell("solvated", {"expt": None, "janaf": 5.0})}
    assert _cell_eval(cells, {"x": 3.6})["verdict"] == "inconclusive"      # undetermined never passes
    cells = {"solvated": _cell("solvated", {"expt": 4.6}), "LiBOB": _cell("solid_salt", {"expt": 4.8})}
    rec = _cell_eval(cells, {"x": 4.3}, never_pass_sinks=("LiBOB",))
    assert rec["cutoff_axis"]["x"]["phases"]["CaCO3"]["sinks"]["LiBOB"]["verdict"] == "inconclusive"
    r = dc.Resolver({"thresholds.decision.credible_level": P})
    rec = dc.evaluate_c5_cell({"solvated": _cell("solvated", {"expt": 9.0})}, r, ["CaCO3"], "oxidation", {"x": 4.3},
                              "thresholds.C5.margin_expt")
    assert rec["verdict"] == "inconclusive" and rec["margin_V"] is None   # m_expt not registered


def test_c5_combines_its_tests_and_reports_gaps():
    r = _resolver()
    omega = dc.evaluate_c5_slurry_omega(_design({"a": np.full(10, 5.0)}), P,
                                        control={"axes": {}, "Omega_bulk": np.full(10, 0.1)})
    grid = [[0.0, 0.0, 0.0]] * 3
    cells = {"solvated": _cell("solvated", {"expt": 4.6}, red=1.0)}
    out = dc.evaluate_c5(RULE, r, omega=omega, pourbaix=_stability(grid), cells=cells)
    assert out["verdict"] == "feasible"
    out = dc.evaluate_c5(RULE, r, omega=omega, pourbaix=_stability(grid), cells={"solvated": _cell("solvated", {"expt": 3.0})})
    assert out["verdict"] == "falsified"
    out = dc.evaluate_c5(RULE, r)
    assert out["verdict"] == "inconclusive" and all("gap" in t for t in out["tests"].values())


# ------------------------------------------------------------------ design axes, framings, study


def test_design_axis_and_framing_reductions():
    assert dc.over_design({"a": "feasible", "b": "feasible"}) == {"verdict": "feasible", "design_dependent": False}
    assert dc.over_design({"a": "feasible", "b": "falsified"})["design_dependent"]
    f = dc.combine_framings({"calcite": "falsified", "ACC": "feasible"})
    assert f["verdict"] == "feasible" and f["governing_framing"] == "ACC" and f["by_framing"]["calcite"] == "falsified"
    assert dc.combine_framings({"calcite": "falsified", "ACC": "falsified"})["verdict"] == "falsified"
    assert dc.combine_framings({"calcite": "falsified", "ACC": "inconclusive"})["verdict"] == "inconclusive"


def _claims(**v):
    base = {c: {"verdict": "feasible", "falsified_mass": 0.0} for c in ("C1", "C3", "C4", "C5")}
    base["C2"] = {"verdict": "descriptor", "falsified_mass": None, "finding": {"statement": "the sequestration premise holds"}}
    base.update(v)
    return base


def test_study_verdict_and_deletion_test():
    r = _resolver()
    tmpl = _claims()
    worse = {"verdict": "inconclusive", "falsified_mass": 0.0}
    controls = {"bare_oxide": _claims(C3=worse), "PVDF": _claims(C4={"verdict": "feasible", "falsified_mass": 0.2})}
    dt = dc.deletion_test(RULE, tmpl, controls, r)
    assert dt["holds"] and dt["controls"]["PVDF"]["degraded"] == ["C4"]      # mass up by >= p_deg
    s = dc.study_verdict(RULE, tmpl, dt)
    assert s["verdict"] == "feasible" and s["gating_links"] == ["C1", "C3", "C4", "C5"]
    assert s["sequestration_premise"] == "the sequestration premise holds"
    c1_only = {"bare_oxide": _claims(C1={"verdict": "falsified", "falsified_mass": 1.0}), "PVDF": controls["PVDF"]}
    dt2 = dc.deletion_test(RULE, tmpl, c1_only, r)
    assert not dt2["holds"] and dt2["on_failure"] == "framing_generic_adhesion"
    s = dc.study_verdict(RULE, tmpl, dt2)
    assert s["verdict"] == "inconclusive" and s["framing"] == "generic adhesion study"
    assert dc.study_verdict(RULE, _claims(C4={"verdict": "falsified"}), dt)["verdict"] == "falsified"
    assert dc.study_verdict(RULE, tmpl, None)["verdict"] == "inconclusive"   # no deletion test run


def test_every_registered_test_of_c1_c3_c4_is_evaluable():
    r = _resolver()
    s = {"W_adh_wet": np.ones(4), "f_theta": np.full(4, 0.1), "N_nuc": np.full(4, 1e40), "S_spread": np.ones(4),
         "cos_theta": np.full(4, 0.5), "gamma_sl_minus_nl": np.ones(4)}
    for claim in ("C1", "C3", "C4"):
        out = dc.evaluate_link(RULE, claim, {"s": s}, r)
        assert set(out["tests"]) == {t["id"] for t in RULE["links"][claim]["tests"]}
        assert out["verdict"] == "feasible"
