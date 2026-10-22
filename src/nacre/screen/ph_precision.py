"""Required-precision map and flip values of the redirected screen (PH-W4.3).

    python -m nacre.screen ph-precision --out results/preprint/screen/precision_ph/precision_map.json

Method: configs/preprint/precision_method.md (nacre.screen.precision). Inputs: the frozen priors, thresholds and ladder of
p0-cp5 and the production runs under results/preprint/screen/*_ph/. Nothing here sets a prior, a threshold or a verdict rule.

Three kinds of row, each stating its kind:
  mc      the registered statistic. The prior of one parameter is contracted about its median (precision.required_precision) on
          the production model at the production design point; draws are reproduced from the production seeds and checked
          against the stored production masses before use.
  closed  a flip value that follows in closed form from a registered edge and production draws (no contraction).
  gap     the quantity has no registered prior. Its flip value is printed; the precision it would need is |q - flip| for a true
          value q, because no registered bound exists to take a width over. Where a registered bound exists it is used.
"""
import csv
import json
import math
import re
import time
from pathlib import Path

import numpy as np
import yaml

from nacre.screen import admissibility, chain, decision, k2_grid, params_adapter, ph_prov, precision, propagate, run, study
from nacre.screen import thresholds as thr

SESSION = "PH-W4.3"
PRE_RUN_SHA = "8073c8e"
OUT_DIR = Path("results") / "preprint" / "screen" / "precision_ph"
DETAIL_POINT = "Ca_T=0.001 mol dm^-3; C_T=dic_slurry@min; a_w=wet_film"
FARADAY = 96485.33212
N_MC = 2 ** 18
N_CHECK = 2 ** 14
RUNS = ("table_ph", "k2_grid_ph", "phosphate_films_ph", "ignorance_ph", "sweep_independent_ph", "sweep_pcred_0.6_ph",
        "sweep_pcred_0.99_ph", "sweep_mcos_0.1_ph", "sweep_mcos_0.2_ph", "sweep_untruncated_ph", "sens_acc_omega_ph",
        "sens_gamma_sl0_untruncated_ph", "sens_gamma_sl0_untruncated_r2_ph")


# ------------------------------------------------------------------ contraction of one parameter inside a joint prior
class Contracted:
    """A joint prior with the prior of one parameter contracted by s about its median (duck-typed JointPrior for propagation)."""

    def __init__(self, joint, name, s):
        self.joint, self.j, self.s = joint, joint.names.index(name), float(s)
        self.prior = joint.priors[self.j]
        self.priors, self.spearman, self.names, self.symbols = joint.priors, joint.spearman, joint.names, joint.symbols
        self.k = joint.k

    def sample(self, rng, n):
        x = self.joint.sample(rng, n)
        x[:, self.j] = precision.contract(self.prior, x[:, self.j], self.s)
        return x


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, root):
        self.root = Path(root)
        self.k2 = k2_grid.Context(self.root)
        self.cfg, self.rule, self.resolver, self.p = self.k2.cfg, self.k2.rule, self.k2.resolver, self.k2.p
        self.level = precision.rule_level(self.p)
        self.params_path = self.k2.params_path
        self.table = yaml.safe_load(self.params_path.read_text(encoding="utf-8"))["params"]
        self.prod = {r: json.loads((self.root / run.SCREEN_DIR / r / "summary.json").read_text(encoding="utf-8")) for r in RUNS}
        seeds = np.random.SeedSequence(self.cfg["propagation"]["seed"]).spawn(len(params_adapter.REGIMES) + 1)
        self.seed = int(seeds[-1].generate_state(1)[0])
        self.points = study.design_points(self.cfg, self.resolver)

    def key(self, name):
        return self.table.get(name) or {}

    def prior_of(self, name):
        e = self.key(name)
        pr = e.get("prior") or {}
        gap = pr.get("family") in (None, "none")
        return {"key": name, "gap": gap, "family": pr.get("family"), "low": pr.get("low", (e.get("range") or {}).get("min")),
                "high": pr.get("high", (e.get("range") or {}).get("max")), "value": e.get("value"), "unit": e.get("unit"),
                "evidence_grade": e.get("best_grade"), "status": e.get("status"), "sources": (e.get("sources") or [])[:6]}


# ------------------------------------------------------------------ evidence table: methods for "measurable by"
KIND_UNITS = {"J/m2": {"J m^-2": 1.0, "J/m^2": 1.0, "mJ m^-2": 1e-3, "mJ/m^2": 1e-3},
              "log10": {"1": 1.0},
              "kJ/mol": {"kJ mol^-1": 1.0, "kJ/mol": 1.0, "kcal mol^-1": 4.184, "kcal/mol": 4.184}}


def _num(text, kind):
    """First number of a stated uncertainty ('+-0.02', '0.02'), in the unit of the value."""
    m = re.search(r"(?:\u00b1|\+-)\s*([0-9.]+(?:[eE][-+]?[0-9]+)?)", text or "")
    return float(m.group(1)) if m else None


def evidence_methods(root, quantities, kind=None):
    """Methods of the evidence-table rows of the named quantities, verbatim, with row counts, the stated uncertainties and the
    spread of the values across rows (both converted to the unit kind, 'J/m2', 'log10', 'kJ/mol', or left as printed)."""
    rows = list(csv.DictReader(open(Path(root) / "lit" / "evidence_table.csv", encoding="utf-8")))
    out = {}
    conv = KIND_UNITS.get(kind, {})
    for r in rows:
        if r["quantity"] not in quantities:
            continue
        m = re.sub(r"\s+", " ", r["method"]).strip()
        d = out.setdefault((r["quantity"], m), {"quantity": r["quantity"], "method": m, "rows": [], "grades": set(), "values": [], "stated": []})
        d["rows"].append(r["row_id"])
        d["grades"].add(r["grade"])
        f = conv.get(r["unit"].strip()) if kind else 1.0
        if f is None:
            continue
        try:
            v = float(r["value"])
        except ValueError:
            continue
        if kind == "log10" and v >= 0:
            continue
        d["values"].append(v * f)
        u = _num(r["range_or_uncertainty"], kind)
        if u is not None:
            d["stated"].append(u * f)
    res = []
    for d in out.values():
        v, st = d.pop("values"), d.pop("stated")
        d["n_rows"] = len(d["rows"])
        d["rows"] = d["rows"][:8]
        d["grades"] = sorted(d["grades"])
        d["value_spread"] = [min(v), max(v)] if len(v) > 1 else None
        d["stated_uncertainty_min"] = min(st) if st else None
        res.append(d)
    return sorted(res, key=lambda d: -d["n_rows"])[:6]


def reach(purposes, methods):
    """Per purpose {hw, kind}: 'within reach' when a listed method states an uncertainty, or shows a spread across its rows, of at
    most the required half-width; 'not within reach' when every figure is larger; 'undetermined' when no method gives one. The
    spread is a reproducibility proxy taken from the evidence table, not a stated uncertainty."""
    out = []
    for pu in purposes:
        figs = []
        for m in methods:
            if m.get("stated_uncertainty_min") is not None:
                figs.append((m["stated_uncertainty_min"], "stated"))
            if m.get("value_spread"):
                figs.append(((m["value_spread"][1] - m["value_spread"][0]) / 2, "spread"))
        if pu.get("hw") is None:
            verdict = "not assessed"
        elif not figs:
            verdict = "undetermined (no listed method gives an uncertainty or a spread in this unit)"
        else:
            best = min(figs)
            verdict = ("within reach" if best[0] <= pu["hw"] else "not within reach") + " (smallest figure %.3g, %s; needed %.3g)" % (best[0], best[1], pu["hw"])
        out.append({"purpose": pu["purpose"], "required_half_width": pu.get("hw"), "unit": pu.get("kind"), "assessment": verdict})
    return out


