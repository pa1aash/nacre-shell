"""K2 over the registered design grid, the falsifiability controls and the acid-adjusted comparator state (PH-W4.2).

    python -m nacre.screen k2-grid --out results/preprint/screen/<run>_ph/summary.json      production (after cp5)
    python -m nacre.screen k2-grid --dry --out results/preprint/screen/dryrun_ph/k2_grid/summary.json

K2 is the Omega test of theory/claims_redirect.md 3a and 11a: Omega_bulk(P) = IAP(P) / K_sp(P) >= 1 passes at a state, with the
activities of the registered speciation (carbonate for CaCO3 phases, phosphate for the Ca phosphates). A cell of the grid is
one point (Ca_T, C_T or P_T, pH, I, a_w at the drying state); pH and I are grid axes here (design_axes.pH, design_axes.I_ionic: the
min, central and max of their table keys), every other input is sampled from its prior. The verdict of a cell is the band-mass
verdict at p_cred, worst over the registered states; a polymorph or phase passes in the cells where it passes, and its
region is that set of cells, named by the grid id. K2 is inconclusive in every cell of a phase whose falsifiability
controls did not come out as they must (the low-dose corner at the lowest pH of ph_slurry_modified reports dissolution,
the supersaturated state stability). A second corner, the same low-dose point in the unmodified alkaline slurry
(pH 10 to 13), is scanned and reported with the pH at which undersaturation sets in; it does not gate.

Acid-adjusted state (comparator): the same test at pH 4.5 to 8.5, the incumbent phosphoric-acid pH control, for the carbonates and
for the Ca phosphates of the K1 ladder's slurry stage. A phase without a K_sp key is undetermined. The row carries no K3 or K4.

Labels are an output field (nacre.screen.k2_carbonate): calcite reads "calcite (suitable against dissolution, a necessary
condition, in [region])" where K2 passes; aragonite reads "aragonite (dissolution stability only; formation unsupported at slurry
pH and room temperature)"; ACC is reported beside them with its dose window. There is no other label.
"""
import json
import resource
import sys
import time
from functools import partial
from pathlib import Path

import numpy as np
import yaml

from nacre.screen import chain, decision, gaps, k2_carbonate, params_adapter, propagate, run, study, summary
from nacre.screen import thresholds as thr
from nacre.screen import units
from nacre.screen.mineral import CALCITE

SESSION = "PH-W4.2"
POLYMORPHS = k2_carbonate.POLYMORPHS
SUBDIR_SUFFIX = "_ph"
START_DRAWS = 2 ** 14
HALF_WIDTH_MAX = 0.01
DRAW_CAP = 2 ** 20
#: Verdict words of the K2 test and the regime vocabulary of claims_redirect.md 11d.
REGIME = {"feasible": "suitable against dissolution", "falsified": "excluded", "inconclusive": "open",
          "undetermined": "undetermined"}
PHOSPHATE_BINDINGS = {"pH": "ph_slurry", "I_ionic": "ionic_strength_slurry", "rho_water": "water_density",
                      "pK1_phosphoric": "pka1_h3po4", "pK2_phosphoric": "pka2_h3po4", "pK3_phosphoric": "pka3_h3po4",
                      "K_CaHPO4_aq": "log10_k_cahpo4_aq", "K_CaH2PO4": "log10_k_cah2po4", "K_CaPO4": "log10_k_capo4",
                      "K_CaOH": "log10_k_caoh", "A_DH": "debye_huckel_a", "b_D": "davies_b", "I_val": "davies_i_val",
                      "pKw": "pkw"}
AXIS_SI = {"Ca_T": "mol m^-3", "C_T": "mol m^-3", "P_T": "mol m^-3", "pH": "1", "I_ionic": "mol kg^-1", "a_w": "1"}


class GridError(ValueError):
    """The K2 grid configuration is missing or inconsistent."""


def peak_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 2 ** 20 if sys.platform == "darwin" else r / 2 ** 10


# ------------------------------------------------------------------ the grid
def _axis(cfg, resolver, name):
    spec = (cfg.get("design_axes") or {}).get(name)
    if spec is None:
        raise GridError("design_axes.%s is not registered in screen.yaml" % name)
    return study._axis_values(spec, resolver, AXIS_SI.get(name, spec.get("unit", "1")))


def _short(label):
    return label.replace("ph_slurry@", "pH@").replace("ionic_strength_slurry@", "I@")


def carbonate_cells(cfg, resolver, ph_axis="pH"):
    """[(cell id, design, fixed, labels)]: Ca_T x C_T x a_w(drying) design points, with pH and I fixed per cell."""
    pts = study.design_points(cfg, resolver)
    out = []
    for ph_lab, ph in _axis(cfg, resolver, ph_axis):
        for i_lab, ii in _axis(cfg, resolver, "I_ionic"):
            for pid, design, labels in pts:
                out.append(("%s; pH=%s; I=%s" % (pid, _short(ph_lab), _short(i_lab)), design,
                            {"pH": ph, "I_ionic": ii}, dict(labels, pH=_short(ph_lab), I=_short(i_lab))))
    return out


