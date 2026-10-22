"""Production screen of the phosphate films: stage rows from the frozen K1 ladder, the K2 maps, K3 and K4 where their inputs
exist, the route layer and the baselines (PH-W4.2).

    python -m nacre.screen ph-production --out results/preprint/screen/<run>_ph/summary.json

Inputs are frozen at p0-cp5 (nacre.screen.ph_prov): lit/params.yaml, thresholds block v8, the symbol bindings, the gap tables
and the K1 ladder (ladder_v3.csv). Nothing here sets a prior, a threshold or a verdict rule.

K1 is READ from the ladder (never recomputed): the framing, stage and conversion rows. A slurry-stage phase runs K2 to K4 under
the F1 proceed rule (it proceeds unless its K1 verdict is falsified at EVERY registered cutoff class); a cell-stage phase runs K1
only; a row carries one stage (nacre.screen.ph_rows.check_presentation).

K2 is the Omega test of the registered phosphate speciation on the alkaline grid (nacre.screen.k2_grid), worst over the slurry and
drying states. K3 and K4 of a nucleus framing need K_sp, V_m, gamma_nl and gamma_nv of the framing; where a key is a gap, the gap
table registers no treatment (configs/preprint/gap_resolution_ph.yaml: "to register at cp5 freeze"), so the test is
undetermined with the missing keys named, and the deletion test has nothing to delete. The route layer (hydrolysis descriptor,
R1, R2, liquid wetting) is report-only: where its data are gaps it reports undetermined, never gating. Verdicts use the regime
vocabulary (excluded, not excluded, suitable against dissolution, open, undetermined). P(feasible) under an ignorance prior is
never stated as a finding.
"""
import time
from pathlib import Path

import numpy as np
import yaml

from nacre.screen import decision, k2_grid, kscreen, params_adapter, ph_prov, ph_rows, routes, run, summary
from nacre.screen import mineral as mineral_mod

SESSION = "PH-W4.2"
#: Nucleus framings of the candidate Ca phosphate: the screen.yaml minerals that carry gamma keys.
NUCLEUS_FRAMINGS = ("hap", "acp")
#: Ca orthophosphates of the ladder's slurry stage used as formed (F5), and the competing Li phosphate.
SLURRY_PHASES = ("hap", "acp", "ocp", "btcp", "brushite", "atcp", "li3po4")
CELL_ROLES = {"Ca2P2O7": "candidate", "Ca(PO3)2 / Ca-polyphosphate glass": "route", "AlPO4": "candidate", "Al(PO3)3": "candidate",
              "Al-polyphosphate (R1 gel)": "route", "Ca-modified aluminophosphate": "candidate"}
#: (LiPO3)n and the baked aluminophosphate are the baselines: K1, K2 and K4 rows (baseline_stage_rows), not cell-only rows.
SILICATES = ("CaSiO3", "Ca2SiO4", "Li2SiO3")
CONVERSIONS = (("brushite", "monetite", "conversion_brushite_monetite_onset"),
               ("monetite", "Ca2P2O7", "conversion_monetite_pyrophosphate_onset"),
               ("ACP", "condensed Ca phosphate", None), ("HAp", "condensed Ca phosphate", None))


def ladder_mineral(phase, state="crystalline"):
    """A mineral object that only names a ladder phase, for the K1 reader."""
    return mineral_mod.Mineral(phase, phase, 1, 1, "unused", "unused", phase, x_symbol="a_X", k1_phase=phase, phase_state=state)


def k1_both(table, phase):
    return {f: kscreen.k1_for(table, ladder_mineral(phase, f), framing=f) for f in kscreen.FRAMINGS}


def is_gap(doc, key):
    e = (doc.get("params") or {}).get(key)
    return e is None or ((e.get("prior") or {}).get("family") in (None, "none"))


# ------------------------------------------------------------------ K3 and K4 of a nucleus framing
def nucleus_keys(minerals, name):
    """{role: table key} the nucleation chain of a framing reads that belongs to the framing."""
    m = minerals[name]
    out = {"K_sp": m.ksp_key, "V_m": m.vm_key}
    out.update({k: v for k, v in m.gamma_keys.items()})
    if m.n_hyd_key:
        out["n_hyd"] = m.n_hyd_key
    return out


