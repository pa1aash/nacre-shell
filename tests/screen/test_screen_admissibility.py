"""The admissibility rule in the screen (decision D27, gap table AM3); synthetic inputs only.

gamma_sl_insitu >= 0 must hold at every registered state for a draw to be admitted; refused draws
are counted, never clipped or floored; C3 and C4 use the admitted draws, the unrestricted verdict
is kept beside, and 1 - M_adm >= p_cred makes the link inconclusive (inadmissible inputs).
"""
from pathlib import Path

import numpy as np
import pytest

from nacre.physics import sequestration
from nacre.screen import admissibility, chain, params_adapter, run, study
from nacre.screen import decision as dc
from nacre.screen import thresholds as thr
from screen_helpers import P, synthetic_resolver

ROOT = Path(__file__).resolve().parents[2]
RULE = thr.load_thresholds(ROOT / thr.COPY)["rule"]
N = 64


def _x(**kw):
    return {k: np.full(N, float(v)) for k, v in kw.items()}


def _c3(f, n_nuc, sl):
    return {"f_theta": np.asarray(f, float), "N_nuc": np.asarray(n_nuc, float), "gamma_sl_insitu": np.asarray(sl, float)}


# ------------------------------------------------------------------ the mask over the states
def test_a_draw_is_admitted_only_if_every_state_admits_it():
    a = {"gamma_sl_insitu": np.array([0.1, -0.1, 0.2, np.nan, 0.0])}
    b = {"gamma_sl_insitu": np.array([0.1, 0.1, -0.2, 0.3, 0.0])}
    m = admissibility.mask({"slurry": a, "drying": b})
    assert m["coupled"]
    assert m["evaluable"].tolist() == [True, True, True, False, True]
    assert m["admitted"].tolist() == [True, False, False, False, True]      # zero is admitted (a non-negative energy)
    s = admissibility.summary({"slurry": a, "drying": b}, m, 0.9)
    assert s["M_adm"] == pytest.approx(2 / 4) and s["n_refused"] == 2 and not s["inadmissible_inputs"]
    assert s["by_state"]["slurry"]["M_adm"] == pytest.approx(3 / 4)


def test_refused_draws_are_excluded_never_clipped_and_the_inputs_are_untouched():
    sl = np.array([0.1, -0.1, 0.2, -0.3])
    st = {"s": _c3([0.2, 0.9, 0.2, 1.0], [20, 20, 20, 20], sl)}
    m = admissibility.mask(st)
    r = admissibility.restrict(st, m)
    assert np.isnan(r["s"]["f_theta"][[1, 3]]).all() and r["s"]["f_theta"][0] == 0.2
    assert st["s"]["f_theta"][1] == 0.9                                    # a copy, not an edit
    out = dc.evaluate_link(RULE, "C3", r, synthetic_resolver())
    assert out["tests"]["C3a"]["n_used"] == 2 and out["tests"]["C3a"]["P_good"] == 1.0


def test_inadmissible_inputs_make_the_link_inconclusive_with_the_restricted_verdict_beside():
    sl = np.r_[np.full(5, 0.1), np.full(95, -0.1)]                         # M_adm = 0.05: 1 - M_adm >= 0.9
    st = {"s": _c3(np.full(100, 0.2), np.full(100, 20.0), sl)}
    m = admissibility.mask(st)
    adm = admissibility.summary(st, m, P)
    assert adm["inadmissible_inputs"]
    r = dc.evaluate_link(RULE, "C3", admissibility.restrict(st, m), synthetic_resolver())
    u = dc.evaluate_link(RULE, "C3", st, synthetic_resolver())
    rec = admissibility.apply(r, u, adm)
    assert r["verdict"] == "feasible" and rec["verdict"] == "inconclusive" and rec["falsified_mass"] is None
    assert rec["admissibility"]["verdict_restricted"] == "feasible"
    assert rec["admissibility"]["verdict_unrestricted"] == u["verdict"]
    assert any("inadmissible inputs" in n for n in rec["notes"])