def phosphate_cells(cfg, resolver, ph_axis="pH", drying=True):
    """Ca_T x P_T x a_w(drying) design points of the phosphate K2, pH and I fixed per cell."""
    ca = _axis(cfg, resolver, "Ca_T")
    pt = _axis(cfg, resolver, "P_T")
    aw = [(None, None)]
    if drying:
        spec = (cfg.get("design_axes") or {}).get("a_w")
        if spec:
            aw = [(lab, v) for lab, v in study._axis_values(spec, resolver, "1")]
    out = []
    for ph_lab, ph in _axis(cfg, resolver, ph_axis):
        for i_lab, ii in _axis(cfg, resolver, "I_ionic"):
            for c_lab, c in ca:
                for p_lab, pv in pt:
                    for a_lab, a in aw:
                        design = {"Ca_T": c, "P_T": pv}
                        labels = {"Ca_T": c_lab, "P_T": p_lab, "pH": _short(ph_lab), "I": _short(i_lab)}
                        if a is not None:
                            design["a_w@drying"] = a
                            labels["a_w"] = a_lab
                        cid = "; ".join("%s=%s" % kv for kv in labels.items())
                        out.append((cid, design, {"pH": ph, "I_ionic": ii}, labels))
    return out


# ------------------------------------------------------------------ Omega draws of one cell
def _sample_speciation(rp, mineral, n, seed, chunk):
    evaluate = partial(chain.evaluate, links=["speciation"], mineral=mineral)
    o, _ = propagate.propagate_chain(evaluate, rp.joint, n, seed, chunk)
    return o


def carbonate_point(params_path, cfg, polymorph, design, fixed, n, seed, chunk, p, allow_mock=False):
    """K2 record of one carbonate cell: the Omega test with the K_sp key of the polymorph, worst over the states."""
    states = study.load_point(params_path, cfg, polymorph, design, allow_mock, "table", True, "R-slurry",
                              fixed_inputs=fixed)
    outs, gap = {}, {}
    for sid, rp in states:
        if "speciation" not in chain.evaluable_links(rp.joint.symbols, CALCITE):
            gap[sid] = dict(rp.unsampled)
            continue
        outs[sid] = (_sample_speciation(rp, CALCITE, n, seed, chunk), None, rp)
    om = study.omega_point(outs, p)
    if om is None:
        return {"verdict": "undetermined", "gap": "Omega_bulk not evaluable: %s" % gap, "unsampled": gap}
    return om


def phosphate_bindings(cfg, spec, sampled_ph=False):
    """{symbol: table key} of a phosphate cell: the registered phosphate speciation plus the K_sp key of the phase."""
    b = dict(PHOSPHATE_BINDINGS)
    b["K_sp"] = spec["ksp"]
    return b


def phosphate_omega_evaluate(spec, a_w, mineral):
    """x ({symbol: array}) -> (outputs, masses) of the phosphate Omega of one phase at the water activity a_w."""
    def evaluate(x):
        xd, sp, mass = chain.derive(dict(x), mineral)
        m = _shape(xd)
        ln_iap = np.zeros(m)
        ok = np.isfinite(np.asarray(xd["K_sp"], dtype=float)) & (np.asarray(xd["K_sp"], dtype=float) > 0)
        for sym, nu in spec["nu"].items():
            if sym == "a_H":
                a = 10.0 ** (-np.asarray(xd["pH"], dtype=float))
            else:
                a = np.asarray(xd[sym], dtype=float)
            ok = ok & np.isfinite(a) & (a > 0)
            with np.errstate(divide="ignore", invalid="ignore"):
                ln_iap = ln_iap + nu * np.log(np.where(a > 0, a, np.nan))
        n_hyd = spec.get("n_hyd")
        if n_hyd is not None and a_w != 1.0:
            ln_iap = ln_iap + float(n_hyd) * np.log(a_w)
        elif spec.get("n_hyd_key") and a_w != 1.0:
            if "n_hyd" not in xd:
                ok = ok & False                      # n unknown: the water term is undetermined away from a_w = 1
            else:
                ln_iap = ln_iap + np.asarray(xd["n_hyd"], dtype=float) * np.log(a_w)
        with np.errstate(divide="ignore", invalid="ignore"):
            om = np.exp(ln_iap - np.log(np.where(ok, np.asarray(xd["K_sp"], dtype=float), np.nan)))
        om = np.where(ok, om, np.nan)
        return ({"speciation": {"Omega_bulk": om, "a_Ca": np.asarray(xd["a_Ca"], dtype=float),
                                "a_CO3": np.asarray(xd.get("a_PO4", xd["a_Ca"]), dtype=float)}},
                {"speciation": {}})
    return evaluate


def phosphate_omega(rp, spec, n, seed, chunk, a_w, mineral):
    """Omega draws of a phosphate phase from the speciated activities (ln IAP summed over the ions, minus ln K_sp)."""
    o, _ = propagate.propagate_chain(phosphate_omega_evaluate(spec, a_w, mineral), rp.joint, n, seed, chunk)
    return o


def _shape(x):
    return np.broadcast(*[np.asarray(v) for v in x.values()]).shape


