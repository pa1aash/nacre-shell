"""The gap-table treatments in the chain and the decision layer (P0-W4.3); synthetic inputs only."""
from pathlib import Path

import numpy as np
import pytest

from nacre.physics import sequestration
from nacre.physics.constants import GAS_CONSTANT
from nacre.screen import chain, decision, sobol, study

ROOT = Path(__file__).resolve().parents[2]
N = 64


def _x(**kw):
    return {k: np.full(N, float(v)) for k, v in kw.items()}


def test_site_analog_gives_the_conditional_binding_constant():
    # Delta_G_site from a solution constant K: the Langmuir odds are K c_bulk / c_std over the deprotonation factor
    x = _x(K_Ca_catecholate=10 ** 4.0, Gamma_s=5e-6, delta_s=1e-9, T=298.15)
    d, _, _ = chain.derive(x)
    pka, ph, c_bulk = 9.3, 12.0, 2.0
    dg_seq = sequestration.sequestration_free_energy(d["Delta_G_site"], pka, ph, 298.15)
    odds = sequestration.binding_odds(dg_seq, 298.15, c_bulk, 5e-6, 1e-9)
    expect = 1e4 * c_bulk / chain.C_STANDARD / (1.0 + 10 ** (pka - ph))
    assert np.allclose(odds, expect, rtol=1e-12)


def test_site_analog_does_not_replace_a_supplied_site_energy():
    x = _x(K_Ca_catecholate=1e4, Gamma_s=5e-6, delta_s=1e-9, T=298.15, Delta_G_site=-1234.0)
    d, _, _ = chain.derive(x)
    assert np.all(d["Delta_G_site"] == -1234.0)


def test_delta_s_lies_in_its_geometric_bound():
    rng = np.random.default_rng(3)
    gs = rng.uniform(1e-6, 1e-5, N)
    x = {"u_delta_s": rng.random(N), "r_Ca": np.full(N, 2.4e-10), "d_layer": np.full(N, 2e-8), "Gamma_s": gs,
         "V_m": np.full(N, 3.7e-5)}
    d, _, _ = chain.derive(x)
    lo = np.maximum(2 * 2.4e-10, gs * 3.7e-5)
    assert np.all((d["delta_s"] >= lo * (1 - 1e-12)) & (d["delta_s"] <= 2e-8 * (1 + 1e-12)))


def test_an_empty_delta_s_interval_is_refused_and_counted():
    x = _x(u_delta_s=0.5, r_Ca=2.4e-10, d_layer=4e-10, Gamma_s=5e-6, V_m=3.7e-5)
    d, _, _ = chain.derive(x)
    assert np.all(np.isnan(d["delta_s"]))
    assert d["_geometry_masses"]["delta_s_interval"].n_refused == N


def test_analog_caps_flag_gamma_s_and_never_refuse():
    # cp3b A3: a bound evaluated with an analog key is reported and flagged, never refusing
    gs = np.linspace(1e-6, 1e-5, N)
    x = {"Gamma_s": gs, "rho_L": np.full(N, 250.0), "d_layer": np.full(N, 2e-8), "r_Ca": np.full(N, 2.4e-10)}
    d, _, _ = chain.derive(x)
    assert np.all(d["Gamma_s"] == gs)
    assert np.array_equal(d["_geometry_flags"]["Gamma_s_above_rho_L_cap"], (gs > 5e-6).astype(float))
    cap = 1.0 / (2 * np.sqrt(3) * 6.02214076e23 * 2.4e-10 ** 2)
    assert np.array_equal(d["_geometry_flags"]["Gamma_s_above_a_site_cap"], (gs > cap).astype(float))


def test_delta_s_drops_the_radius_term_while_r_ca_is_a_gap():
    x = _x(u_delta_s=0.0, d_layer=2e-8, Gamma_s=5e-6, V_m=3.7e-5)
    d, _, _ = chain.derive(x)
    assert np.allclose(d["delta_s"], 5e-6 * 3.7e-5)


def test_the_expt_margin_belongs_to_its_registered_reaction():
    cells = {"LiClO4": {"sink_assumption": {"kind": "solid_salt"},
                        "windows": {"CaCO3": {"oxidation_by_scheme": {"expt": {"status": "ok", "value_V": 4.0}},
                                              "reduction_by_scheme": {"expt": {"status": "ok", "value_V": 1.6}}}}}}
    r = decision.Resolver({"m": {"value": 0.09, "unit": "V"}, "e": {"value": 0.12, "unit": "V"}})
    routes = {"expt": {"applies_to": [{"phase": "CaCO3", "sink": "LiClO4", "side": "oxidation"}]}}
    ox = decision.evaluate_c5_cell(cells, r, ["CaCO3"], "oxidation", {"hi": 4.5}, "m", (), "e", routes)
    red = decision.evaluate_c5_cell(cells, r, ["CaCO3"], "reduction", {"lo": 3.0}, "m", (), "e", routes)
    assert ox["verdict"] == "falsified"                       # 4.0 + 0.09 < 4.5 under the registered budget
    assert red["verdict"] == "inconclusive"                   # no budget key for the reduction limit
    assert "undetermined" in red["cutoff_axis"]["lo"]["phases"]["CaCO3"]["sinks"]["LiClO4"]["note"]