# ------------------------------------------------------------------ the production design point, reproduced
def reproduce_point(ctx, target=DETAIL_POINT, framing="calcite", n=N_CHECK):
    """Draws, inputs and outputs of the production decision point (ignorance prior set), checked against the stored masses."""
    idx = [i for i, (pid, _, _) in enumerate(ctx.points) if pid == target][0]
    framings = list((ctx.rule.get("study", {}).get("framings") or {}).get("registered") or ["calcite"])
    seeds = np.random.SeedSequence(ctx.seed).spawn(len(ctx.points) * len(framings) + 3)
    sd = int(seeds[idx * len(framings) + framings.index(framing)].generate_state(1)[0])
    rec, orig = [], chain.evaluate

    def wrap(x, *a, **k):
        rec.append({kk: np.array(v) for kk, v in x.items()})
        return orig(x, *a, **k)
    chain.evaluate = wrap
    try:
        states = study.load_point(ctx.params_path, ctx.cfg, framing, ctx.points[idx][1], False, "ignorance", True)
        outs, _ = study.propagate_states(states, n, sd, int(ctx.cfg["propagation"]["chunk"]))
    finally:
        chain.evaluate = orig
    st = {sid: study.state_samples(o) for sid, (o, _, _) in outs.items()}
    m = admissibility.mask(st)["admitted"]
    x = rec[0]
    return {"states": states, "outs": outs, "x": x, "mask": m, "o": outs["slurry"][0], "seed": sd, "n": n}


def check_against_production(ctx, pt):
    """The reproduced C3a band mass and M_adm equal the stored production values (exact)."""
    c3 = ctx.prod["ignorance_ph"]["study"]["by_design"]
    det = ctx.prod["ignorance_ph"]["claims"]["C3"]["detail_point"]
    rec = pt["o"]["nucleate"]
    good = float(np.mean((rec["f_theta"] <= 0.5)[pt["mask"]]))
    stored = ctx.prod["ignorance_ph"]["claims"]["C3"]["tests"]["C3a"]["P_good"] if "tests" in ctx.prod["ignorance_ph"]["claims"]["C3"] else None
    return {"design_point": det, "P_good_C3a_reproduced": good, "P_good_C3a_stored": stored,
            "M_adm_reproduced": float(pt["mask"].mean()),
            "equal": stored is None or abs(good - stored) < 1e-12}


def ranking(ctx, run_name, link, quantity, top=3):
    """Top Sobol total-order and Shapley contributors of one production link quantity."""
    lk = ctx.prod[run_name]["regimes"]["R-slurry"]["links"][link]
    sh = lk["shapley"][quantity]
    so = lk["sobol"].get(quantity, {})
    ranked = sorted(sh.items(), key=lambda kv: -abs(kv[1]["estimate"]))[:top]
    return {"run": run_name, "link": link, "quantity": quantity,
            "top": [{"parameter": k, "shapley": round(v["estimate"], 4), "shapley_ci_low": round(v["ci_low"], 4),
                     "sobol_total": round(so.get(k, {}).get("total_order", {}).get("estimate", float("nan")), 4)}
                    for k, v in ranked]}


def qs(v, mask=None, levels=(0.05, 0.5, 0.95)):
    v = np.asarray(v, float)
    if mask is not None:
        v = v[mask]
    v = v[np.isfinite(v)]
    return [float(np.quantile(v, q)) for q in levels]


# ------------------------------------------------------------------ MC rows
def mc_ratio(model, joint, parameter, edges, seed, level, n=N_MC):
    """precision.required_precision twice (two seeds): the second is a replicate; both are reported."""
    outs = []
    for sd in (seed, seed + 1):
        r = precision.required_precision(model, joint, parameter, edges, n, sd, level=level, key="symbol")
        outs.append(r)
    r = outs[0]
    rec = {"status": r.status, "width_ratio": r.width_ratio, "prior_width_stated_variable": r.prior_width,
           "required_width_stated_variable": r.required_width, "nearest_threshold": float(r.nearest_threshold),
           "interval_at_prior": [float(a) for a in r.interval_at_prior], "monotone": bool(r.monotone), "n": n, "seed": seed,
           "replicate": {"seed": seed + 1, "status": outs[1].status, "width_ratio": outs[1].width_ratio}}
    return rec


def joint_ratio(model, joint, parameters, edges, n, seed, level):
    """Largest common s at which the verdict is decided when every named parameter is contracted by s together (same grid and
    bisection as precision.required_precision, common random numbers)."""
    js = [joint.names.index(q) for q in parameters]
    x = joint.sample(np.random.default_rng(seed), n)
    cols = [p.symbol for p in joint.priors]

    def decided_at(s):
        xs = x.copy()
        for j in js:
            xs[:, j] = precision.contract(joint.priors[j], x[:, j], s)
        return precision.decided(precision.credible_interval(model({c: xs[:, i] for i, c in enumerate(cols)}), level), edges)
    if decided_at(1.0):
        return {"status": "already_clears", "width_ratio": 1.0}
    if not decided_at(0.0):
        return {"status": "unreachable", "width_ratio": None}
    grid = np.linspace(0.0, 1.0, precision.GRID)
    flags = [decided_at(g) for g in grid]
    last = max(i for i, f in enumerate(flags) if f)
    lo, hi = grid[last], grid[last + 1]
    while hi - lo > 1e-4:
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if decided_at(mid) else (lo, mid)
    return {"status": "ok", "width_ratio": float(lo), "monotone": bool(all(flags[i] >= flags[i + 1] for i in range(len(flags) - 1))),
            "parameters": list(parameters), "n": n, "seed": seed}


