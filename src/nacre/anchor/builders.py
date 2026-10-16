"""Builders for Ca2+-ligand complexes, their reference species and water clusters.

Every structure here is a starting geometry for later optimisation (W5.2 onward), not a
result. Ligands are embedded with RDKit (ETKDG, then MMFF94). Ca2+ is placed analytically on
the chelation bisector (bidentate) or along the C-O bond (monodentate). Waters fill the
remaining first-shell sites, spread over the sphere by a seeded repulsion step, oxygen
towards Ca and hydrogens away. The initial Ca-O distance is the sum of the covalent radii of
Ca and O from ase.data (Cordero et al. table). It is a placement rule, not a physical input,
and optimisation replaces it.

All builders are deterministic for a fixed seed.
"""
import json
from dataclasses import asdict, dataclass, field

import numpy as np

BUILDER_VERSION = "0.1.0"

LIGANDS = {
    # name: (SMILES, net charge, donor atom selection rule)
    "catecholate_monoanion": ("[O-]c1ccccc1O", -1),
    "catecholate_dianion": ("[O-]c1ccccc1[O-]", -2),
    "acetate": ("CC(=O)[O-]", -1),
}


@dataclass
class Structure:
    name: str
    symbols: list
    coords: np.ndarray
    charge: int
    multiplicity: int
    meta: dict = field(default_factory=dict)
    fragments: list = field(default_factory=list)  # per-atom fragment index
    bonds: list = field(default_factory=list)  # covalent pairs (i, j), excluded from clash checks

    @property
    def formula(self):
        from collections import Counter

        c = Counter(self.symbols)
        order = sorted(c, key=lambda s: (s not in ("C",), s not in ("H",), s))
        return "".join("%s%s" % (s, c[s] if c[s] > 1 else "") for s in order)

    def xyz(self):
        comment = json.dumps({"name": self.name, "charge": self.charge,
                              "multiplicity": self.multiplicity}, sort_keys=True)
        lines = [str(len(self.symbols)), comment]
        for s, (x, y, z) in zip(self.symbols, self.coords):
            lines.append("%-2s %14.8f %14.8f %14.8f" % (s, x, y, z))
        return "\n".join(lines) + "\n"

    def metadata(self):
        return {"name": self.name, "formula": self.formula, "n_atoms": len(self.symbols),
                "charge": self.charge, "multiplicity": self.multiplicity,
                "builder_version": BUILDER_VERSION, **self.meta}


def covalent_radius(symbol):
    from ase.data import atomic_numbers, covalent_radii

    return float(covalent_radii[atomic_numbers[symbol]])


def ca_o_distance():
    """Initial Ca-O placement distance: sum of ase covalent radii (a placement rule only)."""
    return covalent_radius("Ca") + covalent_radius("O")


# ----------------------------------------------------------------------------------- ligands
def embed(smiles, seed):
    """RDKit molecule with explicit H, embedded (ETKDG) and MMFF-relaxed with a fixed seed."""
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    params = AllChem.ETKDGv3()
    params.randomSeed = int(seed)
    if AllChem.EmbedMolecule(mol, params) != 0:
        raise RuntimeError("embedding failed for %s" % smiles)
    AllChem.MMFFOptimizeMolecule(mol, maxIters=2000)
    return mol


def _xyz_of(mol):
    conf = mol.GetConformer()
    return np.array([list(conf.GetAtomPosition(i)) for i in range(mol.GetNumAtoms())])


