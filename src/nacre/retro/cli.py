"""`nacre retro check`: validate preprint/retrodiction/cases.yaml and criterion.md."""


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


def register(subparsers):
    p = subparsers.add_parser("retro", help="retrodiction case checks (lane p0-w2)")
    sub = p.add_subparsers(dest="retro_command", required=True)
    c = sub.add_parser("check", help="validate preprint/retrodiction/cases.yaml and criterion.md")
    c.set_defaults(func=_check)
