"""PH-W4.5: per-pH minimum doses of the K2 maps (cp5b F1), from the frozen cells and from the PH-W4.5 reruns.

Reads results/preprint/screen/{k2_grid_ph, phosphate_films_ph, k2_alkaline_ph2, k2_acid_ph2}/summary.json (never writes them) and
writes data files and a markdown table under results/preprint/screen/k2_perph_ph2/. A cell passes when its K2 verdict is feasible
(suitable against dissolution, worst over the registered states, after the control gate). Doses are in mol dm^-3.
"""
import csv
import json
from pathlib import Path

from nacre.screen import k2_grid, params_adapter, ph_prov, run

SCREEN = Path("results") / "preprint" / "screen"
OUT = SCREEN / "k2_perph_ph2"
SESSION = "PH-W4.5"
ALK_PH = {"pH@min": 10.0, "pH@value": 12.0, "pH@max": 13.0}
PHASES = [("calcite", "calcite"), ("aragonite", "aragonite"), ("ACC", "ACC"), ("hap", "HAp"), ("acp", "ACP"), ("btcp", "b-TCP"),
          ("ocp", "OCP (original key)"), ("ocp_ca4h", "OCP (Ca4H key)"), ("brushite", "brushite"), ("atcp", "a-TCP"),
          ("li3po4", "Li3PO4")]
CARBONATE = ("calcite", "aragonite", "ACC")


def _load(root, name):
    return json.loads((Path(root) / SCREEN / name / "summary.json").read_text(encoding="utf-8"))["extensions"]["p0-w4"]


def sources(root):
    """{(grid, source): {phase: record}} of the frozen runs and of the reruns."""
    fz1, fz2 = _load(root, "phosphate_films_ph"), _load(root, "k2_grid_ph")
    ra, rc = _load(root, "k2_alkaline_ph2")["k2_ph2"], _load(root, "k2_acid_ph2")["k2_ph2"]
    alk = dict(fz2["k2_grid"]["carbonate"]["polymorphs"])
    alk.update(fz1["ph_production"]["k2_phosphate"]["phases"])
    acid = dict(fz2["k2_grid"]["acid_adjusted"]["carbonate"])
    acid.update(fz2["k2_grid"]["acid_adjusted"]["phosphate"])
    return {("alkaline", "frozen"): alk, ("acid", "frozen"): acid,
            ("alkaline", "rerun"): ra["states"]["alkaline"]["phases"], ("acid", "rerun"): rc["states"]["acid"]["phases"]}


def _dose(label):
    return float(str(label).split()[0])


def _ph(label):
    return ALK_PH[label] if label in ALK_PH else float(str(label).split()[0])


def cell_rows(rec, basis="cell"):
    """[(pH, Ca_T, P_T or None, passes)] of the cells of one record."""
    ok_control = rec.get("controls_pass", True)
    out = []
    for c in rec["cells"].values():
        ax = c["axes"]
        if basis == "cell":
            p = c["verdict"] == "feasible"
        else:
            p = bool(ok_control) and (c.get("by_state") or {}).get("slurry", c["verdict"]) == "feasible"
        out.append((_ph(ax["pH"]), _dose(ax["Ca_T"]), _dose(ax["P_T"]) if "P_T" in ax else None, p, c["verdict"]))
    return out


def per_ph(rec, basis="cell"):
    rows = cell_rows(rec, basis)
    out = {}
    for ph in sorted({r[0] for r in rows}):
        sel = [r for r in rows if r[0] == ph]
        ok = [r for r in sel if r[3]]
        ent = {"pH": ph, "n_cells": len(sel), "n_passing": len(ok), "passing_fraction": len(ok) / len(sel),
               "n_undetermined": sum(r[4] == "undetermined" for r in sel),
               "min_passing_Ca_T": min((r[1] for r in ok), default=None),
               "min_passing_P_T": min((r[2] for r in ok if r[2] is not None), default=None),
               "CaP_ratio_range_passing": None}
        if ok and ok[0][2] is not None:
            ratios = [r[1] / r[2] for r in ok]
            ent["CaP_ratio_range_passing"] = [min(ratios), max(ratios)]
            ent["CaP_ratios_1p5_1p67_in_passing"] = any(1.4 <= x <= 1.8 for x in ratios)
        out[ph] = ent
    return out