def phosphate_point(params_path, cfg, spec, design, fixed, n, seed, chunk, p, mineral, states, allow_mock=False):
    """K2 record of one phosphate cell, worst over the registered states (slurry a_w = 1, drying at the design a_w)."""
    if spec.get("ksp") is None:
        return {"verdict": "undetermined", "gap": "no K_sp key for %s in lit/params.yaml" % spec["formula"]}
    doc, _ = params_adapter.read_table(params_path, allow_mock)
    if spec["ksp"] not in doc["params"] or (doc["params"][spec["ksp"]].get("prior") or {}).get("family") in (None, "none"):
        return {"verdict": "undetermined", "gap": "K_sp key %s is a gap in lit/params.yaml" % spec["ksp"]}
    bind = phosphate_bindings(cfg, spec)
    if spec.get("n_hyd_key"):
        bind["n_hyd"] = spec["n_hyd_key"]
    design_here = {k: v for k, v in design.items() if "@" not in k}
    per = {}
    for sid in states:
        a_w = 1.0 if sid == "slurry" else float(design.get("a_w@drying", 1.0))
        extra, drop = [], set(fixed) | set(design_here)
        for sym, v in {**design_here, **fixed}.items():
            extra.append(study._fixed(sym, v, AXIS_SI.get(sym, "1"), "design axis"))
        extra.append(study._fixed("a_w", a_w, "1", "registered state value"))
        bindings = {s: k for s, k in bind.items() if s not in drop}
        rp = params_adapter.regime_priors(params_path, "R-slurry", allow_mock, bindings=bindings, absent="gap", extra=extra)
        if "n_hyd" in bindings and "n_hyd" in rp.unsampled and a_w == 1.0:
            pass                                       # a_w = 1: the water term is zero for any n
        o = phosphate_omega(rp, spec, n, seed, chunk, a_w, mineral)
        per[sid] = (o, None, rp)
    om = study.omega_point(per, p)
    if om is None:
        return {"verdict": "undetermined", "gap": "Omega_bulk not evaluable for %s" % spec["formula"]}
    om["omega_median_by_state"] = {sid: study._median(o["speciation"]["Omega_bulk"]) for sid, (o, _, _) in per.items()}
    gap_states = [sid for sid, (o, _, _) in per.items() if not np.any(np.isfinite(o["speciation"]["Omega_bulk"]))]
    if gap_states:
        om = dict(om, verdict="undetermined", gap="no Omega draw at state %s (a key of the water term or the speciation is a gap)"
                  % ",".join(gap_states))
    return om


# ------------------------------------------------------------------ cell evaluation with sizing
def sized(point_fn, p, target=HALF_WIDTH_MAX, start=START_DRAWS, cap=DRAW_CAP):
    """Doubles the draws of one cell until the band-mass half-width is at most the target, or the cap binds."""
    n = start
    while True:
        rec = point_fn(n)
        hw = rec.get("half_width")
        if hw is None or hw <= target:
            return dict(rec, draws=n, capped=False)
        if 2 * n > cap:
            return dict(rec, draws=n, capped=True)
        n *= 2


def window_of(cells):
    """(feasible, falsified, inconclusive, undetermined) cell ids and the headline verdict of one phase."""
    sets = {v: sorted(c for c, r in cells.items() if r["verdict"] == v) for v in
            ("feasible", "falsified", "inconclusive", "undetermined")}
    if sets["feasible"]:
        head = "feasible"
    elif sets["undetermined"] and not sets["falsified"] and not sets["inconclusive"]:
        head = "undetermined"
    elif len(sets["falsified"]) == len(cells):
        head = "falsified"
    else:
        head = "inconclusive"
    return sets, head


def region_of(cells, cfg):
    """The region where K2 passes: the grid id, the passing cells, and the lowest passing Ca_T per (C_T or P_T, pH, I)."""
    ok = {c: r for c, r in cells.items() if r["verdict"] == "feasible"}
    low = {}
    for cid, r in ok.items():
        ax = r.get("axes") or {}
        ca = ax.get("Ca_T")
        key = "; ".join("%s=%s" % (k, v) for k, v in ax.items() if k != "Ca_T")
        try:
            val = float(str(ca).split()[0])
        except (TypeError, ValueError):
            continue
        low[key] = min(val, low.get(key, val))
    return {"grid": "R-slurry K2 grid g1 (screen.yaml design_axes: Ca_T, C_T or P_T, pH, I, a_w at the drying state)",
            "n_cells": len(cells), "n_passing": len(ok), "passing_cells": sorted(ok),
            "lowest_passing_Ca_T_mol_dm3_by_other_axes": dict(sorted(low.items()))}


def run_cells(cells, point_fn, p, log=None):
    """{cell id: record} with the draws sized per cell."""
    out = {}
    for cid, design, fixed, labels in cells:
        rec = sized(lambda n: point_fn(design, fixed, n), p)
        out[cid] = dict(rec, axes=labels)
        if log:
            log(cid, rec)
    return out


# ------------------------------------------------------------------ controls
def control_states(cfg, resolver):
    """Control states of the carbonate Omega test (screen.yaml omega_control): {name: (values SI, labels)}."""
    return study.control_points(cfg, resolver)