def _orient_hydroxyl_away(mol):
    """Turn a phenol H away from the neighbouring O (dihedral 180 deg), then relax with MMFF
    while holding that dihedral, so the chelation site is free of the hydroxyl H."""
    from rdkit import Chem
    from rdkit.Chem import AllChem, rdMolTransforms
    from rdkit.Chem import rdForceFieldHelpers as ffh

    patt = Chem.MolFromSmarts("[OX2H][c]:[c][O]")
    match = mol.GetSubstructMatch(patt)
    if not match:
        return mol
    o_h, c1, c2, _ = match
    h = [n.GetIdx() for n in mol.GetAtomWithIdx(o_h).GetNeighbors() if n.GetSymbol() == "H"][0]
    conf = mol.GetConformer()
    rdMolTransforms.SetDihedralDeg(conf, c2, c1, o_h, h, 180.0)
    props = ffh.MMFFGetMoleculeProperties(mol)
    ff = AllChem.MMFFGetMoleculeForceField(mol, props)
    ff.MMFFAddTorsionConstraint(c2, c1, o_h, h, False, 180.0, 180.0, 1.0e4)
    ff.Minimize(maxIts=2000)
    return mol


def ligand(name, seed):
    """(molecule, donor O indices, bonds) for a ligand."""
    smiles, _ = LIGANDS[name]
    mol = embed(smiles, seed)
    if name == "catecholate_monoanion":
        mol = _orient_hydroxyl_away(mol)
    donors = [a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "O"]
    bonds = [(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in mol.GetBonds()]
    return mol, donors, bonds


def _unit(v):
    n = np.linalg.norm(v)
    if n == 0:
        raise ValueError("zero vector")
    return v / n


def _plane_normal(x):
    c = x - x.mean(axis=0)
    return np.linalg.svd(c)[2][-1]


def place_ca(xyz, donors, mode, carbon=None):
    """Ca position for a bidentate (two donors) or monodentate (one donor) binding mode."""
    d = ca_o_distance()
    if mode == "bidentate":
        o1, o2 = xyz[donors[0]], xyz[donors[1]]
        mid = (o1 + o2) / 2
        half = np.linalg.norm(o1 - o2) / 2
        if half >= d:
            raise ValueError("donors too far apart for the placement distance")
        n = _plane_normal(xyz)
        u = _unit(np.cross(n, o2 - o1))
        if np.dot(u, mid - xyz.mean(axis=0)) < 0:
            u = -u
        return mid + u * np.sqrt(d * d - half * half)
    if mode == "monodentate":
        o = xyz[donors[0]]
        return o + d * _unit(o - xyz[carbon])
    raise ValueError("unknown mode %r" % mode)


# ------------------------------------------------------------------------------ first shell
def spread_sites(fixed, n_free, seed, steps=4000, lr=0.02):
    """n_free unit vectors spread away from each other and from the fixed unit vectors.

    A seeded Coulomb-like repulsion on the sphere; deterministic for a fixed seed.
    """
    rng = np.random.default_rng(seed)
    fixed = np.asarray(fixed, dtype=float).reshape(-1, 3)
    free = rng.normal(size=(n_free, 3))
    free /= np.linalg.norm(free, axis=1, keepdims=True)
    for _ in range(steps):
        pts = np.vstack([fixed, free])
        diff = free[:, None, :] - pts[None, :, :]
        dist = np.linalg.norm(diff, axis=2)
        dist[np.arange(n_free), len(fixed) + np.arange(n_free)] = np.inf
        force = (diff / dist[..., None] ** 3).sum(axis=1)
        force -= (force * free).sum(axis=1, keepdims=True) * free
        free = free + lr * force
        free /= np.linalg.norm(free, axis=1, keepdims=True)
    return free


_WATER = None


def water_template():
    """RDKit/MMFF water geometry: (O, H1, H2) coordinates with O at the origin."""
    global _WATER
    if _WATER is None:
        mol = embed("O", 0)
        x = _xyz_of(mol)
        o = [a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "O"][0]
        hs = [a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "H"]
        _WATER = (x[[o] + hs] - x[o]).copy()
    return _WATER.copy()


def _rotation_to(a, b):
    """Rotation matrix taking unit vector a onto unit vector b."""
    a, b = _unit(a), _unit(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.isclose(c, -1.0):
        p = _unit(np.cross(a, [1.0, 0, 0] if abs(a[0]) < 0.9 else [0, 1.0, 0]))
        return 2 * np.outer(p, p) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


def _axis_rotation(axis, angle):
    axis = _unit(axis)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k


def place_water(ca, direction, others, rng):
    """Water with O on `direction` from Ca, H2O bisector pointing away from Ca, and the
    molecular plane turned to keep its H atoms furthest from the atoms in `others`."""
    t = water_template()
    bis = _unit(t[1] + t[2])
    r = _rotation_to(bis, direction)
    w = t @ r.T
    o = ca + ca_o_distance() * direction
    best, best_score = None, -np.inf
    start = rng.uniform(0, 2 * np.pi)
    for k in range(24):
        rot = _axis_rotation(direction, start + k * np.pi / 12)
        cand = w @ rot.T + o
        score = (np.min(np.linalg.norm(cand[1:, None, :] - others[None, :, :], axis=2))
                 if len(others) else 0.0)
        if score > best_score:
            best, best_score = cand, score
    return best


def add_first_shell(ca, symbols, coords, fragments, bonds, ligand_dirs, n_water, seed):
    rng = np.random.default_rng(seed)
    dirs = spread_sites(ligand_dirs, n_water, seed)
    for k, d in enumerate(dirs):
        w = place_water(ca, d, np.asarray(coords), rng)
        base = len(symbols)
        symbols += ["O", "H", "H"]
        coords += [list(p) for p in w]
        frag = max(fragments) + 1
        fragments += [frag] * 3
        bonds += [(base, base + 1), (base, base + 2)]
    return symbols, coords, fragments, bonds


# ------------------------------------------------------------------------------- species
def complex_structure(lig, mode, n_water, seed=7):
    """[Ca(L)(H2O)n] for ligand `lig` in binding `mode` (bidentate or monodentate)."""
    smiles, lq = LIGANDS[lig]
    mol, donors, bonds = ligand(lig, seed)
    xyz = _xyz_of(mol)
    if lig == "acetate":
        carbon = [n.GetIdx() for n in mol.GetAtomWithIdx(donors[0]).GetNeighbors()][0]
        used = donors if mode == "bidentate" else donors[:1]
    else:
        if mode != "bidentate":
            raise ValueError("catecholate is built in its bidentate chelation mode only")
        carbon, used = None, donors
    ca = place_ca(xyz, used, mode, carbon)
    symbols = [a.GetSymbol() for a in mol.GetAtoms()] + ["Ca"]
    coords = [list(p) for p in xyz] + [list(ca)]
    fragments = [0] * mol.GetNumAtoms() + [1]
    lig_dirs = [_unit(xyz[i] - ca) for i in used]
    symbols, coords, fragments, bonds = add_first_shell(ca, symbols, coords, fragments, list(bonds),
                                                        lig_dirs, n_water, seed)
    name = "Ca_%s_%s_w%d" % (lig, mode, n_water)
    meta = {"kind": "complex", "ligand": lig, "ligand_smiles": smiles, "ligand_charge": lq,
            "coordination_mode": mode, "denticity": len(used), "n_water": n_water,
            "coordination_number_initial": len(used) + n_water, "seed": seed,
            "ca_o_initial_A": ca_o_distance(), "geometry": "starting geometry, not optimised"}
    return Structure(name, symbols, np.array(coords), 2 + lq, 1, meta, fragments, bonds)


def hydrated_ca(n_water, seed=7):
    ca = np.zeros(3)
    symbols, coords, fragments, bonds = ["Ca"], [list(ca)], [0], []
    symbols, coords, fragments, bonds = add_first_shell(ca, symbols, coords, fragments, bonds,
                                                        [], n_water, seed)
    meta = {"kind": "reference", "role": "hydrated Ca2+ cluster", "coordination_mode": "aqua",
            "n_water": n_water, "seed": seed, "ca_o_initial_A": ca_o_distance(),
            "geometry": "starting geometry, not optimised"}
    return Structure("Ca_aqua_w%d" % n_water, symbols, np.array(coords), 2, 1, meta, fragments, bonds)


def free_ligand(lig, seed=7):
    smiles, lq = LIGANDS[lig]
    mol, _, bonds = ligand(lig, seed)
    meta = {"kind": "reference", "role": "free ligand", "ligand": lig, "ligand_smiles": smiles,
            "coordination_mode": "none", "n_water": 0, "seed": seed,
            "geometry": "RDKit ETKDG + MMFF94"}
    return Structure("ligand_%s" % lig, [a.GetSymbol() for a in mol.GetAtoms()], _xyz_of(mol),
                     lq, 1, meta, [0] * mol.GetNumAtoms(), bonds)


def water_cluster(n_water, seed=7):
    """n waters spread on a shell around an empty centre (a starting geometry for the
    released-water term of the cycle; n = 1 is a single molecule)."""
    rng = np.random.default_rng(seed)
    t = water_template()
    if n_water == 1:
        symbols, coords = ["O", "H", "H"], t.tolist()
        frags, bonds = [0, 0, 0], [(0, 1), (0, 2)]
    else:
        oo = 2 * covalent_radius("O") + 2 * covalent_radius("H")  # O...O placement spacing
        radius = oo / (2 * np.sin(np.pi / max(n_water, 2)))
        dirs = spread_sites([], n_water, seed)
        symbols, coords, frags, bonds = [], [], [], []
        for k, d in enumerate(dirs):
            r = _rotation_to(_unit(t[1] + t[2]), _unit(rng.normal(size=3)))
            w = t @ r.T + radius * d
            base = len(symbols)
            symbols += ["O", "H", "H"]
            coords += w.tolist()
            frags += [k] * 3
            bonds += [(base, base + 1), (base, base + 2)]
    meta = {"kind": "reference", "role": "water cluster", "coordination_mode": "none",
            "n_water": n_water, "seed": seed, "geometry": "starting geometry, not optimised"}
    return Structure("water_w%d" % n_water, symbols, np.array(coords), 0, 1, meta, frags, bonds)


def all_species(n_water_complex_bidentate=4, n_water_complex_monodentate=5, n_water_aqua=6,
                seed=7):
    """Every species of the binding comparison, with consistent first-shell sizes.

    Defaults keep the initial coordination number equal (6) across complexes and the aqua
    ion, so each cycle releases (n_aqua - n_complex) waters; W5.2 sets the numbers.
    """
    s = [
        complex_structure("catecholate_monoanion", "bidentate", n_water_complex_bidentate, seed),
        complex_structure("catecholate_dianion", "bidentate", n_water_complex_bidentate, seed),
        complex_structure("acetate", "monodentate", n_water_complex_monodentate, seed),
        complex_structure("acetate", "bidentate", n_water_complex_bidentate, seed),
        hydrated_ca(n_water_aqua, seed),
        free_ligand("catecholate_monoanion", seed),
        free_ligand("catecholate_dianion", seed),
        free_ligand("acetate", seed),
    ]
    released = sorted({n_water_aqua - n_water_complex_bidentate,
                       n_water_aqua - n_water_complex_monodentate} - {0})
    s += [water_cluster(n, seed) for n in released]
    return s


def min_distances(st):
    """(minimum over all pairs, minimum over pairs in different fragments), in angstrom."""
    x = np.asarray(st.coords)
    d = np.linalg.norm(x[:, None, :] - x[None, :, :], axis=2)
    iu = np.triu_indices(len(x), 1)
    all_min = float(d[iu].min()) if len(iu[0]) else np.inf
    f = np.asarray(st.fragments)
    inter = f[:, None] != f[None, :]
    inter_min = float(d[inter].min()) if inter.any() else np.inf
    return all_min, inter_min


def as_record(st):
    return {**st.metadata(), "fragments": st.fragments, "bonds": [list(b) for b in st.bonds]}


def to_dict(st):
    return {**asdict(st), "coords": np.asarray(st.coords).tolist()}
