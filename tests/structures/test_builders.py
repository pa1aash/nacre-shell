"""Structure builders: atom counts, charge, periodicity, clashes, determinism and metadata."""
from __future__ import annotations

import hashlib
import json
from collections import Counter

import numpy as np
import pytest

from nacre.structures import acc, build, ion, mp_source, oligomer, slab, water
from nacre.structures.meta import CLASH_THRESHOLD, formal_charge, min_distance, read_structure, write_structure

from structures_helpers import STRUCT_DIR, committed_structures


@pytest.fixture(scope="module")
def small_slab():
    return slab.build({"nx": 2, "ny": 3, "n_o_layers": 4, "vacuum": 8.0}, seed=0)


# ---------------------------------------------------------------- source
def test_corundum_source_record():
    rec = mp_source.load()
    assert rec["material_id"].startswith("mp-")
    assert rec["database_version"]
    assert rec["query"]["formula"] == "Al2O3" and rec["query"]["spacegroup_number"] == 167
    assert rec["spacegroup_symbol"] == "R-3c"
    species = Counter(s["species"][0]["element"] for s in rec["structure"]["sites"])
    assert species == {"Al": 4, "O": 6}


def test_source_record_holds_no_key():
    text = mp_source.cached_path().read_text().lower()
    assert "api_key" not in text and "x-api-key" not in text


# ---------------------------------------------------------------- slab
@pytest.mark.parametrize("nx,ny,n_o", [(1, 1, 2), (2, 3, 4), (4, 4, 7)])
def test_slab_counts_and_charge(nx, ny, n_o):
    s = slab.build({"nx": nx, "ny": ny, "n_o_layers": n_o}, seed=0)
    c = Counter(s.get_chemical_symbols())
    cells = nx * ny
    assert c == {"Al": 2 * (n_o - 1) * cells, "O": 3 * n_o * cells, "H": 6 * cells}
    assert s.info["total_charge"] == 0 == formal_charge(s.get_chemical_symbols())


def test_slab_hydroxyl_density(small_slab):
    # Three OH per 1x1 hexagonal surface cell on each face.
    a = np.linalg.norm(small_slab.cell[0]) / 2
    expected = 3 / (np.sqrt(3) / 2 * a * a / 100.0)
    assert slab.surface_hydroxyl_density(small_slab) == pytest.approx(expected, rel=1e-9)


def test_slab_periodicity(small_slab):
    s = small_slab
    assert tuple(s.pbc) == (True, True, False)
    a, b, c, alpha, beta, gamma = s.cell.cellpar()
    bulk, _ = slab.bulk_hexagonal()
    a_hex = bulk.cell.cellpar()[0]
    assert a == pytest.approx(2 * a_hex) and b == pytest.approx(3 * a_hex)
    assert gamma == pytest.approx(120.0) and alpha == pytest.approx(90.0) and beta == pytest.approx(90.0)
    assert s.cell[0][1] == pytest.approx(0.0, abs=1e-9) and s.cell[2][0] == pytest.approx(0.0, abs=1e-9)
    # Every Al is octahedral (six O within 2.1 A) only if the periodic images are consistent.
    sym = np.array(s.get_chemical_symbols())
    pos = s.get_positions()
    cell = np.asarray(s.cell)
    inv = np.linalg.inv(cell)
    for i in np.where(sym == "Al")[0]:
        d = (pos[sym == "O"] - pos[i]) @ inv
        d[:, :2] -= np.round(d[:, :2])
        r = np.linalg.norm(d @ cell, axis=1)
        assert (r < 2.1).sum() == 6
    # A doubled cell has the same nearest-neighbour distance (no seam at the boundary).
    assert min_distance(s.repeat((2, 1, 1))) == pytest.approx(min_distance(s), abs=1e-9)
    # Every terminal O carries exactly one H; no H sits inside the slab.
    o_z = pos[sym == "O", 2]
    h_z = pos[sym == "H", 2]
    assert np.all((h_z > o_z.max()) | (h_z < o_z.min()))


def test_slab_vacuum(small_slab):
    z = small_slab.positions[:, 2]
    assert z.min() == pytest.approx(8.0)
    assert small_slab.cell[2][2] - z.max() == pytest.approx(8.0)


# ---------------------------------------------------------------- molecules
def test_hydrated_ca_counts_and_charge():
    a = ion.build({"cn": 6}, seed=3)
    assert Counter(a.get_chemical_symbols()) == {"Ca": 1, "O": 6, "H": 12}
    assert a.info["total_charge"] == 2 == formal_charge(a.get_chemical_symbols())
    r = np.linalg.norm(a.positions[np.array(a.get_chemical_symbols()) == "O"] - a.positions[0], axis=1)
    assert np.allclose(r, 2.40)


@pytest.mark.parametrize("cn", [6, 7, 8])
def test_hydrated_ca_other_shells(cn):
    a = ion.build({"cn": cn}, seed=0)
    assert Counter(a.get_chemical_symbols())["O"] == cn
    assert min_distance(a) >= CLASH_THRESHOLD