def scan_values(cfg, resolver, spec):
    """pH values of a control scan: from the min to the max of a table key in steps, labelled."""
    lo, hi = float(resolver.range(spec["params"])["min"]), float(resolver.range(spec["params"])["max"])
    step = float(spec["step"])
    n = int(round((hi - lo) / step))
    return [round(lo + i * step, 10) for i in range(n + 1)]


def onset(scan):
    """Where undersaturation sets in along a pH scan: the highest pH of the scan that is falsified (dissolves) and the lowest that is not.

    scan: {pH: record}. Returns a record naming the sign pattern: 'undersaturated throughout', 'supersaturated throughout' or the
    pH interval over which the verdict changes (Omega crosses 1 between the two values), and the direction.
    """
    pts = sorted(scan.items())
    v = [(ph, r["verdict"]) for ph, r in pts]
    if all(x == "falsified" for _, x in v):
        return {"pattern": "undersaturated throughout the scan", "crossing_pH": None}
    if all(x == "feasible" for _, x in v):
        return {"pattern": "not undersaturated anywhere in the scan", "crossing_pH": None}
    changes = [(a, b) for (a, x), (b, y) in zip(v, v[1:]) if x != y]
    return {"pattern": "verdict changes along the scan", "crossing_pH": [list(c) for c in changes],
            "falsified_at": [ph for ph, x in v if x == "falsified"], "not_falsified_at": [ph for ph, x in v if x != "falsified"]}


def carbonate_controls(params_path, cfg, resolver, polymorph, p, n, seed, chunk, allow_mock=False):
    """The falsifiability controls of one polymorph: the modified-pH low-dose corner and the supersaturated state (gating),
    and the same low-dose corner in the unmodified alkaline slurry, scanned over pH 10 to 13 (reported, not gating)."""
    pts = control_states(cfg, resolver)
    out = {}
    for name, (vals, labels) in pts.items():
        design = {k: v for k, v in vals.items() if k in ("Ca_T", "C_T")}
        fixed = {k: v for k, v in vals.items() if k not in design}
        rec = carbonate_point(params_path, cfg, polymorph, design, fixed, n, seed, chunk, p, allow_mock)
        out[name] = dict(rec, axes=labels, label="%s (%s)" % (name, polymorph))
    spec = (cfg.get("omega_control_unmodified") or {})
    scan = {}
    if spec:
        base = pts["undersaturated"][0]
        design = {k: base[k] for k in ("Ca_T", "C_T")}
        for ph in scan_values(cfg, resolver, spec["pH"]):
            r = carbonate_point(params_path, cfg, polymorph, design, {"pH": ph}, n, seed, chunk, p, allow_mock)
            scan[ph] = r
    return out, scan


def controls_pass(ctl):
    """Gating outcome: each control came out as it must (decision.CONTROL_MUST)."""
    return {k: ctl.get(k, {}).get("verdict") == decision.CONTROL_MUST[k] for k in decision.CONTROL_MUST}


# ------------------------------------------------------------------ phosphate controls
def phosphate_control_cells(cfg, resolver):
    """Control cells of the phosphate K2: the low-dose corner at the lowest pH of ph_slurry_modified, the supersaturated state."""
    spec = cfg.get("k2_controls_phosphate") or {}
    out = {}
    for name, c in spec.items():
        design, fixed, labels = {}, {}, {}
        for sym, s in c.items():
            if "value" in s:
                v = units.convert(float(s["value"]), s.get("unit", AXIS_SI.get(sym, "1")), AXIS_SI.get(sym, "1"))
                lab = "%g %s" % (s["value"], s.get("unit", ""))
            else:
                key = s["params"]
                v = resolver.range(key)[s["at"]] if s["at"] != "value" else resolver.value(key)
                v = units.convert(float(v), resolver.get(key)[1] or "1", AXIS_SI.get(sym, "1"))
                lab = "%s@%s" % (key, s["at"])
            (design if sym in ("Ca_T", "P_T") else fixed)[sym] = v
            labels[sym] = lab
        out[name] = (design, fixed, labels)
    return out


# ------------------------------------------------------------------ gating by the controls
def apply_controls(cells, ok):
    """K2 is inconclusive in every cell of a phase whose controls did not come out as they must (block v2 C5s.control)."""
    out = {}
    for cid, r in cells.items():
        r = dict(r)
        r["verdict_before_control"] = r["verdict"]
        if not ok and r["verdict"] != "undetermined":
            r["verdict"] = "inconclusive"
        out[cid] = r
    return out


def brief(r):
    keys = ("verdict", "verdict_before_control", "P_good", "P_bad", "half_width", "n_used", "draws", "capped", "state",
            "by_state", "omega_median_by_state", "a_Ca_median", "a_CO3_median", "gap", "axes")
    return {k: r[k] for k in keys if k in r}


def per_state_summary(cells):
    """{state: {verdict: n cells}} of the per-state verdicts over a phase's cells."""
    out = {}
    for r in cells.values():
        for st, v in (r.get("by_state") or {}).items():
            out.setdefault(st, {}).setdefault(v, 0)
            out[st][v] += 1
    return out


def slurry_only_headline(cells):
    """Headline of the wet-slurry state alone (the dissolution test against solution), beside the worst-state rule."""
    sl = {cid: {"verdict": (r.get("by_state") or {}).get("slurry", r["verdict"])} for cid, r in cells.items()}
    return window_of(sl)[1]


