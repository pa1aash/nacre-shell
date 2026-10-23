"""PH-W4.6: the phosphate K2 on a Ca:P ratio grid (new directories <run>_ph3/, beside the frozen and PH-W4.5 runs).

Ca_T keeps the decade grid of screen.yaml, P_T = Ca_T / ratio for the ratios of configs/preprint/screen_ph3.yaml (1.67, 1.5, 1.0), pH and
ionic strength are the grids of PH-W4.5, the phases and keys are those of screen_ph2.yaml, and the supersaturated control is the
PH-W4.5 rule (cell of maximum median Omega) taken over all ratio cells of the phase. Frozen and PH-W4.5 outputs are read, never written.
"""
import time
from pathlib import Path

import yaml

from nacre.screen import k2_grid, k2_ph2, params_adapter, ph_prov, run, summary

CONFIG = Path("configs") / "preprint" / "screen_ph3.yaml"
SESSION = "PH-W4.6"
SUFFIX = "_ph3"


def load(root):
    return yaml.safe_load((Path(root) / CONFIG).read_text(encoding="utf-8"))


def ratio_cells(cfg, resolver, ph3, ph_axis="pH", drying=True):
    """Ca_T x ratio x a_w(drying) design points, P_T = Ca_T / ratio, pH and I fixed per cell (same loop order as phosphate_cells)."""
    ca = k2_grid._axis(cfg, resolver, "Ca_T")
    aw = [(None, None)]
    if drying:
        spec = (cfg.get("design_axes") or {}).get("a_w")
        if spec:
            aw = [(lab, v) for lab, v in k2_grid.study._axis_values(spec, resolver, "1")]
    out = []
    for ph_lab, ph in k2_grid._axis(cfg, resolver, ph_axis):
        for i_lab, ii in k2_grid._axis(cfg, resolver, "I_ionic"):
            for r in ph3["ratios"]:
                for c_lab, c in ca:
                    cval = float(str(c_lab).split()[0])
                    for a_lab, a in aw:
                        design = {"Ca_T": c, "P_T": c / r["CaP"]}
                        labels = {"Ca_T": c_lab, "P_T": "%.6g mol dm^-3" % (cval / r["CaP"]), "CaP": "%g" % r["CaP"],
                                  "pH": k2_grid._short(ph_lab), "I": k2_grid._short(i_lab)}
                        if a is not None:
                            design["a_w@drying"] = a
                            labels["a_w"] = a_lab
                        out.append(("; ".join("%s=%s" % kv for kv in labels.items()), design, {"pH": ph, "I_ionic": ii}, labels))
    return out


def part(ctx, ph2, ph3, grid):
    phases = {n: v for n, v in k2_ph2.phases_of(ctx.cfg, ph2).items() if n in ph3["phase_order"]}
    if grid == "alkaline":
        cfg, states = ctx.cfg, ("slurry", "drying")
        cells = ratio_cells(cfg, ctx.resolver, ph3, "pH", True)
    else:
        cfg, states = k2_grid.acid_cfg(ctx.cfg), ("slurry",)
        cells = ratio_cells(cfg, ctx.resolver, ph3, "pH_acid_adjusted", False)
    out = {}
    for name in ph3["phase_order"]:
        rec = k2_grid.eval_phosphate(ctx.params_path, cfg, ctx.resolver, name, cells, ctx.p, ctx.minerals, states, ctx.allow_mock,
                                     None, supersaturated_from=k2_ph2.max_omega_control, phases=phases)
        rec["registered_ksp_key"] = phases[name].get("ksp")
        rec["log10_ksp_read"] = k2_ph2.ksp_value(ctx.resolver, phases[name].get("ksp"))
        out[name] = rec
    return {"grid": {"cells": len(cells), "axes": "Ca_T x ratio (P_T = Ca_T / ratio) x pH x I" + (" x a_w(drying)" if grid == "alkaline" else ", wet slurry"),
                     "ratios": [r["CaP"] for r in ph3["ratios"]]}, "state": grid, "phases": out}


def rows_of(body, doc):
    rows = []
    for grid, blk in body["states"].items():
        for name, rec in blk["phases"].items():
            keys = ((rec["ksp_key"],) if rec["ksp_key"] else ()) + k2_grid.PHOSPHATE_INPUTS
            ev = k2_grid.evidence_of(doc, keys)
            state = "registered alkaline slurry grid" if grid == "alkaline" else "acid-adjusted (incumbent phosphoric-acid pH control)"
            rows.append(k2_grid._k2_row("k2:%s:%s:ph3" % (name, grid), "k2_%s" % name, rec["formula"],
                                        "candidate" if grid == "alkaline" else "comparator", rec["ladder_phase"],
                                        ["PH-W4.6 Ca:P ratio grid (P_T = Ca_T / ratio), rule-based supersaturated control"], rec, ev,
                                        {"state": state}))
    return rows


def run_ph3(root, out_path, grids, dry=False, label=None):
    """Write one PH-W4.6 document (production: a new directory <run>_ph3, ledger line appended)."""
    root, out_path = Path(root), Path(out_path)
    t0 = time.perf_counter()
    if not dry:
        ph_prov.check_frozen(root)
        if not run._inside(out_path, root / run.SCREEN_DIR) or not out_path.parent.name.endswith(SUFFIX):
            raise run.ProductionRefused("production output belongs in a new directory %s/<run>%s/" % (run.SCREEN_DIR, SUFFIX))
        if out_path.exists():
            raise run.ProductionRefused("%s exists" % out_path)
    ctx = k2_grid.Context(root)
    ph2, ph3 = k2_ph2.load(root), load(root)
    states = {g: part(ctx, ph2, ph3, g) for g in grids}
    body = {"session": SESSION, "p_cred": ctx.p, "start_draws": k2_grid.START_DRAWS, "half_width_max": k2_grid.HALF_WIDTH_MAX,
            "seed": int(ctx.cfg["propagation"]["seed"]), "reference_runs": ph3["reference_runs"], "frozen_tag": ph3["frozen_tag"],
            "config_ph3_file": CONFIG.as_posix(), "config_ph3_hash": ph_prov.tagged(ph_prov.sha256_file(root / CONFIG)),
            "ratios": ph3["ratios"], "own_ratio": ph3["own_ratio"], "supersaturated_control": ph3["supersaturated_control"], "states": states}
    stats = k2_grid.stats_of(body)
    stats.update(seconds=time.perf_counter() - t0, peak_mb=k2_grid.peak_mb())
    body["run"] = stats
    prov = run._provenance(root, ctx.cfg, root / run.CONFIG, [params_adapter.RegimePriors("R-slurry", None, {}, str(ctx.params_path),
                           run._sha256_file(ctx.params_path), False)], run.THRESHOLDS, dry)
    prov["run_label"] = label or out_path.parent.name
    doc = summary.build(None, prov, mock=dry or ctx.doc["mock"], extensions={"p0-w4": {"k2_ph3": body}}, ph_rows=rows_of(body, ctx.doc))
    path = summary.write(doc, out_path)
    if not dry:
        ph_prov.ledger_append(root, SESSION, prov, prov["config_file"], prov["config_hash"], [path],
                              note="PH-W4.6 ratio grid beside PH-W4.5 %s" % ",".join(ph3["reference_runs"]))
    return path, doc, stats
