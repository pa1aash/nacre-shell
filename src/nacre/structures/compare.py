"""Compare a freshly built structure with the committed file, to a stated tolerance.

Byte equality of the extxyz files holds only on one platform: the floating-point
results of the builders (symmetry analysis, trigonometry, force-field relaxation)
differ in the last bits between operating systems and maths libraries, and after
rounding to 1e-6 A that shows up at the 1e-4 to 1e-3 A level. For illustrative
drawings that is physically negligible, so regeneration is checked as follows:

- species, atom count and atom order: exact;
- periodicity flags and per-atom string arrays (``component``): exact;
- provenance metadata (builder, parameters, seed, library versions, source ids,
  total charge, illustrative label and every other non-float value): exact;
- coordinates: every atom within ``POSITION_TOL`` (minimum image in periodic directions);
- cell vectors: within ``POSITION_TOL`` per component;
- geometry-derived float metadata (``GEOMETRY_DERIVED`` keys, such as a relaxed
  energy or a cluster radius): within ``DERIVED_RTOL`` relative.

``compare`` returns a list of human-readable differences; an empty list means the
two structures agree. The byte-hash check is kept as a same-platform check (see the
tests).
"""
from __future__ import annotations

import json

import numpy as np

# Largest displacement of any atom accepted between two builds (angstrom). Bonds in the
# drawings are tens of times longer; a draw radius is 0.3 A or more.
POSITION_TOL = 1e-2

# Float metadata computed from the geometry, compared relatively, not exactly.
GEOMETRY_DERIVED = frozenset({"c_hex", "radius_initial", "radius_final", "ff_energy_kcal_mol"})
DERIVED_RTOL = 1e-3

# info keys that hold JSON text in the file and parsed objects after read_structure.
_JSON_KEYS = ("params", "library_versions", "source_ids")


def _info(atoms):
    out = {}
    for k, v in atoms.info.items():
        if k in _JSON_KEYS and isinstance(v, str):
            v = json.loads(v)
        if isinstance(v, np.generic):
            v = v.item()
        out[k] = v
    return out


def _displacements(a, b):
    d = b.get_positions() - a.get_positions()
    if any(a.pbc):
        cell = np.asarray(a.cell)
        frac = d @ np.linalg.inv(cell)
        for k in range(3):
            if a.pbc[k]:
                frac[:, k] -= np.round(frac[:, k])
        d = frac @ cell
    return np.linalg.norm(d, axis=1)


def max_displacement(a, b) -> float:
    """Largest per-atom displacement between two structures with the same atom order."""
    r = _displacements(a, b)
    return float(r.max()) if len(r) else 0.0


def compare(committed, fresh, tol=POSITION_TOL, rtol=DERIVED_RTOL):
    """Differences between a committed and a freshly built structure (empty when equal)."""
    out = []
    if len(committed) != len(fresh):
        return [f"atom count {len(committed)} != {len(fresh)}"]
    sa, sb = committed.get_chemical_symbols(), fresh.get_chemical_symbols()
    if sa != sb:
        first = next(i for i, (x, y) in enumerate(zip(sa, sb)) if x != y)
        return [f"species or atom order differ (first at index {first}: {sa[first]} != {sb[first]})"]
    if tuple(bool(x) for x in committed.pbc) != tuple(bool(x) for x in fresh.pbc):
        out.append(f"pbc {tuple(committed.pbc)} != {tuple(fresh.pbc)}")
    keys = (set(committed.arrays) | set(fresh.arrays)) - {"numbers", "positions"}
    for k in sorted(keys):
        if k not in committed.arrays or k not in fresh.arrays:
            out.append(f"per-atom array {k} present in one structure only")
        elif committed.arrays[k].dtype.kind in "USO":
            if list(committed.arrays[k]) != list(fresh.arrays[k]):
                out.append(f"per-atom array {k} differs")
        elif not np.allclose(committed.arrays[k], fresh.arrays[k], rtol=0, atol=tol):
            out.append(f"per-atom array {k} differs beyond {tol}")
    cell_d = float(np.abs(np.asarray(committed.cell) - np.asarray(fresh.cell)).max())
    if cell_d > tol:
        out.append(f"cell differs by {cell_d:.3e} A (tolerance {tol})")
    r = _displacements(committed, fresh)
    if len(r) and r.max() > tol:
        worst = int(np.argmax(r))
        out.append(f"max displacement {r.max():.3e} A at atom {worst} ({sa[worst]}), "
                   f"{int((r > tol).sum())} atoms beyond {tol} A")
    ia, ib = _info(committed), _info(fresh)
    for k in sorted(set(ia) | set(ib)):
        if k not in ia or k not in ib:
            out.append(f"metadata key {k} present in one structure only")
        elif k in GEOMETRY_DERIVED:
            if not np.isclose(float(ia[k]), float(ib[k]), rtol=rtol, atol=0.0):
                out.append(f"metadata {k}: {ia[k]} != {ib[k]} (relative tolerance {rtol})")
        elif ia[k] != ib[k]:
            out.append(f"metadata {k}: {ia[k]!r} != {ib[k]!r}")
    return out
