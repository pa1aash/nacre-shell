"""K2 framings of carbonate: calcite, aragonite and ACC; the row labels; the per-polymorph falsifiability controls (PH-W4.2e, PH-W4.2).

    python -m nacre.screen.k2_carbonate [--draws N] [--out results/preprint/screen/dryrun_ph/k2_carbonate_controls.json]

theory/claims_redirect.md Section 11a. The K2 test of every polymorph is the Omega test of Section 3a with the same code path;
only the K_sp key of the framing changes (screen.yaml bindings.R-slurry.by_framing, one framing per run). The labels are an output
field of each carbonate row, one per polymorph (PH-W4.2 pre-run commit; there is no other label and no row-level label):

    calcite    "calcite (suitable against dissolution, a necessary condition, in [region])"      K2 passes in the registered region
    aragonite  "aragonite (dissolution stability only; formation unsupported at slurry pH and room temperature)"
    ACC        "ACC (reported beside calcite and aragonite; dose window [window]; not required to pass)"

A polymorph that does not pass K2 carries its regime word (excluded, open, undetermined) in place of the pass text. A polymorph
whose control does not flag undersaturation (Omega_bulk < 1) at the low-dose corner of the registered grid has an inconclusive K2
in every row. The dry run writes only under results/preprint/screen/dryrun_ph/ and is never reported.

The aragonite input is log10_ksp_aragonite_25c_i0 (uniform on [-8.376, -8.296]); the older key log10_ksp_aragonite is
"superseded, not read" (screen.yaml registrations.superseded_keys), and a test asserts that no run reads it.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

from nacre._util import repo_root
from nacre.screen import decision, params_adapter, run, study
from nacre.screen import thresholds as thr

#: K2 verdict word -> regime word (theory/claims_redirect.md 11d); None (data missing) is undetermined.
REGIME = {"feasible": "suitable against dissolution", "falsified": "excluded", "inconclusive": "open",
          "undetermined": "undetermined"}
LABEL_CALCITE = "calcite (suitable against dissolution, a necessary condition, in [%s])"
LABEL_ARAGONITE = "aragonite (dissolution stability only; formation unsupported at slurry pH and room temperature)"
LABEL_ACC = "ACC (reported beside calcite and aragonite; dose window [%s]; not required to pass)"
POLYMORPHS = ("calcite", "aragonite", "ACC")
OUT = Path(run.DRYRUN_PH_DIR) / "k2_carbonate_controls.json"


def registered_framings(cfg):
    """{polymorph: required} of screen.yaml registrations.k2_framings, in registration order."""
    reg = (cfg.get("registrations") or {}).get("k2_framings") or {}
    return {name: bool((spec or {}).get("required")) for name, spec in reg.items()}


def ksp_keys(cfg):
    """{polymorph: table key of its K_sp} as bound in screen.yaml."""
    by = cfg["bindings"]["R-slurry"]["by_framing"]
    return {name: by[name]["K_sp"] for name in registered_framings(cfg)}


def superseded_keys(cfg):
    """{table key: reason} of the keys no run reads (screen.yaml registrations.superseded_keys)."""
    return dict((cfg.get("registrations") or {}).get("superseded_keys") or {})


def effective_verdict(verdict, control_ok):
    """K2 verdict of a polymorph at a row: inconclusive when its control did not flag undersaturation."""
    if verdict is None or not control_ok:
        return "inconclusive"
    return verdict


def regime_word(verdict):
    """The regime-vocabulary word of a K2 verdict (None: undetermined)."""
    return REGIME.get(verdict if verdict is not None else "undetermined", "undetermined")


def polymorph_label(polymorph, verdict, region=None, window=None):
    """The label field of one polymorph at a row (verdict: the effective K2 verdict or None).

    calcite passes -> the pass text with the region; aragonite always names the limit of what K2 says (dissolution stability only)
    and carries its regime word when it does not pass; ACC names its dose window, whatever its verdict.
    """
    if polymorph == "calcite":
        if verdict == "feasible":
            return LABEL_CALCITE % (region or "no region named")
        return "calcite (%s in [%s])" % (regime_word(verdict), region or "no region named")
    if polymorph == "aragonite":
        if verdict == "feasible":
            return LABEL_ARAGONITE
        return "aragonite (%s; dissolution stability only; formation unsupported at slurry pH and room temperature)" % \
            regime_word(verdict)
    if polymorph == "ACC":
        return LABEL_ACC % (window or "none")
    raise KeyError(polymorph)


def k2_record(verdicts, controls, required, regions=None, windows=None):
    """The K2 output record of a carbonate row: per-polymorph effective verdicts, regime words and labels.

    verdicts: {polymorph: raw K2 verdict or None (not registered, data missing)}; controls: {polymorph: control flagged
    undersaturation}; regions / windows: {polymorph: text}. There is no row-level label.
    """
    poly = {}
    for p in required:
        eff = effective_verdict(verdicts.get(p), bool(controls.get(p)))
        poly[p] = {"verdict": eff, "raw_verdict": verdicts.get(p), "regime": regime_word(eff if verdicts.get(p) is not None else None),
                   "control_flags_undersaturation": bool(controls.get(p)), "required": required[p],
                   "label": polymorph_label(p, eff if verdicts.get(p) is not None else None, (regions or {}).get(p),
                                            (windows or {}).get(p))}
    return {"polymorphs": poly}


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
    """Document of the controls, per polymorph: the low-dose corner at the lowest pH of ph_slurry_modified and the supersaturated
    state (the gating controls of Section 11a), and the same low-dose corner in the unmodified alkaline slurry scanned over pH 10 to
    13 (reported with the pH at which undersaturation sets in; not gating)."""
    from nacre.screen import k2_grid
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
    chunk = int(cfg["propagation"]["chunk"])
    out = {}
    for pol in required:
        gating, scan = k2_grid.carbonate_controls(path, cfg, resolver, pol, p, draws, seed, min(chunk, draws), allow_mock)
        under, over = gating["undersaturated"], gating["supersaturated"]
        out[pol] = {"ksp_key": keys[pol], "undersaturated": under, "supersaturated": over,
                    "flags_undersaturation": under.get("verdict") == decision.CONTROL_MUST["undersaturated"],
                    "supersaturated_reports_stability": over.get("verdict") == decision.CONTROL_MUST["supersaturated"],
                    "second_control": {"label": "low-dose corner in the unmodified alkaline slurry (pH 10 to 13), scanned; not gating",
                                       "scan": {"%g" % ph: {k: r.get(k) for k in ("verdict", "P_good", "P_bad", "half_width")}
                                                for ph, r in scan.items()},
                                       "undersaturation": k2_grid.onset(scan) if scan else None}}
    return {"session": "PH-W4.2", "dry_run": True, "reported": False, "draws": draws, "seed": seed, "p_cred": p,
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