def test_the_threshold_moves_with_p_cred():
    sl = np.r_[np.full(30, 0.1), np.full(70, -0.1)]                        # 1 - M_adm = 0.7
    st = {"s": {"gamma_sl_insitu": sl}}
    m = admissibility.mask(st)
    assert admissibility.summary(st, m, 0.6)["inadmissible_inputs"]
    assert not admissibility.summary(st, m, 0.9)["inadmissible_inputs"]


def test_uncoupled_states_are_restricted_state_by_state():
    st = {"a": {"gamma_sl_insitu": np.array([0.1, -0.1])}, "b": {"gamma_sl_insitu": np.array([0.1, 0.1, -0.1])}}
    m = admissibility.mask(st)
    assert not m["coupled"]
    s = admissibility.summary(st, m, 0.9)
    assert s["M_adm"] == pytest.approx(0.5) and "state by state" in s["note"]


# ------------------------------------------------------------------ the chain under the rule
def _strong_binding_inputs(n=N, seed=5):
    rng = np.random.default_rng(seed)
    return {"gamma_sl0": rng.uniform(0.0, 0.05, n), "K_Ca_catecholate": 10 ** rng.uniform(1, 6, n),
            "Gamma_s": rng.uniform(1e-6, 1e-5, n), "delta_s": np.full(n, 1e-9), "T": np.full(n, 298.15),
            "pKa": np.full(n, 9.3), "pH": np.full(n, 12.0), "c_bulk": np.full(n, 1.0),
            "a_Ca": np.full(n, 1e-3), "a_CO3": np.full(n, 1e-3), "K_sp": np.full(n, 1e-8),
            "gamma_sn0": rng.uniform(0.0, 0.2, n), "Delta_gamma_w": np.zeros(n), "gamma_nl": np.full(n, 0.1),
            "V_m": np.full(n, 3.7e-5), "J0_het": np.full(n, 1e20), "t_proc": np.full(n, 100.0)}


def test_interface_stability_holds_on_every_admitted_draw_at_every_state():
    x1 = _strong_binding_inputs()
    x2 = dict(x1, T=np.full(N, 310.0), c_bulk=np.full(N, 0.1))          # a second state on the same draws
    o1, o2 = chain.evaluate(x1)[0], chain.evaluate(x2)[0]
    states = {"slurry": study.state_samples(o1), "drying": study.state_samples(o2)}
    m = admissibility.mask(states)
    assert 0 < m["admitted"].sum() < N                                  # the synthetic prior overshoots on part
    for s in (o1, o2):
        assert np.all(s["nucleate"]["gamma_sl_insitu"][m["admitted"]] >= 0)
    r = admissibility.restrict(states, m)
    for s in r.values():
        assert np.all(np.isnan(s["f_theta"][~m["admitted"]]))


def test_two_proton_cycle_is_used_when_pka2_is_bound():
    x = _x(K_Ca_catecholate=1e4, Gamma_s=5e-6, delta_s=1e-9, T=298.15, pKa=9.3, pH=12.0, c_bulk=2.0)
    one = chain.evaluate(dict(x), ["sequester"])[0]["sequester"]
    two = chain.evaluate(dict(x, pKa2=np.full(N, 12.5)), ["sequester"])[0]["sequester"]
    assert np.all(two["Delta_G_seq"] > one["Delta_G_seq"])              # the second proton costs free energy
    odds = sequestration.binding_odds(two["Delta_G_seq"], 298.15, 2.0, 5e-6, 1e-9)
    assert np.allclose(odds, sequestration.binding_odds_from_solution_constant(1e4, 2.0, 9.3, 12.5, 12.0), rtol=1e-10)


def test_admissibility_quantities_on_the_chain():
    x = _strong_binding_inputs()
    nuc = chain.evaluate(x)[0]["nucleate"]
    sl, floor, r = nuc["gamma_sl_insitu"], nuc["gamma_sl_floor"], nuc["r_ads"]
    assert np.all(floor <= sl + 1e-15)
    ok = x["gamma_sl0"] > 0
    assert np.allclose(sl[ok], x["gamma_sl0"][ok] * (1 - r[ok]), rtol=1e-9, atol=1e-15)
    q = chain.admissibility_quantities(np.array([0.02]), np.array([0.001]), np.array([500.0]), np.array([3e-6]),
                                       np.array([298.15]))
    assert q["gamma_sl_floor"][0] == 0.02                                 # Delta_G_seq >= 0 lowers nothing


