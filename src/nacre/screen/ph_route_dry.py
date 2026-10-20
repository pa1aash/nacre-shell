"""Dry runs of the route layer (PH-W4.2a): R1, R2, R3 and one baseline row, on mock priors, through the route
evaluators (nacre.screen.routes) and the stage rows (nacre.screen.ph_rows), to the results schema v5.

    python -m nacre.screen ph-route-dryrun --route R1|R2|R3|baseline --mock [--draws N]

A dry run shows that the code path runs end to end and that its document validates. It reads the mock route table
(configs/preprint/mock_params_ph_routes.yaml) and a K1 ladder in the v2 layout (default: the mock ladder
configs/preprint/mock_k1_ladder_v2.csv; W5's results/preprint/pourbaix/ph_w51/ladder_v2.csv is the production input,
named in screen.yaml k_screen.k1_ladder), and writes only under results/preprint/screen/dryrun_ph/. It is never
reported, tunes nothing and registers nothing. The bindings below are those of the mock table; the production
bindings to lit/params.yaml keys are registered at the cp5 freeze.
"""
import time
from pathlib import Path

import numpy as np


from nacre.physics import film, gelation
from nacre.physics import supersaturation as sat
from nacre.screen import decision, kscreen, params_adapter, ph_rows, routes, run, summary
from nacre.screen import mineral as mineral_mod
from nacre.screen.ph_dry import DryRunRefused, peak_mb

ROUTE_TABLE = Path("configs") / "preprint" / "mock_params_ph_routes.yaml"
MOCK_LADDER = kscreen.MOCK_LADDER
DEFAULT_DRAWS = 2 ** 13
CLASSES = ("R1", "R2", "R3", "baseline")

#: {symbol: key} of the mock route table per route (mock-only bindings).
COMMON = {"T": "temperature", "a_w": "water_activity", "R_A_max": "ra_max_mock", "rho_e": "rho_e_mock"}
R1_BIND = {**COMMON, "K_ox_Al": "polyp_al_log_k_oxide", "a_Al": "polyp_al_activity_pit",
           "a_PP_tot": "polyp_activity_total_mock", "beta_AlPP": "polyp_al_log_beta1_linear",
           "nu_Al": "polyp_nu_al_mock", "nu_PP": "polyp_nu_pp_mock", "K_sp_AlPP": "polyp_log10_ksp_al"}
CA_BIND = {**COMMON, "a_Ca": "ca_activity_mock", "a_X": "po3_activity_mock", "K_sp": "polyp_log10_ksp_cameta",
           "Delta_G_gc": "glass_crystal_correction_cameta", "P_T": "p_total_mock",
           "I_ionic": "ionic_strength_mock"}
WET_BIND = {"gamma_al_l0": "coacervate_gamma_s0_dilute", "gamma_al_n0": "coacervate_gamma_s0_dense",
            "gamma_nl_c": "coacervate_gamma_nl", "Gamma_P": "polyp_ads_alumina_gamma_max",
            "K_P": "polyp_ads_alumina_k_langmuir", "delta_P": "polyp_ads_alumina_layer_thickness",
            "a_P": "polyp_chain_activity_mock", "Pi_osm": "osmotic_pressure_mock"}
HYDROLYSIS_ROWS = ("hydrolysis_polyp_k_ph6", "hydrolysis_polyp_k_ph6_ca1mm", "hydrolysis_polyp_k_ph8",
                   "hydrolysis_polyp_k_ph8_ca1mm")
#: Ca(PO3)2 formula unit (contract v5 stoichiometry), the product of R2 and R3.
CAMETA = {"nu_Ca": 1.0, "nu_X": 2.0, "nu_Y": 0.0, "n_hyd": 0.0}
#: Film ids and K1 phases of the dry-run rows.
FILMS = {"R1": ("r1_alpp_gel", "Al(PO3)3"), "R2": ("r2_capoly_glass", "Ca(PO3)2"),
         "R3": ("r3_capoly_glass", "Ca(PO3)2"), "baseline": ("baseline_tsinghua", "AlPO4")}


