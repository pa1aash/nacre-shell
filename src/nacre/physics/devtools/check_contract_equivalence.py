"""Check the physics implementation against the theory contract on a git ref.

    uv run python -m nacre.physics.devtools.check_contract_equivalence \\
        --ref origin/preprint/p0-w3 --record configs/preprint/contract_check.json

Reads theory/contract.yaml and theory/symbols.yaml with ``git show <ref>:<path>`` (the
theory lane's files reach this branch only after integration), runs every equivalence,
limit, monotonicity and composite check of nacre.physics.devtools.equivalence, prints one
line per function and optionally records the result with the commit it was checked
against. Exit status 0 only if every check passes.
"""
import argparse
import json
import subprocess
import sys
import time

from nacre._util import repo_root
from nacre.physics.devtools.equivalence import RTOL, check_all

CONTRACT = "theory/contract.yaml"
SYMBOLS = "theory/symbols.yaml"


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=True).stdout


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check_contract_equivalence")
    ap.add_argument("--ref", default="origin/preprint/p0-w3")
    ap.add_argument("--points", type=int, default=256)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--record", help="write a JSON record of the check to this path")
    args = ap.parse_args(argv)
    root = repo_root()
    ref_sha = _git(root, "rev-parse", args.ref + "^{commit}").strip()
    contract_sha = _git(root, "log", "-1", "--format=%H", ref_sha, "--", CONTRACT).strip()
    contract_text = _git(root, "show", "%s:%s" % (ref_sha, CONTRACT))
    symbols_text = _git(root, "show", "%s:%s" % (ref_sha, SYMBOLS))
    ok, results, coverage = check_all(contract_text, symbols_text, n=args.points, seed=args.seed)
    rows = {}
    for name, rs in results.items():
        status = "PASS" if all(r.ok for r in rs) else "FAIL"
        eq = rs[0]
        msgs = [m for r in rs for m in r.messages]
        rows[name] = {"status": status, "points": eq.points, "max_rel_err": eq.max_rel_err,
                      "limit_cases": rs[1].points if len(rs) > 1 else 0,
                      "monotonicity_samples": rs[2].points if len(rs) > 2 else 0, "notes": msgs}
        print("%-20s %s  points=%-4d max_rel_err=%.2e  %s" % (name, status, eq.points,
                                                            eq.max_rel_err, "; ".join(msgs)))
    for line in coverage:
        print("COVERAGE: " + line)
    print("checked against %s (%s), contract last changed in %s: %s"
          % (args.ref, ref_sha, contract_sha, "PASS" if ok else "FAIL"))
    if args.record:
        record = {"ref": args.ref, "ref_sha": ref_sha, "contract_sha": contract_sha,
                  "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "implementation_sha": _git(root, "rev-parse", "HEAD").strip(),
                  "rtol": RTOL, "points": args.points, "seed": args.seed,
                  "status": "PASS" if ok else "FAIL", "coverage": coverage, "functions": rows}
        out = root / args.record
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