def c1_rows(ctx, pt):
    states = pt["states"]
    rp = dict(states)["slurry"]
    edge = ctx.prod["ignorance_ph"]["claims"]["C1"]["side_by_side"]["C1_dupre"]["tests"]["C1"]["edge"]
    sub = run.link_joint(rp.joint, "anchor")
    model_all = chain.sensitivity_model("anchor")
    rows = []
    x = pt["x"]
    g_ow = x["u_gamma_ow"] * (x["gamma_o"] + x["gamma_w"])
    g_op = x["u_gamma_op"] * (x["gamma_o"] + x["gamma_p"])
    flip = g_ow + x["gamma_sl0"] - edge          # Dupre: gamma_op* = gamma_ow + gamma_pw - m_W
    out = pt["o"]["anchor"]["W_adh_wet_comparator"]
    for par, unit_scale in (("aux:u_gamma_ow", x["gamma_o"] + x["gamma_w"]), ("aux:u_gamma_op", x["gamma_o"] + x["gamma_p"])):
        mc = mc_ratio(lambda d: model_all(d)["W_adh_wet_comparator"], sub, par, [edge], ctx.seed, ctx.level)
        sym = "gamma_ow" if par.endswith("ow") else "gamma_op"
        scale = float(np.median(unit_scale))
        mc["required_width_J_m2"] = None if mc["required_width_stated_variable"] is None else mc["required_width_stated_variable"] * scale
        mc["prior_width_J_m2"] = mc["prior_width_stated_variable"] * scale
        rows.append({"id": "c1_dupre_" + sym, "link": "C1", "kind": "mc", "quantity": sym + " (ignorance prior u*(sum of dry energies))",
                     "parameter": par, "unit": "J m^-2 (stated variable u, scaled by the median bound %.4g J m^-2)" % scale,
                     "verdict_now": "inconclusive (Dupre comparator; P_good %.3f; never a finding)" % ctx.prod["ignorance_ph"]["claims"]["C1"]["side_by_side"]["C1_dupre"]["P_good"],
                     "settles": "C1 (Dupre comparator) feasible or falsified", "required_precision": mc,
                     "flip": {"quantity": "gamma_op* = gamma_ow + gamma_pw - m_W" if sym == "gamma_op" else "gamma_ow* = gamma_op - gamma_pw + m_W",
                              "unit": "J m^-2", "m_W": edge, "flip_q05_q50_q95": qs(flip if sym == "gamma_op" else g_op - x["gamma_sl0"] + edge)},
                     "prior": {"low_high_J_m2": [0.0, float(np.median(unit_scale))], "gap": False, "family": "ignorance: uniform on [0, sum of dry energies]"},
                     "evidence_grade": "ignorance prior (bounds: gamma_o B, gamma_w C, gamma_p B)",
                     "sensitivity": ranking(ctx, "ignorance_ph", "anchor", "W_adh_wet_comparator"),
                     "_kind": "J/m2", "_reach": [{"purpose": "single-parameter narrowing", "hw": None if mc["required_width_J_m2"] is None else mc["required_width_J_m2"] / 2, "kind": "J m^-2"}],
                     "measurable_by_quantities": ["gamma_oxide_surface", "gamma_oxide_water", "w_adh_wet", "work_of_adhesion_catechol_oxide"]})
    jr = joint_ratio(lambda d: model_all(d)["W_adh_wet_comparator"], sub, ["aux:u_gamma_ow", "aux:u_gamma_op"], [edge], N_MC, ctx.seed, ctx.level)
    sc_ow, sc_op = float(np.median(x["gamma_o"] + x["gamma_w"])), float(np.median(x["gamma_o"] + x["gamma_p"]))
    jr["required_width_J_m2"] = {"gamma_ow": None if jr["width_ratio"] is None else 0.95 * jr["width_ratio"] * sc_ow,
                                 "gamma_op": None if jr["width_ratio"] is None else 0.95 * jr["width_ratio"] * sc_op}
    rows.append({"id": "c1_dupre_joint", "link": "C1", "kind": "mc", "quantity": "gamma_ow and gamma_op together (both contracted by s)",
                 "parameter": "aux:u_gamma_ow + aux:u_gamma_op", "unit": "J m^-2", "verdict_now": "inconclusive (Dupre comparator; no single parameter decides it)",
                 "settles": "C1 (Dupre comparator)", "required_precision": jr, "flip": {"quantity": "gamma_op* = gamma_ow + gamma_pw - m_W", "unit": "J m^-2", "m_W": edge},
                 "prior": {"gap": False, "family": "ignorance"}, "evidence_grade": "ignorance prior", "sensitivity": ranking(ctx, "ignorance_ph", "anchor", "W_adh_wet_comparator"),
                 "_kind": "J/m2", "_reach": [{"purpose": "both contact energies narrowed together", "hw": None if jr["width_ratio"] is None else jr["required_width_J_m2"]["gamma_op"] / 2, "kind": "J m^-2"}],
                 "measurable_by_quantities": ["gamma_oxide_surface", "gamma_oxide_water", "work_of_adhesion_catechol_oxide"]})
    # flagged analog (side by side)
    sub_a = run.link_joint(rp.joint, "anchor")
    key = "w_adh_wet_catechol_oxide_analog"
    name = [n for n in sub_a.names if n == key]
    if name:
        mc = mc_ratio(lambda d: model_all(d)["W_adh_wet_analog"], sub_a, key, [edge], ctx.seed, ctx.level)
        pr = ctx.prior_of(key)
        rows.append({"id": "c1_analog_w_adh_wet", "link": "C1", "kind": "mc", "quantity": "W_adh,wet (flagged analog key)",
                     "parameter": key, "unit": "ln(J m^-2) (loguniform prior, stated variable ln)", "verdict_now": "inconclusive (analog; P_good %.3f)" % ctx.prod["ignorance_ph"]["claims"]["C1"]["side_by_side"]["C1_analog"]["P_good"],
                     "settles": "C1 (analog) feasible or falsified", "required_precision": mc,
                     "flip": {"quantity": "W_adh,wet = m_W", "unit": "J m^-2", "value": edge},
                     "prior": {"low_high_J_m2": [pr["low"], pr["high"]], "gap": False, "family": pr["family"]},
                     "evidence_grade": pr["evidence_grade"], "sensitivity": ranking(ctx, "ignorance_ph", "anchor", "W_adh_wet_analog", 2),
                     "_kind": "J/m2", "_reach": [{"purpose": "true value at the analog median 0.002 J m^-2", "hw": abs(edge - 0.002), "kind": "J m^-2"}],
                     "measurable_by_quantities": ["w_adh_wet", "work_of_adhesion_catechol_oxide", "adhesion_force"]})
    rows.append({"id": "c1_pmf", "link": "C1", "kind": "gap", "quantity": "Delta_F_pmf and A_c (registered PMF route W = Delta_F_pmf / A_c)",
                 "parameter": "Delta_F_pmf, A_c", "unit": "J m^-2 for W; J for Delta_F_pmf", "verdict_now": "inconclusive (gap, counted inconclusive)",
                 "settles": "C1 (decisive route)", "prior": {"gap": True},
                 "flip": {"quantity": "W_adh,wet* = m_W; Delta_F_pmf* = m_W * A_c", "unit": "J m^-2", "value": edge},
                 "required_precision": {"status": "gap", "rule": "no registered prior or bound: a W (or Delta_F/A_c) known to +-d decides the verdict "
                                        "when |W - %.5f| > d; for W at the analog median 0.002 J m^-2 that is d < %.5f J m^-2" % (edge, abs(0.002 - edge))},
                 "evidence_grade": "gap", "sensitivity": None, "_kind": "J/m2", "_reach": [{"purpose": "true value at the analog median 0.002 J m^-2", "hw": abs(edge - 0.002), "kind": "J m^-2"}],
                 "measurable_by_quantities": ["w_adh_wet", "work_of_adhesion_catechol_oxide", "adhesion_force", "binding_energy_catechol_oxide"]})
    return rows