def k34_record(test, minerals, name, doc, gap_table):
    """K3 or K4 of one nucleus framing: undetermined with the missing keys named, or a refusal to guess when none is missing."""
    keys = nucleus_keys(minerals, name)
    missing = {role: k for role, k in keys.items() if is_gap(doc, k)}
    ev = {k: ("gap" if is_gap(doc, k) else routes.grade_of(doc["params"].get(k))) for k in keys.values()}
    if not missing:
        raise RuntimeError("every nucleus input of %s is present in the table; the production path for a phosphate nucleus chain "
                           "with sourced interfacial energies is not exercised in PH-W4.2" % name)
    treat = {k: ((gap_table.get("keys") or {}).get(k) or {}).get("treatment", "no entry") for k in missing.values()}
    return {"test": test, "verdict": "undetermined", "evidence": ev,
            "gap": "nucleation link not evaluable: %s %s" % (
                ", ".join(sorted(missing.values())), "(no admissible treatment is registered: %s)" % "; ".join(sorted(set(treat.values())))),
            "missing_keys": sorted(missing.values()), "gap_table_treatment": treat,
            "framing": minerals[name].framing, "states": ["slurry", "drying"],
            "priors": {"sourced": "gap", "analog": "none registered", "ignorance": "none registered"},
            "retained_mass": None,
            "note": "M_adm is printed beside a gamma_sl verdict; there is none (gamma_nl is a gap), so no retained mass exists"}


def phosphate_k2_record(rec):
    """The K2 test record of a row from a k2_grid phosphate record."""
    return {"verdict": rec["verdict"], "evidence": {}, "regime": rec["regime"], "controls_pass": rec.get("controls_pass"),
            "slurry_state_headline": rec.get("slurry_state_headline"), "n_passing_cells": rec["region"]["n_passing"],
            "n_cells": rec["region"]["n_cells"], "dose_window_Ca_T_mol_dm3": rec.get("dose_window_Ca_T_mol_dm3"),
            "region": rec["region"]["grid"], "per_state": rec.get("per_state")}


def combine_framings(by):
    """Framing rule (claims_redirect.md 3d) over {framing: K2 verdict}: falsified only if falsified under every framing."""
    good = {f: v for f, v in by.items() if v in decision.ORDER}
    if not good:
        return {"verdict": "undetermined", "feasible_under": None}
    r = decision.combine_framings(good)
    return {"verdict": r["verdict"], "feasible_under": r.get("governing_framing")}


# ------------------------------------------------------------------ slurry-stage rows (F5: used as formed)
def slurry_stage_rows(ctx, ladder, k2_by_phase, doc, gap_table):
    """For each slurry-stage phase of the ladder: its slurry row (K2 to K4) and its cell row (K1), one film_id.

    The two nucleus framings of the candidate HAp (apatite, ACP) have a row each; their K2 verdicts are combined by the framing
    rule beside them (nacre.screen.ph_prod.combine_framings), not inside one row."""
    cfg = ctx.cfg
    rows = []
    for name in SLURRY_PHASES:
        spec = cfg["k2_phases"][name]
        phase = spec["ladder"]
        k1 = k1_both(ladder, phase)
        scope = ladder.low_cutoff_class(phase)
        note = ["used as formed: frame C applies to the Ca orthophosphates only"] if name != "li3po4" else \
            ["competing phase (Li3PO4): K1 read, no film claim"]
        cell = ph_rows.k1_cell_row("%s_as_formed" % name, phase, k1, "candidate" if name != "li3po4" else "comparator",
                                   scope_class=scope, labels=note)
        k2 = phosphate_k2_record(k2_by_phase[name])
        if name in NUCLEUS_FRAMINGS:
            k3r = k34_record("K3", ctx.minerals, name, doc, gap_table)
            k4r = k34_record("K4", ctx.minerals, name, doc, gap_table)
            framing = ctx.minerals[name].framing
        else:
            k3r = k4r = {"verdict": "undetermined", "evidence": {}, "gap": (
                "%s is not a registered nucleus framing: no gamma_nl, gamma_nv or V_m key exists for it in the gap table" % spec["formula"])}
            framing = "crystalline"
        gate = kscreen.proceeds({"by_class": _combined_classes(k1)})
        row = ph_rows.slurry_row("%s_as_formed" % name, phase, "candidate" if name != "li3po4" else "comparator", framing, k2, k3r,
                                 k4r, gate=gate, labels=["K3 and K4: undetermined, inputs are gaps; nothing gates on them"])
        row["deletion_test"] = {"holds": False, "verdict": "not run", "note": "K3 and K4 are undetermined: nothing to delete"}
        rows += [row, cell]
    return rows


def hap_framing_rule(k2_by_phase):
    """K2 of the candidate HAp over its two nucleus framings: falsified only if falsified under every framing."""
    by = {"apatite": k2_by_phase["hap"]["verdict"], "ACP": k2_by_phase["acp"]["verdict"]}
    r = combine_framings(by)
    return {"by_framing": by, "verdict": r["verdict"], "regime": k2_grid.REGIME.get(r["verdict"], "undetermined"),
            "feasible_under": r["feasible_under"], "rule": "claims_redirect.md 3d"}