def test_the_sensitivity_model_sees_only_admitted_draws():
    x = _strong_binding_inputs()
    full = chain.evaluate(dict(x), ["nucleate"])[0]
    keep = chain.admissible_mask(full)
    out = chain.sensitivity_model("nucleate", admissible=True)(dict(x))
    assert np.all(np.isnan(out["f_theta"][~keep])) and np.all(np.isfinite(out["f_theta"][keep]))
    assert np.isfinite(chain.sensitivity_model("nucleate")(dict(x))["f_theta"]).sum() == N


# ------------------------------------------------------------------ bindings and guards
def test_pka2_binds_the_table_key_recorded_under_pka():
    rp = params_adapter.regime_priors(ROOT / params_adapter.PRODUCTION_PARAMS, "R-slurry",
                                      bindings={"pKa": "pka_catechol", "pKa2": "pka2_catechol"}, absent="gap")
    assert {"pKa", "pKa2"} <= set(rp.joint.symbols)
    with pytest.raises(params_adapter.PriorFileError):
        params_adapter.regime_priors(ROOT / params_adapter.PRODUCTION_PARAMS, "R-slurry",
                                     bindings={"pH": "pka2_catechol"}, absent="gap")


def test_a_production_document_is_never_overwritten(tmp_path):
    out = ROOT / "results" / "preprint" / "screen" / "table" / "summary.json"
    assert out.exists()
    with pytest.raises(run.ProductionRefused, match="never overwritten"):
        run.production_guard(ROOT, [], out)


def test_the_rule_is_registered_in_the_config_and_the_gap_table():
    cfg = run.load_config(ROOT)
    assert cfg["registrations"]["admissibility"]["rule"] == "thresholds.decision.admissibility"
    assert RULE["decision"]["admissibility"]["condition"] == {"quantity": "gamma_sl_insitu", "comparator": ">=", "edge": "0"}
    import yaml
    gt = yaml.safe_load((ROOT / "configs" / "preprint" / "gap_resolution.yaml").read_text(encoding="utf-8"))
    am3 = [a for a in gt["amendments"] if a["id"] == "AM3"][0]
    assert am3["w3_admissibility_sha"] == "fd5846fd43d43e457566068f381a43ed96a8c1c3"


def test_sizing_reads_m_adm_and_skips_the_masses_of_inadmissible_inputs():
    sl = np.r_[np.full(5, 0.1), np.full(95, -0.1)]
    st = {"s": _c3(np.full(100, 0.2), np.full(100, 20.0), sl)}
    m = admissibility.mask(st)
    adm = admissibility.summary(st, m, P)
    assert adm["half_width"] == pytest.approx(2 * np.sqrt(0.05 * 0.95 / 100))
    r = dc.evaluate_link(RULE, "C3", admissibility.restrict(st, m), synthetic_resolver())
    rec = admissibility.apply(r, dc.evaluate_link(RULE, "C3", st, synthetic_resolver()), adm)
    assert study.max_half_width(rec) == pytest.approx(adm["half_width"])
    assert rec["tests"]["C3a"]["half_width_unsized"] is not None and "half_width" not in rec["tests"]["C3a"]


def test_an_inadmissible_headline_record_validates_against_the_schema():
    import jsonschema
    from nacre.screen import summary
    sl = np.r_[np.full(5, 0.1), np.full(95, -0.1)]
    st = {"s": _c3(np.full(100, 0.2), np.full(100, 20.0), sl)}
    m = admissibility.mask(st)
    adm = admissibility.summary(st, m, P)
    r = dc.evaluate_link(RULE, "C3", admissibility.restrict(st, m), synthetic_resolver())
    rec = dc.public(admissibility.apply(r, dc.evaluate_link(RULE, "C3", st, synthetic_resolver()), adm))
    schema = summary.load_schema()
    jsonschema.validate(rec, dict(schema["$defs"]["claim"], **{"$defs": schema["$defs"]}))
