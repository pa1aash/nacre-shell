"""PH-W4.5: the numbers behind the nucleation wording (cp5b F3) and the Sobol half-width (F5), from the production files.

Reads results/preprint/screen/ignorance_ph/summary.json and reproduces the production draws of the decision point (checked against
the stored C3a band mass, as nacre.screen.ph_precision does). Writes results/preprint/screen/f3_ph2/f3_numbers.json and .md.
"""
import json
from pathlib import Path

import numpy as np

from nacre.screen import k2_grid, params_adapter, ph_precision as pp, ph_prov, run

SESSION = "PH-W4.5"
OUT = Path("results") / "preprint" / "screen" / "f3_ph2"
NV_GRID = [0.0, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 1.84]      # J m^-2


def q(v, ps=(0.0, 0.05, 0.5, 0.95, 1.0)):
    return {("min" if p == 0 else "max" if p == 1 else "q%02d" % round(p * 100)): float(np.quantile(v, p)) for p in ps}


def compute(root):
    ctx = pp.Ctx(root)
    pt = pp.reproduce_point(ctx)
    check = pp.check_against_production(ctx, pt)
    x, o, m = pt["x"], pt["o"]["nucleate"], pt["mask"]
    sl = np.asarray(o["gamma_sl_insitu"], float)
    fin = np.isfinite(sl)
    gp, gnv, u = (np.asarray(x[k], float) for k in ("gamma_p", "gamma_nv", "u_gamma_sn"))
    gsn = u * (gp + gnv)
    sel = m & fin
    frac = {}
    for g in NV_GRID:
        gs = u * (gp + g)
        frac["%g" % g] = {"gamma_nv_J_m2": g, "mass_gamma_sn_le_gamma_sl": float(np.mean((gs <= sl)[sel])),
                          "gamma_sn_support_upper_J_m2_q50": float(np.median(gp[sel] + g))}
    per_pt = []
    for pid, _, _ in ctx.points:
        r = pp.reproduce_point(ctx, target=pid)
        s_l = np.asarray(r["o"]["nucleate"]["gamma_sl_insitu"], float)
        k = r["mask"] & np.isfinite(s_l)
        g_p, g_nv, uu = (np.asarray(r["x"][n], float) for n in ("gamma_p", "gamma_nv", "u_gamma_sn"))
        per_pt.append({"design_point": pid, "M_adm": float(r["mask"].mean()), "n_admitted": int(k.sum()),
                       "gamma_sl_q05_q50_q95_J_m2": [float(np.quantile(s_l[k], p_)) for p_ in (0.05, 0.5, 0.95)] if k.any() else None,
                       "mass_at_gamma_nv_0": float(np.mean((uu * g_p <= s_l)[k])) if k.any() else None,
                       "mass_sourced_gamma_nv": float(np.mean((uu * (g_p + g_nv) <= s_l)[k])) if k.any() else None})
    prod = json.loads((Path(root) / run.SCREEN_DIR / "ignorance_ph" / "summary.json").read_text(encoding="utf-8"))
    c3 = prod["claims"]["C3"]
    cnt = {}
    for v in c3["by_design"].values():
        cnt[v["verdict"]] = cnt.get(v["verdict"], 0) + 1
    conv = prod["regimes"]["R-slurry"]["links"]["nucleate"]["convergence"]
    design = prod["regimes"]["R-slurry"]["links"]["nucleate"]["sobol_design"]
    out = {"session": SESSION, "point": check["design_point"], "reproduction_check": check, "n_draws": int(pt["n"]),
           "n_admitted_finite": int(sel.sum()), "M_adm": float(m.mean()),
           "gamma_sl_J_m2": {"admitted_draws": q(sl[sel]), "all_finite_draws": q(sl[fin])},
           "gamma_sn_J_m2_prior_with_sourced_calcite_gamma_nv": {"admitted_draws": q(gsn[sel])},
           "mass_gamma_sn_le_gamma_sl": {"sourced_calcite_gamma_nv": float(np.mean((gsn <= sl)[sel])),
                                         "stored_C3a_P_good": c3["tests"]["C3a"]["P_good"],
                                         "fixed_gamma_nv": frac,
                                         "max_over_grid": max(v["mass_gamma_sn_le_gamma_sl"] for v in frac.values()),
                                         "by_design_point": per_pt,
                                         "max_over_design_points_gamma_nv_0": max(r["mass_at_gamma_nv_0"] or 0 for r in per_pt),
                                         "max_over_design_points_gamma_nv_0_with_M_adm_at_least_0.02": max(
                                             r["mass_at_gamma_nv_0"] or 0 for r in per_pt if r["M_adm"] >= 0.02),
                                         "max_over_design_points_sourced": max(r["mass_sourced_gamma_nv"] or 0 for r in per_pt)},
           "gamma_p_J_m2": q(gp[sel]), "gamma_nv_prior_J_m2": q(gnv[sel]),
           "c3_link_by_design_point": {"counts": cnt, "n": len(c3["by_design"])},
           "sobol_nucleate": {"max_total_order_ci_half_width": conv["max_ci_half_width"], "target": conv["target_ci_half_width"],
                              "capped": conv["capped"], "base_samples": design["base_samples"], "log2_base": int(np.log2(design["base_samples"])),
                              "evaluations": design["evaluations"]}}
    return ctx, out