def dose_window(cells):
    """(lowest passing Ca_T, highest) in mol dm^-3 over the passing cells, or None."""
    vals = []
    for r in cells.values():
        if r["verdict"] == "feasible":
            try:
                vals.append(float(str((r.get("axes") or {}).get("Ca_T")).split()[0]))
            except (TypeError, ValueError):
                pass
    return (min(vals), max(vals)) if vals else None


def second_control_onset(cells):
    """Where undersaturation sets in along the dose axis in the unmodified slurry (pH 10 to 13, C_T minimum): per (pH, I), the lowest
    Ca_T of the grid at which the cell is not falsified."""
    by = {}
    for r in cells.values():
        ax = r.get("axes") or {}
        if not str(ax.get("C_T", "")).endswith("@min"):
            continue
        key = "%s; %s; %s" % (ax.get("pH"), ax.get("I"), ax.get("a_w", "slurry"))
        ca = float(str(ax["Ca_T"]).split()[0])
        d = by.setdefault(key, {})
        d[ca] = r["verdict"]
    out = {}
    for key, d in by.items():
        ok = sorted(c for c, v in d.items() if v != "falsified")
        out[key] = {"lowest_Ca_T_not_falsified_mol_dm3": ok[0] if ok else None,
                    "falsified_at_every_Ca_T": not ok}
    return out


# ------------------------------------------------------------------ one phase on one grid
def eval_carbonate(params_path, cfg, resolver, polymorph, cells, p, allow_mock=False, log=None, controls=True):
    """Cells, controls and the headline of one polymorph on a list of carbonate cells."""
    chunk = int(cfg["propagation"]["chunk"])
    seed = int(cfg["propagation"]["seed"])

    def point(design, fixed, n):
        return carbonate_point(params_path, cfg, polymorph, design, fixed, n, seed, min(chunk, n), p, allow_mock)
    recs = run_cells(cells, point, p, log)
    rec = {"ksp_key": k2_carbonate.ksp_keys(cfg)[polymorph]}
    ok = True
    if controls:
        ctl, scan = carbonate_controls(params_path, cfg, resolver, polymorph, p, START_DRAWS, seed, min(chunk, START_DRAWS), allow_mock)
        res = controls_pass(ctl)
        ok = all(res.values())
        rec["controls"] = {"gating": {k: brief(v) for k, v in ctl.items()}, "pass": res,
                           "low_dose_corner_flags_omega_below_1": res["undersaturated"],
                           "supersaturated_reports_stability": res["supersaturated"],
                           "second_control": {"label": "low-dose corner in the unmodified alkaline slurry (pH 10 to 13); scanned, not gating",
                                              "pH_scan": {"%g" % ph: brief(r) for ph, r in scan.items()},
                                              "undersaturation": onset(scan) if scan else None}}
    recs = apply_controls(recs, ok)
    sets, head = window_of(recs)
    rec.update({"verdict": head, "regime": REGIME[head], "controls_pass": ok, "sets": {k: len(v) for k, v in sets.items()},
                "slurry_state_headline": slurry_only_headline(recs), "per_state": per_state_summary(recs),
                "region": region_of(recs, cfg), "dose_window_Ca_T_mol_dm3": dose_window(recs),
                "cells": {cid: brief(r) for cid, r in recs.items()}})
    return rec


def eval_phosphate(params_path, cfg, resolver, name, cells, p, minerals, states, allow_mock=False, log=None,
                   supersaturated_from=None, phases=None):
    """Cells, controls and the headline of one Ca phosphate (or an undetermined phase) on a list of phosphate cells.

    supersaturated_from: optional callable (cell records) -> control record that replaces the configured supersaturated state
    (PH-W4.5: the grid state of maximum Omega); the configured state is then run and reported beside it, not gating.
    phases: optional {name: spec} replacing cfg["k2_phases"]."""
    spec = (phases or cfg["k2_phases"])[name]
    chunk = int(cfg["propagation"]["chunk"])
    seed = int(cfg["propagation"]["seed"])
    base = minerals["hap"]

    def point(design, fixed, n):
        return phosphate_point(params_path, cfg, spec, design, fixed, n, seed, min(chunk, n), p, base, states, allow_mock)
    recs = run_cells(cells, point, p, log)
    rec = {"formula": spec["formula"], "ksp_key": spec.get("ksp"), "ladder_phase": spec["ladder"]}
    ok = True
    if spec.get("ksp"):
        ctl = {}
        for cname, (design, fixed, labels) in phosphate_control_cells(cfg, resolver).items():
            r = phosphate_point(params_path, cfg, spec, design, fixed, START_DRAWS, seed, min(chunk, START_DRAWS), p, base,
                                ("slurry",), allow_mock)
            ctl[cname] = dict(r, axes=labels)
        legacy = None
        if supersaturated_from is not None:
            legacy = ctl["supersaturated"]
            ctl["supersaturated"] = supersaturated_from(recs)
        res = controls_pass(ctl)
        ok = all(res.values())
        rec["controls"] = {"gating": {k: brief(v) for k, v in ctl.items()}, "pass": res,
                           "low_dose_corner_flags_omega_below_1": res["undersaturated"],
                           "supersaturated_reports_stability": res["supersaturated"]}
        if legacy is not None:
            rec["controls"]["supersaturated_configured_state_not_gating"] = brief(legacy)
            rec["controls"]["supersaturated_control_cell"] = {k: ctl["supersaturated"].get(k) for k in ("control_cell", "omega_median")}
    recs = apply_controls(recs, ok)
    sets, head = window_of(recs)
    rec.update({"verdict": head, "regime": REGIME[head], "controls_pass": ok, "sets": {k: len(v) for k, v in sets.items()},
                "slurry_state_headline": slurry_only_headline(recs), "per_state": per_state_summary(recs),
                "region": region_of(recs, cfg), "dose_window_Ca_T_mol_dm3": dose_window(recs),
                "cells": {cid: brief(r) for cid, r in recs.items()}})
    if not spec.get("ksp"):
        rec["note"] = spec.get("note")
    return rec