# ------------------------------------------------------------------ table access
def support(entry):
    """(lo, hi) of a table entry's prior: a fixed value twice, the bounds of a uniform or loguniform; else None."""
    if not entry:
        return None
    pr = entry.get("prior") or {}
    fam = pr.get("family")
    if fam == "fixed":
        return float(pr["value"]), float(pr["value"])
    if fam in ("uniform", "loguniform"):
        return float(pr["low"]), float(pr["high"])
    return None


def value(entry):
    s = support(entry)
    return s[0] if s and s[0] == s[1] else None


def draws(path, bindings, n, seed):
    """{symbol: (n,) array} of the bound keys (common random numbers by seed); unsampled symbols map to None."""
    rp = params_adapter.regime_priors(path, "R-slurry", allow_mock=True, bindings=bindings, absent="gap")
    xs = rp.joint.sample(np.random.default_rng(seed), n)
    out = {p.symbol: xs[:, j] for j, p in enumerate(rp.joint.priors)}
    for sym in rp.unsampled:
        out[sym] = None
    return out, rp


def grades(doc, keys):
    return {k: routes.grade_of(doc["params"].get(k), mock=bool(doc["mock"])) if k in doc["params"] else "gap"
            for k in keys}


def hydrolysis_inputs(doc, route):
    p = doc["params"]
    rows = []
    t_data = value(p.get("hydrolysis_data_temperature"))
    for k in HYDROLYSIS_ROWS:
        e = p.get(k)
        s = support(e)
        if e is None or s is None or t_data is None:
            continue
        c = e.get("conditions") or {}
        rows.append({"key": k, "pH": c["pH"], "ca_mM": c["ca_mM"], "T": t_data, "k": s})
    keys = list(HYDROLYSIS_ROWS) + ["hydrolysis_transfer_factor", "hydrolysis_t_wet_%s" % route.lower(),
                                    "hydrolysis_f_min", "hydrolysis_temperature_tolerance", "hydrolysis_data_temperature"]
    return {"rows": rows, "tau": support(p.get("hydrolysis_transfer_factor")),
            "t_wet": value(p.get("hydrolysis_t_wet_%s" % route.lower())), "f_min": value(p.get("hydrolysis_f_min")),
            "t_tol": value(p.get("hydrolysis_temperature_tolerance")), "grades": grades(doc, keys)}


# ------------------------------------------------------------------ K tests on draws
def k2_omega(omega, p_cred, framing, evidence, label):
    m = decision.mass_of(decision.indicator(omega, ">=", 1.0))
    return {"test": "K2", "verdict": decision.verdict_from_mass(m["P_good"], p_cred), "P_good": m["P_good"],
            "P_bad": m["P_bad"], "n_used": m["n_used"], "framing": framing, "edge": "Omega >= 1",
            "evidence": evidence, "label": label}


def d_max_of(x):
    r, rho = x.get("R_A_max"), x.get("rho_e")
    if r is None or rho is None:
        return None
    return float(np.max(film.ohmic_thickness_bound(r, rho)))


def k4_descriptor(route, d_max):
    return {"test": "K4", "verdict": "undetermined", "evidence": {},
            "note": "no K4 route form is registered for %s; the insulating bound d_max is reported as a descriptor"
                    % route, "d_max": d_max}


def over_states(per, key):
    vs = {i: r[key]["verdict"] for i, r in enumerate(per) if r.get(key) is not None}
    o = decision.over_design(vs)
    return o


def _state_label(s):
    return "pH %g, Ca %g mM%s" % (s["pH"], s.get("ca_mM", 0.0), ", drying" if s.get("drying") else "")


