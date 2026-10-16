"""Fully hydroxylated alpha-Al2O3(0001) slab from the fetched bulk corundum structure.

Construction (illustrative):

1. The fetched rhombohedral cell is converted to the conventional hexagonal cell,
   whose c axis is [0001]. Along c the stacking is a flat close-packed O layer
   followed by two Al sublayers, repeated six times per cell.
2. The hexagonal cell is repeated along c and cut so that both faces are O layers:
   the slab holds ``n_o_layers`` O layers and the ``n_o_layers - 1`` Al pairs between them.
   Per 1x1 surface cell this is Al_{2(n-1)} O_{3n}, carrying a formal charge of -6.
3. Every terminal O (three per face per 1x1 cell) receives one H, which removes the
   charge: the fully hydroxylated termination with the surface Al layer removed
   (the gibbsite-like termination). The O-H bond is set along the surface normal,
   tilted by ``oh_tilt_deg`` in a seeded random azimuth.
4. The 1x1 slab is repeated ``nx`` x ``ny`` laterally and given ``vacuum`` above and
   below; the cell is periodic in-plane only. With ``orthogonal`` the lateral cell is the
   rectangular supercell spanned by ``nx`` a1 and ``ny`` (a1 + 2 a2), that is nx x 2ny
   hexagonal cells, so a rectangular window of a scene lies inside one cell.
"""
from __future__ import annotations

import numpy as np

from nacre.structures import mp_source
from nacre.structures.meta import formal_charge, stamp

DEFAULTS = {
    "nx": 4,
    "ny": 4,
    "n_o_layers": 7,
    "vacuum": 10.0,
    "oh_bond": 0.97,
    "oh_tilt_deg": 15.0,
    "layer_tol": 0.3,
    "orthogonal": False,
}

# Coordinates closer than this (angstrom) count as equal when ordering atoms.
ORDER_TOL = 0.05


def bulk_hexagonal():
    """Conventional hexagonal cell of the fetched corundum record, as ase.Atoms, plus the record."""
    from pymatgen.core import Structure
    from pymatgen.io.ase import AseAtomsAdaptor
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    rec = mp_source.load()
    prim = Structure.from_dict(rec["structure"])
    conv = SpacegroupAnalyzer(prim, symprec=1e-3).get_conventional_standard_structure()
    atoms = AseAtomsAdaptor.get_atoms(conv)
    atoms.info.clear()
    # Rigid rotation into the standard orientation (a1 along x, c along z); fractional coordinates kept.
    atoms.set_cell(atoms.cell.standard_form()[0], scale_atoms=True)
    return atoms, rec


def _layers(z, tol):
    """Group sorted z values into layers; returns list of index arrays (ascending z)."""
    order = np.argsort(z)
    groups, cur = [], [order[0]]
    for i in order[1:]:
        if z[i] - z[cur[-1]] > tol:
            groups.append(np.array(cur))
            cur = [i]
        else:
            cur.append(i)
    groups.append(np.array(cur))
    return groups


