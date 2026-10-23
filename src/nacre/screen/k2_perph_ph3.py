"""PH-W4.6: per-pH minimum doses of the Ca:P ratio grid, beside the crossed decade grid of PH-W4.5 (same format as k2_perph_ph2).

Reads results/preprint/screen/{k2_alkaline_ph2, k2_acid_ph2, k2_alkaline_ph3, k2_acid_ph3}/summary.json (never writes them) and writes
perph.{json,csv,md} under results/preprint/screen/k2_perph_ph3/. A cell passes when its K2 verdict is feasible (worst over the
registered states, after the control gate); 'wet' is the wet slurry state alone. Doses are in mol dm^-3.
"""
import csv
import json
from pathlib import Path

from nacre.screen import k2_grid, k2_perph as pp, params_adapter, ph_prov, run

SCREEN = pp.SCREEN
OUT = SCREEN / "k2_perph_ph3"
SESSION = "PH-W4.6"
PHASES = [("hap", "HAp"), ("acp", "ACP"), ("btcp", "b-TCP"), ("ocp_ca4h", "OCP (Ca4H key)"), ("brushite", "brushite")]
RATIOS = ["1.67", "1.5", "1"]
OWN = {"hap": "1.67", "btcp": "1.5", "brushite": "1"}


def _load(root, name, key):
    return json.loads((Path(root) / SCREEN / name / "summary.json").read_text(encoding="utf-8"))["extensions"]["p0-w4"][key]


def sources(root):
    return {("alkaline", "crossed"): _load(root, "k2_alkaline_ph2", "k2_ph2")["states"]["alkaline"]["phases"],
            ("acid", "crossed"): _load(root, "k2_acid_ph2", "k2_ph2")["states"]["acid"]["phases"],
            ("alkaline", "ratio"): _load(root, "k2_alkaline_ph3", "k2_ph3")["states"]["alkaline"]["phases"],
            ("acid", "ratio"): _load(root, "k2_acid_ph3", "k2_ph3")["states"]["acid"]["phases"]}


def _view(rec, ratio):
    return dict(rec, cells={cid: c for cid, c in rec["cells"].items() if c["axes"]["CaP"] == ratio})