def nucleation_rows(ctx, pt):
    x, o, m = pt["x"], pt["o"]["nucleate"], pt["mask"]
    p = ctx.p
    gp, gnv = x["gamma_p"], x["gamma_nv"]
    sl, nl = o["gamma_sl_insitu"], x["gamma_nl"]
    gsn = x["u_gamma_sn"] * (gp + gnv)
    rows = []
    rk_f = ranking(ctx, "ignorance_ph", "nucleate", "f_theta")
    rk_s = ranking(ctx, "ignorance_ph", "nucleate", "S_spread")
    # gamma_sn
    pr_sn = [float(np.quantile(gsn[m], 0.025)), float(np.quantile(gsn[m], 0.975))]
    rows.append({"id": "gamma_sn", "link": "C3a / K3a", "kind": "closed", "quantity": "gamma_sn (template-nucleus energy, ignorance prior u*(gamma_p+gamma_nv))",
                 "parameter": "aux:u_gamma_sn", "unit": "J m^-2",
                 "verdict_now": "falsified (P_good = P(gamma_sn <= gamma_sl) = %.4f at the detail point; carbonate chain, admitted draws)" % float(np.mean((gsn <= sl)[m])),
                 "settles": "C3a / K3a (cos theta >= 0): feasible only if gamma_sn <= gamma_sl",
                 "prior": {"central95_J_m2": pr_sn, "gap": False, "family": "ignorance (carbonate: gamma_nv sourced); for HAp and ACP gamma_nv is a gap, so the range is undefined"},
                 "flip": {"quantity": "gamma_sn* = gamma_sl - m_cos*gamma_nl (m_cos = 0)", "unit": "J m^-2", "q05_q50_q95": qs(sl, m),
                          "prior_mass_below_flip": float(np.mean((gsn <= sl)[m]))},
                 "required_precision": {"status": "already_clears", "width_ratio": 1.0,
                                        "note": "decided (falsified) at the prior; reversal needs a measured gamma_sn below the flip: a true value at 0 needs +-%.5f J m^-2, "
                                                "at the prior median %.3f needs +-%.3f" % (float(np.median(sl[m])), float(np.median(gsn[m])), float(np.median(gsn[m]) - np.median(sl[m]))),
                                        "required_half_width_at_prior_median_J_m2": float(np.median(gsn[m]) - np.median(sl[m]))},
                 "evidence_grade": "ignorance prior (bounds gamma_p B, gamma_nv B)", "sensitivity": rk_f,
                 "measurable_by_quantities": ["gamma_sub_nuc", "gamma_eff_het"], "_kind": "J/m2", "_reach": [{"purpose": "confirm falsified (true value at the prior median)", "hw": float(np.median(gsn[m]) - np.median(sl[m])), "kind": "J m^-2"}, {"purpose": "reverse to feasible (true value below the flip)", "hw": float(np.median(sl[m])), "kind": "J m^-2"}]})
    # gamma_nv: K3a does not depend on it for any value >= 0
    need = float(np.median(sl[m])) / p
    rows.append({"id": "gamma_nv", "link": "K3a / K4", "kind": "closed", "quantity": "gamma_nv (nucleus-vapour energy; gap for HAp and ACP, sourced for calcite)",
                 "parameter": "gamma_nv_hap, gamma_nv_acp (gaps)", "unit": "J m^-2",
                 "verdict_now": "undetermined for HAp and ACP (gap); the carbonate chain is falsified", "settles": "K3a and K4 (through gamma_sn <= u*(gamma_p + gamma_nv))",
                 "prior": {"gap": True, "calcite_analog_range_J_m2": [0.428, 0.86]},
                 "flip": {"quantity": "gamma_p + gamma_nv <= gamma_sl / p_cred for P(gamma_sn <= gamma_sl) >= p_cred", "unit": "J m^-2",
                          "value": need, "note": "needs gamma_p + gamma_nv <= %.4f J m^-2 but gamma_p alone is >= 0.0433 J m^-2: no gamma_nv >= 0 reaches the flip" % need},
                 "required_precision": {"status": "no_flip", "rule": "K3a is falsified under the ignorance prior of gamma_sn for every gamma_nv >= 0; a measurement of gamma_nv cannot settle K3a or K4 towards feasible"},
                 "evidence_grade": "gap (HAp, ACP); calcite B", "sensitivity": ranking(ctx, "ignorance_ph", "nucleate", "S_spread"),
                 "measurable_by_quantities": ["surface_energy_calcite_dry", "gamma_organic_water"]})
    # gamma_nl
    up = sl[m]
    rows.append({"id": "gamma_nl", "link": "K4 (spreading) / C4", "kind": "closed",
                 "quantity": "gamma_nl (nucleus-liquid energy; calcite sourced, HAp and ACP gaps)", "parameter": "gamma_nl_calcite; gamma_nl_hap, gamma_nl_acp (gaps)",
                 "unit": "J m^-2", "verdict_now": "falsified for calcite (P(S_spread >= 0) = 0); undetermined for HAp and ACP (gap)",
                 "settles": "K4 spreading route S_spread = gamma_sl - gamma_sn - gamma_nl >= m_S",
                 "prior": {"low_high_J_m2": [0.072, 0.487], "gap": False, "family": "uniform (calcite); HAp, ACP none registered"},
                 "flip": {"quantity": "gamma_nl* = gamma_sl - gamma_sn - m_S <= gamma_sl", "unit": "J m^-2", "upper_bound_q05_q50_q95": qs(sl, m),
                          "P_gamma_sl_gt_gamma_nl": float(np.mean((sl > nl)[m])),
                          "note": "a spreading verdict of feasible needs gamma_nl below about %.4f J m^-2, %.0fx below the lowest calcite value 0.072" % (float(np.median(up)), 0.072 / float(np.median(up)))},
                 "required_precision": {"status": "ok_by_inspection", "required_half_width_J_m2": float(0.072 - np.median(up)),
                                        "rule": "any estimate of gamma_nl_hap with an uncertainty below its own distance to the flip (%.4f J m^-2) decides; for a value as low as the calcite minimum this is +-%.3f J m^-2" % (float(np.median(up)), float(0.072 - np.median(up)))},
                 "evidence_grade": "calcite B; HAp, ACP gap", "sensitivity": rk_s,
                 "measurable_by_quantities": ["gamma_calcite_water", "gamma_eff_het", "contact_angle_caco3"],
                 "_kind": "J/m2", "_reach": [{"purpose": "confirm falsified (value at the calcite minimum)", "hw": float(0.072 - np.median(up)), "kind": "J m^-2"}, {"purpose": "reverse to feasible (value below the flip)", "hw": float(np.median(up)), "kind": "J m^-2"}]})
    # A_patch (C3b)
    nn = o["N_nuc"][m]
    nn = nn[np.isfinite(nn)]
    qn = float(np.quantile(nn, p))
    q1 = float(np.quantile(nn, 1 - p))
    a_fals = math.log(1 / (1 - p)) / qn if qn > 0 else float("inf")
    rows.append({"id": "A_patch", "link": "C3b / K3b", "kind": "gap", "quantity": "A_patch (receiving patch area; N_req = ln(1/(1-p))/A_patch)",
                 "parameter": "patch_area", "unit": "m^2", "verdict_now": "inconclusive (gap counted inconclusive)", "settles": "C3b falsified",
                 "prior": {"gap": True, "registered_bound": "a_asp <= A_patch <= pi d_p^2/4 (loguniform); both bound keys absent"},
                 "flip": {"quantity": "A* = ln(1/(1-p)) / q_p(N_nuc) for the falsified side; the feasible side needs N_nuc q_(1-p) >= N_req", "unit": "m^2",
                          "falsified_for_A_below": a_fals, "N_nuc_q_1_minus_p": q1, "N_nuc_q_p": qn,
                          "note": "C3b is falsified for every A_patch below %.3g m^2; a feasible verdict is impossible (q_(1-p) of N_nuc is %.3g m^-2)" % (a_fals, q1)},
                 "required_precision": {"status": "no_flip_in_physical_range", "rule": "A_patch is a micrometre-scale contact patch (<= pi d_p^2/4); the flip lies ~20 orders above it, so the verdict does not depend on A_patch"},
                 "evidence_grade": "gap", "sensitivity": ranking(ctx, "ignorance_ph", "nucleate", "N_nuc"),
                 "measurable_by_quantities": ["asperity_contact_area", "cathode_particle_diameter"], "_reach": []})
    return rows