# ------------------------------------------------------------------ one route
def route_rows(root, route, doc, path, ladder, k, n, seed):
    p_cred = float(k["p_cred"])
    film_id, phase = FILMS[route]
    states = (doc.get("design") or {}).get(route) or []
    if not states:
        raise DryRunRefused("the mock table has no design states for %s" % route)
    hyd = hydrolysis_inputs(doc, route)
    bind = R1_BIND if route == "R1" else {**CA_BIND, **(WET_BIND if route == "R2" else {})}
    x, rp = draws(path, bind, n, seed)
    ev = grades(doc, list(bind.values()))
    if (doc.get("maps") or {}).get("coacervate_binodal_map"):
        ev["coacervate_binodal_map"] = "mock" if doc["mock"] else "sourced"
    per = []
    for s in states:
        st = dict(s, T=float(np.median(x["T"])))
        rec = {"state": _state_label(s)}
        rec["K2h"] = routes.hydrolysis_descriptor(st, hyd["rows"], hyd["tau"], hyd["t_wet"], hyd["f_min"], hyd["t_tol"],
                                                  grades=hyd["grades"], route=route)
        if route == "R1":
            a_ox = gelation.aluminium_activity_oxide_equilibrium(x["K_ox_Al"], s["pH"], x["a_w"])
            common = {"a_PP_tot": x["a_PP_tot"], "nu_Al": x["nu_Al"], "nu_PP": x["nu_PP"],
                      "K_sp_AlPP": x["K_sp_AlPP"], "beta_AlPP": x["beta_AlPP"]}
            rec["K3"] = routes.formation_accessibility(
                "R1", p_cred, grades=ev, r1={"states": {"oxide-equilibrium": dict(common, a_Al=a_ox),
                                                        "pit-state": dict(common, a_Al=x["a_Al"])}})
            a_pp = gelation.free_chain_unit_activity(x["a_PP_tot"], 0.0 if x["beta_AlPP"] is None else x["beta_AlPP"], a_ox)
            om = gelation.saturation_ratio_alpp(a_ox, a_pp, x["nu_Al"], x["nu_PP"], x["K_sp_AlPP"])
            rec["K2"] = k2_omega(om, p_cred, "amorphous", {"polyp_log10_ksp_al": ev["polyp_log10_ksp_al"]},
                                 "gel K_sp (amorphous product) at the oxide-equilibrium state")
            rec["K4"] = k4_descriptor("R1", d_max_of(x))
        else:
            args = (x["a_Ca"], x["a_X"], 1.0, CAMETA["nu_Ca"], CAMETA["nu_X"], CAMETA["nu_Y"], x["a_w"],
                    CAMETA["n_hyd"], x["K_sp"])
            om_c = sat.saturation_ratio_mineral(*args)
            om_g = sat.saturation_ratio_glass(*args, x["Delta_G_gc"], x["T"])
            k2g = k2_omega(om_g, p_cred, "amorphous", {k_: ev[k_] for k_ in ("polyp_log10_ksp_cameta", "glass_crystal_correction_cameta")},
                           "Omega_glass (governing framing)")
            k2c = k2_omega(om_c, p_cred, "crystalline", {"polyp_log10_ksp_cameta": ev["polyp_log10_ksp_cameta"]},
                           "Omega_nu (optimistic upper reference)")
            rec["K2"] = dict(k2g, framings=routes.route_framing(k2c["verdict"], k2g["verdict"]))
            if route == "R2":
                rec["K3"] = routes.formation_accessibility(
                    "R2", p_cred, grades=ev, r2={"state": {"Ca_T": np.full(n, float(s.get("ca_mM", 0.0))), "P_T": x["P_T"],
                                                           "I_ionic": x["I_ionic"],
                                                           "pH": s["pH"]},
                                                 "map": (doc.get("maps") or {}).get("coacervate_binodal_map")})
                site = {q: x[q] for q in ("T", "Gamma_P", "K_P", "a_P", "delta_P", "Pi_osm")}
                if rec["K3"]["row"] == "B2":
                    rec["K4"] = {"test": "K4", "verdict": "not run", "evidence": {},
                                 "note": "no liquid precursor at this state (B2): the K4 route form does not apply"}
                else:
                    rec["K4"] = routes.liquid_precursor_wetting(p_cred, float(k["m_S"]), x["gamma_al_l0"],
                                                                x["gamma_al_n0"], x["gamma_nl_c"], site=site, grades=ev)
            else:
                rec["K3"] = routes.formation_accessibility("R3", p_cred)
                rec["K4"] = k4_descriptor("R3", d_max_of(x))
        per.append(rec)
    m = _mineral(phase)
    k1 = {f: kscreen.k1_for(ladder, m, framing=f) for f in kscreen.FRAMINGS}
    cell = ph_rows.k1_cell_row(film_id, phase, k1, "route", route=route)
    row_k = {}
    for key in ("K2", "K2h", "K3", "K4"):
        o = over_states(per, key)
        row_k[key] = {"verdict": o["verdict"], "design_dependent": o["design_dependent"],
                      "evidence": _merge_evidence(per, key), "by_state": {r["state"]: decision.public(r[key]) for r in per}}
    gated = [r["state"] for r in per if r["K2h"]["gates"]]
    if gated:
        row_k["K2h"]["gates_at"] = gated
    adm = [r["K4"].get("retained_mass") for r in per if r["K4"].get("retained_mass")]
    slurry = ph_rows.slurry_row(film_id, phase, "route", "amorphous", row_k["K2"], row_k["K3"], row_k["K4"],
                                K2h=row_k["K2h"], route=route, gate=cell["proceeds"],
                                retained_mass=min(adm, key=lambda a: a["M_adm"]) if adm else None,
                                labels=[routes.KINETIC_HYPOTHESIS] if route == "R1" else [])
    return [slurry, cell], rp


