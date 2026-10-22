"""Command line of the screen.

    python -m nacre.screen smoke --mock                       Day 1 smoke path (v1 links)
    python -m nacre.screen dryrun --mock [--params P] [--out O] [--independence]
                                                              dry run, output under results/preprint/screen/dryrun/
    python -m nacre.screen ph-dryrun --mineral M --mock [--k1-override] [--draws N] [--out O]
    python -m nacre.screen ph-route-dryrun --route R1|R2|R3|baseline --mock [--draws N] [--out O] [--ladder L]
                                                              PH-W4.1 mineral screen on mock priors, under dryrun_ph/
    python -m nacre.screen production --out O [--prior-set S] [--control C ...] [--convention K=V ...]
                                     [--bind SYM=KEY ...] [--independence] [--no-sensitivity]
                                                              P0-W4.3 only: refused before cp3
    python -m nacre.screen k2-grid --out O [--parts carbonate acid phosphate] [--dry] [--stride N] [--label L]
                                                              PH-W4.2: K2 over the registered grid, the controls and the acid-adjusted state
    python -m nacre.screen ph-production --out O [--dry] [--stride N] [--label L]
                                                              PH-W4.2: phosphate films (stage rows, K2 maps, K3 and K4 gaps, route layer, baselines)
    python -m nacre.screen thresholds copy|check --ref R      copy or check the thresholds block of
                                                              theory/thresholds.md at a git ref
"""
import argparse
import sys
from pathlib import Path

from nacre._util import repo_root
from nacre.screen import k2_grid, ph_dry, ph_prod, ph_route_dry, ph_prov, run, smoke
from nacre.screen import thresholds as thr
from nacre.screen.priors import MockPriorsRefused