def build(root):
    src = sources(root)
    doc = {"session": SESSION, "definition": "a cell passes when its K2 verdict is feasible (worst over the registered states, after the "
           "control gate); 'wet' basis: the wet slurry state alone, honouring the control gate; doses in mol dm^-3; the Ca:P ratio is "
           "Ca_T/P_T of the passing cells; the decade grid has ratios 10^k only, so 1.5 and 1.67 are not on the grid",
           "sources": {"frozen": ["k2_grid_ph", "phosphate_films_ph"], "rerun": ["k2_alkaline_ph2", "k2_acid_ph2"]},
           "tables": {}, "headline": {}}
    for (grid, source), phases in src.items():
        for key, disp in PHASES:
            rec = phases.get(key)
            if rec is None:
                continue
            doc["tables"].setdefault(grid, {}).setdefault(source, {})[key] = {
                "display": disp, "headline_verdict": rec["verdict"], "controls_pass": rec.get("controls_pass"),
                "ksp_key": rec.get("ksp_key"), "n_cells": len(rec["cells"]),
                "cell": per_ph(rec, "cell"), "wet": per_ph(rec, "wet")}
    for grid in ("alkaline", "acid"):
        for key, disp in PHASES:
            fz = doc["tables"][grid]["frozen"].get(key)
            rr = doc["tables"][grid]["rerun"].get(key)
            changed = None
            if fz and rr and fz["ksp_key"] == rr["ksp_key"] and fz["n_cells"] == rr["n_cells"]:
                fzc, rrc = src[(grid, "frozen")][key]["cells"], src[(grid, "rerun")][key]["cells"]
                changed = sum(fzc[c]["verdict"] != rrc[c]["verdict"] for c in fzc if c in rrc)
            doc["headline"].setdefault(grid, {})[key] = {
                "display": disp, "frozen_verdict": fz and fz["headline_verdict"], "rerun_verdict": rr and rr["headline_verdict"],
                "frozen_controls_pass": fz and fz["controls_pass"], "rerun_controls_pass": rr and rr["controls_pass"],
                "cells_changed": changed,
                "frozen_passing": fz and sum(v["n_passing"] for v in fz["cell"].values()),
                "rerun_passing": rr and sum(v["n_passing"] for v in rr["cell"].values()),
                "n_cells": rr and rr["n_cells"]}
    # first-pass pH of every phase (lowest pH with a passing cell) in the acid-adjusted state
    doc["first_pass"] = {}
    for source in ("frozen", "rerun"):
        for key, tab in doc["tables"]["acid"][source].items():
            hit = [e for ph, e in sorted(tab["cell"].items(), key=lambda kv: float(kv[0])) if e["n_passing"]]
            doc["first_pass"].setdefault(source, {})[key] = hit[0] if hit else None
    doc["min_dose_at_or_above_0.01"] = []
    for grid in doc["tables"]:
        for source, ph in doc["tables"][grid].items():
            for key, tab in ph.items():
                for e in tab["cell"].values():
                    for what in ("min_passing_Ca_T", "min_passing_P_T"):
                        if e[what] is not None and e[what] >= 0.01:
                            doc["min_dose_at_or_above_0.01"].append({"grid": grid, "source": source, "phase": tab["display"],
                                                                     "pH": e["pH"], "quantity": what, "value": e[what]})
    return doc


def _g(x):
    return "-" if x is None else "%g" % x