# ------------------------------------------------------------------ K2 phosphate cells
def k2_cells(ctx):
    cells = k2_grid.phosphate_cells(ctx.cfg, ctx.resolver, "pH", drying=True)
    return {cid: (design, fixed, labels) for cid, design, fixed, labels in cells}


def cell_model_and_joint(ctx, spec, design, fixed, states=("slurry", "drying")):
    base = ctx.k2.minerals["hap"]
    bind = k2_grid.phosphate_bindings(ctx.cfg, spec)
    if spec.get("n_hyd_key"):
        bind["n_hyd"] = spec["n_hyd_key"]
    design_here = {k: v for k, v in design.items() if "@" not in k}
    rps, evals = {}, {}
    for sid in states:
        a_w = 1.0 if sid == "slurry" else float(design.get("a_w@drying", 1.0))
        extra = [study._fixed(s, v, k2_grid.AXIS_SI.get(s, "1"), "design axis") for s, v in {**design_here, **fixed}.items()]
        extra.append(study._fixed("a_w", a_w, "1", "registered state value"))
        drop = set(fixed) | set(design_here)
        rps[sid] = params_adapter.regime_priors(ctx.params_path, "R-slurry", False, bindings={s: k for s, k in bind.items() if s not in drop},
                                                absent="gap", extra=extra)
        evals[sid] = (k2_grid.phosphate_omega_evaluate(spec, a_w, base), a_w)
    return rps[states[0]].joint, evals


def cell_statistic(values, level):
    """Worst-state interval: (min of lower ends, min of upper ends) over the states; decided iff no edge lies inside."""
    los, his = [], []
    for j in range(values.shape[1]):
        v = values[:, j]
        v = v[np.isfinite(v)]
        if not v.size:
            return (float("nan"), float("nan"))
        a = (1 - level) / 2
        los.append(np.quantile(v, a))
        his.append(np.quantile(v, 1 - a))
    return (min(los), min(his))


