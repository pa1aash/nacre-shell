"""nacre gate: layer A checks, packets and signed gate tags.

Gate definition: ops/gates/<G>.yaml
  gate: G0
  criteria:
    - {type: files_exist, paths: [a, b]}
    - {type: tests_pass}                      # optional: args: ["tests/x"]
    - {type: hashes_match, entries: [{path: p, sha256: h}]}
    - {type: command_ok, command: ["cmd", "arg"]}
Sign-off record: ops/gates/<G>.md (A-check, C-audit and H-signoff lines).
"""
import hashlib
import re
import subprocess
from datetime import date
from pathlib import Path

import yaml

from nacre import _util

PENDING = re.compile(r"^\s*(PENDING)?\s*$", re.IGNORECASE)


def load_gate(root, gate):
    path = Path(root) / "ops" / "gates" / (gate + ".yaml")
    if not path.exists():
        raise SystemExit("no gate definition: %s" % path.relative_to(root))
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def evaluate(root, definition):
    """Layer A: return a list of (criterion description, ok, detail)."""
    results = []
    for crit in definition.get("criteria") or []:
        kind = crit.get("type")
        if kind == "files_exist":
            for rel in crit.get("paths") or []:
                ok = (Path(root) / rel).exists()
                results.append(("files_exist %s" % rel, ok, "" if ok else "missing"))
        elif kind == "tests_pass":
            p = subprocess.run(["uv", "run", "pytest", "-q", *crit.get("args", [])], cwd=root,
                               capture_output=True, text=True)
            tail = (p.stdout.strip().splitlines() or [""])[-1]
            results.append(("tests_pass", p.returncode == 0, tail))
        elif kind == "hashes_match":
            for entry in crit.get("entries") or []:
                f = Path(root) / entry["path"]
                ok = f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest() == entry["sha256"]
                results.append(("hashes_match %s" % entry["path"], ok, "" if ok else "hash differs or file missing"))
        elif kind == "command_ok":
            cmd = crit["command"]
            p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, shell=isinstance(cmd, str))
            results.append(("command_ok %s" % (cmd if isinstance(cmd, str) else " ".join(cmd)),
                            p.returncode == 0, "exit %d" % p.returncode))
        else:
            results.append(("unknown criterion type %r" % kind, False, ""))
    return results


def a_summary(results):
    ok = all(r[1] for r in results)
    return ok, "PASS" if ok else "FAIL: " + "; ".join("%s (%s)" % (r[0], r[2]) for r in results if not r[1])


def record_path(root, gate):
    return Path(root) / "ops" / "gates" / (gate + ".md")


def signoff_problems(root, gate):
    """What is still missing in ops/gates/<G>.md before a tag may be made."""
    path = record_path(root, gate)
    if not path.exists():
        return ["ops/gates/%s.md is missing" % gate]
    text = path.read_text(encoding="utf-8")
    problems = []
    if not re.search(r"^C-audit:\s*PASS\s+\d{4}-\d{2}-\d{2}", text, re.MULTILINE):
        problems.append("C-audit is not 'PASS <date>'")
    heads = re.findall(r"^H-signoff ([^:\n]+):(.*)$", text, re.MULTILINE)
    if not heads:
        problems.append("no H-signoff fields")
    for who, value in heads:
        if PENDING.match(value):
            problems.append("H-signoff %s is not filled" % who.strip())
    return problems


def write_a_check(root, gate, ok, summary):
    path = record_path(root, gate)
    line = "A-check: %s %s" % ("PASS" if ok else "FAIL", date.today().isoformat())
    if not ok:
        line += " (%s)" % summary.removeprefix("FAIL: ")
    text = path.read_text(encoding="utf-8") if path.exists() else "Gate: %s\n" % gate
    if re.search(r"^A-check:.*$", text, re.MULTILINE):
        text = re.sub(r"^A-check:.*$", lambda m: line, text, flags=re.MULTILINE)
    else:
        text += line + "\n"
    path.write_text(text, encoding="utf-8")


def write_packet(root, gate, results):
    ok, summary = a_summary(results)
    rec = record_path(root, gate)
    lines = ["# Gate %s packet" % gate, "", "## Layer A result", "", summary, "", "## Files and criteria", ""]
    lines += ["- %s: %s %s" % (d, "ok" if good else "FAIL", detail) for d, good, detail in results]
    lines += ["", "## Open questions", ""]
    problems = signoff_problems(root, gate)
    lines += ["- " + p for p in problems] if problems else ["- none"]
    out = Path(root) / "ops" / "packets" / (gate + ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out.relative_to(root), rec


def make_tag(root, gate, definition):
    results = evaluate(root, definition)
    ok, summary = a_summary(results)
    missing = []
    if not ok:
        missing.append("layer A: " + summary)
    missing += signoff_problems(root, gate)
    if missing:
        return False, missing
    tag = gate.lower()
    if _util.tag_exists(root, tag):
        return False, ["tag %s already exists" % tag]
    p = _util.git(root, "tag", "-a", tag, "-m", "gate %s passed" % gate)
    if p.returncode != 0:
        return False, ["git tag failed: " + p.stderr.strip()]
    body = _util.git(root, "cat-file", "tag", tag).stdout
    if "-----BEGIN SSH SIGNATURE-----" not in body and "-----BEGIN PGP SIGNATURE-----" not in body:
        _util.git(root, "tag", "-d", tag)
        return False, ["tag was not signed (set tag.gpgSign and a signing key); tag removed"]
    return True, [tag]


def _cmd(args):
    root = _util.repo_root()
    gate = args.gate.upper()
    definition = load_gate(root, gate)
    if not (args.check or args.packet or args.tag):
        args.check = True
    rc = 0
    if args.check or args.packet:
        results = evaluate(root, definition)
        ok, summary = a_summary(results)
        if args.check:
            write_a_check(root, gate, ok, summary)
            print("%s layer A: %s" % (gate, summary))
            rc = 0 if ok else 1
        if args.packet:
            out, _ = write_packet(root, gate, results)
            print("wrote %s" % out)
    if args.tag:
        ok, info = make_tag(root, gate, definition)
        if not ok:
            print("REFUSED: cannot tag %s; missing:" % gate)
            for item in info:
                print("  - " + item)
            return 1
        print("created signed tag %s" % info[0])
    return rc


def register(subparsers):
    p = subparsers.add_parser("gate", help="evaluate a gate, write its packet, tag it")
    p.add_argument("gate", help="gate id such as G0")
    p.add_argument("--check", action="store_true", help="evaluate layer A and record it in ops/gates/<G>.md")
    p.add_argument("--packet", action="store_true", help="write ops/packets/<G>.md")
    p.add_argument("--tag", action="store_true", help="create the signed gate tag")
    p.set_defaults(func=_cmd)
