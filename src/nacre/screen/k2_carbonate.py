"""K2 framings of carbonate: calcite, aragonite and ACC; the row label; the per-polymorph falsifiability control (PH-W4.2e).

    python -m nacre.screen.k2_carbonate [--draws N] [--out results/preprint/screen/dryrun_ph/k2_carbonate_controls.json]

theory/claims_redirect.md Section 11a. The K2 test of every polymorph is the Omega test of Section 3a with the same code path;
only the K_sp key of the framing changes (screen.yaml bindings.R-slurry.by_framing, one framing per run). The label is an output
field with two values, never free text:

    nacre-type           aragonite AND calcite both pass K2 (ACC may fail or be undetermined)
    carbonate (calcite)  every other carbonate row

A polymorph whose control does not flag undersaturation (Omega_bulk < 1) at the low-dose corner of the registered grid has an
inconclusive K2 in every row, and the rows that depend on it cannot be labelled nacre-type. The dry run writes only under
results/preprint/screen/dryrun_ph/ and is never reported.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

from nacre._util import repo_root
from nacre.screen import decision, params_adapter, run, study
from nacre.screen import thresholds as thr

LABEL_NACRE_TYPE = "nacre-type"
LABEL_CARBONATE = "carbonate (calcite)"
LABELS = (LABEL_NACRE_TYPE, LABEL_CARBONATE)
OUT = Path(run.DRYRUN_PH_DIR) / "k2_carbonate_controls.json"


def registered_framings(cfg):
    """{polymorph: required} of screen.yaml registrations.k2_framings, in registration order."""
    reg = (cfg.get("registrations") or {}).get("k2_framings") or {}
    return {name: bool((spec or {}).get("required")) for name, spec in reg.items()}


def ksp_keys(cfg):
    """{polymorph: table key of its K_sp} as bound in screen.yaml."""
    by = cfg["bindings"]["R-slurry"]["by_framing"]
    return {name: by[name]["K_sp"] for name in registered_framings(cfg)}


def effective_verdict(verdict, control_ok):
    """K2 verdict of a polymorph at a row: inconclusive when its control did not flag undersaturation."""
    if verdict is None or not control_ok:
        return "inconclusive"
    return verdict


def carbonate_label(verdicts, controls, required):
    """The label field of a carbonate row (Section 11a).

    verdicts: {polymorph: K2 verdict or None (not registered, data missing)}; controls: {polymorph: control flagged
    undersaturation}; required: {polymorph: bool}. Passing calcite alone never earns nacre-type; a polymorph absent from
    ``verdicts`` (a study that has not registered it) is undetermined.
    """
    need = [p for p, r in required.items() if r]
    if not need:
        return LABEL_CARBONATE
    for p in need:
        if effective_verdict(verdicts.get(p), bool(controls.get(p))) != "feasible":
            return LABEL_CARBONATE
    return LABEL_NACRE_TYPE


def k2_record(verdicts, controls, required):
    """The K2 output record of a carbonate row: per-polymorph effective verdicts beside the label field."""
    poly = {p: {"verdict": effective_verdict(verdicts.get(p), bool(controls.get(p))), "raw_verdict": verdicts.get(p),
                "control_flags_undersaturation": bool(controls.get(p)), "required": required[p]} for p in required}
    return {"polymorphs": poly, "carbonate_label": carbonate_label(verdicts, controls, required)}


def more_soluble(resolver, keys):
    """The more soluble of the crystalline polymorphs, read from the two K_sp keys (larger log10 K_sp), never assumed."""
    vals = {p: float(resolver.value(k)) for p, k in keys.items() if p != "ACC"}
    top = max(vals, key=vals.get)
    return {"log10_ksp": vals, "more_soluble": top}


def low_dose_corner(cfg, resolver):
    """(values, labels) of the registered undersaturated control state, with a check that it is the grid's low-dose corner."""
    pts = study.control_points(cfg, resolver)
    vals, labels = pts["undersaturated"]
    ca_axis = study._axis_values(cfg["design_axes"]["Ca_T"], resolver, study.AXIS_UNITS["Ca_T"])
    c_axis = study._axis_values(cfg["design_axes"]["C_T"], resolver, study.AXIS_UNITS["C_T"])
    corner = {"Ca_T": min(v for _, v in ca_axis), "C_T": min(v for _, v in c_axis)}
    for k, v in corner.items():
        if not np.isclose(vals[k], v):
            raise ValueError("the registered undersaturated control is not the low-dose corner on %s: %g against %g"
                             % (k, vals[k], v))
    return vals, labels


def run_controls(root, draws=2 ** 13, params_path=None, allow_mock=False, prior_set="table"):
    """Document of the controls: the Omega test at the low-dose corner and the supersaturated state, per polymorph."""
    root = Path(root)
    cfg = run.load_config(root)
    path = root / (params_path or params_adapter.PRODUCTION_PARAMS)
    doc, _ = params_adapter.read_table(path, allow_mock)
    resolver = decision.Resolver.from_table(doc)
    rule = thr.load_thresholds(root / thr.COPY)["rule"]
    p = decision.credible_level(rule, resolver)
    required = registered_framings(cfg)
    keys = ksp_keys(cfg)
    pts = study.control_points(cfg, resolver)
    corner, _ = low_dose_corner(cfg, resolver)
    seed = int(cfg["propagation"]["seed"])
    out = {}
    for pol in required:
        out[pol] = {"ksp_key": keys[pol]}
        for name, (vals, labels) in pts.items():
            rec = study._control(path, cfg, allow_mock, prior_set, True, draws, int(cfg["propagation"]["chunk"]), seed, p,
                                 vals, labels, framing=pol)
            out[pol][name] = rec
        under, over = out[pol]["undersaturated"], out[pol]["supersaturated"]
        out[pol]["flags_undersaturation"] = under.get("verdict") == decision.CONTROL_MUST["undersaturated"]
        out[pol]["supersaturated_reports_stability"] = over.get("verdict") == decision.CONTROL_MUST["supersaturated"]
    return {"session": "PH-W4.2e", "dry_run": True, "reported": False, "draws": draws, "seed": seed, "p_cred": p,
            "prior_set": prior_set, "corner": {"Ca_T_mol_m3": corner["Ca_T"], "C_T_mol_m3": corner["C_T"],
                                               "axes": pts["undersaturated"][1]},
            "solubility_order": more_soluble(resolver, keys), "polymorphs": out}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.screen.k2_carbonate")
    ap.add_argument("--draws", type=int, default=2 ** 13)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    root = repo_root()
    path = Path(root) / a.out
    if not run._inside(path, Path(root) / run.DRYRUN_PH_DIR):
        raise SystemExit("output belongs under %s" % run.DRYRUN_PH_DIR)
    doc = run_controls(root, a.draws)
    for pol, r in doc["polymorphs"].items():
        print("%-9s corner verdict %-10s flags Omega < 1: %-5s  supersaturated: %s" %
              (pol, r["undersaturated"].get("verdict"), r["flags_undersaturation"], r["supersaturated"].get("verdict")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True, default=float) + "\n", encoding="utf-8")
    return 0 if all(r["flags_undersaturation"] for r in doc["polymorphs"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