def build(root):
    src = sources(root)
    doc = {"session": SESSION, "definition": "a cell passes when its K2 verdict is feasible (worst over the registered states, after the "
           "control gate); 'wet' basis: the wet slurry state alone, honouring the control gate; doses in mol dm^-3; sources: 'crossed' = "
           "the PH-W4.5 rerun on the crossed decade grid (Ca:P = 10^k only), 'ratio_<r>' = the PH-W4.6 grid with P_T = Ca_T / r; the "
           "control cell of the ratio grid is the maximum-Omega cell over all three ratios of that grid state",
           "sources": {"crossed": ["k2_alkaline_ph2", "k2_acid_ph2"], "ratio": ["k2_alkaline_ph3", "k2_acid_ph3"]},
           "own_ratio": OWN, "tables": {}, "headline": {}, "differences": []}
    for grid in ("alkaline", "acid"):
        for key, disp in PHASES:
            cr, ra = src[(grid, "crossed")][key], src[(grid, "ratio")][key]
            t = doc["tables"].setdefault(grid, {})
            t.setdefault("crossed", {})[key] = {"display": disp, "headline_verdict": cr["verdict"], "controls_pass": cr["controls_pass"],
                                                "ksp_key": cr["ksp_key"], "n_cells": len(cr["cells"]),
                                                "cell": pp.per_ph(cr, "cell"), "wet": pp.per_ph(cr, "wet")}
            for r in RATIOS:
                v = _view(ra, r)
                t.setdefault("ratio_" + r, {})[key] = {"display": disp, "headline_verdict": ra["verdict"], "controls_pass": ra["controls_pass"],
                                                       "ksp_key": ra["ksp_key"], "n_cells": len(v["cells"]),
                                                       "cell": pp.per_ph(v, "cell"), "wet": pp.per_ph(v, "wet")}
            doc["headline"].setdefault(grid, {})[key] = {
                "display": disp, "crossed_verdict": cr["verdict"], "ratio_verdict": ra["verdict"],
                "crossed_controls_pass": cr["controls_pass"], "ratio_controls_pass": ra["controls_pass"],
                "ratio_control_cell": ra["controls"]["supersaturated_control_cell"]["control_cell"],
                "crossed_passing": sum(v["n_passing"] for v in t["crossed"][key]["cell"].values()), "crossed_cells": len(cr["cells"]),
                "ratio_passing": {r: sum(v["n_passing"] for v in t["ratio_" + r][key]["cell"].values()) for r in RATIOS},
                "ratio_cells_each": len(ra["cells"]) // len(RATIOS)}
            for r in RATIOS:                       # verdict-level differences per ratio and pH against the crossed grid
                for ph, e in t["ratio_" + r][key]["cell"].items():
                    c = t["crossed"][key]["cell"][ph]
                    diff = {"grid": grid, "phase": disp, "ratio": r, "pH": e["pH"],
                            "passes_on_ratio": e["n_passing"] > 0, "passes_on_crossed": c["n_passing"] > 0,
                            "min_Ca_T_ratio": e["min_passing_Ca_T"], "min_Ca_T_crossed": c["min_passing_Ca_T"],
                            "min_P_T_ratio": e["min_passing_P_T"], "min_P_T_crossed": c["min_passing_P_T"]}
                    diff["differs"] = (diff["passes_on_ratio"] != diff["passes_on_crossed"]
                                       or diff["min_Ca_T_ratio"] != diff["min_Ca_T_crossed"])
                    doc["differences"].append(diff)
    return doc


def _g(x):
    return "-" if x is None else "%g" % x


def markdown(doc):
    L = ["# Per-pH minimum doses of the Ca:P ratio grid (PH-W4.6) beside the crossed decade grid (PH-W4.5)", "", doc["definition"], "",
         "## Headline verdicts, crossed against ratio grid", "",
         "| grid | phase | crossed | ratio grid | controls crossed/ratio | passing crossed of n | passing at 1.67 / 1.5 / 1.0 of n each | control cell (ratio grid) |",
         "|---|---|---|---|---|---|---|---|"]
    for grid, ph in doc["headline"].items():
        for key, h in ph.items():
            p = h["ratio_passing"]
            L.append("| %s | %s | %s | %s | %s / %s | %d of %d | %d / %d / %d of %d | %s |" % (
                grid, h["display"], h["crossed_verdict"], h["ratio_verdict"], h["crossed_controls_pass"], h["ratio_controls_pass"],
                h["crossed_passing"], h["crossed_cells"], p["1.67"], p["1.5"], p["1"], h["ratio_cells_each"], h["ratio_control_cell"]))
    for grid in ("acid", "alkaline"):
        for source in ["crossed"] + ["ratio_" + r for r in RATIOS]:
            L += ["", "## %s state, %s (K2 verdict basis)" % ("Acid-adjusted" if grid == "acid" else "Slurry (alkaline grid)", source), "",
                  "| phase | pH | cells | passing | fraction | min Ca_T | min P_T | Ca:P range (passing) |", "|---|---|---|---|---|---|---|---|"]
            for key, tab in doc["tables"][grid][source].items():
                for ph, e in sorted(tab["cell"].items(), key=lambda kv: float(kv[0])):
                    rg = e["CaP_ratio_range_passing"]
                    L.append("| %s | %g | %d | %d | %.3f | %s | %s | %s |" % (
                        tab["display"], e["pH"], e["n_cells"], e["n_passing"], e["passing_fraction"], _g(e["min_passing_Ca_T"]),
                        _g(e["min_passing_P_T"]), "-" if rg is None else "%g to %g" % tuple(rg)))
    L += ["", "## Verdict differences against the crossed grid (pass/fail at the pH, or a different minimum passing Ca_T)", "",
          "| grid | phase | ratio | pH | ratio grid passes | crossed passes | min Ca_T ratio / crossed | min P_T ratio / crossed |", "|---|---|---|---|---|---|---|---|"]
    for d in doc["differences"]:
        if d["differs"]:
            L.append("| %s | %s | %s | %g | %s | %s | %s / %s | %s / %s |" % (
                d["grid"], d["phase"], d["ratio"], d["pH"], d["passes_on_ratio"], d["passes_on_crossed"], _g(d["min_Ca_T_ratio"]),
                _g(d["min_Ca_T_crossed"]), _g(d["min_P_T_ratio"]), _g(d["min_P_T_crossed"])))
    L += ["", "## Phases at their own stoichiometric ratio (pass at any pH, lowest-dose cell)", "",
          "| grid | phase | ratio | pH | min Ca_T | min P_T | fraction |", "|---|---|---|---|---|---|---|"]
    for grid in ("alkaline", "acid"):
        for key, r in OWN.items():
            tab = doc["tables"][grid]["ratio_" + r][key]
            hit = [e for e in tab["cell"].values() if e["n_passing"]]
            if not hit:
                L.append("| %s | %s | %s | none passes | - | - | - |" % (grid, tab["display"], r))
            for e in sorted(hit, key=lambda e: (e["min_passing_Ca_T"], e["pH"]))[:1]:
                L.append("| %s | %s | %s | %g | %s | %s | %.3f |" % (grid, tab["display"], r, e["pH"], _g(e["min_passing_Ca_T"]),
                                                                   _g(e["min_passing_P_T"]), e["passing_fraction"]))
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
    ctx = k2_grid.Context(root)
    prov = run._provenance(root, ctx.cfg, root / run.CONFIG, [params_adapter.RegimePriors("R-slurry", None, {}, str(ctx.params_path),
                           run._sha256_file(ctx.params_path), False)], run.THRESHOLDS, False)
    ph_prov.ledger_append(root, SESSION, prov, prov["config_file"], prov["config_hash"],
                          [out / "perph.json", out / "perph.md", out / "perph.csv"], note="per-pH minimum doses of the ratio grid beside the crossed grid")
    return doc


if __name__ == "__main__":
    from nacre._util import repo_root
    main(repo_root())