def test_acc_counts_and_charge():
    a = acc.build({"n_fu": 8}, seed=5)
    c = Counter(a.get_chemical_symbols())
    assert c == {"Ca": 8, "C": 8, "O": 24}
    assert a.info["total_charge"] == 0 == formal_charge(a.get_chemical_symbols())


@pytest.mark.parametrize("n", [1, 2, 4])
def test_oligomer_counts_and_charge(n):
    a = oligomer.build({"n_units": n}, seed=7)
    # 5,6-dihydroxyindole is C8H7NO2; each 2-7' link removes two H.
    assert Counter(a.get_chemical_symbols()) == {"C": 8 * n, "N": n, "O": 2 * n, "H": 5 * n + 2}
    assert a.info["total_charge"] == 0
    assert a.info["ff_converged"]


def test_oligomer_smiles_is_catechol_indole_chain():
    from rdkit import Chem

    mol = Chem.MolFromSmiles(oligomer.dhi_chain_smiles(3))
    catechol = Chem.MolFromSmarts("c(O)c(O)")
    indole = Chem.MolFromSmarts("c1ccc2[nH]ccc2c1")
    assert len(mol.GetSubstructMatches(catechol)) == 3
    assert len(mol.GetSubstructMatches(indole)) == 3


def test_water_layer(small_slab):
    w = water.build(small_slab, {"thickness": 6.0}, seed=1)
    comp = w.arrays["component"]
    sym = np.array(w.get_chemical_symbols())
    wat = comp == "water"
    assert (comp == "substrate").sum() == len(small_slab)
    assert (sym[wat] == "O").sum() * 2 == (sym[wat] == "H").sum()
    assert w.info["n_water_placed"] == w.info["n_water_target"] > 0
    assert w.info["total_charge"] == 0
    # Water sits above the slab.
    assert w.positions[wat, 2].min() > small_slab.positions[:, 2].max()
    # Minimum-distance rule: O-O and intermolecular distances (molecule id from atom order).
    mol = np.r_[np.full(len(small_slab), -1), np.arange(wat.sum()) // 3]
    same = mol[:, None] == mol[None, :]
    assert min_distance(w, exclude_pairs=same) >= water.DEFAULTS["min_any"] - 1e-9


# ---------------------------------------------------------------- determinism
@pytest.mark.parametrize("builder", [
    (lambda s: slab.build({"nx": 2, "ny": 2, "n_o_layers": 3}, seed=s)),
    (lambda s: ion.build(None, seed=s)),
    (lambda s: acc.build({"n_fu": 4}, seed=s)),
    (lambda s: oligomer.build({"n_units": 2}, seed=s)),
])
def test_deterministic_for_fixed_seed(builder, tmp_path):
    a, b = builder(11), builder(11)
    assert a.get_chemical_symbols() == b.get_chemical_symbols()
    assert np.array_equal(a.positions, b.positions)
    assert write_structure(a, tmp_path / "a.extxyz") == write_structure(b, tmp_path / "b.extxyz")


def test_seed_changes_random_constructions(small_slab):
    w1 = water.build(small_slab, {"n_molecules": 4}, seed=1)
    w2 = water.build(small_slab, {"n_molecules": 4}, seed=2)
    assert not np.array_equal(w1.positions, w2.positions)


def test_committed_files_regenerate_bit_for_bit(tmp_path):
    _, manifest = build.build_all(out_dir=tmp_path)
    committed = json.loads((STRUCT_DIR / "manifest.json").read_text())
    for name, entry in manifest.items():
        assert entry["sha256"] == committed[name]["sha256"], name
        assert hashlib.sha256((STRUCT_DIR / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]


# ---------------------------------------------------------------- committed outputs
@pytest.fixture(scope="module")
def committed():
    return {name: read_structure(path) for name, path in committed_structures().items()}


def test_every_build_target_is_committed(committed):
    cfg = build.load_config()
    written = {n for n, spec in cfg["targets"].items() if spec.get("write", True)}
    assert written == set(committed)


def test_metadata_on_every_structure(committed):
    for name, a in committed.items():
        info = a.info
        assert info["illustrative"] is True, name
        assert "not a simulated structure" in info["label"], name
        assert info["builder"].startswith("nacre.structures."), name
        assert isinstance(info["params"], dict) and isinstance(info["seed"], (int, np.integer)), name
        assert {"ase", "numpy", "rdkit"} <= set(info["library_versions"]), name


def test_slab_metadata_names_the_source(committed):
    rec = mp_source.load()
    for name in ("al2o3_0001_oh", "al2o3_0001_oh_water"):
        src = committed[name].info["source_ids"]
        assert src["bulk"] == rec["material_id"]
        assert src["database_version"] == rec["database_version"]


def test_total_charge_of_committed(committed):
    for name, a in committed.items():
        if name == "catechol_oligomer":
            assert a.info["total_charge"] == 0
            continue
        assert a.info["total_charge"] == formal_charge(a.get_chemical_symbols()), name


def test_no_clashes_in_committed(committed):
    for name, a in committed.items():
        assert min_distance(a) >= CLASH_THRESHOLD, name