def markdown(doc):
    L = ["# Per-pH minimum doses of the K2 maps (PH-W4.5, cp5b F1)", "", doc["definition"], ""]
    L += ["## Headline verdicts, frozen against rerun", "", "| grid | phase | frozen | rerun | controls frozen/rerun | passing cells frozen/rerun of n | cells changed |",
          "|---|---|---|---|---|---|---|"]
    for grid, ph in doc["headline"].items():
        for key, h in ph.items():
            if h["frozen_verdict"] is None and h["rerun_verdict"] is None:
                continue
            nr = "(not rerun)"
            L.append("| %s | %s | %s | %s | %s / %s | %s / %s of %s | %s |" % (
                grid, h["display"], h["frozen_verdict"] or "(not in frozen run)", h["rerun_verdict"] or nr,
                nr if h["frozen_controls_pass"] is None else h["frozen_controls_pass"],
                "-" if h["rerun_controls_pass"] is None else h["rerun_controls_pass"], h["frozen_passing"],
                "-" if h["rerun_passing"] is None else h["rerun_passing"], h["n_cells"] or "-",
                "-" if h["cells_changed"] is None else h["cells_changed"]))
    for grid in ("acid", "alkaline"):
        for source in ("frozen", "rerun"):
            L += ["", "## %s state, %s cells (K2 verdict basis)" % ("Acid-adjusted" if grid == "acid" else "Slurry (alkaline grid)", source), "",
                  "| phase | pH | cells | passing | fraction | min Ca_T | min P_T | Ca:P range (passing) |", "|---|---|---|---|---|---|---|---|"]
            for key, tab in doc["tables"][grid][source].items():
                for ph, e in sorted(tab["cell"].items(), key=lambda kv: float(kv[0])):
                    rg = e["CaP_ratio_range_passing"]
                    L.append("| %s | %g | %d | %d | %.3f | %s | %s | %s |" % (
                        tab["display"], e["pH"], e["n_cells"], e["n_passing"], e["passing_fraction"], _g(e["min_passing_Ca_T"]),
                        _g(e["min_passing_P_T"]), "-" if rg is None else "%g to %g" % tuple(rg)))
    L += ["", "## First-pass pH (acid-adjusted state: lowest pH with a passing cell)", "", "| phase | source | pH | min Ca_T | min P_T | fraction | Ca:P range |", "|---|---|---|---|---|---|---|"]
    names = dict(PHASES)
    for source, ph in doc["first_pass"].items():
        for key, e in ph.items():
            if e is None:
                L.append("| %s | %s | none passes | - | - | - | - |" % (names[key], source))
            else:
                rg = e["CaP_ratio_range_passing"]
                L.append("| %s | %s | %g | %s | %s | %.3f | %s |" % (names[key], source, e["pH"], _g(e["min_passing_Ca_T"]), _g(e["min_passing_P_T"]),
                                                                  e["passing_fraction"], "-" if rg is None else "%g to %g" % tuple(rg)))
    L += ["", "## Minimum doses at or above 0.01 mol dm^-3", ""]
    L += ["- %(grid)s, %(source)s, %(phase)s, pH %(pH)g, %(quantity)s = %(value)g" % d for d in doc["min_dose_at_or_above_0.01"]] or ["none"]
    return "\n".join(L) + "\n"


def main(root):
    root = Path(root)
    out = root / OUT
    if out.exists():
        raise run.ProductionRefused("%s exists" % out)
    doc = build(root)
    out.mkdir(parents=True)
    (out / "perph.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (out / "perph.md").write_text(markdown(doc), encoding="utf-8")
    with (out / "perph.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["grid", "source", "phase", "pH", "n_cells", "n_passing", "passing_fraction", "min_passing_Ca_T_mol_dm3",
                    "min_passing_P_T_mol_dm3", "CaP_min", "CaP_max"])
        for grid, srcs in doc["tables"].items():
            for source, ph in srcs.items():
                for key, tab in ph.items():
                    for e in tab["cell"].values():
                        rg = e["CaP_ratio_range_passing"] or ["", ""]
                        w.writerow([grid, source, tab["display"], e["pH"], e["n_cells"], e["n_passing"], "%.6f" % e["passing_fraction"],
                                    e["min_passing_Ca_T"] if e["min_passing_Ca_T"] is not None else "",
                                    e["min_passing_P_T"] if e["min_passing_P_T"] is not None else "", rg[0], rg[1]])
    from nacre.screen import k2_grid as kg
    ctx = kg.Context(root)
    prov = run._provenance(root, ctx.cfg, root / run.CONFIG, [params_adapter.RegimePriors("R-slurry", None, {}, str(ctx.params_path),
                           run._sha256_file(ctx.params_path), False)], run.THRESHOLDS, False)
    ph_prov.ledger_append(root, SESSION, prov, prov["config_file"], prov["config_hash"],
                          [out / "perph.json", out / "perph.md", out / "perph.csv"], note="per-pH minimum doses from frozen and rerun cells")
    return doc


if __name__ == "__main__":
    from nacre._util import repo_root
    main(repo_root())
