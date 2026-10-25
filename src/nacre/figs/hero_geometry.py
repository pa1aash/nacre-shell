"""Atom positions for the molecular hero figure (fig1), built in the repository environment and
handed to the Blender script as JSON (Blender's interpreter has neither ase nor RDKit).

Every coordinate is generated, never typed:
  aluminium   ase.build.fcc111 with the ase reference lattice constant of Al (ase.data.reference_states)
  water       ase.build.molecule("H2O"), the G2 geometry shipped with ase
  carbonate   D3h with the C-O length of lit/params.yaml c_o_bond_length_calcite (TM-030)
  PC          RDKit ETKDG embedding of propylene carbonate with a fixed seed, then MMFF94
  phosphate   regular PO4 tetrahedra sharing corners, bridging angle equal to the tetrahedral
              angle, P-O at a normalised schematic length (no committed P-O source; the caption
              says so); perchlorate is drawn on the same schematic tetrahedron
Liquid molecules and ions are placed at random (fixed seed) above the slab, at a fraction of the
liquid number density, with a minimum heavy-atom separation; positions carry no quantitative meaning.

Units are Angstrom; z = 0 is the plane of the top Al layer.
"""
import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np
import yaml

TETRA = math.acos(-1.0 / 3.0)
# The random fill is sized from the molar mass (ase/RDKit) and liquid_density_g_cm3 in renders.yaml.
AVOGADRO = 6.02214076e23

SPECIES_CLASS = {"Al": "Al", "O": "O", "H": "H", "C": "C", "Ca": "Ca", "Li": "Li", "Cl": "Cl"}


def _params(root):
    return yaml.safe_load((Path(root) / "lit" / "params.yaml").read_text())


def c_o_length(root):
    for v in _params(root).values():
        if isinstance(v, dict) and "c_o_bond_length_calcite" in v:
            return float(v["c_o_bond_length_calcite"]["value"]) * 1e10, v["c_o_bond_length_calcite"]["sources"]
    raise KeyError("c_o_bond_length_calcite not in lit/params.yaml")


def _rot(rng):
    """A uniformly random rotation matrix from a private generator (Shoemake quaternion)."""
    u1, u2, u3 = rng.random(), rng.random(), rng.random()
    a, b = math.sqrt(1 - u1), math.sqrt(u1)
    w, x, y, z = a * math.sin(math.tau * u2), a * math.cos(math.tau * u2), b * math.sin(math.tau * u3), b * math.cos(math.tau * u3)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _bonds_by_distance(symbols, pos, scale=1.2):
    from ase.data import atomic_numbers, covalent_radii
    r = np.array([covalent_radii[atomic_numbers[s]] for s in symbols])
    out = []
    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            if np.linalg.norm(pos[i] - pos[j]) < scale * (r[i] + r[j]):
                out.append((i, j))
    return out


def water():
    from ase.build import molecule
    m = molecule("H2O")
    pos = m.positions - m.positions[[s == "O" for s in m.get_chemical_symbols()]][0]
    return {"symbols": m.get_chemical_symbols(), "pos": pos, "bonds": [(0, 1), (0, 2)], "mass": float(m.get_masses().sum())}


def propylene_carbonate(seed):
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors
    mol = Chem.AddHs(Chem.MolFromSmiles("CC1COC(=O)O1"))
    p = AllChem.ETKDGv3()
    p.randomSeed = seed
    if AllChem.EmbedMolecule(mol, p) != 0:
        raise RuntimeError("RDKit embedding of propylene carbonate failed")
    AllChem.MMFFOptimizeMolecule(mol)
    pos = np.array(mol.GetConformer().GetPositions())
    pos -= pos.mean(axis=0)
    bonds = [(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in mol.GetBonds()]
    return {"symbols": [a.GetSymbol() for a in mol.GetAtoms()], "pos": pos, "bonds": bonds,
            "mass": float(Descriptors.MolWt(mol))}


def carbonate(d_co):
    pos = [np.zeros(3)] + [d_co * np.array([math.cos(k * math.tau / 3), math.sin(k * math.tau / 3), 0.0]) for k in range(3)]
    return {"symbols": ["C", "O", "O", "O"], "pos": np.array(pos), "bonds": [(0, 1), (0, 2), (0, 3)]}


def _tetra_dirs():
    return np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=float) / math.sqrt(3.0)


def perchlorate(d):
    pos = np.vstack([np.zeros(3), d * _tetra_dirs()])
    return {"symbols": ["Cl", "O", "O", "O", "O"], "pos": pos, "bonds": [(0, k) for k in range(1, 5)]}