def carbonate_rows(poly):
    """Labels per polymorph from the evaluated records."""
    verdicts = {p: r["verdict"] for p, r in poly.items()}
    controls = {p: bool(r.get("controls_pass", True)) for p, r in poly.items()}
    regions = {p: "%s: %d of %d cells" % (r["region"]["grid"].split(" (")[0], r["region"]["n_passing"], r["region"]["n_cells"])
               for p, r in poly.items()}
    windows = {}
    for p, r in poly.items():
        w = r.get("dose_window_Ca_T_mol_dm3")
        windows[p] = "Ca_T %g to %g mol dm^-3" % w if w else "none"
    return k2_carbonate.k2_record(verdicts, controls, k2_carbonate_required(poly), regions, windows)


def k2_carbonate_required(poly):
    return {p: p != "ACC" for p in poly}


# ------------------------------------------------------------------ runs
class Context:
    """The inputs shared by the parts of one run."""

    def __init__(self, root, params_path=None, allow_mock=False, stride=1):
        self.stride = int(stride)                    # dry runs only: every stride-th cell of a grid (a path check)
        self.root = Path(root)
        self.cfg = run.load_config(self.root)
        self.params_path = self.root / (params_path or params_adapter.PRODUCTION_PARAMS)
        self.allow_mock = allow_mock
        self.doc, _ = params_adapter.read_table(self.params_path, allow_mock)
        self.resolver = decision.Resolver.from_table(self.doc)
        gt = self.root / gaps.GAP_TABLE
        if gt.exists():
            self.resolver = self.resolver.alias(gaps.load(gt).get("key_aliases"))
        self.rule = thr.load_thresholds(self.root / thr.COPY)["rule"]
        self.p = decision.credible_level(self.rule, self.resolver)
        from nacre.screen import mineral as mineral_mod
        self.minerals = mineral_mod.registry(self.cfg)


def acid_cfg(cfg):
    """A copy of the configuration with the wet slurry as the only registered state (the comparator is a slurry-stage state)."""
    c = json.loads(json.dumps(cfg))
    b = c["bindings"]["R-slurry"]
    b["states"] = {"slurry": b["states"]["slurry"]}
    return c


def part_carbonate(ctx, log=None):
    """K2 of calcite, aragonite and ACC over the registered grid (Ca_T, C_T, pH, I, a_w at the drying state) with the controls."""
    cells = carbonate_cells(ctx.cfg, ctx.resolver)[::ctx.stride]
    poly = {}
    for pol in POLYMORPHS:
        poly[pol] = eval_carbonate(ctx.params_path, ctx.cfg, ctx.resolver, pol, cells, ctx.p, ctx.allow_mock, log)
        poly[pol]["second_control"] = {"dose_axis_onset": second_control_onset({c: dict(r, axes=r["axes"]) for c, r in poly[pol]["cells"].items()})}
    return {"grid": {"cells": len(cells), "axes": "Ca_T x C_T x a_w(drying) x pH x I",
                     "pH": [lab for lab, _ in _axis(ctx.cfg, ctx.resolver, "pH")],
                     "I": [lab for lab, _ in _axis(ctx.cfg, ctx.resolver, "I_ionic")]},
            "polymorphs": poly, "rows": carbonate_rows(poly),
            "solubility_order": k2_carbonate.more_soluble(ctx.resolver, k2_carbonate.ksp_keys(ctx.cfg)),
            "superseded_keys": k2_carbonate.superseded_keys(ctx.cfg)}


