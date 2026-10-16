"""xtb smoke test: one GFN2-xTB optimisation of the smallest complex, single-threaded.

    uv run python -m nacre.anchor.xtb_smoke [--env ~/.nacre-envs/xtb]

Checks that the conformer tooling in the pinned environment (xtb_env.yaml) runs on this
machine. The energy is a smoke-test number only. It is not a binding energy and is not used
anywhere. Writes results/preprint/anchor/xtb_smoke/{summary.json, xtbopt.xyz}. The raw xtb log
is not kept because it records machine-specific paths.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from nacre.anchor import builders as b

REPO = Path(__file__).resolve().parents[3]
STRUCT = REPO / "results" / "preprint" / "anchor" / "structures"
OUT = REPO / "results" / "preprint" / "anchor" / "xtb_smoke"
DEFAULT_ENV = Path.home() / ".nacre-envs" / "xtb"


def smallest_complex():
    idx = json.loads((STRUCT / "index.json").read_text(encoding="utf-8"))["species"]
    cx = [s for s in idx if s["kind"] == "complex"]
    return min(cx, key=lambda s: (s["n_atoms"], s["name"]))


def _version(exe):
    p = subprocess.run([str(exe), "--version"], capture_output=True, text=True)
    m = re.search(r"(?:xtb version|Version)\s+([0-9][0-9.]*)", p.stdout + p.stderr)
    return m.group(1) if m else None


def run(env=DEFAULT_ENV, out=OUT):
    xtb, crest = Path(env) / "bin" / "xtb", Path(env) / "bin" / "crest"
    if not xtb.is_file():
        return {"status": "outstanding", "reason": "xtb not found in %s" % env}
    sp = smallest_complex()
    src = STRUCT / (sp["name"] + ".xyz")
    cmd = ["xtb", "in.xyz", "--opt", "normal", "--gfn", "2", "--chrg", str(sp["charge"]),
           "--uhf", str(sp["multiplicity"] - 1), "--alpb", "water", "-P", "1"]
    envv = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OMP_STACKSIZE="1G")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(src, Path(tmp) / "in.xyz")
        t0 = time.time()
        p = subprocess.run([str(xtb)] + cmd[1:], cwd=tmp, capture_output=True, text=True, env=envv)
        wall = time.time() - t0
        text = p.stdout + p.stderr
        converged = "GEOMETRY OPTIMIZATION CONVERGED" in text
        normal = "normal termination of xtb" in text
        energy = re.findall(r"TOTAL ENERGY\s+(-?[0-9.]+)\s+Eh", text)
        iters = re.search(r"CONVERGED AFTER\s+(\d+)\s+ITERATIONS", text)
        opt = Path(tmp) / "xtbopt.xyz"
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        geom = None
        if opt.is_file():
            lines = opt.read_text(encoding="utf-8").splitlines()
            n = int(lines[0])
            syms = [ln.split()[0] for ln in lines[2:2 + n]]
            xyz = np.array([[float(v) for v in ln.split()[1:4]] for ln in lines[2:2 + n]])
            st = b.Structure(sp["name"] + "_xtbopt", syms, xyz, sp["charge"], sp["multiplicity"])
            (out / "xtbopt.xyz").write_text(st.xyz(), encoding="utf-8")
            ca = syms.index("Ca")
            d = np.linalg.norm(xyz - xyz[ca], axis=1)
            geom = {"ca_o_distances_A": sorted(round(float(d[i]), 3) for i, s in enumerate(syms)
                                               if s == "O" and d[i] < 3.2),
                    "n_atoms": n}
    summary = {
        "question": "Does the pinned xtb/CREST environment run a GFN2-xTB optimisation of the "
                    "smallest Ca2+ complex on this machine? (tooling smoke test; the energy is "
                    "not a binding energy and is not used)",
        "status": "ok" if (p.returncode == 0 and converged and normal) else "failed",
        "species": sp["name"], "charge": sp["charge"], "multiplicity": sp["multiplicity"],
        "command": " ".join(cmd), "threads": 1, "returncode": p.returncode,
        "converged": converged, "normal_termination": normal,
        "iterations": int(iters.group(1)) if iters else None,
        "total_energy_Eh": float(energy[-1]) if energy else None,
        "wall_s": round(wall, 2), "xtb_version": _version(xtb),
        "crest_version": _version(crest) if crest.is_file() else None,
        "environment_spec": "src/nacre/anchor/xtb_env.yaml", "geometry": geom,
    }
    (Path(out) / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n",
                                            encoding="utf-8")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.anchor.xtb_smoke")
    ap.add_argument("--env", default=str(DEFAULT_ENV))
    args = ap.parse_args(argv)
    s = run(Path(args.env).expanduser())
    print(json.dumps(s, indent=1, sort_keys=True))
    return 0 if s.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
