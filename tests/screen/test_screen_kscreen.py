"""K1 to K4 for solid-like nuclei, the framing rule, the admissibility restriction and the deletion test (PH-W4.1);
the cp4 F1 proceed rule and the v2 ladder layout (PH-W4.2a)."""
import numpy as np
import pytest

from nacre.screen import gaps, kscreen, routes
from nacre.screen.mineral import Mineral
from nacre.screen.run import load_config

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
N = 4000
P = dict(p_cred=0.9, p_deg=0.1, m_cos=0.0, m_S=0.0, admissible=True)


def _sample(omega=10.0, het=2.0, hom=20.0, b=8.0, cos=0.5, spread=1.0, n_nuc=1e20, sl=1.0, n=N):
    full = lambda v: np.full(n, float(v))
    return {"Omega_bulk": full(omega), "barrier_het_template_kT": full(het), "barrier_hom_bulk_kT": full(hom),
            "B_acc_kT": full(b), "cos_theta": full(cos), "S_spread": full(spread), "N_nuc": full(n_nuc),
            "gamma_sl_insitu": full(sl)}


def _doses(**kw):
    return {0.0: {"slurry": _sample(**kw)}}


# ------------------------------------------------------------------ K1 reader
def _ladder(tmp_path, rows):
    head = "phase,role,class,cutoff_inf_V,cutoff_sup_V,tier1_onset_V,status,note\n"
    path = tmp_path / "ladder.csv"
    path.write_text("# comment\n" + head + "".join(rows), encoding="utf-8")
    return path


def test_k1_reader_reads_the_committed_ladder_without_recomputing():
    t = kscreen.read_k1(ROOT / kscreen.LADDER_V1)
    assert "HAp" in t.phases() and "CaCO3" in t.phases()
    v = t.verdicts("HAp", "crystalline")
    assert v["4.2-4.3 V"] == "falsified" and v["LFP-class"] == "inconclusive"     # upper bound: not a pass
    assert t.passing_classes("HAp", "crystalline") == []
    br = t.row("HAp", "LFP-class", "crystalline").bracket()                        # v1: the solid-salt onset is E_ub
    assert br["E_ub"] == pytest.approx(4.0674) and br["E_lb"] is None and br["E_lb_status"] == "pending"
    assert t.row("HAp", "LFP-class", "crystalline").stage == "cell"
    assert t.low_cutoff_class("HAp") == "LFP-class"


def test_k1_reads_the_v2_layout_framing_stage_and_bracket(tmp_path):
    head = "phase,class,cutoff_inf_V,framing,stage,E_ub_V,E_lb_V,status,note\n"
    p = tmp_path / "v2.csv"
    p.write_text(head + "Ca(PO3)2,C_lo,3.6,amorphous,cell,4.1,3.9,within,x\n"
                 "Ca(PO3)2,C_lo,3.6,crystalline,cell,4.6,,above,upper bound only\n", encoding="utf-8")
    t = kscreen.read_k1(p)
    am = t.row("Ca(PO3)2", "C_lo", "amorphous").bracket()
    assert (am["E_ub"], am["E_lb"], am["E_lb_status"]) == (4.1, 3.9, "sourced")
    cr = t.row("Ca(PO3)2", "C_lo", "crystalline").bracket()
    assert cr["E_lb"] is None and cr["E_lb_status"] == "pending"
    p.write_text(head + "X,C,1,crystalline,kiln,1,1,above,x\n", encoding="utf-8")
    with pytest.raises(kscreen.K1Error):
        kscreen.read_k1(p)


def test_k1_reads_a_verdict_column_as_written(tmp_path):
    p = tmp_path / "v.csv"
    p.write_text("phase,class,status,note,k1_verdict\nX,C1,above,x,not excluded (class A)\nX,C2,below,x,falsified at E_c\n",
                 encoding="utf-8")
    t = kscreen.read_k1(p)
    assert t.verdicts("X", "crystalline") == {"C1": "not excluded", "C2": "falsified"}
    p.write_text("phase,class,status,note,k1_verdict\nX,C1,above,x,maybe\n", encoding="utf-8")
    with pytest.raises(kscreen.K1Error):
        kscreen.read_k1(p)