def part_acid(ctx, log=None):
    """The acid-adjusted comparator state (pH 4.5 to 8.5): carbonates and the Ca phosphates of the ladder's slurry stage."""
    cfg = acid_cfg(ctx.cfg)
    pts = study.design_points(cfg, ctx.resolver, axes=["Ca_T", "C_T"])
    cells = []
    for ph_lab, ph in _axis(cfg, ctx.resolver, "pH_acid_adjusted"):
        for i_lab, ii in _axis(cfg, ctx.resolver, "I_ionic"):
            for pid, design, labels in pts:
                cells.append(("%s; pH=%s; I=%s" % (pid, ph_lab, _short(i_lab)), design, {"pH": ph, "I_ionic": ii},
                              dict(labels, pH=ph_lab, I=_short(i_lab))))
    carbonate = {}
    for pol in POLYMORPHS:
        carbonate[pol] = eval_carbonate(ctx.params_path, cfg, ctx.resolver, pol, cells, ctx.p, ctx.allow_mock, log, controls=True)
    cells = cells[::ctx.stride]
    pcells = phosphate_cells(cfg, ctx.resolver, "pH_acid_adjusted", drying=False)[::ctx.stride]
    phosphate = {}
    for name in cfg["k2_phases"]:
        phosphate[name] = eval_phosphate(ctx.params_path, cfg, ctx.resolver, name, pcells, ctx.p, ctx.minerals, ("slurry",),
                                         ctx.allow_mock, log)
    try:
        key_range = ctx.resolver.range("ph_slurry_acid_adjusted")
    except decision.Gap:
        key_range = None
    return {"state": "acid-adjusted comparator (incumbent phosphoric-acid pH control), wet slurry state only",
            "pH_grid": [lab for lab, _ in _axis(cfg, ctx.resolver, "pH_acid_adjusted")],
            "ph_slurry_acid_adjusted_key_range": key_range,
            "carbonate": carbonate, "phosphate": phosphate,
            "note": "comparator row: K2 only, no K3 or K4 verdict is drawn from this state (claims_redirect.md 5)"}


def part_phosphate(ctx, log=None, names=None):
    """K2 of the Ca phosphates of the ladder's slurry stage on the registered alkaline grid (Ca_T, P_T, pH, I, a_w at the drying state)."""
    cells = phosphate_cells(ctx.cfg, ctx.resolver, "pH", drying=True)[::ctx.stride]
    out = {}
    for name in (names or ctx.cfg["k2_phases"]):
        out[name] = eval_phosphate(ctx.params_path, ctx.cfg, ctx.resolver, name, cells, ctx.p, ctx.minerals,
                                   ("slurry", "drying"), ctx.allow_mock, log)
    return {"grid": {"cells": len(cells), "axes": "Ca_T x P_T x a_w(drying) x pH x I"}, "phases": out}


def stats_of(blocks):
    """(draws, capped cells, cells) over every evaluated cell of a document's parts."""
    n_cells = capped = 0
    draws = []

    def walk(node):
        nonlocal n_cells, capped
        if isinstance(node, dict):
            if "cells" in node and isinstance(node["cells"], dict):
                for r in node["cells"].values():
                    n_cells += 1
                    capped += bool(r.get("capped"))
                    if r.get("draws"):
                        draws.append(r["draws"])
            for v in node.values():
                walk(v)
    walk(blocks)
    return {"cells": n_cells, "capped_cells": capped, "draws_min": min(draws) if draws else None,
            "draws_max": max(draws) if draws else None}


def run_k2_grid(root, out_path, parts=("carbonate", "acid"), dry=False, params_path=None, allow_mock=False, label=None, log=None,
                stride=1):
    """Write one K2 document; production runs append the ledger line. Returns (path, document, stats)."""
    root, out_path = Path(root), Path(out_path)
    t0 = time.perf_counter()
    if dry:
        if not run._inside(out_path, root / run.DRYRUN_PH_DIR):
            raise run.ProductionRefused("a dry run writes only under %s" % run.DRYRUN_PH_DIR)
    else:
        from nacre.screen import ph_prov
        ph_prov.check_frozen(root)
        if not run._inside(out_path, root / run.SCREEN_DIR) or run._inside(out_path, root / run.DRYRUN_PH_DIR) \
                or run._inside(out_path, root / run.DRYRUN_DIR) or not out_path.parent.name.endswith(SUBDIR_SUFFIX):
            raise run.ProductionRefused("production output belongs in a new directory %s/<run>%s/" % (run.SCREEN_DIR, SUBDIR_SUFFIX))
        if out_path.exists():
            raise run.ProductionRefused("%s exists: a production document is never overwritten" % out_path)
    if stride != 1 and not dry:
        raise run.ProductionRefused("a production run covers the whole grid (stride 1)")
    ctx = Context(root, params_path, allow_mock, stride)
    body = {"session": SESSION, "p_cred": ctx.p, "start_draws": START_DRAWS, "half_width_max": HALF_WIDTH_MAX,
            "draw_cap": DRAW_CAP, "seed": int(ctx.cfg["propagation"]["seed"]),
            "labels": {"vocabulary": list(REGIME.values()), "nacre_type_label": "none (no such label is emitted)"}}
    if "carbonate" in parts:
        body["carbonate"] = part_carbonate(ctx, log)
    if "acid" in parts:
        body["acid_adjusted"] = part_acid(ctx, log)
    if "phosphate" in parts:
        body["phosphate"] = part_phosphate(ctx, log)
    stats = stats_of(body)
    stats.update(seconds=time.perf_counter() - t0, peak_mb=peak_mb())
    body["run"] = stats
    cfg_path = root / run.CONFIG
    prov = run._provenance(root, ctx.cfg, cfg_path, [params_adapter.RegimePriors("R-slurry", None, {}, str(ctx.params_path),
                                                                                  run._sha256_file(ctx.params_path), False)],
                           run.THRESHOLDS, dry)
    prov["run_label"] = label or out_path.parent.name
    doc = summary.build(None, prov, mock=dry or ctx.doc["mock"], extensions={"p0-w4": {"k2_grid": body}},
                        ph_rows=rows_of(body, ctx.doc))
    path = summary.write(doc, out_path)
    if not dry:
        from nacre.screen import ph_prov
        ph_prov.ledger_append(root, SESSION, prov, prov["config_file"], prov["config_hash"], [path])
    return path, doc, stats


