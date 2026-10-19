"""Explicit lock of the pod environment (P0-W5.4): pod_env_linux64.yaml solved for linux-64.

    uv run python -m nacre.anchor.pod_env lock      # network: conda-forge repodata (dry-run solve only)

The solve runs the local micromamba with --dry-run --platform linux-64, so nothing is installed. The
virtual packages of a Linux host (glibc, kernel) are not visible from macOS and are set by
CONDA_OVERRIDE_GLIBC and CONDA_OVERRIDE_LINUX below; the lock records the highest glibc any package
requires, and the pod's install step refuses a host with an older glibc. The lock is in the explicit
format (one URL#md5 per line) that `micromamba create -f` installs without solving; the sha256 of
every package is kept in the JSON beside it.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE / "pod_env_linux64.yaml"
LOCK = HERE / "pod_env_linux64.lock"
LOCK_JSON = HERE / "pod_env_linux64.lock.json"
MICROMAMBA = Path.home() / ".nacre-envs" / "bin" / "micromamba"
OVERRIDES = {"CONDA_OVERRIDE_GLIBC": "2.28", "CONDA_OVERRIDE_LINUX": "5.15"}


def solve(env_file=ENV_FILE, micromamba=MICROMAMBA):
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, CONDA_SUBDIR="linux-64", **OVERRIDES,
                   MAMBA_ROOT_PREFIX=str(Path.home() / ".nacre-envs" / "mamba-root"))
        p = subprocess.run([str(micromamba), "create", "--dry-run", "--json", "-y", "-p", str(Path(tmp) / "env"),
                            "--platform", "linux-64", "-f", str(env_file)], capture_output=True, text=True, env=env)
        version = subprocess.run([str(micromamba), "--version"], capture_output=True, text=True).stdout.strip()
    doc = json.loads(p.stdout)
    if not doc.get("success"):
        raise SystemExit("linux-64 solve failed: %s" % doc.get("solver_problems"))
    return doc["actions"]["LINK"], version


def max_glibc(pkgs):
    best = (0, 0)
    for p in pkgs:
        for d in p.get("depends") or []:
            m = re.match(r"__glibc >=(\d+)\.(\d+)", d)
            if m:
                best = max(best, (int(m.group(1)), int(m.group(2))))
    return "%d.%d" % best


def write_lock(pkgs, version):
    glibc = max_glibc(pkgs)  # the lock keeps the solver's link order (explicit files install in order)
    lines = ["# Explicit lock of src/nacre/anchor/pod_env_linux64.yaml for linux-64 (python -m nacre.anchor.pod_env lock).",
             "# Solved with micromamba %s, %s; the host needs glibc >= %s."
             % (version, ", ".join("%s=%s" % kv for kv in OVERRIDES.items()), glibc),
             "@EXPLICIT"] + ["%s#%s" % (p["url"], p["md5"]) for p in pkgs]
    LOCK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    LOCK_JSON.write_text(json.dumps({
        "env_file": "src/nacre/anchor/pod_env_linux64.yaml", "platform": "linux-64", "micromamba": version,
        "overrides": OVERRIDES, "glibc_required": glibc, "n": len(pkgs),
        "packages": [{k: p[k] for k in ("name", "version", "build_string", "url", "md5", "sha256", "size")}
                     for p in sorted(pkgs, key=lambda p: p["name"])]},
        indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return glibc


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.anchor.pod_env")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lock", help="solve the pod environment for linux-64 and write the explicit lock")
    ap.parse_args(argv)
    pkgs, version = solve()
    glibc = write_lock(pkgs, version)
    print("%d packages; glibc >= %s; %s" % (len(pkgs), glibc, LOCK.relative_to(HERE.parents[2]).as_posix()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
