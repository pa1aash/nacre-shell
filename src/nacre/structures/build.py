"""Build every target in ``structures/preprint/build.yaml`` into ``structures/preprint/*.extxyz``.

Usage: ``python -m nacre.structures.build [--target NAME ...] [--out DIR]``.
A manifest (``structures/preprint/manifest.json``) records the sha256, atom count and
total charge of each output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from nacre.structures import acc, assemble, ion, oligomer, slab, water
from nacre.structures.meta import OUT_DIR, write_structure

CONFIG = OUT_DIR / "build.yaml"

BUILDERS = {
    "slab": lambda spec, built: slab.build(spec.get("params"), spec.get("seed", 0)),
    "water_layer": lambda spec, built: water.build(built[spec["substrate"]], spec.get("params"),
                                                   spec.get("seed", 0)),
    "hydrated_ion": lambda spec, built: ion.build(spec.get("params"), spec.get("seed", 0)),
    "acc_cluster": lambda spec, built: acc.build(spec.get("params"), spec.get("seed", 0)),
    "oligomer": lambda spec, built: oligomer.build(spec.get("params"), spec.get("seed", 0)),
    "assembly": lambda spec, built: assemble.build(
        [(part["name"], built[part["target"]], part.get("place")) for part in spec["parts"]],
        spec.get("params"), spec.get("seed", 0)),
}


def load_config(path=CONFIG):
    cfg = yaml.safe_load(Path(path).read_text())
    for name, spec in cfg["targets"].items():
        if spec["builder"] not in BUILDERS:
            raise ValueError(f"{name}: unknown builder {spec['builder']}")
    return cfg


def _deps(spec):
    if spec["builder"] == "water_layer":
        return [spec["substrate"]]
    if spec["builder"] == "assembly":
        return [part["target"] for part in spec["parts"]]
    return []


def build_all(names=None, out_dir=OUT_DIR, config=CONFIG):
    cfg = load_config(config)
    targets = cfg["targets"]
    wanted = list(names or targets)
    order, seen = [], set()

    def visit(n):
        if n in seen:
            return
        for d in _deps(targets[n]):
            visit(d)
        seen.add(n)
        order.append(n)

    for n in wanted:
        visit(n)
    built, manifest = {}, {}
    for n in order:
        atoms = BUILDERS[targets[n]["builder"]](targets[n], built)
        built[n] = atoms
        if targets[n].get("write", True):
            path = Path(out_dir) / f"{n}.extxyz"
            sha = write_structure(atoms, path)
            manifest[n] = {"file": path.name, "sha256": sha, "n_atoms": len(atoms),
                           "total_charge": int(atoms.info["total_charge"]),
                           "builder": atoms.info["builder"]}
    return built, manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", action="append")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args(argv)
    _, manifest = build_all(args.target, args.out)
    mpath = Path(args.out) / "manifest.json"
    old = json.loads(mpath.read_text()) if mpath.exists() else {}
    old.update(manifest)
    mpath.write_text(json.dumps(old, indent=1, sort_keys=True) + "\n")
    for n, m in manifest.items():
        print(f"{n}: {m['n_atoms']} atoms, charge {m['total_charge']:+d}, {m['sha256'][:12]}")


if __name__ == "__main__":
    main()
