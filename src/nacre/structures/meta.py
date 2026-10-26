"""Metadata, numerical hygiene and extxyz output shared by the structure builders."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np

ILLUSTRATIVE_LABEL = "illustrative construction for a schematic figure; not a simulated structure"

# Numerical-hygiene threshold: no two atoms in any built structure, including
# periodic images in periodic directions, may be closer than this (angstrom).
# It is a guard against overlapping atoms in a drawing, not a physical criterion.
CLASH_THRESHOLD = 0.70

# Formal oxidation states used for the total-charge bookkeeping of ionic builders.
FORMAL_OXIDATION = {"H": 1, "C": 4, "N": -3, "O": -2, "Al": 3, "Ca": 2}

LIBRARIES = ("ase", "numpy", "rdkit", "pymatgen", "mp-api")

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "structures" / "preprint"
SOURCE_DIR = OUT_DIR / "sources"


def library_versions(names=LIBRARIES):
    out = {}
    for name in names:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = "absent"
    return out


def formal_charge(symbols) -> int:
    return int(sum(FORMAL_OXIDATION[s] for s in symbols))


# Neighbour-list search for the smallest distance: first cutoff and the cap (angstrom). The
# cutoff doubles until a pair is found; past the cap the dense routine takes over.
_NL_START = 4.0
_NL_CAP = 64.0


def _min_distance_neighbours(atoms):
    """Smallest i != j distance from a neighbour list (memory linear in the pair count), or None."""
    from ase.neighborlist import neighbor_list

    cutoff = _NL_START
    while cutoff <= _NL_CAP:
        i, j, d = neighbor_list("ijd", atoms, cutoff)
        keep = i != j
        if keep.any():
            return float(d[keep].min())
        cutoff *= 2
    return None


def min_distance(atoms, exclude_pairs=None) -> float:
    """Smallest interatomic distance, with minimum image in periodic directions.

    ``exclude_pairs`` is an optional boolean (n, n) mask of pairs to ignore. Without it the
    distance comes from a neighbour list, so large cells need no (n, n, 3) arrays; with it the
    dense routine is used (its only caller builds structures of a few hundred atoms).
    """
    pos = atoms.get_positions()
    n = len(pos)
    if n < 2:
        return float("inf")
    if exclude_pairs is None:
        r = _min_distance_neighbours(atoms)
        if r is not None:
            return r
    d = pos[:, None, :] - pos[None, :, :]
    if any(atoms.pbc):
        cell = np.asarray(atoms.cell)
        inv = np.linalg.inv(cell)
        frac = d @ inv
        for k in range(3):
            if atoms.pbc[k]:
                frac[..., k] -= np.round(frac[..., k])
        d = frac @ cell
    r = np.linalg.norm(d, axis=-1)
    r[np.diag_indices(n)] = np.inf
    if exclude_pairs is not None:
        r[exclude_pairs] = np.inf
    return float(r.min())


def stamp(atoms, *, builder, params, seed, source_ids=None, total_charge, notes=""):
    """Attach the standard metadata block to ``atoms.info`` (JSON strings for nested values)."""
    atoms.info.clear()
    atoms.info["builder"] = builder
    atoms.info["params"] = json.dumps(params, sort_keys=True)
    atoms.info["seed"] = -1 if seed is None else int(seed)
    atoms.info["library_versions"] = json.dumps(library_versions(), sort_keys=True)
    atoms.info["source_ids"] = json.dumps(source_ids or {}, sort_keys=True)
    atoms.info["total_charge"] = int(total_charge)
    atoms.info["illustrative"] = True
    atoms.info["label"] = ILLUSTRATIVE_LABEL
    if notes:
        atoms.info["notes"] = notes
    return atoms


def write_structure(atoms, path) -> str:
    """Write extxyz and return its sha256. Positions are rounded to 1e-6 A for stable bytes."""
    import ase.io

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    atoms = atoms.copy()
    atoms.set_positions(np.round(atoms.get_positions(), 6) + 0.0)
    ase.io.write(path, atoms, format="extxyz")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_structure(path):
    import ase.io

    atoms = ase.io.read(path, format="extxyz")
    for key in ("params", "library_versions", "source_ids"):
        if isinstance(atoms.info.get(key), str):
            atoms.info[key] = json.loads(atoms.info[key])
    return atoms
