"""Hydrated Ca2+: a Ca ion with a first shell of ``cn`` water molecules.

Shell O positions are the minimum-energy arrangement of ``cn`` points on a sphere of
radius ``r_ca_o`` under a 1/r repulsion (seeded start, fixed iteration count), which
gives the octahedron for six and the square antiprism for eight. Each water points its
dipole away from the ion and is rotated about the Ca-O axis by a seeded angle.

``cn`` and ``r_ca_o`` have no defaults: build.yaml takes them from lane p0-w1's evidence
rows (``evidence: ca_hydration``, see nacre.structures.evidence) and the row_ids are
written into the file's source ids.
"""
from __future__ import annotations

import numpy as np

from nacre.structures.meta import formal_charge, stamp
from nacre.structures.water import WATER, water_frame

DEFAULTS = {"sphere_iterations": 2000, **WATER}
REQUIRED = ("cn", "r_ca_o")


def sphere_points(n, rng, iterations=2000):
    x = rng.normal(size=(n, 3))
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    step = 0.05
    for _ in range(iterations):
        d = x[:, None, :] - x[None, :, :]
        r = np.linalg.norm(d, axis=-1)
        np.fill_diagonal(r, np.inf)
        f = (d / r[..., None] ** 3).sum(axis=1)
        f -= (f * x).sum(axis=1, keepdims=True) * x  # tangential part
        x += step * f
        x /= np.linalg.norm(x, axis=1, keepdims=True)
    return x


def _align(z_to):
    """Rotation taking +z onto unit vector z_to."""
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(z, z_to)
    c = float(np.dot(z, z_to))
    if np.linalg.norm(v) < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1.0 / (1.0 + c))


def build(params=None, seed=0, source_ids=None):
    from ase import Atoms

    p = {**DEFAULTS, **(params or {})}
    missing = [k for k in REQUIRED if k not in p]
    if missing:
        raise ValueError(f"hydrated_ion needs {missing} (from evidence rows, never typed defaults)")
    rng = np.random.default_rng(seed)
    dirs = sphere_points(int(p["cn"]), rng, int(p["sphere_iterations"]))
    frame = water_frame(p["r_oh"], p["angle_hoh_deg"])
    symbols = ["Ca"]
    positions = [np.zeros(3)]
    for u in dirs:
        spin = rng.uniform(0, 2 * np.pi)
        cs, sn = np.cos(spin), np.sin(spin)
        rz = np.array([[cs, -sn, 0], [sn, cs, 0], [0, 0, 1]])
        mol = (frame @ rz.T) @ _align(u).T + p["r_ca_o"] * u
        symbols += ["O", "H", "H"]
        positions += list(mol)
    atoms = Atoms(symbols=symbols, positions=np.array(positions), pbc=False)
    atoms.new_array("component", np.array(["ion"] + ["hydration"] * (len(atoms) - 1)))
    stamp(
        atoms,
        builder="nacre.structures.ion.build",
        params=p,
        seed=seed,
        source_ids=source_ids,
        total_charge=formal_charge(atoms.get_chemical_symbols()),
        notes="Ca2+ with a first hydration shell; coordination number and Ca-O distance "
        "are drawing parameters taken from the cited evidence rows, not results",
    )
    return atoms