def _combined_classes(k1_by_framing):
    """Per class, falsified only if falsified under every framing (the F1 proceed rule reads the phase, not one framing)."""
    classes = []
    for f in k1_by_framing.values():
        for c in f["by_class"]:
            if c not in classes:
                classes.append(c)
    out = {}
    for c in classes:
        vs = [f["by_class"].get(c, "undetermined") for f in k1_by_framing.values()]
        out[c] = "falsified" if all(v == "falsified" for v in vs) else next(v for v in vs if v != "falsified")
    return out


def cell_stage_rows(ladder):
    """K1-only rows of the cell-stage phases of the ladder; the framings are the ladder's."""
    rows = []
    for phase, role in CELL_ROLES.items():
        k1 = k1_both(ladder, phase)
        if role in ("route", "baseline") or phase.startswith("(LiPO3)n"):
            r = ph_rows.k1_cell_row("cell_" + _slug(phase), phase, k1, role, baked=(role == "baseline"),
                                    route=("R2" if "Ca(PO3)2" in phase else "R1" if "R1" in phase else None) if role == "route" else None)
        else:
            r = ph_rows.k1_cell_row("cell_" + _slug(phase), phase, k1, role)
        rows.append(r)
    return rows


def _slug(text):
    return "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")[:40]


def silicate_rows(ladder, doc):
    """The silicate comparator (as registered in the ladder): K1 read, K2 undetermined (no K_sp key), K4 undetermined."""
    rows = []
    for ph in SILICATES:
        k1 = k1_both(ladder, ph)
        k2 = routes.baseline_k2("%s silicate comparator" % ph)
        k4 = {"test": "K4", "row": "L5", "verdict": "undetermined", "evidence": {"matrix_baseline_film_thickness": "gap"},
              "note": "no film thickness for the comparator: insulating bound undetermined"}
        s = ph_rows.slurry_row("comparator_" + _slug(ph), ph, "comparator", "structure unspecified", k2, K4=k4,
                               labels=["silicate comparator: K1, K2, K4 only; composition-based solubility flagged; no performance claim"])
        cell = ph_rows.k1_cell_row("comparator_" + _slug(ph), ph, k1, "comparator", baked=True,
                                   labels=["silicate comparator"])
        rows += [s, cell]
    return rows


def baseline_stage_rows(ladder, doc):
    """(LiPO3)n comparator and the baked aluminophosphate through K1, K2 and K4; composition-based solubility is flagged."""
    p = doc["params"]
    rows = []
    k1_hq = k1_both(ladder, "(LiPO3)n Hydro-Quebec film")
    k4_hq = ph_rows.baseline_k4(None, None, "gap")
    k4_hq["evidence"] = {"matrix_baseline_hq_film_thickness": "gap"}
    rows += ph_rows.comparator_lipo3_rows("baseline_hq_lipo3n", k1_hq, solubility=None, k4=k4_hq)
    for r in rows:
        if r["stage"] == "slurry":
            r["labels"].append("composition-based solubility: flagged; a water-soluble Li polyphosphate is an inference from chemistry")
    k1_ts = k1_both(ladder, "baked aluminophosphate (Tsinghua)")
    k4_ts = ph_rows.baseline_k4(None, None, "gap")
    k4_ts["evidence"] = {"matrix_baseline_tsinghua_film_thickness": "gap"}
    rows += ph_rows.baseline_rows("baseline_tsinghua", "Tsinghua/Hon Hai", "baked aluminophosphate (Tsinghua)", k1_ts,
                                  routes.baseline_k2("Tsinghua/Hon Hai baked aluminophosphate"), k4_ts)
    return rows


# ------------------------------------------------------------------ conversion rows
def conversion_rows(doc, ladder):
    rows = []
    p = doc["params"]
    for pre, prod, key in CONVERSIONS:
        t = None
        if key and key in p and (p[key].get("prior") or {}).get("family") == "fixed":
            t = float(p[key]["prior"]["value"])
        elif key and key in p and (p[key].get("prior") or {}).get("family") == "uniform":
            t = float(p[key]["value"]) if p[key].get("value") is not None else None
        rows.append(ph_rows.conversion_row("conv_%s_%s" % (_slug(pre), _slug(prod)), pre, prod, a_w_star=None, T_conv_lit=t,
                                           T_cure=None, hydrolysis=None,
                                           sources={"T_conv_lit": key or "gap", "T_cure_baseline": "gap",
                                                    "a_w_star": "gap"}))
    return rows