def test_k1_accepts_two_rows_per_phase_one_per_framing(tmp_path):
    head = "phase,role,class,cutoff_inf_V,cutoff_sup_V,tier1_onset_V,framing,status,note\n"
    p = tmp_path / "l.csv"
    p.write_text(head + "HAp,candidate,C1,1,1,4.5,crystalline,above,sink solvated\n"
                 "HAp,candidate,C1,1,1,3.0,amorphous,below,tier 1\n", encoding="utf-8")
    t = kscreen.read_k1(p)
    assert t.verdicts("HAp", "crystalline") == {"C1": "feasible"} and t.verdicts("HAp", "amorphous") == {"C1": "falsified"}
    assert t.framings("HAp") == ["amorphous", "crystalline"]


def test_k1_refuses_a_third_row_or_a_duplicate_framing(tmp_path):
    rows = ["HAp,c,C1,1,1,4,above,x\n", "HAp,c,C1,1,1,4,below,x\n"]
    with pytest.raises(kscreen.K1Error):
        kscreen.read_k1(_ladder(tmp_path, rows))                        # two rows, same (default) framing
    head = "phase,role,class,cutoff_inf_V,cutoff_sup_V,tier1_onset_V,framing,status,note\n"
    p = tmp_path / "bad.csv"
    p.write_text(head + "HAp,c,C1,1,1,4,glassy,above,x\n", encoding="utf-8")
    with pytest.raises(kscreen.K1Error):
        kscreen.read_k1(p)


@pytest.mark.parametrize("status,note,expected", [("below", "", "falsified"), ("above", "upper bound only", "inconclusive"),
                                                  ("above", "solvated sink", "feasible"), ("within budget", "", "inconclusive"),
                                                  ("undetermined", "", "undetermined")])
def test_k1_verdict_mapping(status, note, expected):
    assert kscreen.k1_verdict(status, note) == expected


def test_f1_proceeds_unless_falsified_at_every_class():
    """cp4 F1 (claims_redirect.md 2d): proceeding is not passing; K1 keeps its verdict."""
    every = {"by_class": {"C_lo": "falsified", "C_mid": "falsified", "C_hi": "falsified"}}
    g = kscreen.proceeds(every)
    assert not g["proceeds"] and g["k1_status"] == every["by_class"]
    for v in ("inconclusive", "undetermined", "feasible", "not excluded"):
        g = kscreen.proceeds({"by_class": {"C_lo": v, "C_mid": "falsified", "C_hi": "falsified"}})
        assert g["proceeds"] and g["classes"] == ["C_lo"] and g["k1_status"]["C_mid"] == "falsified"
    forced = kscreen.proceeds(every, override=True)
    assert forced["proceeds"] and forced["overridden"]
    none = kscreen.proceeds({"by_class": {}})
    assert none["proceeds"] and "undetermined" in none["note"]