DEFAULT_PRIORS = Path("configs") / "preprint" / "mock_priors.yaml"
DEFAULT_OUT = Path("results") / "preprint" / "screen" / "mock" / "summary.json"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.screen")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sm = sub.add_parser("smoke", help="smoke run on mock priors")
    sm.add_argument("--priors", default=str(DEFAULT_PRIORS))
    sm.add_argument("--out", default=str(DEFAULT_OUT))
    sm.add_argument("--mock", action="store_true", help="allow a prior file marked mock: true")
    sm.add_argument("--draws", type=int, default=4096)
    sm.add_argument("--sobol-base", type=int, default=512)
    sm.add_argument("--bootstrap", type=int, default=200)
    sm.add_argument("--seed", type=int, default=0)
    dr = sub.add_parser("dryrun", help="dry run on mock or draft priors (never reported)")
    dr.add_argument("--params", default=str(Path("configs") / "preprint" / "mock_params.yaml"))
    dr.add_argument("--out", default=str(run.DRYRUN_DIR / "summary.json"))
    dr.add_argument("--mock", action="store_true", help="allow a parameter table marked mock: true")
    dr.add_argument("--independence", action="store_true", help="sample the inputs independently")
    dr.add_argument("--framing", help="framing to bind while the table has none registered (dry runs only)")
    ph = sub.add_parser("ph-dryrun", help="dry run of the generic mineral screen on mock priors (PH-W4.1; never reported)")
    ph.add_argument("--mineral", required=True, help="a mineral of screen.yaml `minerals` (hap, acp, capoly)")
    ph.add_argument("--params", default=str(ph_dry.MOCK_TABLE))
    ph.add_argument("--out", help="output summary; default dryrun_ph/<mineral>/summary.json")
    ph.add_argument("--mock", action="store_true", help="allow a parameter table marked mock: true")
    ph.add_argument("--k1-override", action="store_true", help="dry run only: run K3 and K4 although K1 passes no class")
    ph.add_argument("--draws", type=int, default=ph_dry.DEFAULT_DRAWS)
    ph.add_argument("--ladder", help="K1 ladder (v2 or v3 layout); default the mock ladder")
    rd = sub.add_parser("ph-route-dryrun", help="dry run of the route layer on mock priors (PH-W4.2a; never reported)")
    rd.add_argument("--route", required=True, choices=ph_route_dry.CLASSES)
    rd.add_argument("--params", default=str(ph_route_dry.ROUTE_TABLE))
    rd.add_argument("--ladder", default=str(ph_route_dry.MOCK_LADDER), help="K1 ladder (v2 or v3 layout)")
    rd.add_argument("--out", help="output summary; default dryrun_ph/route_<class>/summary.json")
    rd.add_argument("--mock", action="store_true", help="allow a parameter table marked mock: true")
    rd.add_argument("--draws", type=int, default=ph_route_dry.DEFAULT_DRAWS)
    pr = sub.add_parser("production", help="production screen (P0-W4.3, after cp3)")
    pr.add_argument("--out", default=str(run.SCREEN_DIR / "summary.json"))
    for p in (dr, pr):
        p.add_argument("--prior-set", default="table", choices=("table", "ignorance", "analog"),
                       help="prior set of the unmeasured interfacial energies (labelled in the output)")
        p.add_argument("--untruncated", action="store_true", help="run gamma_sl0 untruncated (labelled sensitivity)")
        p.add_argument("--truncation-sensitivity", action="store_true",
                       help="also rerun the decisions untruncated and list the verdicts that change")
        p.add_argument("--stability", help="W5 document with the R-slurry Pourbaix section")
        p.add_argument("--cell", action="append", default=[], help="W5 R-cell document (one per sink; repeatable)")
        p.add_argument("--decision-draws", type=int, help="draws per state of the decision layer")
        p.add_argument("--draws", type=int, help="draws per state of the sensitivity propagation")
        p.add_argument("--control", action="append", default=[],
                       help="deletion-test control of screen.yaml controls (repeatable): bare_oxide, PVDF")
        p.add_argument("--convention", action="append", default=[], metavar="KEY=VALUE",
                       help="sweep override of a registered convention (table key), labelled in the output")
        p.add_argument("--bind", action="append", default=[], metavar="SYMBOL=KEY",
                       help="override an R-slurry binding (a labelled sensitivity)")
        p.add_argument("--no-sensitivity", action="store_true", help="skip the Sobol and Shapley analysis (sweeps)")
        p.add_argument("--label", help="run label recorded in the provenance")
        p.add_argument("--mechanism", action="store_true",
                       help="write the admitted and refused draws of the admissibility rule (report-only diagnostic)")
    pr.add_argument("--independence", action="store_true", help="drop the stated correlations (dependence sweep)")
    kg = sub.add_parser("k2-grid", help="K2 over the registered grid, controls and the acid-adjusted state (PH-W4.2)")
    kg.add_argument("--out", required=True)
    kg.add_argument("--parts", nargs="+", default=["carbonate", "acid"], choices=("carbonate", "acid", "phosphate"))
    kg.add_argument("--dry", action="store_true", help="dry run: output under results/preprint/screen/dryrun_ph/, no ledger")
    kg.add_argument("--stride", type=int, default=1, help="dry run only: every N-th cell of a grid")
    kg.add_argument("--label")
    pp = sub.add_parser("ph-production", help="phosphate films: stage rows, K2 maps, K3 and K4 gaps, route layer (PH-W4.2)")
    pp.add_argument("--out", required=True)
    pp.add_argument("--dry", action="store_true")
    pp.add_argument("--stride", type=int, default=1)
    pp.add_argument("--label")
    th = sub.add_parser("thresholds", help="copy or check configs/preprint/thresholds.yaml")
    th.add_argument("action", choices=("copy", "check"))
    th.add_argument("--ref", default="origin/preprint/p0-w3", help="git ref holding theory/thresholds.md")
    args = ap.parse_args(argv)
    root = repo_root()
    if args.cmd == "thresholds":
        try:
            text, sha = thr.source_at(root, args.ref)
        except Exception:
            print("%s is not present at %s" % (thr.THEORY, args.ref), file=sys.stderr)
            return 2
        target = root / thr.COPY
        if args.action == "copy":
            target.write_text(thr.make_copy(text, sha), encoding="utf-8")
            print("wrote %s from %s@%s" % (thr.COPY, thr.THEORY, sha))
            return 0
        try:
            thr.equal(text, target.read_text(encoding="utf-8"))
        except (thr.ThresholdsMismatch, FileNotFoundError) as exc:
            print("MISMATCH against %s@%s: %s" % (thr.THEORY, sha, exc), file=sys.stderr)
            return 1
        print("EQUAL: %s matches %s@%s" % (thr.COPY, thr.THEORY, sha))
        return 0
    if args.cmd == "k2-grid":
        def log(cid, rec):
            print("  %-4s %-12s %s" % (rec.get("draws"), rec.get("verdict"), cid[:100]), flush=True)
        try:
            path, doc, stats = k2_grid.run_k2_grid(root, root / args.out, tuple(args.parts), args.dry, label=args.label,
                                                   log=log if args.dry else None, stride=args.stride)
        except (run.ProductionRefused, ph_prov.Frozen, run.params_adapter.PriorFileError) as exc:
            print("refused: %s" % exc, file=sys.stderr)
            return 2
        print("wrote %s  (%.1f s, peak %.0f MB, %d cells, %d capped)" % (path.relative_to(root), stats["seconds"], stats["peak_mb"],
                                                                         stats["cells"], stats["capped_cells"]))
        return 0
    if args.cmd == "ph-production":
        try:
            path, doc, stats = ph_prod.run_phosphate(root, root / args.out, args.dry, args.label, args.stride)
        except (run.ProductionRefused, ph_prov.Frozen, run.params_adapter.PriorFileError) as exc:
            print("refused: %s" % exc, file=sys.stderr)
            return 2
        print("wrote %s  (%.1f s, peak %.0f MB, %d cells, %d capped)" % (path.relative_to(root), stats["seconds"], stats["peak_mb"],
                                                                         stats["cells"], stats["capped_cells"]))
        return 0
    if args.cmd == "ph-dryrun":
        out = root / (args.out or (run.DRYRUN_PH_DIR / args.mineral / "summary.json"))
        try:
            path, _, stats = ph_dry.run_mineral(root, args.mineral, out, params_path=root / args.params,
                                                allow_mock=args.mock, k1_override=args.k1_override,
                                                draws=args.draws, ladder_path=args.ladder)
        except (MockPriorsRefused, ph_dry.DryRunRefused, run.params_adapter.PriorFileError) as exc:
            print("refused: %s" % exc, file=sys.stderr)
            return 2
        print("wrote %s  (%.1f s, peak %.0f MB)" % (path.relative_to(root), stats["seconds"], stats["peak_mb"]))
        return 0
    if args.cmd == "ph-route-dryrun":
        out = root / (args.out or (run.DRYRUN_PH_DIR / ("route_%s" % args.route) / "summary.json"))
        try:
            path, _, stats = ph_route_dry.run_route(root, args.route, out, params_path=root / args.params,
                                                    ladder_path=args.ladder, allow_mock=args.mock, draws_n=args.draws)
        except (MockPriorsRefused, ph_dry.DryRunRefused, run.params_adapter.PriorFileError) as exc:
            print("refused: %s" % exc, file=sys.stderr)
            return 2
        print("wrote %s  (%.1f s, peak %.0f MB)" % (path.relative_to(root), stats["seconds"], stats["peak_mb"]))
        return 0
    if args.cmd in ("dryrun", "production"):
        try:
            kw = dict(prior_set=args.prior_set, truncation=not args.untruncated, controls=args.control,
                      conventions={k: float(v) for k, v in (c.split("=", 1) for c in args.convention)} or None,
                      bind=dict(b.split("=", 1) for b in args.bind) or None, sensitivity=not args.no_sensitivity,
                      run_label=args.label, mechanism=args.mechanism,
                      truncation_sensitivity=args.truncation_sensitivity,
                      stability_path=(root / args.stability) if args.stability else None,
                      cell_paths=[root / c for c in args.cell], decision_draws=args.decision_draws,
                      overrides={"propagation": {"draws_per_regime": args.draws}} if args.draws else None)
            if args.cmd == "dryrun":
                path, _ = run.run(root, root / args.out, params_path=root / args.params, dry_run=True,
                                  allow_mock=args.mock, independence=args.independence, framing=args.framing, **kw)
            else:
                path, _ = run.run(root, root / args.out, dry_run=False, independence=args.independence, **kw)
        except (MockPriorsRefused, run.ProductionRefused, run.params_adapter.PriorFileError) as exc:
            print("refused: %s" % exc, file=sys.stderr)
            return 2
        print("wrote %s" % path.relative_to(root))
        return 0
    try:
        path, _ = smoke.run(root, root / args.priors, root / args.out, draws=args.draws,
                            sobol_base=args.sobol_base, bootstrap=args.bootstrap, seed=args.seed,
                            allow_mock=args.mock)
    except MockPriorsRefused as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return 2
    print("wrote %s" % path.relative_to(root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