def k2_mc_rows(ctx, max_cells=6):
    """Required precision of log10 K_sp at inconclusive cells of the sourced phosphates (hap, btcp, acp)."""
    cells = k2_cells(ctx)
    films = ctx.prod["phosphate_films_ph"]["extensions"]["p0-w4"]["ph_production"]["k2_phosphate"]["phases"]
    rows = []
    for name in ("hap", "btcp", "acp", "ocp"):
        spec = ctx.cfg["k2_phases"][name]
        rec = films[name]
        inc = sorted(c for c, r in rec["cells"].items() if r["verdict"] == "inconclusive" and r.get("verdict_before_control", r["verdict"]) == "inconclusive")
        if not inc:
            rows.append({"id": "k2_ksp_" + name, "link": "K2", "kind": "mc", "quantity": "log10 K_sp (%s)" % spec["formula"], "parameter": spec["ksp"],
                         "required_precision": {"status": "no_inconclusive_cell_before_control", "n_inconclusive_cells_before_control": 0,
                                                "note": "the phase's cells are inconclusive only through its failed falsifiability control (%s)" % rec.get("controls_pass")},
                         "verdict_now": rec["regime"], "settles": "K2", "kind_note": "control-gated"})
            continue
        step = max(1, len(inc) // max_cells)
        sel = inc[::step][:max_cells]
        per = []
        for cid in sel:
            design, fixed, labels = cells[cid]
            joint, evals = cell_model_and_joint(ctx, spec, design, fixed)

            def model(d, evals=evals):
                cols = []
                for sid, (ev, a_w) in evals.items():
                    dd = dict(d)
                    dd["a_w"] = np.full_like(np.asarray(d["K_sp"], float), a_w)
                    cols.append(ev(dd)[0]["speciation"]["Omega_bulk"])
                return np.column_stack(cols)
            per.append(_cell_precision(ctx, joint, model, spec, cid, labels))
        rows.append({"id": "k2_ksp_" + name, "link": "K2", "kind": "mc", "quantity": "log10 K_sp (%s)" % spec["formula"], "parameter": spec["ksp"],
                     "unit": "log10 units (stated variable; log10-transform key)", "verdict_now": "%s (%d of %d cells inconclusive)" % (rec["regime"], len(inc), len(rec["cells"])),
                     "settles": "K2 (dissolution stability) in the inconclusive cells", "cells": per,
                     "prior": ctx.prior_of(spec["ksp"]), "evidence_grade": ctx.key(spec["ksp"]).get("best_grade"),
                     "n_inconclusive_cells": len(inc), "summary": _k2_summary(per), "sensitivity": None,
                     "_kind": "log10", "_reach": [{"purpose": "median required half-width over the cells where K_sp alone decides", "hw": _k2_summary(per)["median_required_half_width_log10"], "kind": "log10"}],
                     "measurable_by_quantities": {"hap": ["ksp_hap"], "btcp": ["ksp_beta_tcp"], "acp": ["ksp_acc_phosphate"], "ocp": ["ksp_ocp"]}[name]})
    return rows


def _k2_summary(per):
    ok = [c for c in per if c["status"] == "ok"]
    return {"cells_evaluated": len(per), "ok": len(ok), "unreachable": sum(c["status"] == "unreachable" for c in per),
            "already_clears": sum(c["status"] == "already_clears" for c in per),
            "median_width_ratio": float(np.median([c["width_ratio"] for c in ok])) if ok else None,
            "median_required_half_width_log10": float(np.median([c["required_width_log10"] for c in ok])) / 2 if ok else None,
            "prior_width_log10": per[0]["prior_width_log10"] if per else None,
            "note": "unreachable: narrowing K_sp alone leaves the cell inconclusive; the speciation inputs must improve with it"}


def _cell_precision(ctx, joint, model, spec, cid, labels):
    def stat(values, level):
        return cell_statistic(values, level)
    r = precision.required_precision(model, joint, spec["ksp"], [1.0], N_MC // 4, int(ctx.cfg["propagation"]["seed"]), level=ctx.level,
                                     key="symbol", statistic=stat)
    pr = [p for p in joint.priors if p.symbol == "K_sp"][0]
    return {"cell": cid, "axes": labels, "status": r.status, "width_ratio": r.width_ratio,
            "prior_width_log10": r.prior_width, "required_width_log10": r.required_width,
            "interval_at_prior_omega": [float(a) for a in r.interval_at_prior], "nearest_threshold": 1.0}


# ------------------------------------------------------------------ gap K_sp keys: flip log10 K_sp* = log10 IAP
GAP_PHASES = {"brushite": {"formula": "CaHPO4.2H2O", "nu": {"a_Ca": 1, "a_HPO4": 1}, "n_hyd": 2, "evidence": ["ksp_brushite"]},
              "atcp": {"formula": "alpha-Ca3(PO4)2", "nu": {"a_Ca": 3, "a_PO4": 2}, "n_hyd": 0, "evidence": ["ksp_alpha_tcp"]}}


def gap_ksp_rows(ctx):
    cells = k2_cells(ctx)
    base = ctx.k2.minerals["hap"]
    spec_hap = ctx.cfg["k2_phases"]["hap"]
    rows = []
    ids = [c for c in cells if "a_w" in cells[c][2]]
    sel = [c for c in cells if cells[c][2].get("a_w") in (None,) or True][:0]
    # slurry state only (a_w = 1), every cell of the registered grid with the drying axis collapsed
    seen, pick = set(), []
    for cid, (design, fixed, labels) in cells.items():
        key = tuple((k, str(v)) for k, v in labels.items() if k != "a_w")
        if key in seen:
            continue
        seen.add(key)
        pick.append((cid, design, fixed, labels))
    for name, g in GAP_PHASES.items():
        spec = {"formula": g["formula"], "ksp": "log10_ksp_hap", "nu": g["nu"], "n_hyd": g["n_hyd"]}
        flips = []
        for cid, design, fixed, labels in pick:
            spec_i = dict(spec_hap, nu=g["nu"], n_hyd=g["n_hyd"])
            joint, evals = cell_model_and_joint(ctx, spec_i, design, fixed, states=("slurry",))
            ev = evals["slurry"][0]

            def log10_iap(d, ev=ev):
                dd = dict(d)
                dd["K_sp"] = np.ones_like(np.asarray(d["K_sp"], float))
                return np.log10(ev(dd)[0]["speciation"]["Omega_bulk"])
            x = joint.sample(np.random.default_rng(ctx.seed), N_CHECK)
            v = log10_iap({s: x[:, i] for i, s in enumerate(joint.symbols)})
            flips.append(qs(v))
        arr = np.array(flips)
        ev_rows = evidence_methods(ctx.root, g["evidence"])
        rows.append({"id": "k2_ksp_" + name, "link": "K2", "kind": "gap", "quantity": "log10 K_sp (%s)" % g["formula"], "parameter": "no key (gap)",
                     "unit": "log10 units", "verdict_now": "undetermined (no K_sp key in lit/params.yaml)", "settles": "K2 in every cell of the registered slurry grid",
                     "prior": {"gap": True},
                     "flip": {"quantity": "log10 K_sp* = log10 IAP (per cell, slurry state, a_w = 1)", "unit": "log10", "over_cells_q05_median_q95_of_medians":
                              [float(np.quantile(arr[:, 1], q)) for q in (0.05, 0.5, 0.95)], "n_cells": int(arr.shape[0]),
                              "within_cell_spread_q05_q95_median": float(np.median(arr[:, 2] - arr[:, 0])),
                              "note": "stoichiometry from the formula unit (not registered in screen.yaml k2_phases); IAP from the registered phosphate speciation"},
                     "required_precision": {"status": "gap", "rule": "no registered bound; log10 K_sp known to +-d decides a cell when |log10 K_sp - flip| > d (the speciation spread within a cell is +-%.2f log10)" % (float(np.median(arr[:, 2] - arr[:, 0])) / 2)},
                     "evidence_grade": "evidence-table row exists, no params key: " + ", ".join(sorted({r["grade"] for r in csv.DictReader(open(ctx.root / 'lit' / 'evidence_table.csv')) if r["quantity"] in g["evidence"]})),
                     "_kind": "log10", "_reach": [{"purpose": "below the within-cell speciation spread", "hw": float(np.median(arr[:, 2] - arr[:, 0])) / 2, "kind": "log10"}],
                     "measurable_by_quantities": g["evidence"], "evidence_values": [(r["row_id"], r["value"], r["grade"]) for r in csv.DictReader(open(ctx.root / "lit" / "evidence_table.csv")) if r["quantity"] in g["evidence"]]})
    rows.append({"id": "k2_ksp_li3po4", "link": "K2", "kind": "gap", "quantity": "log10 K_sp (Li3PO4)", "parameter": "no key (gap)", "unit": "log10 units",
                 "verdict_now": "undetermined", "settles": "K2 of the competing phase", "prior": {"gap": True},
                 "flip": {"quantity": "log10 K_sp* = log10 IAP", "note": "not computable: the speciation carries no Li+ activity"},
                 "required_precision": {"status": "not_computable"}, "evidence_grade": "evidence-table rows grade B (solubility) and D (K_sp compilation); no params key",
                 "measurable_by_quantities": ["solubility_li3po4", "ksp_li3po4"]})
    return rows


def hydration_row(ctx):
    """n_hyd_acp (ACP hydration number): ACP is undetermined at drying cells with a_w < 1. Flip n* = ln(Omega_anhydrous) / ln(1/a_w)."""
    cells = k2_cells(ctx)
    spec = ctx.cfg["k2_phases"]["acp"]
    out = []
    for cid, (design, fixed, labels) in cells.items():
        a_w = design.get("a_w@drying")
        if a_w is None or a_w >= 1:
            continue
        spec_i = dict(spec, n_hyd=0.0)
        spec_i.pop("n_hyd_key", None)
        joint, evals = cell_model_and_joint(ctx, spec_i, design, fixed, states=("drying",))
        ev = evals["drying"][0]
        x = joint.sample(np.random.default_rng(ctx.seed), N_CHECK)
        d = {s: x[:, i] for i, s in enumerate(joint.symbols)}
        dd = dict(d)
        dd["a_w"] = np.ones(N_CHECK)
        om = ev(dd)[0]["speciation"]["Omega_bulk"]
        with np.errstate(invalid="ignore", divide="ignore"):
            n_star = np.log(om) / np.log(1.0 / a_w)
        out.append((cid, a_w, qs(n_star)))
    arr = np.array([o[2] for o in out])
    return {"id": "n_hyd_acp", "link": "K2 (ACP, drying)", "kind": "gap", "quantity": "n_hyd (ACP structural water per formula unit)", "parameter": "n_hyd_acp (gap)",
            "unit": "mol H2O per formula unit", "verdict_now": "undetermined at drying cells with a_w < 1", "settles": "K2 of ACP at drying cells",
            "prior": {"gap": True}, "flip": {"quantity": "n* = ln(Omega_anhydrous) / ln(1/a_w); K2 passes for n <= n*", "unit": "1",
                                              "over_cells_median_of_medians": float(np.nanmedian(arr[:, 1])), "q05_q95_of_medians": [float(np.nanquantile(arr[:, 1], 0.05)), float(np.nanquantile(arr[:, 1], 0.95))],
                                              "n_cells": len(out), "fraction_of_cells_with_median_n_star_ge_0": float(np.mean(arr[:, 1] >= 0))},
            "required_precision": {"status": "gap", "rule": "n known to +-d decides a cell when |n - n*| > d; evidence-table values of acc_hydration_n (calcium carbonate ACC, 0.25 to 1.58) are not an ACP datum"},
            "evidence_grade": "gap (acp_water_content: one compilation row)", "measurable_by_quantities": ["acc_hydration_n", "acp_water_content"]}


# ------------------------------------------------------------------ K1 rows (closed form from the frozen block and the ladder)
def k1_rows(ctx):
    th = yaml.safe_load((ctx.root / thr.COPY).read_text(encoding="utf-8"))
    cls = th["screen_ph"]["margins_v6"]["cutoff_classes"]
    ladder = [r for r in csv.DictReader(open(ctx.root / ph_prov.LADDER, encoding="utf-8")) if r["reaction_id"] == "ALL"]
    params = th["screen_ph"]["margins_v6"]["m_K1"]["rows"]
    n_e = {}
    for r in params:
        n_e.setdefault((r["phase"], r["framing"]), []).append(r)
    u_tr_kj = None
    rows = []
    for r in ladder:
        if not r["E_ub_V"] or "inconclusive" not in (r["k1_class_lfp"], r["k1_class_42_43"], r["k1_class_44_45"]):
            continue
        if r["phase"].startswith("CaCO3") or r["phase"].startswith("Ca2SiO4"):
            continue
        eub, m = float(r["E_ub_V"]), float(r["margin_V"])
        cand = [x for x in n_e.get((r["phase"], r["framing"]), []) if x.get("E_ub_V") is not None]
        gov = min(cand, key=lambda x: abs(float(x["E_ub_V"]) - eub)) if cand else None
        ne = float(gov["n_e"]) if gov and abs(float(gov["E_ub_V"]) - eub) < 0.05 else None
        per = {}
        for c, col in (("C_lo", "k1_class_lfp"), ("C_mid", "k1_class_42_43"), ("C_hi", "k1_class_44_45")):
            if r[col] != "inconclusive":
                continue
            ec = max(cls[c]["E_c_V"])
            flip = ec + m
            per[c] = {"E_c_sup_V": ec, "E_lb_flip_V": flip, "headroom_V": eub - flip,
                      "headroom_kJ_per_formula_reaction": None if ne is None else (eub - flip) * ne * FARADAY / 1000.0,
                      "pass_possible": flip <= eub}
        rows.append({"id": "k1_%s_%s" % (re.sub(r"\W+", "_", r["phase"]).strip("_").lower()[:24], r["framing"]), "link": "K1", "kind": "closed",
                     "quantity": "E_lb (aqueous-ion lower bound of the onset), %s %s" % (r["phase"], r["framing"]), "parameter": "E_lb / Delta_G_tr_rel (transfer premise)",
                     "unit": "V (and kJ mol^-1 of reaction via n_e F)", "verdict_now": "inconclusive at %s (E_ub %.4f V, E_lb pending)" % (", ".join(per), eub),
                     "settles": "K1 pass (E_lb >= E_c + m_expt) at the listed classes", "prior": {"gap": True},
                     "flip": {"quantity": "E_lb* = sup(E_c) + m_expt", "unit": "V", "E_ub_V": eub, "m_expt_V": m, "n_e": ne, "by_class": per},
                     "required_precision": {"status": "gap", "rule": "E_lb known to +-d decides a class when |E_lb - E_lb*| > d; the pass is possible only where headroom_V > 0, and a computed premise adds u_tr/(n_e F) to the edge"},
                     "evidence_grade": "E_ub sourced (tabulated thermochemistry); E_lb pending (no measured Ca2+ or Al3+ transfer free energy water to PC; the evidence-table Ca2+ transfer rows are water to acetonitrile)",
                     "_kind": "kJ/mol", "_reach": [{"purpose": "headroom at C_lo (kJ per formula reaction)", "hw": (per.get("C_lo") or {}).get("headroom_kJ_per_formula_reaction"), "kind": "kJ mol^-1"}],
                     "measurable_by_quantities": ["transfer_multi_ca2_water_acetonitrile", "transfer_free_energy_li_pc_compiled", "hydration_free_energy_ca", "transfer_multi_cu2_water_pc"]})
    return rows


# ------------------------------------------------------------------ route layer: hydrolysis, f_min
def k2h_rows(ctx):
    names = ["hydrolysis_polyp_k_ph6", "hydrolysis_polyp_k_ph6_ca1mm", "hydrolysis_polyp_k_ph8", "hydrolysis_polyp_k_ph8_ca1mm"]
    ks = [ctx.prior_of(k) for k in names]
    k_slow, k_fast = min(p["low"] for p in ks), max(p["high"] for p in ks)
    sq, sc = ctx.key("p_c_site_square")["value"], ctx.key("p_c_site_sc")["value"]
    fm = {"low_2D_square": 1 - sq, "high_3D_sc": 1 - sc}
    tw = ctx.prior_of("t_proc_slurry")
    rows = []
    flips = {}
    for fe, f in fm.items():
        for rate, k in (("slowest", k_slow), ("fastest", k_fast)):
            flips["%s_%s" % (fe, rate)] = {"f_min": f, "k_s-1": k, "t_wet_flip_s": math.log(1 / f) / k, "t_wet_flip_days": math.log(1 / f) / k / 86400}
    rows.append({"id": "t_wet", "link": "K2h", "kind": "gap", "quantity": "t_wet (wet residence time at which the polyphosphate fraction falls to f_min)",
                 "parameter": "hydrolysis_t_wet_* (gap)", "unit": "s", "verdict_now": "undetermined (coverage: temperature tolerance, transfer factor and t_wet are gaps)",
                 "settles": "K2h_falsify (f_cond < f_min at the slowest rate) or K2h_not_gating (f_cond >= f_min at the fastest rate)",
                 "prior": {"gap": True, "slurry_residence_time_key_s": [tw["low"], tw["high"]]},
                 "flip": {"quantity": "t_wet* = ln(1/f_min) / k, f_cond = exp(-k t)", "unit": "s", "by_case": flips,
                          "note": "conditional on transferring the gamma-Al2O3 particle rates (pH 6 and 8, 0 and 1 mM Ca2+, 298.15 K) unchanged; the transfer factor is a gap"},
                 "required_precision": {"status": "gap", "rule": "t_wet known to a factor r decides when t_wet is outside [t*/r, t* r]; the key t_proc_slurry spans 1.2e3 to 1.2e6 s, all below the fastest-rate flip %.3g s" % min(v["t_wet_flip_s"] for v in flips.values() if True)},
                 "evidence_grade": "rates: C single-source (4 keys); t_wet, transfer factor, temperature tolerance: gap",
                 "measurable_by_quantities": ["hydrolysis_polyp_k_al2o3", "slurry_time", "drying_time"]})
    rows.append({"id": "f_min", "link": "K2h", "kind": "closed", "quantity": "f_min (condensed fraction below which the film's K1 is lost)", "parameter": "p_c_site_square, p_c_site_sc",
                 "unit": "1", "verdict_now": "undetermined", "settles": "K2h at the interval ends",
                 "prior": {"gap": False, "registered_interval": [fm["low_2D_square"], fm["high_3D_sc"]], "triangular_2D_sensitivity": 1 - ctx.key("p_c_site_triangular")["value"]},
                 "flip": {"quantity": "f_min* = exp(-k t_wet)", "unit": "1", "note": "for a wet time t the condensed fraction is exp(-k t): at 1.2e6 s and the fastest rate it is %.4f, at the slowest %.4f" % (math.exp(-k_fast * tw["high"]), math.exp(-k_slow * tw["high"])),
                          "f_cond_at_longest_t_proc": {"fastest": math.exp(-k_fast * tw["high"]), "slowest": math.exp(-k_slow * tw["high"])}},
                 "required_precision": {"status": "closed", "rule": "f_min is computed (percolation thresholds, grade B), not measured; the interval width %.3f is a lattice-dimension choice, not an uncertainty that a measurement narrows" % (fm["high_3D_sc"] - fm["low_2D_square"])},
                 "evidence_grade": "p_c keys B (computation: transfer-matrix and Monte Carlo)", "measurable_by_quantities": ["p_c_site_square", "p_c_site_sc"]})
    return rows


def gap_only_rows(ctx):
    rows = []
    for rid, q, verdict, ev, why in (
            ("ksp_alpp", "log10 K_sp,AlPP (R1 aluminium polyphosphate)", "undetermined (F1r)", ["polyp_al_log_k_oxide", "polyp_log10_ksp_al", "polyp_al_log_beta1_linear"], "flip K_sp* = IAP_AlPP needs a(Al3+) and a(PP): both gaps"),
            ("binodal_map", "coacervate binodal map (R2)", "undetermined", ["coacervate_binodal_map"], "no map: B1 at every state"),
            ("gamma_nl_coacervate", "coacervate gamma_nl and contact angle (K4, R2)", "undetermined", ["coacervate_gamma_nl", "coacervate_contact_angle_alumina"], "flip S_coac = m_S needs the contact difference: gaps")):
        rows.append({"id": rid, "link": "route layer", "kind": "gap", "quantity": q, "parameter": ", ".join(ev), "unit": "-", "verdict_now": verdict,
                     "settles": "route verdict (report-only, never gating)", "prior": {"gap": True},
                     "flip": {"quantity": None, "note": why}, "required_precision": {"status": "not_computable", "rule": why},
                     "evidence_grade": "gap", "measurable_by_quantities": {"ksp_alpp": ["polyp_al_binding_logbeta1"], "binodal_map": ["coacervate_onset_volume", "coacervate_ca_threshold"],
                                                                               "gamma_nl_coacervate": ["coacervate_gamma_complex", "water_contact_angle_alumina"]}[rid]})
    return rows


# ------------------------------------------------------------------ assembly
def finish(ctx, row):
    """Adds the measurable-by column from the evidence table (methods verbatim)."""
    qn = row.pop("measurable_by_quantities", None)
    purposes = row.pop("_reach", [])
    kind = row.pop("_kind", None)
    if qn is not None:
        ms = evidence_methods(ctx.root, qn, kind)
        row["measurable_by"] = {"methods_from_evidence_table": ms, "assessments": reach(purposes, ms),
                                "basis": "stated uncertainty or spread across the evidence-table rows of each method (a reproducibility proxy)"}
    return row


def build(root, log=print):
    t0 = time.perf_counter()
    ctx = Ctx(root)
    pt = reproduce_point(ctx)
    check = check_against_production(ctx, pt)
    if not check["equal"]:
        raise run.ProductionRefused("the reproduced draws differ from the production masses: %s" % check)
    rows = []
    for fn in (lambda: nucleation_rows(ctx, pt), lambda: c1_rows(ctx, pt), lambda: k2_mc_rows(ctx), lambda: gap_ksp_rows(ctx),
               lambda: [hydration_row(ctx)], lambda: k1_rows(ctx), lambda: k2h_rows(ctx), lambda: gap_only_rows(ctx)):
        got = fn()
        log("%d rows (%.0f s)" % (len(got), time.perf_counter() - t0))
        rows += got
    rows = [finish(ctx, r) for r in rows]
    return ctx, check, rows


def markdown(rows):
    def fmt(r):
        rp = r.get("required_precision") or {}
        fl = r.get("flip") or {}
        q = [fl[k] for k in ("q05_q50_q95", "flip_q05_q50_q95", "q05_q50_q95") if k in fl]
        flip = "%s = %s" % (fl.get("quantity"), ", ".join("%.3g" % v for v in q[0])) if q else str(fl.get("value") or fl.get("quantity") or "")
        prior = r.get("prior") or {}
        pr = "gap" if prior.get("gap") else (str(prior.get("low_high_J_m2") or prior.get("central95_J_m2") or prior.get("registered_interval") or prior.get("low")))
        ratio = rp.get("width_ratio")
        mb = (r.get("measurable_by") or {}).get("assessment", "")
        return "| %s | %s | %s | %s | %s | %s | %s | %s |" % (r["id"], r["link"], pr, str(flip)[:90], rp.get("status", "") + ("" if ratio is None else " s*=%.3f" % ratio),
                                                                  (r.get("settles") or "")[:50], str(r.get("evidence_grade"))[:40], mb[:40])
    head = "| id | verdict link | prior | flip | required precision | settles | evidence grade | measurable by |\n|---|---|---|---|---|---|---|---|\n"
    return head + "\n".join(fmt(r) for r in rows) + "\n"


def run_map(root, out_path, dry=False, log=print):
    root, out_path = Path(root), Path(out_path)
    if not dry:
        ph_prov.check_frozen(root)
        if not run._inside(out_path, root / run.SCREEN_DIR) or not out_path.parent.name.endswith("_ph"):
            raise run.ProductionRefused("production output belongs in %s/<name>_ph/" % run.SCREEN_DIR)
        if out_path.exists():
            raise run.ProductionRefused("%s exists: a production document is never overwritten" % out_path)
    ctx, check, rows = build(root, log)
    prov = run._provenance(root, ctx.cfg, root / run.CONFIG, [params_adapter.RegimePriors("R-slurry", None, {}, str(ctx.params_path),
                                                                                         run._sha256_file(ctx.params_path), False)], run.THRESHOLDS, dry)
    prov["session"] = SESSION
    prov["run_label"] = out_path.parent.name
    runs = []
    for r in RUNS:
        pv = ctx.prod[r]["provenance"]
        runs.append({"run_label": pv.get("run_label"), "git_sha": pv.get("git_sha"), "path": "%s/%s/summary.json" % (run.SCREEN_DIR.as_posix(), r),
                     "sha256": ph_prov.sha256_file(root / run.SCREEN_DIR / r / "summary.json")})
    doc = {"session": SESSION, "method": "configs/preprint/precision_method.md", "p_cred": ctx.p, "interval_level": ctx.level, "pre_run_sha": PRE_RUN_SHA,
           "design_point": DETAIL_POINT, "reproduction_check": check, "n_mc": N_MC, "provenance": prov, "production_runs": runs, "rows": rows,
           "statement": "flip values and required precisions are conditional on the frozen priors and thresholds; an ignorance prior is never a finding"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=1, sort_keys=True, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n", encoding="utf-8")
    md = out_path.with_suffix(".md")
    md.write_text("# Required-precision map (PH-W4.3)\n\ncode sha %s, params sha %s, thresholds block sha %s, pre-run sha %s\n\n%s" % (
        prov.get("git_sha"), prov.get("params_sha"), prov.get("thresholds_block_sha256"), PRE_RUN_SHA, markdown(rows)), encoding="utf-8")
    if not dry:
        ph_prov.ledger_append(root, SESSION, prov, prov["config_file"], prov["config_hash"], [out_path, md])
    return out_path, doc
