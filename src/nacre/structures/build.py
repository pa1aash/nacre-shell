"""Build every target in ``structures/preprint/build.yaml`` into ``structures/preprint/*.extxyz``.

Usage: ``python -m nacre.structures.build [--target NAME ...] [--out DIR]``.
A manifest (``structures/preprint/manifest.json``) records the sha256, atom count and
total charge of each output. ``reference_platform.json`` records the operating system and
processor architecture the committed files were built on: their bytes are reproducible on
that platform only, and elsewhere they agree to the tolerance of ``nacre.structures.compare``.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import yaml

from nacre.structures import acc, assemble, evidence, hero, ion, oligomer, params_source, slab, water
from nacre.structures.meta import OUT_DIR, write_structure

CONFIG = OUT_DIR / "build.yaml"
REFERENCE_PLATFORM = "reference_platform.json"

BUILDERS = {
    "slab": lambda spec, built: slab.build(spec.get("params"), spec.get("seed", 0)),
    "water_layer": lambda spec, built: water.build(built[spec["substrate"]], spec.get("params"),
                                                   spec.get("seed", 0)),
    "hydrated_ion": lambda spec, built: _hydrated_ion(spec),
    "acc_cluster": lambda spec, built: _acc(spec),
    "oligomer": lambda spec, built: oligomer.build(spec.get("params"), spec.get("seed", 0)),
    "hero": lambda spec, built: _hero(spec, built),
    "assembly": lambda spec, built: assemble.build(
        [(part["name"], built[part["target"]], part.get("place")) for part in spec["parts"]],
        spec.get("params"), spec.get("seed", 0)),
}


def _evidence_params(spec):
    """Parameters and source ids of a target, with its ``evidence`` geometry merged in."""
    params = dict(spec.get("params") or {})
    if spec.get("evidence") != "ca_hydration":
        return params, None
    g = evidence.hydration_geometry()
    typed = {"cn", "r_ca_o"} & set(params)
    if typed:
        raise ValueError(f"{sorted(typed)} come from the evidence rows and may not be typed in build.yaml")
    params.update(cn=g["cn"], r_ca_o=g["r_ca_o"])
    src = {"evidence": evidence.RECORD.name, "evidence_commit": g["evidence_commit"],
           "row_ids": g["row_ids"], "context_row_ids": g["context_row_ids"], "rule": g["rule"]}
    return params, src


def _acc_source():
    g = params_source.acc_geometry()
    return {"params": params_source.RECORD.name, "params_commit": g["params_commit"], "keys": g["keys"],
            "sources": g["sources"], "rule": g["rule"]}


def _acc(spec):
    if spec.get("evidence") != "acc":
        raise ValueError("acc_cluster needs evidence: acc (packing and C-O from the params record)")
    return acc.build(spec.get("params"), spec.get("seed", 0), params_source.acc_geometry(),
                     source_ids={"acc": _acc_source()})


def _hydrated_ion(spec):
    params, src = _evidence_params(spec)
    return ion.build(params, seed=spec.get("seed", 0), source_ids=src)


def _chain_targets(spec):
    """Chain templates of a hero target: ``chain`` names one target or maps names to targets."""
    ch = spec["chain"]
    return {"default": ch} if isinstance(ch, str) else dict(ch)


def _src(atoms):
    v = atoms.info["source_ids"]
    return json.loads(v) if isinstance(v, str) else v


def _hero(spec, built):
    slab_atoms = built[spec["slab"]]
    chains = {name: built[t] for name, t in _chain_targets(spec).items()}
    _, ev_src = _evidence_params({"evidence": spec.get("evidence")})
    if ev_src is None:
        raise ValueError("the hero scene needs evidence: ca_hydration for its Ca2+ shells")
    src = {"slab": _src(slab_atoms), "ca_hydration": ev_src}
    for name, atoms in chains.items():
        src["chain" if name == "default" else f"chain_{name}"] = _src(atoms)
    if (spec.get("params") or {}).get("nucleus", {}) is not None:
        src["acc"] = _acc_source()
    return hero.build(slab_atoms, chains, evidence.hydration_geometry(), params_source.acc_geometry(),
                      spec.get("params"), spec.get("seed", 0), source_ids=src,
                      drawing_choices=spec.get("drawing_choices"))


def current_platform():
    """Operating system and processor architecture (no host name, user or path)."""
    return {"system": platform.system(), "machine": platform.machine()}


def load_config(path=CONFIG):
    cfg = yaml.safe_load(Path(path).read_text())
    for name, spec in cfg["targets"].items():
        if spec["builder"] not in BUILDERS:
            raise ValueError(f"{name}: unknown builder {spec['builder']}")
    return cfg


def _deps(spec):
    if spec["builder"] == "water_layer":
        return [spec["substrate"]]
    if spec["builder"] == "hero":
        return [spec["slab"], *_chain_targets(spec).values()]
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
    (Path(args.out) / REFERENCE_PLATFORM).write_text(
        json.dumps(current_platform(), indent=1, sort_keys=True) + "\n")
    for n, m in manifest.items():
        print(f"{n}: {m['n_atoms']} atoms, charge {m['total_charge']:+d}, {m['sha256'][:12]}")


if __name__ == "__main__":
    main()
