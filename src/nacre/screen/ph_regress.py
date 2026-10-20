"""Carbonate regression of the generalised chain (PH-W4.1): the mineral-object chain must reproduce the frozen results.

    python -m nacre.screen.ph_regress [--doc results/preprint/screen/ignorance_adm/summary.json] [--prior-set ignorance]

Reruns the propagation of the committed W4.3b document's primary state (same table, prior set, framing, seed and draws, the
central design point) through the generalised chain with the calcite control, and compares each quantity of each link with the
document: mean and the registered quantiles. The comparison is within the sampling tolerance, two standard errors of the mean
of the committed draws (the seeds are fixed, so a difference above rounding means the chain changed). The committed documents are
read, never written. Output of a rerun belongs under results/preprint/screen/dryrun_ph/ and is never reported.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

from nacre._util import repo_root
from nacre.screen import chain, params_adapter, propagate, run
from nacre.screen.mineral import CALCITE

DOC = Path("results") / "preprint" / "screen" / "ignorance_adm" / "summary.json"
RELATIVE_ROUNDING = 1e-9


def primary_state(root, doc_path, prior_set, framing="calcite"):
    """(state id, RegimePriors, regime entry) of the committed document's primary state, rebuilt from the table."""
    root = Path(root)
    doc = json.loads((root / doc_path).read_text(encoding="utf-8"))
    entry = doc["regimes"]["R-slurry"]
    cfg = run.load_config(root)
    states = run.load_states(root / run.params_adapter.PRODUCTION_PARAMS, "R-slurry", cfg, False, framing, True, prior_set)
    for sid, rp in states:
        if chain.evaluable_links(rp.joint.symbols):
            if sid != entry["primary_state"]:
                raise ValueError("the first evaluable state is %r, the document's primary state is %r" % (sid, entry["primary_state"]))
            return sid, rp, entry, cfg
    raise ValueError("no evaluable state")


def rerun(rp, entry, cfg, mineral=CALCITE):
    """Chain outputs of the primary state with the document's seed and draws (the pre-sensitivity steps of run_regime)."""
    mc_seq, _ = np.random.SeedSequence(entry["seed"]).spawn(2)
    outputs, _ = propagate.propagate_chain(lambda x: chain.evaluate(x, mineral=mineral), rp.joint, int(entry["draws"]),
                                           int(mc_seq.generate_state(1)[0]), cfg["propagation"]["chunk"])
    if (cfg.get("registrations") or {}).get("admissibility") and "nucleate" in outputs:
        keep = chain.admissible_mask(outputs)
        outputs["nucleate"] = {q: np.where(keep, np.asarray(v, dtype=float), np.nan) for q, v in outputs["nucleate"].items()}
    return outputs


def compare(outputs, entry):
    """{link: {quantity: {...}}} differences between the rerun and the committed quantities, with the tolerance."""
    levels = tuple(float(k) for k in next(iter(next(iter(entry["links"].values()))["quantities"].values()))["quantiles"])
    out = {}
    for link, rec in entry["links"].items():
        out[link] = {}
        for q, ref in rec["quantities"].items():
            new = propagate.describe(outputs[link][q], levels)
            tol = max(2.0 * ref["sd"] / np.sqrt(ref["n_valid"]), RELATIVE_ROUNDING * abs(ref["mean"]))
            diffs = [abs(new["mean"] - ref["mean"])] + [abs(new["quantiles"][k] - ref["quantiles"][k]) for k in ref["quantiles"]]
            scale = max(abs(ref["mean"]), 1e-300)
            out[link][q] = {"n_valid_new": new["n_valid"], "n_valid_doc": ref["n_valid"], "max_abs_diff": float(max(diffs)),
                            "max_rel_diff": float(max(diffs) / scale), "tolerance": float(tol),
                            "within_tolerance": bool(max(diffs) <= tol and new["n_valid"] == ref["n_valid"])}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.screen.ph_regress")
    ap.add_argument("--doc", default=str(DOC))
    ap.add_argument("--prior-set", default="ignorance")
    ap.add_argument("--out", help="write the comparison under results/preprint/screen/dryrun_ph/")
    a = ap.parse_args(argv)
    root = repo_root()
    sid, rp, entry, cfg = primary_state(root, a.doc, a.prior_set)
    res = compare(rerun(rp, entry, cfg), entry)
    n = sum(len(v) for v in res.values())
    ok = sum(r["within_tolerance"] for v in res.values() for r in v.values())
    for link, qs in res.items():
        worst = max(qs.values(), key=lambda r: r["max_rel_diff"])
        print("%-11s %2d quantities, within tolerance %2d, max relative difference %.2e" %
              (link, len(qs), sum(r["within_tolerance"] for r in qs.values()), worst["max_rel_diff"]))
    print("%s state %s: %d of %d quantities match %s" % (a.prior_set, sid, ok, n, a.doc))
    if a.out:
        path = Path(root) / a.out
        if not run._inside(path, root / run.DRYRUN_PH_DIR):
            raise SystemExit("output belongs under %s" % run.DRYRUN_PH_DIR)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"doc": a.doc, "state": sid, "links": res}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