# ------------------------------------------------------------------ rows of the document (schema v5 ph_rows)
EVIDENCE = {"sourced": "sourced", "single-source": "single-source", "computed": "computed", "gap": "gap", "analog": "analog"}
CARBONATE_INPUTS = ("pk1_carbonic", "pk2_carbonic", "log10_k_cahco3", "log10_k_caco3_aq", "log10_k_caoh", "debye_huckel_a",
                    "davies_b", "davies_i_val", "dic_slurry", "ph_slurry", "ionic_strength_slurry", "water_density")
PHOSPHATE_INPUTS = ("pka1_h3po4", "pka2_h3po4", "pka3_h3po4", "log10_k_cahpo4_aq", "log10_k_cah2po4", "log10_k_capo4", "pkw",
                    "log10_k_caoh", "debye_huckel_a", "davies_b", "davies_i_val", "ph_slurry", "ionic_strength_slurry",
                    "water_density")


def evidence_of(doc, keys):
    """{key: evidence grade} of the table keys a K2 test read; design inputs (set by the design) are not graded."""
    out = {}
    for k in keys:
        e = (doc.get("params") or {}).get(k)
        if e is None:
            out[k] = "gap"
        elif e.get("status") in EVIDENCE:
            out[k] = EVIDENCE[e["status"]]
    return out


def _k2_row(row_id, film, phase, role, framing, labels, rec, evidence, extra=None):
    k2 = {"verdict": rec["verdict"], "evidence": evidence, "regime": rec["regime"], "controls_pass": rec.get("controls_pass"),
          "slurry_state_headline": rec.get("slurry_state_headline"), "n_passing_cells": rec["region"]["n_passing"],
          "n_cells": rec["region"]["n_cells"], "dose_window_Ca_T_mol_dm3": rec.get("dose_window_Ca_T_mol_dm3"),
          "region": rec["region"]["grid"]}
    row = {"row_id": row_id, "film_id": film, "phase": phase, "stage": "slurry", "role": role, "route": None,
           "framing": framing, "labels": list(labels), "provisional": False, "retained_mass": None, "K2": k2}
    row.update(extra or {})
    return row


def rows_of(body, doc):
    """ph_rows of a K2 document: one row per polymorph or phase and state (registered alkaline grid, acid-adjusted comparator)."""
    rows = []
    cb = body.get("carbonate")
    if cb:
        for pol, rec in cb["polymorphs"].items():
            lab = cb["rows"]["polymorphs"][pol]["label"]
            ev = evidence_of(doc, (rec["ksp_key"],) + CARBONATE_INPUTS)
            rows.append(_k2_row("k2:carbonate:%s:registered" % pol, "k2_carbonate_%s" % pol, "CaCO3 (%s)" % pol, "baseline", pol,
                                [lab], rec, ev, {"state": "registered alkaline slurry grid", "carbonate_label": lab,
                                                 "controls": rec.get("controls", {}).get("pass")}))
    ac = body.get("acid_adjusted")
    if ac:
        for pol, rec in ac["carbonate"].items():
            ev = evidence_of(doc, (rec["ksp_key"],) + CARBONATE_INPUTS)
            rows.append(_k2_row("k2:carbonate:%s:acid" % pol, "k2_carbonate_%s" % pol, "CaCO3 (%s)" % pol, "comparator", pol,
                                ["acid-adjusted comparator state, pH 4.5 to 8.5; K2 only"], rec, ev,
                                {"state": "acid-adjusted (incumbent phosphoric-acid pH control)"}))
        for name, rec in ac["phosphate"].items():
            keys = ((rec["ksp_key"],) if rec["ksp_key"] else ()) + PHOSPHATE_INPUTS
            ev = evidence_of(doc, keys)
            if not rec["ksp_key"]:
                ev["K_sp"] = "gap"
            rows.append(_k2_row("k2:%s:acid" % name, "k2_%s" % name, rec["formula"], "comparator", rec["ladder_phase"],
                                ["acid-adjusted comparator state, pH 4.5 to 8.5; K2 only"], rec, ev,
                                {"state": "acid-adjusted (incumbent phosphoric-acid pH control)"}))
    ph = body.get("phosphate")
    if ph:
        for name, rec in ph["phases"].items():
            keys = ((rec["ksp_key"],) if rec["ksp_key"] else ()) + PHOSPHATE_INPUTS
            ev = evidence_of(doc, keys)
            if not rec["ksp_key"]:
                ev["K_sp"] = "gap"
            rows.append(_k2_row("k2:%s:registered" % name, "k2_%s" % name, rec["formula"], "candidate", rec["ladder_phase"],
                                ["registered alkaline slurry grid; K2 only here (K3, K4 in their own rows)"], rec, ev,
                                {"state": "registered alkaline slurry grid"}))
    return rows