def markdown(d):
    s, f = d["gamma_sl_J_m2"], d["mass_gamma_sn_le_gamma_sl"]
    L = ["# Nucleation wording numbers (PH-W4.5, cp5b F3 and F5)", "",
         "Design point %s, %d draws of the production seed (C3a band mass reproduced: %s)." % (d["point"], d["n_draws"], d["reproduction_check"]["equal"]), "",
         "gamma_sl (J m^-2), admitted draws: " + ", ".join("%s %.3g" % kv for kv in s["admitted_draws"].items()),
         "gamma_sl (J m^-2), all finite draws: " + ", ".join("%s %.3g" % kv for kv in s["all_finite_draws"].items()), "",
         "Mass with gamma_sn <= gamma_sl under the registered gamma_nv prior of calcite: %.4f (stored C3a P_good %.4f)." % (
             f["sourced_calcite_gamma_nv"], f["stored_C3a_P_good"]), "",
         "| gamma_nv (J m^-2) | median gamma_p + gamma_nv | mass gamma_sn <= gamma_sl |", "|---|---|---|"]
    L += ["| %g | %.4g | %.4f |" % (v["gamma_nv_J_m2"], v["gamma_sn_support_upper_J_m2_q50"], v["mass_gamma_sn_le_gamma_sl"]) for v in f["fixed_gamma_nv"].values()]
    L += ["", "Over the 36 design points: mass at gamma_nv = 0 at most %.4f (%.4f where M_adm >= 0.02, i.e. at least 0.02 of the draws admitted); "
          "under the sourced gamma_nv prior at most %.4f." % (f["max_over_design_points_gamma_nv_0"],
                                                               f["max_over_design_points_gamma_nv_0_with_M_adm_at_least_0.02"],
                                                               f["max_over_design_points_sourced"])]
    c = d["c3_link_by_design_point"]
    so = d["sobol_nucleate"]
    L += ["", "C3 link falsified at %s of %d design points (%s)." % (c["counts"].get("falsified"), c["n"], c["counts"]), "",
          "Nucleate Sobol total-order (and first-order) confidence-interval half-width: %.4f against the target %g; capped %s at 2^%d base rows (%d evaluations)." % (
              so["max_total_order_ci_half_width"], so["target"], so["capped"], so["log2_base"], so["evaluations"])]
    return "\n".join(L) + "\n"


def main(root):
    root = Path(root)
    out = root / OUT
    if out.exists():
        raise run.ProductionRefused("%s exists" % out)
    ctx, d = compute(root)
    out.mkdir(parents=True)
    (out / "f3_numbers.json").write_text(json.dumps(d, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (out / "f3_numbers.md").write_text(markdown(d), encoding="utf-8")
    prov = run._provenance(root, ctx.cfg, root / run.CONFIG, [params_adapter.RegimePriors("R-slurry", None, {}, str(ctx.params_path),
                           run._sha256_file(ctx.params_path), False)], run.THRESHOLDS, False)
    ph_prov.ledger_append(root, SESSION, prov, prov["config_file"], prov["config_hash"], [out / "f3_numbers.json", out / "f3_numbers.md"],
                          note="F3 and F5 numbers from the production draws and the ignorance_ph summary")
    return d


if __name__ == "__main__":
    from nacre._util import repo_root
    main(repo_root())