# ------------------------------------------------------------------ K2
def test_k2_feasible_falsified_and_inconclusive():
    assert kscreen.k2(_doses(omega=5.0), 0.9)["verdict"] == "feasible"
    assert kscreen.k2(_doses(omega=0.5), 0.9)["verdict"] == "falsified"
    mixed = _doses(omega=2.0)
    mixed[0.0]["slurry"]["Omega_bulk"][: N // 2] = 0.5
    assert kscreen.k2(mixed, 0.9)["verdict"] == "inconclusive"


def test_k2_worst_state_a_falsification_stands():
    doses = {0.0: {"slurry": _sample(omega=5.0), "drying": _sample(omega=0.5)}}
    r = kscreen.k2(doses, 0.9)
    assert r["verdict"] == "falsified"


def test_k2_controls_must_come_out_as_they_must():
    ok = kscreen.k2(_doses(omega=5.0), 0.9, {"undersaturated": np.full(N, 0.1), "supersaturated": np.full(N, 9.0)})
    assert ok["verdict"] == "feasible"
    bad = kscreen.k2(_doses(omega=5.0), 0.9, {"undersaturated": np.full(N, 3.0), "supersaturated": np.full(N, 9.0)})
    assert bad["verdict"] == "inconclusive"


# ------------------------------------------------------------------ K3
def test_k3_window_needs_het_below_and_hom_above_the_criterion():
    r = kscreen.k3(_doses(het=2.0, hom=20.0, b=8.0), 0.9, 0.0)
    assert r["verdict"] == "feasible" and r["window"] == [0.0]
    assert kscreen.k3(_doses(het=12.0, hom=20.0, b=8.0), 0.9, 0.0)["verdict"] == "falsified"      # het misses
    assert kscreen.k3(_doses(het=2.0, hom=5.0, b=8.0), 0.9, 0.0)["verdict"] == "falsified"        # bulk takes over
    assert kscreen.k3(_doses(omega=0.8, het=np.nan, hom=np.nan), 0.9, 0.0)["verdict"] == "falsified"   # no supersaturation


def test_k3_states_the_dose_where_bulk_precipitation_takes_over():
    doses = {-1.0: {"slurry": _sample(het=2.0, hom=20.0)}, 1.0: {"slurry": _sample(het=1.0, hom=4.0)}}
    r = kscreen.k3(doses, 0.9, 0.0)
    assert r["window"] == [-1.0] and r["bulk_precipitation_takes_over_at"] == 1.0
    assert "competing_phases" in r


def test_k3_c3a_edge_follows_the_margin():
    s = _doses(cos=0.1)
    assert kscreen.k3(s, 0.9, 0.0)["verdict"] == "feasible"
    assert kscreen.k3(s, 0.9, 0.2)["verdict"] == "falsified"


def test_k3_reports_competing_phases_inside_the_window():
    r = kscreen.k3(_doses(), 0.9, 0.0, competing={"Li3PO4": {0.0: np.full(N, 3.0)}})
    assert r["competing_phases"]["Li3PO4"]["0.0"] == 1.0


# ------------------------------------------------------------------ K4
def test_k4_spread_route_closure_route_and_both_fail():
    assert kscreen.k4(_doses(spread=1.0, n_nuc=0.0), 0.9, 0.0, 1e-8)["verdict"] == "feasible"
    closure = kscreen.k4(_doses(spread=-1.0, n_nuc=1e22, cos=0.0), 0.9, 0.0, 1e-8)
    assert closure["verdict"] == "feasible" and closure["route"] == "closure only (optimistic)"
    assert kscreen.k4(_doses(spread=-1.0, n_nuc=0.0, cos=0.0), 0.9, 0.0, 1e-8)["verdict"] == "falsified"


def test_k4_cannot_falsify_without_the_thickness_bound():
    r = kscreen.k4(_doses(spread=-1.0, n_nuc=0.0), 0.9, 0.0, None)
    assert r["verdict"] == "inconclusive"
    assert any("closure route not evaluated" in n for p in r["points"].values() for s in p["by_state"].values() for n in s["notes"])


def test_closure_edge_matches_the_contract_function():
    from nacre.physics import conformality
    theta = np.array([0.4, 1.2, 2.5])
    assert np.allclose(kscreen.closure_edge(np.cos(theta), 3e-9), conformality.closure_island_density(theta, 3e-9), rtol=1e-12)
    assert kscreen.closure_edge(1.0, 1e-8) == 0.0 and kscreen.closure_edge(-1.0, 1e-8) > 1e30


# ------------------------------------------------------------------ admissibility, deletion test, framing rule
def test_admissibility_restricts_k3_and_prints_the_retained_mass():
    s = _sample()
    s["gamma_sl_insitu"][: N // 4] = -0.1                 # 25 % of the draws are inadmissible
    r = kscreen.k3({0.0: {"slurry": s}}, 0.9, 0.0)
    adm = r["admissibility"]["0.0"]
    assert adm["M_adm"] == pytest.approx(0.75, abs=1e-12) and adm["n_refused"] == N // 4
    assert r["verdict"] == "feasible"                      # on the admitted draws; 1 - M_adm = 0.25 < p_cred


def test_inadmissible_inputs_make_the_verdict_inconclusive():
    s = _sample()
    s["gamma_sl_insitu"][: int(0.95 * N)] = -0.1
    r = kscreen.k3({0.0: {"slurry": s}}, 0.9, 0.0)
    assert r["verdict"] == "inconclusive"
    assert r["points"]["0.0"]["verdict_restricted"] == "feasible"
    assert r["points"]["0.0"]["unrestricted_verdict"] == "feasible"            # the same draws without the restriction


def test_deletion_test_labels_a_pass_that_does_not_degrade_generic():
    tm = {"K3": {"verdict": "feasible", "falsified_mass": 0.0}, "K4": {"verdict": "feasible", "falsified_mass": 0.0}}
    same = {"K3": {"verdict": "feasible", "falsified_mass": 0.0}, "K4": {"verdict": "feasible", "falsified_mass": 0.0}}
    r = kscreen.deletion_test(tm, same, 0.1)
    assert not r["holds"] and r["per"]["K3"]["label"] == "generic" and r["per"]["K4"]["label"] == "generic"
    worse = {"K3": {"verdict": "falsified", "falsified_mass": 0.95}, "K4": {"verdict": "feasible", "falsified_mass": 0.0}}
    r = kscreen.deletion_test(tm, worse, 0.1)
    assert r["holds"] and r["degraded"] == ["K3"] and r["per"]["K3"]["label"] == "template-specific"
    assert r["per"]["K4"]["label"] == "generic"


def test_deletion_test_counts_a_rise_in_the_falsified_mass():
    tm = {"K3": {"verdict": "inconclusive", "falsified_mass": 0.2}, "K4": {"verdict": "inconclusive", "falsified_mass": 0.1}}
    ct = {"K3": {"verdict": "inconclusive", "falsified_mass": 0.35}, "K4": {"verdict": "inconclusive", "falsified_mass": 0.1}}
    r = kscreen.deletion_test(tm, ct, 0.1)
    assert r["degraded"] == ["K3"]


def test_framing_rule_falsified_only_under_every_framing():
    both = kscreen.framing_rule({"apatite": "falsified", "ACP": "falsified"})
    assert both["verdict"] == "falsified"
    one = kscreen.framing_rule({"apatite": "falsified", "ACP": "feasible"})
    assert one["verdict"] == "feasible" and one["governing_framing"] == "ACP"
    assert kscreen.framing_rule({"apatite": "falsified", "ACP": "inconclusive"})["verdict"] == "inconclusive"


# ------------------------------------------------------------------ the phase record and the route extension points
def _mineral(**kw):
    base = dict(name="hap", formula_unit="x", nu_ca=5, nu_x=3, nu_y=1, ksp_key="k", vm_key="v", framing="apatite", k1_phase="HAp")
    base.update(kw)
    return Mineral(**base)


def test_evaluate_mineral_runs_k3_k4_unless_k1_is_falsified_at_every_class(tmp_path):
    t = kscreen.read_k1(ROOT / kscreen.LADDER_V1)            # HAp: inconclusive at the LFP class, falsified above
    rec = kscreen.evaluate_mineral(_mineral(), t, _doses(), P, control_doses=_doses(het=30.0, hom=40.0, b=8.0), d_max=1e-8)
    assert rec["gate"]["proceeds"] and not rec["gate"]["overridden"] and rec["K3"]["verdict"] == "feasible"
    assert rec["K1"]["by_class"]["4.2-4.3 V"] == "falsified"                    # proceeding is not passing
    assert rec["deletion_test"]["holds"] and rec["deletion_test"]["per"]["K3"]["label"] == "template-specific"
    p = tmp_path / "all.csv"
    p.write_text("phase,class,status,note\nHAp,C1,below,x\nHAp,C2,below,x\n", encoding="utf-8")
    rec = kscreen.evaluate_mineral(_mineral(), kscreen.read_k1(p), _doses(), P)
    assert rec["K3"]["verdict"] == "not run" and rec["K4"]["verdict"] == "not run" and rec["provisional"] is True


def test_liquid_precursor_is_left_to_the_route_evaluator():
    t = kscreen.read_k1(ROOT / kscreen.LADDER_V1)
    rec = kscreen.evaluate_mineral(_mineral(phase_state="liquid_precursor"), t, _doses(), P)
    assert rec["K3"]["verdict"] == "not applicable" and "liquid_precursor_wetting" in rec["route_evaluators"]


def test_route_extension_points_are_implemented():
    assert set(routes.NAMES) == set(routes.ROUTE_EVALUATORS)
    for name, fn in routes.ROUTE_EVALUATORS.items():
        assert fn.__doc__ and len(fn.__doc__) > 80, name
    r = routes.ROUTE_EVALUATORS["hydrolysis_descriptor"]({"pH": 7.0, "T": 298.0, "pit": True}, [], (1, 1), 1.0, 0.9, 5.0)
    assert r["row"] == "H1"
    assert routes.ROUTE_EVALUATORS["formation_accessibility"]("R3", 0.9)["verdict"] == "not applicable"
    assert routes.ROUTE_EVALUATORS["liquid_precursor_wetting"](0.9, 0.0)["verdict"] == "undetermined"


def test_pending_extension_points_follow_the_mineral():
    assert routes.pending_for(_mineral()) == []
    assert routes.pending_for(_mineral(chain_length_n=8, speciation=None)) == ["formation_accessibility", "hydrolysis_descriptor"]
    assert routes.pending_for(_mineral(phase_state="liquid_precursor")) == ["liquid_precursor_wetting", "formation_accessibility"]


# ------------------------------------------------------------------ configuration and the phosphate gap skeleton
def test_k_screen_block_is_provisional():
    cfg = load_config(ROOT)
    k = kscreen.k_config(cfg)
    assert k["provisional"] is True
    with pytest.raises(kscreen.KConfigError):
        kscreen.k_config({"k_screen": dict(k, provisional=False)})
    with pytest.raises(kscreen.KConfigError):
        kscreen.k_config({})


def test_gap_skeleton_fills_only_registered_treatments():
    t = gaps.load_ph(ROOT / gaps.PH_TABLE)
    assert gaps.check_ph(t) == []
    assert t["status"] == "skeleton" and t["written_before_production_output"] is True
    wait = gaps.awaiting(t)
    assert wait and all(p.split(".")[0] in {"keys", "speciation", "margins", "ladder", "design_axes", "inputs_with_rule",
                                                     "route_layer"} for p in wait)
    rules = dict(gaps.treatments_ph(t))
    assert rules["inputs_with_rule.gamma_sn0_phosphate"] == "ignorance"
    assert rules["inputs_with_rule.competing_phases"] == "unresolved"
    assert rules["design_axes.p_total_slurry"] == "design_axis"
    assert rules["keys.log10_ksp_hap"] == gaps.PENDING
    assert rules["route_layer.r1.polyp_log10_ksp_al"] == "unresolved"            # F1r
    assert rules["route_layer.r2.coacervate_binodal_map"] == "unresolved"        # B1
    assert rules["route_layer.hydrolysis.hydrolysis_f_min"] == gaps.PENDING     # PH-W3.2 sets the number
    assert set(t["route_layer"]["evaluators"]) == set(routes.NAMES)


def test_gap_skeleton_names_match_claims_redirect_section_7():
    t = gaps.load_ph(ROOT / gaps.PH_TABLE)
    names = set(t["keys"]) | set(t["speciation"]) | set(t["ladder"]) | set(t["design_axes"])
    for p in ("hap", "acp", "ocp", "btcp", "capp", "cameta"):
        for stem in ("log10_ksp_", "v_m_", "gamma_nl_", "gamma_nv_"):
            assert stem + p in names
    for k in ("pka1_h3po4", "pka2_h3po4", "pka3_h3po4", "log10_k_cahpo4_aq", "log10_k_cah2po4", "log10_k_capo4", "pkw",
              "p_total_slurry", "ph_slurry_acid_adjusted", "al_passivation_window", "acp_hydration_n", "dv_film",
              "j_corr_max", "t_max_corr", "s_tol"):
        assert k in names, k
    for F in ("alpo4", "al_pmeta3", "al_borate", "al_oxalate", "al2o3"):
        assert "log10_ksp_el_" + F in names and "sigma_corr_" + F in names and "rho_film_" + F in names