# ------------------------------------------------------------------ the route layer (report-only)
def route_layer(doc, f_min_ends):
    """K2h, R1, R2 and the liquid wetting from the table: undetermined wherever a datum is a gap; never gating."""
    p = doc["params"]
    rows = []
    for key in ("hydrolysis_polyp_k_ph6", "hydrolysis_polyp_k_ph6_ca1mm", "hydrolysis_polyp_k_ph8", "hydrolysis_polyp_k_ph8_ca1mm"):
        e = p.get(key)
        pr = (e or {}).get("prior") or {}
        if pr.get("family") == "uniform":
            rows.append({"key": key, "k": (float(pr["low"]), float(pr["high"]))})
    conds = {"hydrolysis_polyp_k_ph6": (6.0, 0.0), "hydrolysis_polyp_k_ph6_ca1mm": (6.0, 1.0),
             "hydrolysis_polyp_k_ph8": (8.0, 0.0), "hydrolysis_polyp_k_ph8_ca1mm": (8.0, 1.0)}
    data = [{"key": r["key"], "pH": conds[r["key"]][0], "ca_mM": conds[r["key"]][1], "T": 298.15, "k": r["k"]} for r in rows]
    grades = {k: routes.grade_of(p.get(k)) for k in conds}
    for k in ("hydrolysis_transfer_factor", "hydrolysis_t_wet_r1", "hydrolysis_t_wet_r2", "hydrolysis_t_wet_r3", "hydrolysis_f_min",
              "hydrolysis_temperature_tolerance"):
        grades[k] = routes.grade_of(p.get(k)) if k in p else "gap"
    states = [{"pH": ph, "ca_mM": ca, "T": 298.15} for ph in (6.0, 8.0) for ca in (0.0, 1.0)] + \
             [{"pH": 8.0, "ca_mM": 1.0, "T": 333.15, "drying": True}]
    out = {"K2h": {}, "f_min_interval": f_min_ends, "note": "K2h is report-only: it gates a row only through H2, and every datum "
           "it needs beyond the four measured rates (transfer factor, wet times, f_min, temperature tolerance) is a gap"}
    for end, f in f_min_ends["ends"].items():
        out["K2h"][end] = {"f_min": f, "states": [routes.hydrolysis_descriptor(s, data, None, None, f, None, grades=grades,
                                                                              route=None) for s in states]}
    out["R1"] = {"test": "K3", "route": "R1", "verdict": "undetermined",
                 "label": "polyp_log10_ksp_al, polyp_al_log_k_oxide, polyp_chain activity and the linear complexation constant are gaps: "
                          "F1r, flip value K_sp* = IAP_AlPP not computable without a_Al and a_PP",
                 "evidence": {k: ("gap" if k not in p or (p[k].get("prior") or {}).get("family") in (None, "none") else
                                  routes.grade_of(p[k])) for k in ("polyp_log10_ksp_al", "polyp_al_log_k_oxide",
                                                                  "polyp_al_log_beta1_linear")},
                 "hypothesis": routes.KINETIC_HYPOTHESIS, "gating": False}
    out["R2"] = {"test": "K3", "route": "R2", "verdict": "undetermined", "row": "B1",
                 "label": routes.LABELS["B1"] + " (the binodal map coacervate_binodal_map is a gap: B1 at every state)",
                 "evidence": {"coacervate_binodal_map": "gap"}, "gating": False}
    out["liquid_wetting"] = {"test": "K4", "route": "R2", "verdict": "undetermined",
                             "label": "coacervate_gamma_s0_dilute, coacervate_gamma_s0_dense, coacervate_contact_angle_alumina and "
                                      "coacervate_gamma_nl are gaps; the analog keys coacervate_gamma_analog* are never a substitute",
                             "evidence": {"coacervate_gamma_nl": "gap", "coacervate_gamma_analog": routes.grade_of(p.get("coacervate_gamma_analog"))},
                             "gating": False}
    out["R3"] = routes.formation_accessibility("R3", 0.9)
    return out