def test_the_termination_mixture_mixes_the_works():
    rng = np.random.default_rng(5)
    test = {"quantity": "W_adh_wet", "comparator": ">", "edge": "m_W", "params": {"m_W": "mw"},
            "mixture": {"over": "termination"}}
    rule = {"decision": {"credible_level": {"params": "p"}, "conventions": {"p_cred": {"primary": 0.9}},
                         "forbidden_in_verdicts": []}}
    r = decision.Resolver({"mw": {"value": 0.0, "unit": "J m^-2"}})
    a, b = np.full(2000, 0.01), np.full(2000, -0.01)
    rec = decision.evaluate_test(rule, test, {}, r, mixture={"A": {"W_adh_wet": a}, "B": {"W_adh_wet": b}}, rng=rng)
    assert rec["weight_free"]["P_min_good"] == 0.0 and rec["weight_free"]["P_max_good"] == 1.0
    assert 0.4 < rec["P_good"] < 0.6                          # W_mix > 0 iff w_A > 1/2
    assert rec["falsified_alone"] == ["B"] and "conditional" in rec["weight_free"]["reading"]


def test_gamma_pw_is_gamma_sl0():
    d, _, _ = chain.derive(_x(gamma_sl0=0.002))
    assert np.all(d["gamma_pw"] == 0.002)


def test_control_surface_carries_the_ignorance_bounds():
    # on a deletion control gamma_p is not bound: the oxide's dry energy bounds both contacts
    x = _x(u_gamma_sn=0.5, u_gamma_sl=0.25, gamma_o=0.04, gamma_nv=0.5, gamma_w=0.072)
    d, _, _ = chain.derive(x)
    assert np.allclose(d["gamma_sn0"], 0.5 * (0.04 + 0.5)) and np.allclose(d["gamma_sl"], 0.25 * (0.04 + 0.072))
    assert chain.template_energy_mode(chain.derived_symbols(x)) == "in_situ"


def test_template_keeps_the_template_bound_when_the_oxide_is_also_bound():
    x = _x(u_gamma_sn=0.5, gamma_p=0.05, gamma_o=0.04, gamma_nv=0.5)
    d, _, _ = chain.derive(x)
    assert np.allclose(d["gamma_sn0"], 0.5 * (0.05 + 0.5))


def test_the_w_analog_is_reported_beside_the_pmf_route():
    out, _ = chain.evaluate(_x(W_adh_wet=0.003), ["anchor"])
    assert np.all(out["anchor"]["W_adh_wet_analog"] == 0.003) and np.all(np.isnan(out["anchor"]["W_adh_wet"]))




def test_design_axes_by_state_by_class_and_by_points():
    r = decision.Resolver({"aw2": {"value": 1e-3, "unit": "1", "range": {"min": 1e-6, "max": 2e-3}},
                           "lfp": {"value": 4.0, "unit": "V", "range": {"min": 3.6, "max": 4.2}},
                           "dic": {"value": 10.0, "unit": "mol m^-3", "range": {"min": 4.0, "max": 18.0}}})
    cfg = {"design_axes": {"Ca_T": {"unit": "mol dm^-3", "values": [1e-3]}, "C_T": {"params": "dic", "at": ["min"]},
                           "a_w": {"state": "drying", "points": [{"label": "wet", "value": 1.0},
                                                                 {"label": "dry", "params": "aw2", "at": "min"}]}}}
    pts = study.design_points(cfg, r)
    assert len(pts) == 2 and {p[1]["a_w@drying"] for p in pts} == {1.0, 1e-6}
    assert all(p[1]["Ca_T"] == pytest.approx(1.0) for p in pts)
    cuts = dict(study._axis_values({"classes": {"LFP": "lfp"}, "at": ["min", "max"]}, r, "V"))
    assert cuts == {"LFP@min": 3.6, "LFP@max": 4.2}


def test_w5_documents_are_mapped_to_design_points():
    stab = study.load_slurry_stability(ROOT / "results" / "preprint" / "pourbaix" / "c5" / "slurry")
    assert stab is not None
    found = study.pourbaix_for(stab, {"Ca_T": "0.001 mol dm^-3", "C_T": "dic_slurry@max"})
    assert len(found) == 3 and all(v is not None for v in found.values())
    assert study.pourbaix_for(None, {}) == {None: None}


