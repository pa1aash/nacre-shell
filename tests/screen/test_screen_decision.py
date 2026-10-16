"""Per-link evaluators and the study-level rule, applied to the frozen thresholds block.

The rule is read from configs/preprint/thresholds.yaml (the copy of theory/thresholds.md).
Every number fed to it here is synthetic (round values chosen to exercise each branch); the
parameter-table keys are the ones the block names.
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


def test_c1_dupre_work_against_its_margin_with_the_termination_mixture():
    r = _resolver()
    w = np.linspace(-1.0, 1.0, 2001)
    rec = dc.evaluate_test(RULE, _test("C1", "C1"), {"W_adh_wet": w}, r)
    assert rec["edge"] == 0.1 and rec["P_good"] == pytest.approx(np.mean(w > 0.1))
    assert rec["verdict"] == "inconclusive"
    mix = {"t1": {"W_adh_wet": np.full(10, 1.0)}, "t2": {"W_adh_wet": np.full(10, -1.0)}}
    rec = dc.evaluate_test(RULE, _test("C1", "C1"), None, r, mixture=mix)
    assert rec["P_good"] == pytest.approx(0.75)               # weights 3 : 1


def test_c2_binding_beyond_the_margin():
    r = _resolver()
    out = dc.evaluate_link(RULE, "C2", {"s": {"Delta_G_seq": np.full(100, -5000.0)}}, r)
    assert out["verdict"] == "feasible" and out["tests"]["C2"]["edge"] == -1000.0
    out = dc.evaluate_link(RULE, "C2", {"s": {"Delta_G_seq": np.full(100, -500.0)}}, r)
    assert out["verdict"] == "falsified"


def test_c3_wetting_edge_is_one_half_and_accessibility_sums_over_states():
    r = _resolver()
    assert dc._edge(_test("C3", "C3a")["edge"], _test("C3", "C3a")["params"], r) == 0.5
    s1 = {"f_theta": np.full(10, 0.2), "N_nuc": np.full(10, 6.0)}
    s2 = {"f_theta": np.full(10, 0.3), "N_nuc": np.full(10, 6.0)}
    out = dc.evaluate_link(RULE, "C3", {"slurry": s1, "drying": s2}, r)
    assert out["tests"]["C3a"]["verdict"] == "feasible"
    assert out["tests"]["C3b"]["verdict"] == "feasible"       # 6 + 6 >= N_req = 10
    assert out["verdict"] == "feasible"
    out = dc.evaluate_link(RULE, "C3", {"slurry": s1}, r)      # 6 < 10 on one state alone
    assert out["tests"]["C3b"]["verdict"] == "falsified" and out["verdict"] == "falsified"


def test_c3_worst_state_governs_the_wetting_part():
    r = _resolver()
    good = {"f_theta": np.full(10, 0.2), "N_nuc": np.full(10, 20.0)}
    bad = {"f_theta": np.full(10, 0.8), "N_nuc": np.full(10, 20.0)}
    out = dc.evaluate_link(RULE, "C3", {"a": good, "b": bad}, r)
    assert out["tests"]["C3a"]["verdict"] == "falsified" and "b of 2" in out["tests"]["C3a"]["aggregation"]


def test_c4_is_falsified_only_when_islands_also_fail_to_close():
    r = _resolver()
    d_max = dc.admissible_thickness(_test("C4", "C4s"), r)
    assert d_max > 0
    edge_at_90 = 1.0 / (2 * d_max ** 2)                       # tan^2(pi/4) = 1
    cos90 = np.zeros(10)
    islands_close = {"S_spread": np.full(10, -1.0), "N_nuc": np.full(10, 2 * edge_at_90), "cos_theta": cos90}
    islands_open = {"S_spread": np.full(10, -1.0), "N_nuc": np.full(10, 0.5 * edge_at_90), "cos_theta": cos90}
    spreads = {"S_spread": np.full(10, 0.5), "N_nuc": np.zeros(10), "cos_theta": np.ones(10)}
    assert dc.evaluate_link(RULE, "C4", {"s": islands_close}, r)["verdict"] == "inconclusive"
    assert dc.evaluate_link(RULE, "C4", {"s": islands_open}, r)["verdict"] == "falsified"
    assert dc.evaluate_link(RULE, "C4", {"s": spreads}, r)["verdict"] == "feasible"


def test_forbidden_quantities_never_enter_a_verdict():
    bad = dict(_test("C2", "C2"), quantity="E_enr")
    with pytest.raises(dc.RuleError, match="forbidden"):
        dc.evaluate_test(RULE, bad, {"E_enr": np.ones(3)}, _resolver())


def test_missing_parameter_key_is_named():
    r = dc.Resolver({"thresholds.decision.credible_level": P})
    with pytest.raises(KeyError, match="thresholds.C2.margin_DG_seq"):
        dc.evaluate_link(RULE, "C2", {"s": {"Delta_G_seq": np.ones(3)}}, r)


# ------------------------------------------------------------------ C5

def _stability(calcite_grid, cell_ox=4.5, cell_red=1.0, ox_status="ok", kind="solid_salt", al=True):
    lim = lambda s, v: {"status": s, "value_V": v if s == "ok" else None,
                        "reaction": "r" if s == "ok" else "", "reason": "" if s == "ok" else "missing"}
    windows = {"CaCO3": {"reduction": lim("ok", cell_red), "oxidation": lim(ox_status, cell_ox)}}
    if al:
        windows["Al2O3"] = {"reduction": lim("ok", 1.0), "oxidation": lim("ok", 5.0)}
    return {"R-slurry": {"kind": "pourbaix", "reference_electrode": "SHE", "temperature_K": 300.0,
                         "axes": {"pH": [1.0, 2.0, 3.0], "E_V": [-1.0, 0.0, 1.0]},
                         "states": {"bulk": {"conditions": {"a_Ca": 1.0, "a_CO3": 1.0}, "phases": [],
                                             "domains": {"index_grid": [[0]]},
                                             "decomposition_energy": {"calcite": {"units": "eV/atom", "formula": "CaCO3",
                                                                                  "grid": calcite_grid}}}}},
            "R-cell": {"kind": "window", "reference_electrode": "Li+/Li", "temperature_K": 300.0,
                       "sink_assumption": {"active": "s", "statement": "x", "kind": kind}, "windows": windows}}


def test_c5_slurry_worst_point_inside_the_registered_region():
    r = _resolver()
    grid = [[9.0, 0.01, 0.02], [9.0, 0.0, 0.03], [9.0, 9.0, 9.0]]   # region: pH 2-3, E -1..0
    out = dc.evaluate_c5_slurry(_test("C5", "C5s"), _stability(grid)["R-slurry"], r, "calcite", True)
    assert out["verdict"] == "feasible"
    assert out["value"] == pytest.approx(0.03 * 5 / 2) and out["edge"] == pytest.approx(0.05 * 5 / 2)
    assert dc.evaluate_c5_slurry(_test("C5", "C5s"), _stability(grid)["R-slurry"], r, "calcite", None)["verdict"] \
        == "inconclusive"                                       # control not shown to fail
    grid[1][2] = 0.06
    assert dc.evaluate_c5_slurry(_test("C5", "C5s"), _stability(grid)["R-slurry"], r, "calcite", True)["verdict"] \
        == "falsified"


def test_c5_cell_window_rules():
    r = _resolver()
    ox, red = _test("C5", "C5c_ox"), _test("C5", "C5c_red")
    st = _stability([[0.0]], cell_ox=4.5)["R-cell"]
    assert dc.evaluate_c5_cell(ox, st, r, ["CaCO3", "Al2O3"])["verdict"] == "inconclusive"     # solid salt
    assert dc.evaluate_c5_cell(ox, st, r, ["CaCO3", "Al2O3"], solid_salt_registered=True)["verdict"] == "feasible"
    st = _stability([[0.0]], cell_ox=4.05)["R-cell"]
    assert dc.evaluate_c5_cell(ox, st, r, ["CaCO3"], True)["verdict"] == "inconclusive"         # inside the margin
    st = _stability([[0.0]], cell_ox=3.5)["R-cell"]
    assert dc.evaluate_c5_cell(ox, st, r, ["CaCO3"])["verdict"] == "falsified"                  # falsification stands
    st = _stability([[0.0]], ox_status="undetermined")["R-cell"]
    assert dc.evaluate_c5_cell(ox, st, r, ["CaCO3"], True)["verdict"] == "inconclusive"         # never passes
    st = _stability([[0.0]], cell_red=2.5)["R-cell"]
    assert dc.evaluate_c5_cell(red, st, r, ["CaCO3"])["verdict"] == "falsified"
    st = _stability([[0.0]])["R-cell"]
    st["windows"]["CaCO3"]["oxidation_by_scheme"] = {"a": {"status": "ok", "value_V": 4.6, "reaction": "r", "reason": ""},
                                                     "b": {"status": "ok", "value_V": 3.0, "reaction": "r", "reason": ""}}
    assert dc.evaluate_c5_cell(ox, st, r, ["CaCO3"], True)["verdict"] == "falsified"             # lowest scheme


def test_c5_combines_both_regimes():
    r = _resolver()
    grid = [[0.0, 0.0, 0.0]] * 3
    out = dc.evaluate_c5(RULE, _stability(grid, cell_ox=4.5, kind="solvated"), r, control_fails_where_it_must=True)
    assert out["verdict"] == "feasible"
    out = dc.evaluate_c5(RULE, _stability(grid, cell_ox=3.0, kind="solvated"), r, control_fails_where_it_must=True)
    assert out["verdict"] == "falsified"


# ------------------------------------------------------------------ study

def _claims(**v):
    base = {c: {"verdict": "feasible", "falsified_mass": 0.0} for c in ("C1", "C2", "C3", "C4", "C5")}
    for k, val in v.items():
        base[k] = val
    return base


def test_study_verdict_and_deletion_test():
    r = _resolver()
    tmpl = _claims()
    worse = {"verdict": "inconclusive", "falsified_mass": 0.0}
    controls = {"bare_oxide": _claims(C3=worse), "PVDF": _claims(C2={"verdict": "feasible", "falsified_mass": 0.2})}
    dt = dc.deletion_test(RULE, tmpl, controls, r)
    assert dt["holds"] and dt["controls"]["PVDF"]["degraded"] == ["C2"]       # mass up by >= p_deg
    assert dc.study_verdict(RULE, tmpl, dt)["verdict"] == "feasible"
    c1_only = {"bare_oxide": _claims(C1={"verdict": "falsified", "falsified_mass": 1.0}), "PVDF": controls["PVDF"]}
    dt2 = dc.deletion_test(RULE, tmpl, c1_only, r)
    assert not dt2["holds"] and dt2["on_failure"] == "framing_generic_adhesion"
    s = dc.study_verdict(RULE, tmpl, dt2)
    assert s["verdict"] == "inconclusive" and s["framing"] == "generic adhesion study"
    assert dc.study_verdict(RULE, _claims(C4={"verdict": "falsified"}), dt)["verdict"] == "falsified"
    assert dc.study_verdict(RULE, tmpl, None)["verdict"] == "inconclusive"   # no deletion test run


def test_every_registered_test_of_c1_to_c4_is_evaluable():
    r = _resolver()
    s = {"W_adh_wet": np.ones(4), "Delta_G_seq": -np.ones(4) * 5e3, "f_theta": np.full(4, 0.1),
         "N_nuc": np.full(4, 1e40), "S_spread": np.ones(4), "cos_theta": np.full(4, 0.5)}
    for claim in ("C1", "C2", "C3", "C4"):
        out = dc.evaluate_link(RULE, claim, {"s": s}, r)
        assert set(out["tests"]) == {t["id"] for t in RULE["links"][claim]["tests"]}
        assert out["verdict"] == "feasible"