def _merge_evidence(per, key):
    out = {}
    for r in per:
        out.update((r.get(key) or {}).get("evidence") or {})
    return out


def _mineral(phase):
    return mineral_mod.Mineral(phase, phase, 1, 1, "unused", "unused", phase, x_symbol="a_X", k1_phase=phase,
                               phase_state="amorphous")


def baseline(doc, path, ladder, k, n, seed):
    film_id, phase = FILMS["baseline"]
    x, rp = draws(path, COMMON, n, seed)
    p = doc["params"]
    k2 = routes.baseline_k2("Tsinghua/Hon Hai baked aluminophosphate (US 8,252,463; US 8,821,969)")
    key = "matrix_baseline_tsinghua_film_thickness"
    k4 = ph_rows.baseline_k4(value(p.get(key)), d_max_of(x), routes.grade_of(p.get(key), mock=bool(doc["mock"])))
    m = _mineral(phase)
    k1 = {f: kscreen.k1_for(ladder, m, framing=f) for f in kscreen.FRAMINGS}
    return ph_rows.baseline_rows(film_id, "Tsinghua/Hon Hai", phase, k1, k2, k4), rp


# ------------------------------------------------------------------ driver
def run_route(root, cls, out_path, params_path=None, ladder_path=None, allow_mock=False, draws_n=DEFAULT_DRAWS, seed=None):
    """One route-layer dry run: returns (path, document, stats)."""
    t0 = time.perf_counter()
    root, out_path = Path(root), Path(out_path)
    if cls not in CLASSES:
        raise DryRunRefused("route class must be one of %s, got %r" % (CLASSES, cls))
    if not run._inside(out_path, root / run.DRYRUN_PH_DIR):
        raise DryRunRefused("a route dry run writes only under %s, got %s" % (run.DRYRUN_PH_DIR, out_path))
    path = Path(params_path) if params_path else root / ROUTE_TABLE
    doc, _ = params_adapter.read_table(path, allow_mock)
    if not doc["mock"]:
        raise DryRunRefused("a route dry run reads a mock table only")
    cfg_path = root / run.CONFIG
    cfg = run.load_config(root)
    k = kscreen.k_config(cfg)
    ladder = kscreen.read_k1(root / (ladder_path or MOCK_LADDER))
    seed = int(seed if seed is not None else cfg["propagation"]["seed"])
    if cls == "baseline":
        rows, rp = baseline(doc, path, ladder, k, draws_n, seed)
    else:
        rows, rp = route_rows(root, cls, doc, path, ladder, k, draws_n, seed)
    problems = ph_rows.check_presentation(rows)
    if problems:
        raise DryRunRefused("presentation rule: %s" % problems)
    prov = run._provenance(root, cfg, cfg_path, [rp], run.THRESHOLDS, True)
    prov["run_label"] = "ph-route-dryrun %s" % cls
    prov["session"] = "PH-W4.2a"
    meta = {"route_class": cls, "mock_table": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            "k1_ladder": str(ladder.path), "draws": int(draws_n), "seed": seed,
            "thresholds_structure": routes.thresholds_ph(k),
            "note": "path check on mock priors; never reported; tunes nothing"}
    document = summary.build(None, prov, mock=True, ph_rows=rows, extensions={"p0-w4": {"ph_route_dry": meta}})
    out = summary.write(document, out_path)
    stats = {"route_class": cls, "seconds": time.perf_counter() - t0, "peak_mb": peak_mb(), "path": str(out)}
    return out, document, stats