def phosphate_chain(n, d, z0, x0=0.0, y0=0.0):
    """n corner-sharing PO4 tetrahedra lying along x on the surface: a planar all-trans P-O-P
    backbone standing upright (P on the lower line, bridging O on the upper one), every backbone
    angle equal to the tetrahedral angle, two terminal O per inner P and three at the ends.
    Built in the xy plane and turned about x so that the bridging O point up."""
    half = TETRA / 2.0
    # P-O-P bridging: P_i to O_b along direction with angle half from the chain axis.
    step = 2 * d * math.sin(half)            # P...P distance
    rise = d * math.cos(half)                # offset of the bridging O from the P...P line
    ps = [np.array([x0 + i * step - (n - 1) * step / 2, y0, z0]) for i in range(n)]
    sym, pos, bonds = [], [], []
    p_idx = []
    for p in ps:
        p_idx.append(len(pos))
        sym.append("P")
        pos.append(p)
    ob = []
    for i in range(n - 1):
        o = (ps[i] + ps[i + 1]) / 2 + np.array([0.0, rise, 0.0])
        ob.append(len(pos))
        sym.append("O")
        pos.append(o)
        bonds += [(p_idx[i], ob[-1]), (p_idx[i + 1], ob[-1])]
    for i, p in enumerate(ps):
        dirs = []
        if i > 0:
            dirs.append((pos[ob[i - 1]] - p) / d)
        if i < n - 1:
            dirs.append((pos[ob[i]] - p) / d)
        if len(dirs) == 1:  # chain end: continue the zig-zag for the missing bridge, as a terminal O
            u = dirs[0]
            mirror = np.array([-u[0], u[1], u[2]])
            dirs.append(mirror)
            extra = [mirror]
        else:
            extra = []
        u, v = dirs
        b = (u + v) / np.linalg.norm(u + v)
        nrm = np.cross(u, v)
        nrm /= np.linalg.norm(nrm)
        for s in (1.0, -1.0):
            extra.append(-b * math.cos(half) + s * nrm * math.sin(half))
        for e in extra:
            sym.append("O")
            pos.append(p + d * e)
            bonds.append((p_idx[i], len(pos) - 1))
    centre = np.array([x0, y0, z0])
    turn = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
    return {"symbols": sym, "pos": (np.array(pos) - centre) @ turn.T + centre, "bonds": bonds}


def al_slab(lx, ly, layers):
    from ase.build import fcc111
    from ase.data import atomic_numbers, reference_states
    a = reference_states[atomic_numbers["Al"]]["a"]
    nn = a / math.sqrt(2.0)
    nx = int(round(lx / nn))
    ny = int(round(ly / (nn * math.sqrt(3.0) / 2))) // 2 * 2
    slab = fcc111("Al", size=(nx, ny, layers), a=a, orthogonal=True)
    pos = slab.positions.copy()
    pos[:, 0] -= slab.cell[0, 0] / 2
    pos[:, 1] -= slab.cell[1, 1] / 2
    pos[:, 2] -= pos[:, 2].max()
    return {"symbols": ["Al"] * len(pos), "pos": pos, "a": float(a), "size": [nx, ny, layers],
            "extent": [float(slab.cell[0, 0]), float(slab.cell[1, 1])]}


class Scene:
    def __init__(self):
        self.atoms = []   # [class, element, x, y, z]
        self.bonds = []   # [i, j]
        self.heavy = []   # positions of non-H atoms of liquid/ion species, for overlap checks

    def add(self, frag, cls=None, where=None, rot=None, track=True):
        start = len(self.atoms)
        pos = frag["pos"] @ rot.T if rot is not None else frag["pos"]
        if where is not None:
            pos = pos + where
        for s, p in zip(frag["symbols"], pos):
            self.atoms.append([cls or SPECIES_CLASS.get(s, s), s] + [round(float(x), 4) for x in p])
            if track and s != "H":
                self.heavy.append(p)
        self.bonds += [[start + i, start + j] for i, j in frag.get("bonds", [])]
        return pos

    def free(self, pos, symbols, dmin):
        if not self.heavy:
            return True
        h = np.array(self.heavy)
        for s, p in zip(symbols, pos):
            if s == "H":
                continue
            if np.min(np.sum((h - p) ** 2, axis=1)) < dmin * dmin:
                return False
        return True


def _fill(sc, rng, frag, n, box, dmin, cls=None, tries=400):
    placed = 0
    for _ in range(n):
        for _t in range(tries):
            rot = _rot(rng)
            where = np.array([rng.uniform(*box[0]), rng.uniform(*box[1]), rng.uniform(*box[2])])
            pos = frag["pos"] @ rot.T + where
            if pos[:, 2].min() < box[2][0] - 0.5:
                continue
            if sc.free(pos, frag["symbols"], dmin):
                sc.add(frag, cls=cls, where=where, rot=rot)
                placed += 1
                break
    return placed


