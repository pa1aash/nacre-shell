"""nacre verify: the repository-wide checks."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import yaml

from nacre import _util


def _result(name, status, detail=""):
    return {"name": name, "status": status, "detail": detail}


def check_tests(root, strict):
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("NACRE_VERIFY_SKIP_TESTS"):
        return _result("tests", "SKIP", "running inside pytest")
    p = subprocess.run(["uv", "run", "pytest", "-q"], cwd=root, capture_output=True, text=True)
    last = (p.stdout.strip().splitlines() or [""])[-1]
    return _result("tests", "PASS" if p.returncode == 0 else "FAIL", last)


def _commits(root):
    p = _util.git(root, "rev-list", "HEAD")
    return p.stdout.split() if p.returncode == 0 else []


def check_attribution(root, strict):
    scan = _util.hooklib(root, "_scan")
    bad = []
    files = _util.git(root, "ls-files", "-z").stdout.split("\0")
    for rel in [f for f in files if f]:
        for rule in scan.scan_path(rel):
            bad.append("%s [%s] path" % (rel, rule))
        path = Path(root) / rel
        if path.is_file() and not path.is_symlink():
            for no, rule in scan.scan_bytes(path.read_bytes()):
                bad.append("%s:%d [%s]" % (rel, no, rule))
    shas = _commits(root)
    for sha in shas:
        msg = _util.git(root, "show", "-s", "--format=%B", sha).stdout
        for no, rule in scan.scan_message(msg):
            bad.append("commit %s:%d [%s]" % (sha[:12], no, rule))
    detail = "%d files, %d commits" % (len([f for f in files if f]), len(shas))
    return _result("attribution", "FAIL" if bad else "PASS", "; ".join(bad[:5]) if bad else detail)


def check_identity(root, strict):
    scan = _util.hooklib(root, "_scan")
    bad = []
    out = _util.git(root, "log", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce", "HEAD").stdout
    rows = [ln.split("\0") for ln in out.splitlines() if ln]
    for sha, an, ae, cn, ce in rows:
        if not (scan.ident_ok(an, ae) and scan.ident_ok(cn, ce)):
            bad.append("%s %s <%s> / %s <%s>" % (sha[:12], an, ae, cn, ce))
    return _result("identity", "FAIL" if bad else "PASS", "; ".join(bad[:5]) if bad else "%d commits" % len(rows))


def check_signatures(root, strict):
    shas = _commits(root)
    bad = []
    for sha in shas:
        body = _util.git(root, "cat-file", "commit", sha).stdout.split("\n\n", 1)[0]
        if not any(ln.startswith("gpgsig") for ln in body.split("\n")):
            bad.append(sha[:12] + " unsigned")
        elif strict:
            signers = Path(root) / "ops" / "allowed_signers"
            p = _util.git(root, "-c", "gpg.format=ssh", "-c", "gpg.ssh.allowedSignersFile=%s" % signers,
                          "verify-commit", sha)
            if p.returncode != 0:
                err = (p.stderr.strip().splitlines() or [""])[-1]
                bad.append("%s signature does not verify: %s" % (sha[:12], err))
    mode = "verified" if strict else "headers"
    return _result("signatures", "FAIL" if bad else "PASS", "; ".join(bad[:5]) if bad else "%d commits (%s)" % (len(shas), mode))


def check_lanes(root, strict):
    branch = _util.current_branch(root)
    if not branch or not branch.startswith("lane/"):
        return _result("lane ownership", "INACTIVE", "not a lane branch")
    lib = _util.hooklib(root, "_lanes")
    cfg = lib.load_lanes(str(root))
    lane, err = lib.resolve_lane(branch, cfg)
    if err:
        return _result("lane ownership", "FAIL", err)
    main = "origin/main" if _util.git(root, "rev-parse", "-q", "--verify", "origin/main").returncode == 0 else "main"
    mb = _util.git(root, "merge-base", main, "HEAD")
    if mb.returncode != 0:
        return _result("lane ownership", "FAIL", "no merge-base with " + main)
    names = _util.git(root, "diff", "--name-only", "-z", "--no-renames", mb.stdout.strip(), "HEAD").stdout
    paths = [p for p in names.split("\0") if p]
    bad = lib.lane_violations(lane, paths, cfg)
    return _result("lane ownership", "FAIL" if bad else "PASS",
                   "; ".join("%s (%s)" % b for b in bad[:5]) if bad else "%d paths, lane %s" % (len(paths), lane))


def check_frozen(root, strict):
    lib = _util.hooklib(root, "_lanes")
    rules = lib.load_frozen(str(root))
    active = [r for r in rules if _util.tag_exists(root, r["after_tag"])]
    bad = []
    for rule in active:
        out = _util.git(root, "diff", "--numstat", "-z", "--no-renames", rule["after_tag"], "HEAD").stdout
        bad += lib.frozen_violations([rule], lambda t: True, lib.parse_numstat(out))
    if bad:
        return _result("frozen paths", "FAIL", "; ".join("%s (%s)" % b for b in bad[:5]))
    return _result("frozen paths", "PASS", "%d of %d rules active" % (len(active), len(rules)))


def check_provenance(root, strict):
    count, bad = 0, []
    for ledger in sorted((Path(root) / "jobs" / "ledger").glob("*.jsonl")):
        for no, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            count += 1
            try:
                rec = json.loads(line)
            except ValueError:
                bad.append("%s:%d invalid JSON" % (ledger.name, no))
                continue
            outs = rec.get("outputs") or []
            if not outs:
                bad.append("%s:%d no outputs" % (ledger.name, no))
            for out in outs:
                path = Path(root) / str(out.get("path", ""))
                if not path.is_file():
                    bad.append("%s:%d missing %s" % (ledger.name, no, out.get("path")))
                elif hashlib.sha256(path.read_bytes()).hexdigest() != out.get("sha256"):
                    bad.append("%s:%d hash mismatch %s" % (ledger.name, no, out.get("path")))
    if bad:
        return _result("provenance", "FAIL", "; ".join(bad[:5]))
    return _result("provenance", "PASS", "%d records" % count)


def check_number_linter(root, strict):
    cfg = Path(root) / "ops" / "config.yaml"
    enabled = bool(cfg.exists() and (yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("number_linter"))
    if not enabled:
        return _result("number linter", "INACTIVE", "ops/config.yaml number_linter is false")
    return _result("number linter", "FAIL", "enabled in ops/config.yaml but not implemented yet")


CHECKS = [check_tests, check_attribution, check_identity, check_signatures,
          check_lanes, check_frozen, check_provenance, check_number_linter]


def run_checks(root, strict=False):
    return [check(root, strict) for check in CHECKS]


def summary(results):
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    head = "FAIL" if counts.get("FAIL") else "PASS"
    return "%s (%s)" % (head, ", ".join("%d %s" % (v, k.lower()) for k, v in sorted(counts.items())))


def _cmd(args):
    root = _util.repo_root()
    results = run_checks(root, args.strict)
    if args.json:
        print(json.dumps({"summary": summary(results), "checks": results}, indent=2))
    else:
        for i, r in enumerate(results, 1):
            print("%d. %-15s %-8s %s" % (i, r["name"], r["status"], r["detail"]))
        print("verify: " + summary(results))
    return 1 if any(r["status"] == "FAIL" for r in results) else 0


def register(subparsers):
    p = subparsers.add_parser("verify", help="run the repository checks")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--strict", action="store_true", help="verify signatures against ops/allowed_signers")
    p.set_defaults(func=_cmd)
