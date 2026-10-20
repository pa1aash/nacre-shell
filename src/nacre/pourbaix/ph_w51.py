"""PH-W5.1 (lane p0-w5): phosphate benchmark, Al-O-H passivation window, K1 ladder v2 with framings and stages.

Outputs under results/preprint/pourbaix/ph_w51/. The frozen carbonate outputs and the PH-K1 outputs are only
read. Materials Project numbers come from database 2026.09.28 (the PH-K1 cache plus the PH-W5.1 additions)
and are comparators only.

    uv run python -m nacre.pourbaix.ph_w51 benchmark   # step 1
    uv run python -m nacre.pourbaix.ph_w51 run         # every step
    uv run python -m nacre.pourbaix.ph_w51 ledger      # provenance record of the current outputs
"""
import argparse
import json
import sys
import warnings

from nacre.pourbaix import cache, gasref, provenance
from nacre.pourbaix import ph_k1 as k
from nacre.pourbaix import ph_w51_bench as bm
from nacre.pourbaix import ph_w51_cache as wc
from nacre.pourbaix import window as w
from nacre.pourbaix.paths import rel

SESSION = "PH-W5.1"
OUT = wc.W51_DIR


def pooled():
    warnings.simplefilter("ignore")
    entries, excluded = wc.load_entries()
    ew = w.EnergyBook(entries, k.T0, gasref.SCHEMES["janaf"], cache.CACHE_DIR)
    return entries, excluded, ew


def _dump(path, doc):
    path.write_text(json.dumps(doc, indent=1, default=float) + "\n", encoding="utf-8")


def run_benchmark(entries=None, ew=None):
    if entries is None:
        entries, _, ew = pooled()
    bench, summary = bm.run(entries, ew)
    OUT.mkdir(parents=True, exist_ok=True)
    bm.write_csv(bench, OUT / "benchmark_w51.csv")
    _dump(OUT / "benchmark_w51.json", {"session": SESSION, "step": "1 phosphate benchmark",
                                       "generated_utc": provenance.utc_now(), "git_sha": provenance.git_sha(),
                                       "inputs": bm.inputs_record(), "summary": summary, "rows": bench})
    print("wrote", rel(OUT / "benchmark_w51.csv"))
    return bench, summary


LEDGER = k.REPO / "jobs" / "ledger" / "p0-w5.jsonl"


def ledger(outputs):
    """Append one provenance record for the named outputs (paths relative to OUT)."""
    man = wc.manifest()
    rec = {"session": SESSION, "run": "ph-w51", "kind": "pourbaix-ph-w51", "mock": False,
           "utc": provenance.utc_now(), "git_sha": provenance.git_sha(), "git_dirty": provenance.git_dirty(),
           "params_sha": k.PARAMS_SHA, "cache_hash": cache.cache_hash(), "w51_cache_hash": wc.cache_hash(),
           "evidence_table_sha256": k.evidence_sha256(), "mp_database_version": man["mp_database_version"],
           "outputs": [{"path": rel(OUT / o), "sha256": provenance.sha256_file(OUT / o)} for o in outputs
                       if (OUT / o).is_file()],
           "local_only": [{"path": f["location"], "sha256": f["sha256"], "bytes": f["bytes"]}
                          for f in man["files"] if f.get("local_only")]}
    provenance.ledger_append(LEDGER, rec)
    return rec


STEP1_OUTPUTS = ("benchmark_w51.csv", "benchmark_w51.json", "cache/manifest.json", "cache/janaf_P_white.json",
                 "cache/janaf_Ca_alpha.json", "cache/janaf_Li_cr.json")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.ph_w51")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("benchmark")
    sub.add_parser("run")
    lg = sub.add_parser("ledger")
    lg.add_argument("--step1", action="store_true", help="record the step-1 outputs only")
    args = ap.parse_args(argv)
    if args.cmd == "benchmark":
        run_benchmark()
        return 0
    if args.cmd == "ledger":
        if args.step1:
            outs = STEP1_OUTPUTS
        else:
            from nacre.pourbaix import ph_w51_run
            outs = STEP1_OUTPUTS + ph_w51_run.OUTPUTS
        print(json.dumps({"appended": len(ledger(outs)["outputs"])}))
        return 0
    from nacre.pourbaix import ph_w51_run
    return ph_w51_run.run()


if __name__ == "__main__":
    sys.exit(main())
