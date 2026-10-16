"""Assemble built parts into one scene structure (for example slab + water + hydrated ion).

Each part after the first is placed above the parts already present: its centroid goes
to fractional in-plane position ``xy`` of the base cell, and it is lifted until its
lowest atom is ``gap`` above the highest atom underneath it (within ``footprint`` of its
in-plane extent). The result is rejected if any intermolecular distance is below
``min_any``.
"""
from __future__ import annotations

import json

import numpy as np

from nacre.structures.meta import formal_charge, min_distance, stamp

DEFAULTS = {"gap": 2.4, "footprint": 2.0, "min_any": 1.5}


def place_above(base, part, xy, gap, footprint):
    cell = np.asarray(base.cell)
    pos = part.get_positions() - part.get_positions().mean(axis=0)
    target = xy[0] * cell[0] + xy[1] * cell[1]
    pos[:, :2] += target[:2]
    reach = np.linalg.norm(pos[:, :2] - target[:2], axis=1).max() + footprint
    bpos = base.get_positions()
    below = np.linalg.norm(bpos[:, :2] - target[:2], axis=1) < reach
    z_top = bpos[below, 2].max() if below.any() else bpos[:, 2].max()
    pos[:, 2] += z_top + gap - pos[:, 2].min()
    return pos


def build(parts, params=None, seed=0):
    """parts: list of (name, atoms, placement dict or None for the base)."""
    from ase import Atoms

    p = {**DEFAULTS, **(params or {})}
    name0, base, _ = parts[0]
    comp0 = base.arrays.get("component", np.array([name0] * len(base)))
    out = Atoms(symbols=base.get_chemical_symbols(), positions=base.get_positions(),
                cell=base.cell, pbc=base.pbc)
    comps = [f"{name0}:{c}" for c in comp0]
    sources = {}
    charge = int(base.info.get("total_charge", 0))
    _merge_sources(sources, name0, base)
    for name, atoms, place in parts[1:]:
        place = place or {}
        pos = place_above(out, atoms, place.get("xy", [0.5, 0.5]), place.get("gap", p["gap"]),
                          p["footprint"])
        out += Atoms(symbols=atoms.get_chemical_symbols(), positions=pos)
        comp = atoms.arrays.get("component", np.array([name] * len(atoms)))
        comps += [f"{name}:{c}" for c in comp]
        charge += int(atoms.info.get("total_charge", 0))
        _merge_sources(sources, name, atoms)
    out.new_array("component", np.array(comps))
    same_part = np.array([c.split(":")[0] for c in comps])
    mask = same_part[:, None] == same_part[None, :]
    d = min_distance(out, exclude_pairs=mask)
    if d < p["min_any"]:
        raise RuntimeError(f"assembly clash: {d:.3f} A between parts")
    stamp(
        out,
        builder="nacre.structures.assemble.build",
        params={**p, "parts": [[n, (pl or {})] for n, _, pl in parts]},
        seed=seed,
        source_ids=sources,
        total_charge=charge,
        notes="composite of separately built illustrative parts",
    )
    out.info["formal_charge_check"] = formal_charge(
        [s for s, c in zip(out.get_chemical_symbols(), comps) if not c.startswith("oligomer")])
    return out


def _merge_sources(acc, name, atoms):
    src = atoms.info.get("source_ids")
    if isinstance(src, str):
        src = json.loads(src)
    if src:
        acc[name] = src