def build(entry, root, seed):
    """Both panels' atoms and bonds plus the record of where each geometry came from."""
    g = entry["geometry"]
    d_co, co_src = c_o_length(root)
    d_schem = d_co * float(g["schematic_bond_factor"])
    slab = al_slab(g["slab_x"], g["slab_y"], g["slab_layers"])
    lx, ly = slab["extent"]
    h = float(g["liquid_height"])
    box = ((-lx / 2 + 1.0, lx / 2 - 1.0), (max(-ly / 2 + 1.0, float(g["liquid_front"])), ly / 2 - 1.0),
           (float(g["liquid_bottom"]), h))
    vol = (box[0][1] - box[0][0]) * (box[1][1] - box[1][0]) * (box[2][1] - box[2][0])
    w, pc = water(), propylene_carbonate(seed)
    panels, counts = {}, {}
    for panel in ("a", "b"):
        rng = random.Random(seed * 1000 + (1 if panel == "a" else 2))
        sc = Scene()
        sc.add(slab, track=False)
        if panel == "a":
            ions = [(carbonate(d_co), "carbonate", int(g["ions_a"]["CO3"])), ({"symbols": ["Ca"], "pos": np.zeros((1, 3))}, "Ca", int(g["ions_a"]["Ca"]))]
            solvent, rho = w, float(g["liquid_density_g_cm3"]["water"])
        else:
            chain = phosphate_chain(int(g["chain_units"]), d_schem, float(g["chain_z"]), y0=float(g["chain_y"]))
            sc.add(chain, cls="phosphate")
            ions = [(perchlorate(d_schem), None, int(g["ions_b"]["ClO4"])), ({"symbols": ["Li"], "pos": np.zeros((1, 3))}, "Li", int(g["ions_b"]["Li"]))]
            solvent, rho = pc, float(g["liquid_density_g_cm3"]["propylene_carbonate"])
        placed = {}
        zone = tuple(tuple(float(v) for v in g["ion_zone"][k]) for k in ("x", "y", "z"))
        for frag, cls, n in ions:
            placed[cls or frag["symbols"][0]] = _fill(sc, rng, frag, n, zone, float(g["min_heavy_separation"]), cls=cls)
        n_solvent = int(round(rho / solvent["mass"] * AVOGADRO * 1e-24 * vol * float(g["density_fraction"])))
        placed["solvent"] = _fill(sc, rng, solvent, n_solvent, box, float(g["min_heavy_separation"]))
        placed["solvent_target"] = n_solvent
        panels[panel] = {"atoms": sc.atoms, "bonds": sc.bonds}
        counts[panel] = placed
    sources = {
        "Al": "ase.build.fcc111, a = %.4f Angstrom from ase.data.reference_states (ase %s)" % (slab["a"], _ver("ase")),
        "water": "ase.build.molecule('H2O'), G2 geometry (ase %s)" % _ver("ase"),
        "carbonate": "C-O %.4f Angstrom, lit/params.yaml c_o_bond_length_calcite (%s)" % (d_co, ", ".join(co_src)),
        "propylene_carbonate": "RDKit %s ETKDGv3 (seed %d) + MMFF94" % (_ver("rdkit"), seed),
        "phosphate": "schematic: regular corner-sharing tetrahedra, P-O normalised to %.2f x the calcite C-O length" % float(g["schematic_bond_factor"]),
        "perchlorate": "schematic: the same normalised tetrahedron",
    }
    return {"panels": panels, "counts": counts, "slab": {"size": slab["size"], "extent": [round(x, 3) for x in slab["extent"]]},
            "liquid_box": [[round(x, 3) for x in b] for b in box], "sources": sources}


def _ver(pkg):
    import importlib.metadata as md
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return __import__(pkg).__version__


def write(entry, root, seed, path):
    """Geometry plus the drawing settings of renders.yaml and the ase covalent radii, as one JSON."""
    from ase.data import atomic_numbers, covalent_radii
    data = build(entry, root, seed)
    els = sorted({a[1] for p in data["panels"].values() for a in p["atoms"]})
    data["style"] = dict(entry["scene"], covalent={e: round(float(covalent_radii[atomic_numbers[e]]), 4) for e in els})
    text = json.dumps(data, sort_keys=True, separators=(",", ":"))
    Path(path).write_text(text)
    return data, hashlib.sha256(text.encode()).hexdigest()