def build(params=None, seed=0):
    from ase import Atoms

    p = {**DEFAULTS, **(params or {})}
    n_o = int(p["n_o_layers"])
    if n_o < 2:
        raise ValueError("n_o_layers must be at least 2")
    bulk, rec = bulk_hexagonal()
    cell = np.asarray(bulk.cell)
    c = cell[2, 2]
    # Enough repeats along c to contain n_o O layers (six per hexagonal cell) plus margin.
    reps = int(np.ceil((n_o + 1) / 6)) + 1
    col = bulk.repeat((1, 1, reps))
    sym = np.array(col.get_chemical_symbols())
    pos = col.get_positions()

    o_idx = np.where(sym == "O")[0]
    o_layers = [o_idx[g] for g in _layers(pos[o_idx, 2], p["layer_tol"])]
    if len(o_layers) < n_o + 1:
        raise RuntimeError("not enough O layers in the repeated cell")
    for lay in o_layers:
        if len(lay) != 3:
            raise RuntimeError(f"expected 3 O per layer per 1x1 cell, found {len(lay)}")
    # Skip the first layer so the cut never sits on a cell boundary artefact.
    chosen = o_layers[1 : 1 + n_o]
    z_lo = pos[chosen[0], 2].mean()
    z_hi = pos[chosen[-1], 2].mean()
    keep_o = np.concatenate(chosen)
    al_idx = np.where(sym == "Al")[0]
    keep_al = al_idx[(pos[al_idx, 2] > z_lo + p["layer_tol"]) & (pos[al_idx, 2] < z_hi - p["layer_tol"])]
    if len(keep_al) != 2 * (n_o - 1):
        raise RuntimeError(f"expected {2 * (n_o - 1)} Al, found {len(keep_al)}")

    rng = np.random.default_rng(seed)
    keep = np.concatenate([keep_al, keep_o])
    symbols = list(sym[keep])
    positions = list(pos[keep])
    for lay, sign in ((chosen[0], -1.0), (chosen[-1], 1.0)):
        for i in lay:
            symbols.append("H")
            positions.append(pos[i] + p["oh_bond"] * np.array([0.0, 0.0, sign]))

    slab1 = Atoms(symbols=symbols, positions=np.array(positions), cell=cell.copy(), pbc=(True, True, False))
    if p["orthogonal"]:
        # Rectangular in-plane cell (a1, a1 + 2 a2), so a rectangular drawing window fits inside it.
        from ase.build import make_supercell

        nx, ny = int(p["nx"]), int(p["ny"])
        slab = make_supercell(slab1, [[nx, 0, 0], [ny, 2 * ny, 0], [0, 0, 1]], wrap=True)
        slab.pbc = (True, True, False)
    else:
        slab = slab1.repeat((int(p["nx"]), int(p["ny"]), 1))
    # Tilt every O-H in a seeded azimuth after the lateral repeat, so the pattern is not a strict tile.
    _tilt_oh(slab, rng, p)
    zmin = slab.positions[:, 2].min()
    slab.positions[:, 2] -= zmin - p["vacuum"]
    height = slab.positions[:, 2].max() + p["vacuum"]
    new_cell = np.asarray(slab.cell).copy()
    new_cell[2] = [0.0, 0.0, height]
    slab.set_cell(new_cell)
    slab = slab[stable_order(slab.numbers, slab.positions)]

    charge = formal_charge(slab.get_chemical_symbols())
    stamp(
        slab,
        builder="nacre.structures.slab.build",
        params=p,
        seed=seed,
        source_ids={
            "bulk": rec["material_id"],
            "database": "Materials Project",
            "database_version": rec["database_version"],
            "structure_sha256": rec["structure_sha256"],
        },
        total_charge=charge,
        notes="alpha-Al2O3(0001), both faces fully hydroxylated (surface Al layer removed, "
        "three OH per 1x1 cell per face); in-plane periodic; bulk interlayer spacings unrelaxed",
    )
    slab.info["c_hex"] = round(float(c), 6)
    return slab


def _cluster_rank(values, tol):
    """Rank of each value's cluster, clusters being runs of sorted values with gaps <= tol.

    Values that differ by less than ``tol`` share a rank, so last-bit differences between
    platforms cannot reorder them.
    """
    order = np.argsort(values, kind="stable")
    gaps = np.diff(values[order]) > tol
    rank = np.empty(len(values), dtype=int)
    rank[order] = np.concatenate([[0], np.cumsum(gaps)])
    return rank


def stable_order(numbers, positions, tol=ORDER_TOL):
    """Atom order by element, then z, y and x clusters, then input order.

    Sorting on raw coordinates puts atoms of one layer (equal z up to rounding) in an
    order that depends on the last bits of the floating-point results, which differ
    between platforms. Clustering each coordinate at ``tol`` removes that dependence.
    """
    pos = np.asarray(positions)
    keys = (np.arange(len(pos)), _cluster_rank(pos[:, 0], tol), _cluster_rank(pos[:, 1], tol),
            _cluster_rank(pos[:, 2], tol), np.asarray(numbers))
    return np.lexsort(keys)


def _tilt_oh(slab, rng, p):
    sym = np.array(slab.get_chemical_symbols())
    pos = slab.get_positions()
    tilt = np.radians(p["oh_tilt_deg"])
    o_idx = np.where(sym == "O")[0]
    for h in np.where(sym == "H")[0]:
        d = pos[o_idx] - pos[h]
        o = o_idx[np.argmin(np.linalg.norm(d, axis=1))]
        sign = 1.0 if pos[h, 2] > pos[o, 2] else -1.0
        phi = rng.uniform(0.0, 2.0 * np.pi)
        u = np.array([np.sin(tilt) * np.cos(phi), np.sin(tilt) * np.sin(phi), sign * np.cos(tilt)])
        pos[h] = pos[o] + p["oh_bond"] * u
    slab.set_positions(pos)


def surface_hydroxyl_density(slab) -> float:
    """OH groups per nm^2 on one face."""
    area = np.linalg.norm(np.cross(slab.cell[0], slab.cell[1])) / 100.0
    n_h = sum(1 for s in slab.get_chemical_symbols() if s == "H")
    return n_h / 2.0 / area
