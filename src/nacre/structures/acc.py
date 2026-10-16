"""A small amorphous calcium carbonate (ACC) cluster for the nucleus drawing.

Ca2+ ions and rigid trigonal-planar CO3^2- units are inserted alternately at random
positions (and random carbonate orientations) inside a sphere whose radius follows from
``n_fu`` formula units at ``density_g_cm3``. A trial is accepted only under the
minimum-distance rules below; after ``attempts_per_unit`` failures the radius grows by
``grow`` and the final radius is recorded. The cluster is charge-neutral by construction.
"""
from __future__ import annotations

import numpy as np

from nacre.structures.meta import formal_charge, stamp
from nacre.structures.water import random_rotation

DEFAULTS = {
    "n_fu": 8,
    "density_g_cm3": 1.9,
    "r_co": 1.28,
    "min_ca_ca": 3.4,
    "min_ca_c": 2.9,
    "min_ca_o": 2.3,
    "min_c_c": 3.0,
    "min_o_o": 2.5,
    "attempts_per_unit": 5000,
    "grow": 1.05,
}


def carbonate(r_co):
    ang = np.radians([90.0, 210.0, 330.0])
    o = np.stack([r_co * np.cos(ang), r_co * np.sin(ang), np.zeros(3)], axis=1)
    return ["C", "O", "O", "O"], np.vstack([np.zeros(3), o])


def _ok(new_sym, new_pos, sym, pos, p):
    if not len(pos):
        return True
    rules = {
        frozenset(["Ca"]): p["min_ca_ca"],
        frozenset(["Ca", "C"]): p["min_ca_c"],
        frozenset(["Ca", "O"]): p["min_ca_o"],
        frozenset(["C"]): p["min_c_c"],
        frozenset(["O"]): p["min_o_o"],
        frozenset(["C", "O"]): p["min_o_o"],
    }
    r = np.linalg.norm(new_pos[:, None, :] - pos[None, :, :], axis=-1)
    for i, a in enumerate(new_sym):
        for j, b in enumerate(sym):
            if r[i, j] < rules[frozenset([a, b])]:
                return False
    return True


def build(params=None, seed=0):
    from ase import Atoms
    from ase.data import atomic_masses, atomic_numbers

    p = {**DEFAULTS, **(params or {})}
    rng = np.random.default_rng(seed)
    m = sum(atomic_masses[atomic_numbers[s]] for s in ("Ca", "C", "O", "O", "O"))
    vol = int(p["n_fu"]) * m / (p["density_g_cm3"] * 0.602214076)  # A^3
    radius = (3 * vol / (4 * np.pi)) ** (1 / 3)
    radius0 = radius
    c_sym, c_pos = carbonate(p["r_co"])
    sym, pos = [], np.zeros((0, 3))
    units = ["Ca", "CO3"] * int(p["n_fu"])
    for unit in units:
        fails = 0
        while True:
            v = rng.normal(size=3)
            centre = v / np.linalg.norm(v) * radius * rng.uniform(0, 1) ** (1 / 3)
            if unit == "Ca":
                ns, npos = ["Ca"], centre[None, :]
            else:
                ns, npos = c_sym, centre + c_pos @ random_rotation(rng).T
            if _ok(ns, npos, sym, pos, p):
                sym += ns
                pos = np.vstack([pos, npos])
                break
            fails += 1
            if fails >= p["attempts_per_unit"]:
                radius *= p["grow"]
                fails = 0
    pos -= pos.mean(axis=0)
    atoms = Atoms(symbols=sym, positions=pos, pbc=False)
    stamp(
        atoms,
        builder="nacre.structures.acc.build",
        params=p,
        seed=seed,
        total_charge=formal_charge(sym),
        notes="anhydrous random close insertion of Ca2+ and CO3^2- in a sphere; "
        "not a simulated ACC structure",
    )
    atoms.info["radius_initial"] = float(radius0)
    atoms.info["radius_final"] = float(radius)
    return atoms
