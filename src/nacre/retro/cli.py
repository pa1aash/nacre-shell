"""`nacre retro check`: validate preprint/retrodiction/cases.yaml and criterion.md; `nacre retro run`: the run."""


def _check(args):
    from nacre.retro import cases
    errors, summary = cases.check()
    for e in errors:
        print("ERROR: %s" % e)
    print("retro: usable %s, excluded %s; terminations %s; templated %s; negatives %s; k = %s of N = %s, "
          "chance probability %.4f" % (summary.get("usable"), summary.get("excluded"),
                                       ", ".join(summary.get("terminations") or []),
                                       ", ".join(summary.get("templated") or []) or "none",
                                       summary.get("negatives"), summary.get("k"), summary.get("usable"),
                                       summary.get("chance_probability") or 0.0))
    if summary.get("missing_terminations"):
        print("coverage: no usable case for %s" % ", ".join(summary["missing_terminations"]))
    print("retro check: %s" % ("FAIL" if errors else "PASS"))
    return 1 if errors else 0


def _run(args):
    from nacre import _util
    from nacre.retro import run
    try:
        rec = run.run(_util.repo_root(), args.fixed_before_run, params_tag=args.params_tag, draws=args.draws,
                      seed=args.seed, n_perm=args.perm)
    except run.RunError as exc:
        print("retro run: BLOCKED: %s" % exc)
        return 2
    s = rec["summary"]
    for r in rec["cases"]:
        d = r["delta"] or {}
        print("%s  delta %s [%s, %s]  %s  %s" % (r["id"], d.get("median"), d.get("q05"), d.get("q95"),
                                                 r["observed_relation"], r["verdict"]))
    print("retro run: %d/%d correct (k = %d): %s; swap check %s" % (
        s["correct"], s["N"], s["k"], "PASS" if s["pass"] else "FAIL", "holds" if s["swap_check"]["holds"] else "FAILS"))
    return 0


def register(subparsers):
    p = subparsers.add_parser("retro", help="retrodiction case checks (lane p0-w2)")
    sub = p.add_subparsers(dest="retro_command", required=True)
    c = sub.add_parser("check", help="validate preprint/retrodiction/cases.yaml and criterion.md")
    c.set_defaults(func=_check)
    r = sub.add_parser("run", help="run the frozen retrodiction set once (P0-W2.3)")
    r.add_argument("--fixed-before-run", required=True, help="the fixed-before-run commit")
    r.add_argument("--params-tag", default="p0-cp3")
    r.add_argument("--draws", type=int, default=20000)
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--perm", type=int, default=2000, help="permutations per null scheme")
    r.set_defaults(func=_run)