def test_a_control_without_inputs_cannot_hold_the_deletion_test():
    rule = {"decision": {"credible_level": {"params": "p"}, "conventions": {"p_cred": {"primary": 0.9},
                                                                          "p_deg": {"rule": "1 - p_cred"}}},
            "study": {"deletion_test": {"gating_controls": ["bare_oxide", "PVDF"], "links": ["C3", "C4"],
                                        "on_failure": "framing_generic_adhesion", "params": {"p_deg": "x"}}}}
    t = {"C3": {"verdict": "inconclusive", "falsified_mass": 0.2}, "C4": {"verdict": "inconclusive", "falsified_mass": 0.2}}
    ctl = {"bare_oxide": {"C3": {"verdict": "falsified", "falsified_mass": 0.95}, "C4": t["C4"]},
           "PVDF": {"_gap": "no PVDF key", "C3": {"verdict": "inconclusive"}, "C4": {"verdict": "inconclusive"}}}
    dt = decision.deletion_test(rule, t, ctl, decision.Resolver({}))
    assert dt["controls"]["bare_oxide"]["holds"] and not dt["controls"]["PVDF"]["holds"]
    assert "not evaluable" in dt["controls"]["PVDF"]["note"] and not dt["holds"]


def test_sizing_doubles_until_the_half_width_rule_holds(monkeypatch):
    calls = []

    def fake(rule, resolver, params_path, cfg, allow_mock, prior_set, truncation, draws=None, **kw):
        calls.append(draws)
        return {}, {}, {"max_band_half_width": 2.0 / np.sqrt(draws)}
    monkeypatch.setattr(study, "evaluate", fake)
    cfg = {"propagation": {"draws_per_regime": 2 ** 20},
           "sizing": {"start": 2 ** 14, "band_mass_half_width_max": 0.01, "draw_cap": 2 ** 20, "wall_clock_s": 1e9}}
    _, s, _ = study.evaluate_sized({}, None, None, cfg)
    assert calls == [2 ** 14, 2 ** 15, 2 ** 16] and s["sizing"]["met"] and not s["sizing"]["capped"]


def test_sizing_reports_the_draw_cap(monkeypatch):
    monkeypatch.setattr(study, "evaluate", lambda *a, draws=None, **k: ({}, {}, {"max_band_half_width": 0.5}))
    cfg = {"propagation": {"draws_per_regime": 2 ** 15},
           "sizing": {"start": 2 ** 14, "band_mass_half_width_max": 0.01, "draw_cap": 2 ** 20, "wall_clock_s": 1e9}}
    _, s, _ = study.evaluate_sized({}, None, None, cfg)
    assert s["sizing"]["capped"] and s["sizing"]["draws_per_state"] == 2 ** 15 and "draw cap" in s["sizing"]["cap"]


def test_resolver_override_and_alias():
    r = decision.Resolver({"a": {"value": 0.9, "unit": "1"}, "m": {"value": 0.08, "unit": "V"}})
    assert r.override({"a": 0.6}).value("a") == 0.6 and r.value("a") == 0.9
    assert r.alias({"b": "m"}).si("b", "V") == pytest.approx(0.08) and not r.has("b")


def test_sobol_target_scope_reads_the_top_total_order_indices():
    idx = {"q": {"x": {"first_order": {"estimate": 0.5, "ci_low": 0.0, "ci_high": 1.0},
                       "total_order": {"estimate": 0.6, "ci_low": 0.59, "ci_high": 0.61}},
                 "y": {"first_order": {"estimate": 0.0, "ci_low": -0.5, "ci_high": 0.5},
                       "total_order": {"estimate": 0.01, "ci_low": -0.3, "ci_high": 0.32}}}}
    assert sobol.max_half_width(idx, "top_total", 1) == pytest.approx(0.01)
    assert sobol.max_half_width(idx) == pytest.approx(0.5)


def test_derive_keeps_the_gas_constant_convention():
    x = _x(K_Ca_catecholate=1.0, Gamma_s=1e-6, delta_s=1e-9, T=300.0)          # c_max = c_std
    d, _, _ = chain.derive(x)
    assert np.allclose(d["Delta_G_site"], 0.0, atol=1e-9)
    x = _x(K_Ca_catecholate=np.e, Gamma_s=1e-6, delta_s=1e-9, T=300.0)
    assert np.allclose(chain.derive(x)[0]["Delta_G_site"], -GAS_CONSTANT * 300.0)


def test_w5_cells_read_with_the_registered_phase_names_and_benchmarks():
    base = ROOT / "results" / "preprint" / "pourbaix" / "c5"
    cells = study.load_cells(sorted((base / "cell").glob("*.json")), {"corundum": "Al2O3"}, base / "cell_scheme_table.json")
    assert set(cells) == {"LiBOB", "LiClO4", "LiPCP", "solvated"}
    assert all("corundum" in c["windows"] and "boehmite" not in c["windows"] for c in cells.values())
    assert set(cells["LiClO4"]["schemes"]) == {"janaf", "mp"}
