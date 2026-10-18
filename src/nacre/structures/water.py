"""Water geometry and a water layer packed above a substrate by random sequential insertion.

Insertion rule (minimum-distance rule): a trial molecule at a uniformly random position
and orientation is accepted only if its O is at least ``min_oo`` from every O of
the substrate and earlier waters, at least ``min_heavy`` from every other non-H atom,
and every one of its atoms is at least ``min_any`` from every atom outside the molecule.
Distances use the minimum image in the periodic directions of the substrate.

Optional region: ``xy_box`` ([[fx0, fx1], [fy0, fy1]], fractions of the in-plane cell
vectors) limits the molecules to part of the cell, which is how a scene keeps water
behind a cut-away plane; ``z_base_component`` measures the start height ``gap`` above the
atoms of that component only (for example the slab), not above everything already placed.
"""
from __future__ import annotations

import numpy as np

from nacre.structures.meta import formal_charge, stamp

# Rigid water geometry (gas-phase experimental values, also used by common rigid models).
WATER = {"r_oh": 0.9572, "angle_hoh_deg": 104.52}

DEFAULTS = {
    "gap": 1.6,
    "thickness": 8.0,
    "density_g_cm3": 1.0,
    "n_molecules": None,
    "min_oo": 2.5,
    "min_heavy": 2.4,
    "min_any": 1.5,
    "max_attempts": 200000,
    "xy_box": None,
    "z_base_component": None,
    **WATER,
}


def water_frame(r_oh=WATER["r_oh"], angle_hoh_deg=WATER["angle_hoh_deg"]):
    """O at origin, dipole (O -> H midpoint) along +z, molecule in the xz plane."""
    half = np.radians(angle_hoh_deg) / 2.0
    h1 = r_oh * np.array([np.sin(half), 0.0, np.cos(half)])
    h2 = r_oh * np.array([-np.sin(half), 0.0, np.cos(half)])
    return np.array([[0.0, 0.0, 0.0], h1, h2])


def random_rotation(rng):
    """Uniform random rotation matrix (from a random unit quaternion)."""
    q = rng.normal(size=4)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def _mic(d, cell, pbc):
    if not any(pbc):
        return d
    inv = np.linalg.inv(cell)
    f = d @ inv
    for k in range(3):
        if pbc[k]:
            f[..., k] -= np.round(f[..., k])
    return f @ cell


def build(substrate, params=None, seed=0):
    """Return substrate + water layer, with a per-atom ``component`` array."""
    from ase import Atoms
    from ase.data import atomic_masses, atomic_numbers

    p = {**DEFAULTS, **(params or {})}
    rng = np.random.default_rng(seed)
    cell = np.asarray(substrate.cell)
    pbc = tuple(bool(x) for x in substrate.pbc)
    sub_pos = substrate.get_positions()
    sub_sym = np.array(substrate.get_chemical_symbols())
    base = sub_pos
    if p["z_base_component"]:
        comp = np.asarray(substrate.arrays["component"])
        base = sub_pos[np.char.startswith(comp.astype(str), p["z_base_component"])]
    z0 = base[:, 2].max() + p["gap"]
    z1 = z0 + p["thickness"]
    (fx0, fx1), (fy0, fy1) = p["xy_box"] or ([0.0, 1.0], [0.0, 1.0])
    area = np.linalg.norm(np.cross(cell[0], cell[1])) * (fx1 - fx0) * (fy1 - fy0)
    if p["n_molecules"] is not None:
        target = int(p["n_molecules"])
    else:
        m_w = 2 * atomic_masses[atomic_numbers["H"]] + atomic_masses[atomic_numbers["O"]]
        n_per_a3 = p["density_g_cm3"] / m_w * 0.602214076  # mol/cm^3 -> molecules/A^3
        target = int(round(n_per_a3 * area * p["thickness"]))

    frame = water_frame(p["r_oh"], p["angle_hoh_deg"])
    pos = [sub_pos]
    sym = [sub_sym]
    all_pos = sub_pos.copy()
    all_sym = sub_sym.copy()
    placed = attempts = 0
    cutoff = max(p["min_any"], p["min_heavy"], p["min_oo"])
    while placed < target and attempts < p["max_attempts"]:
        attempts += 1
        fx, fy = rng.uniform(fx0, fx1), rng.uniform(fy0, fy1)
        o = fx * cell[0] + fy * cell[1]
        o[2] = rng.uniform(z0, z1)
        mol = o + frame @ random_rotation(rng).T
        # O-H must also lie inside the slab-normal window so H does not dip into the substrate.
        if mol[:, 2].min() < z0 - p["gap"] + p["min_any"]:
            continue
        # Only atoms within the largest cutoff in z can decide the trial (z is not periodic),
        # so the others are skipped before the minimum-image distances; the decision is the
        # same as over all atoms.
        if not pbc[2]:
            near = (all_pos[:, 2] > mol[:, 2].min() - cutoff) & (all_pos[:, 2] < mol[:, 2].max() + cutoff)
        else:
            near = slice(None)
        d = _mic(mol[:, None, :] - all_pos[near][None, :, :], cell, pbc)
        r = np.linalg.norm(d, axis=-1)
        if r.min(initial=np.inf) < p["min_any"]:
            continue
        near_sym = all_sym[near]
        heavy = near_sym != "H"
        if r[0, heavy].min(initial=np.inf) < p["min_heavy"]:
            continue
        is_o = near_sym == "O"
        if r[0, is_o].min(initial=np.inf) < p["min_oo"]:
            continue
        all_pos = np.vstack([all_pos, mol])
        all_sym = np.concatenate([all_sym, ["O", "H", "H"]])
        placed += 1

    n_sub = len(substrate)
    atoms = Atoms(symbols=list(all_sym), positions=all_pos, cell=cell, pbc=pbc)
    sub_comp = substrate.arrays.get("component", np.array(["substrate"] * n_sub))
    comp = np.array(list(sub_comp) + ["water"] * (len(atoms) - n_sub))
    atoms.new_array("component", comp)
    sub_info = dict(substrate.info)
    stamp(
        atoms,
        builder="nacre.structures.water.build",
        params={**p, "substrate_builder": sub_info.get("builder")},
        seed=seed,
        source_ids=_parse(sub_info.get("source_ids")),
        total_charge=formal_charge(atoms.get_chemical_symbols()),
        notes="water layer by random sequential insertion under a minimum-distance rule; "
        "not equilibrated",
    )
    atoms.info["n_water_target"] = target
    atoms.info["n_water_placed"] = placed
    atoms.info["insertion_attempts"] = attempts
    atoms.info["substrate_params"] = sub_info.get("params") if isinstance(sub_info.get("params"), str) else ""
    return atoms


def _parse(v):
    import json

    if isinstance(v, str):
        return json.loads(v)
    return v or {}