def f_min_interval(doc):
    """f_min in [1 - p_c_site_square, 1 - p_c_site_sc] (claims_redirect.md 11e): the registered interval, a sensitivity."""
    p = doc["params"]

    def val(k):
        pr = (p.get(k) or {}).get("prior") or {}
        return float(p[k]["value"]) if p.get(k) and p[k].get("value") is not None else None
    sq, sc, tri = val("p_c_site_square"), val("p_c_site_sc"), val("p_c_site_triangular")
    if sq is None or sc is None:
        return {"ends": {}, "gap": "p_c keys missing"}
    return {"ends": {"low_2D_square": 1.0 - sq, "high_3D_sc": 1.0 - sc}, "keys": ["p_c_site_square", "p_c_site_sc"],
            "lattice_sensitivity_triangular": (1.0 - tri) if tri is not None else None,
            "rule": "f_min in [1 - p_c_site_square, 1 - p_c_site_sc]; H2 at the lower end, H3 at the upper end (11e); K2h report-only"}


# ------------------------------------------------------------------ the run
def run_phosphate(root, out_path, dry=False, label=None, stride=1, log=None):
    """Write the phosphate-film document; production runs append the ledger line. Returns (path, document, stats)."""
    t0 = time.perf_counter()
    root, out_path = Path(root), Path(out_path)
    if dry:
        if not run._inside(out_path, root / run.DRYRUN_PH_DIR):
            raise run.ProductionRefused("a dry run writes only under %s" % run.DRYRUN_PH_DIR)
    else:
        ph_prov.check_frozen(root)
        if not run._inside(out_path, root / run.SCREEN_DIR) or run._inside(out_path, root / run.DRYRUN_PH_DIR) \
                or not out_path.parent.name.endswith(k2_grid.SUBDIR_SUFFIX):
            raise run.ProductionRefused("production output belongs in a new directory %s/<run>%s/" % (run.SCREEN_DIR, k2_grid.SUBDIR_SUFFIX))
        if out_path.exists():
            raise run.ProductionRefused("%s exists: a production document is never overwritten" % out_path)
        if stride != 1:
            raise run.ProductionRefused("a production run covers the whole grid (stride 1)")
    ctx = k2_grid.Context(root, stride=stride)
    ladder = kscreen.read_k1(root / ph_prov.LADDER)
    gap_table = yaml.safe_load((root / ph_prov.GAP_TABLES[1]).read_text(encoding="utf-8"))
    k2body = k2_grid.part_phosphate(ctx, log)
    rows = slurry_stage_rows(ctx, ladder, k2body["phases"], ctx.doc, gap_table)
    rows += cell_stage_rows(ladder)
    rows += baseline_stage_rows(ladder, ctx.doc)
    rows += silicate_rows(ladder, ctx.doc)
    rows += conversion_rows(ctx.doc, ladder)
    problems = ph_rows.check_presentation(rows)
    if problems:
        raise run.ProductionRefused("presentation rule: %s" % problems)
    fm = f_min_interval(ctx.doc)
    routes_body = route_layer(ctx.doc, fm)
    cb = {f: ladder.verdicts("CaCO3", f) for f in kscreen.FRAMINGS}
    body = {"session": SESSION, "p_cred": ctx.p, "k2_phosphate": k2body,
            "carbonate_baseline": {"K1": cb, "K1_stage": "control", "K2": "k2_grid_ph (run 1) per polymorph",
                                   "K4": "table_ph claims.C4 (run 3)", "source": "ladder_v3.csv, phase CaCO3"}, "hap_framing_rule": hap_framing_rule(k2body["phases"]),
            "route_layer": routes_body,
            "k1_ladder": {"file": ph_prov.LADDER.as_posix(), "layout": ladder.layout,
                          "inconsistencies": ladder.inconsistencies, "skipped": ladder.skipped},
            "f1_gate": {r["film_id"]: r["gate"] for r in rows if r.get("gate")},
            "study_verdict_phosphate": {"verdict": "undetermined",
                                        "rule": "no phosphate framing has an evaluable nucleation link (gamma_nl is a gap); "
                                                "K2 and K1 are reported per row, nothing is gated on K3 or K4"}}
    stats = k2_grid.stats_of(body)
    stats.update(seconds=time.perf_counter() - t0, peak_mb=k2_grid.peak_mb())
    body["run"] = stats
    cfg_path = root / run.CONFIG
    prov = run._provenance(root, ctx.cfg, cfg_path, [params_adapter.RegimePriors("R-slurry", None, {}, str(ctx.params_path),
                                                                                  run._sha256_file(ctx.params_path), False)],
                           run.THRESHOLDS, dry)
    prov["run_label"] = label or out_path.parent.name
    prov["session"] = SESSION
    doc = summary.build(None, prov, mock=dry or ctx.doc["mock"], extensions={"p0-w4": {"ph_production": body}}, ph_rows=rows)
    path = summary.write(doc, out_path)
    if not dry:
        ph_prov.ledger_append(root, SESSION, prov, prov["config_file"], prov["config_hash"], [path])
    return path, doc, stats
