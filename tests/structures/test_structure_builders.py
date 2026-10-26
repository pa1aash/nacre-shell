"""Structure builders: atom counts, charge, periodicity, clashes, determinism and metadata."""
from __future__ import annotations

import hashlib
import json
from collections import Counter

import numpy as np
import pytest

from nacre.structures import acc, build, compare, ion, mp_source, oligomer, params_source, slab, water
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


def test_slab_atom_order_ignores_last_bit_noise(small_slab):
    # On Linux CI the raw z sort permuted atoms within a layer (5.8 A apparent displacements).
    rng = np.random.default_rng(0)
    for scale in (1e-12, 1e-6, 1e-3):
        noisy = small_slab.positions + rng.normal(scale=scale, size=small_slab.positions.shape)
        assert np.array_equal(slab.stable_order(small_slab.numbers, noisy), np.arange(len(small_slab)))


def test_orthogonal_slab_cell():
    s = slab.build({"nx": 2, "ny": 1, "n_o_layers": 3, "orthogonal": True}, seed=0)
    cell = np.asarray(s.cell)
    assert cell[0][1] == pytest.approx(0.0, abs=1e-9) and cell[1][0] == pytest.approx(0.0, abs=1e-9)
    hexa = slab.build({"nx": 2, "ny": 2, "n_o_layers": 3}, seed=0)
    assert len(s) == len(hexa)  # 2 x 1 rectangular cells hold 2 x 2 hexagonal cells
    assert s.info["total_charge"] == 0
    assert min_distance(s) >= CLASH_THRESHOLD


def test_slab_vacuum(small_slab):
    z = small_slab.positions[:, 2]
    assert z.min() == pytest.approx(8.0)
    assert small_slab.cell[2][2] - z.max() == pytest.approx(8.0)


# ---------------------------------------------------------------- molecules
def test_hydrated_ca_counts_and_charge():
    a = ion.build({"cn": 6, "r_ca_o": 2.5}, seed=3)
    assert Counter(a.get_chemical_symbols()) == {"Ca": 1, "O": 6, "H": 12}
    assert a.info["total_charge"] == 2 == formal_charge(a.get_chemical_symbols())
    r = np.linalg.norm(a.positions[np.array(a.get_chemical_symbols()) == "O"] - a.positions[0], axis=1)
    assert np.allclose(r, 2.5)


def test_hydrated_ca_has_no_typed_defaults():
    with pytest.raises(ValueError):
        ion.build(None, seed=0)
    assert "cn" not in ion.DEFAULTS and "r_ca_o" not in ion.DEFAULTS


@pytest.mark.parametrize("cn", [6, 7, 8])
def test_hydrated_ca_other_shells(cn):
    a = ion.build({"cn": cn, "r_ca_o": 2.4}, seed=0)
    assert Counter(a.get_chemical_symbols())["O"] == cn
    assert min_distance(a) >= CLASH_THRESHOLD


def test_acc_counts_and_charge():
    a = acc.build({"n_fu": 8}, seed=5, accg=params_source.acc_geometry())
    c = Counter(a.get_chemical_symbols())
    assert c == {"Ca": 8, "C": 8, "O": 24}
    assert a.info["total_charge"] == 0 == formal_charge(a.get_chemical_symbols())


def test_acc_geometry_comes_from_w1_params_keys():
    rec = params_source.load()
    assert rec["ref"] == "origin/preprint/p0-w1" and len(rec["commit"]) == 40
    g = params_source.acc_geometry()
    v_m = rec["keys"]["v_m_acc"]["value"]
    assert g["fu_per_a3"] == pytest.approx(6.02214076e23 / (v_m * 1e30))
    assert g["r_co"] == pytest.approx(rec["keys"]["c_o_bond_length_acc"]["value"] * 1e10)
    assert g["keys"] == {"packing": "v_m_acc", "packing_check": "rho_acc", "r_co": "c_o_bond_length_acc"}
    a = acc.build({"n_fu": 4}, seed=5, accg=g)
    sym = np.array(a.get_chemical_symbols())
    c, o = a.positions[sym == "C"], a.positions[sym == "O"]
    d = np.linalg.norm(c[:, None] - o[None], axis=-1)
    assert np.allclose(np.sort(d, axis=1)[:, :3], g["r_co"], atol=1e-9)


@pytest.mark.parametrize("typed", [{"density_g_cm3": 1.9}, {"r_co": 1.28}])
def test_acc_drawing_values_cannot_be_typed(typed):
    with pytest.raises(ValueError):
        acc.build({"n_fu": 4, **typed}, seed=5, accg=params_source.acc_geometry())
    with pytest.raises(ValueError):
        acc.build({"n_fu": 4}, seed=5)


def test_params_record_cross_check_refuses_disagreeing_keys():
    rec = params_source.load()
    bad = {**rec, "keys": {**rec["keys"], "rho_acc": {**rec["keys"]["rho_acc"], "value": 1000.0}}}
    with pytest.raises(ValueError):
        params_source.acc_geometry(bad)


@pytest.mark.parametrize("n", [1, 2, 4])
def test_oligomer_counts_and_charge(n):
    rec = oligomer.generate({"n_units": n}, seed=7)
    # 5,6-dihydroxyindole is C8H7NO2; each 2-7' link removes two H.
    assert Counter(rec["symbols"]) == {"C": 8 * n, "N": n, "O": 2 * n, "H": 5 * n + 2}
    assert rec["formal_charge"] == 0
    assert rec["ff_converged"]
    # Two catechol O and their two H per unit, unit 0 at the anchoring end (atom 0).
    unit = np.array(rec["catechol"])
    assert unit[0] == 0
    for k in range(n):
        assert sorted(np.array(rec["symbols"])[unit == k]) == ["H", "H", "O", "O"], k


def test_oligomer_targets_are_built_from_the_conformer_record():
    rec = oligomer.load_record()
    for spec in build.load_config()["targets"].values():
        if spec["builder"] == "oligomer":
            key = oligomer.conformer_key(spec.get("params"), spec.get("seed", 0))
            entry = rec[key]
            a = oligomer.build(spec.get("params"), spec.get("seed", 0))
            assert np.array_equal(a.positions, np.array(entry["positions"]))
            assert json.loads(a.info["source_ids"])["conformer"] == key
            assert entry["smiles"] == oligomer.dhi_chain_smiles(entry["params"]["n_units"],
                                                                entry["params"].get("end_group"))
            assert set(entry["generated_on"]) == {"system", "machine"}


def test_oligomer_without_record_entry_is_refused():
    with pytest.raises(LookupError):
        oligomer.build({"n_units": 3}, seed=123, record={})


def test_conformer_record_regenerates_on_its_platform():
    import platform

    for key, entry in oligomer.load_record().items():
        here = {"system": platform.system(), "machine": platform.machine()}
        if here != entry["generated_on"]:
            pytest.skip(f"same-platform check: conformer {key} was generated on {entry['generated_on']}; "
                        "ETKDG embedding differs between platforms, which is why the record exists")
        fresh = oligomer.generate(entry["params"], entry["seed"])
        assert fresh["positions"] == entry["positions"], key


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
    (lambda s: ion.build({"cn": 7, "r_ca_o": 2.4}, seed=s)),
    (lambda s: acc.build({"n_fu": 4}, seed=s, accg=params_source.acc_geometry())),
    (lambda s: oligomer.to_atoms(oligomer.generate({"n_units": 2}, seed=s))),
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


@pytest.fixture(scope="module")
def fresh_build(tmp_path_factory):
    # Each written target is built on its own, so one that fails does not hide the others.
    out = tmp_path_factory.mktemp("fresh")
    manifest, errors = {}, {}
    for name, spec in build.load_config()["targets"].items():
        if not spec.get("write", True):
            continue
        try:
            _, m = build.build_all([name], out_dir=out)
        except (RuntimeError, ValueError) as exc:
            errors[name] = f"build failed: {exc}"
            continue
        manifest[name] = m[name]
    return out, manifest, errors


def _tolerance_report(out_dir, manifest):
    """Differences of every freshly built file from the committed one (all files, not the first)."""
    problems = {}
    for name, entry in manifest.items():
        diffs = compare.compare(read_structure(STRUCT_DIR / entry["file"]), read_structure(out_dir / entry["file"]))
        if diffs:
            problems[name] = diffs
    return problems


def test_committed_files_regenerate_within_tolerance(fresh_build):
    # Coordinates within compare.POSITION_TOL; species, order, counts and metadata exact.
    out, manifest, errors = fresh_build
    committed = json.loads((STRUCT_DIR / "manifest.json").read_text())
    report = {**errors, **_tolerance_report(out, manifest)}
    for name, entry in manifest.items():
        for key in ("n_atoms", "total_charge", "builder"):
            if entry[key] != committed[name][key]:
                report.setdefault(name, []).append(f"{key} {entry[key]} != {committed[name][key]}")
    assert set(manifest) | set(errors) == set(committed)
    assert report == {}


def test_committed_files_regenerate_bit_for_bit(fresh_build):
    ref = json.loads((STRUCT_DIR / build.REFERENCE_PLATFORM).read_text())
    here = build.current_platform()
    if here != ref:
        pytest.skip(f"same-platform check: committed bytes were built on {ref['system']} {ref['machine']}, "
                    f"this is {here['system']} {here['machine']}; regeneration is checked to "
                    f"{compare.POSITION_TOL} A by test_committed_files_regenerate_within_tolerance")
    out, manifest, errors = fresh_build
    assert errors == {}
    committed = json.loads((STRUCT_DIR / "manifest.json").read_text())
    for name, entry in manifest.items():
        assert entry["sha256"] == committed[name]["sha256"], name
        assert hashlib.sha256((STRUCT_DIR / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]


def test_reference_platform_record_names_no_machine():
    ref = json.loads((STRUCT_DIR / build.REFERENCE_PLATFORM).read_text())
    assert set(ref) == {"system", "machine"}


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
        if a.info["builder"] == "nacre.structures.hero.build":
            continue  # organic parts: checked through the charge ledger in test_structure_hero.py
        assert a.info["total_charge"] == formal_charge(a.get_chemical_symbols()), name


def test_no_clashes_in_committed(committed):
    for name, a in committed.items():
        assert min_distance(a) >= CLASH_THRESHOLD, name


def _dense_min_distance(atoms, exclude_pairs=None) -> float:
    """The previous dense (n, n, 3) minimum-image routine, kept as the reference."""
    pos = atoms.get_positions()
    n = len(pos)
    if n < 2:
        return float("inf")
    d = pos[:, None, :] - pos[None, :, :]
    if any(atoms.pbc):
        cell = np.asarray(atoms.cell)
        frac = d @ np.linalg.inv(cell)
        for k in range(3):
            if atoms.pbc[k]:
                frac[..., k] -= np.round(frac[..., k])
        d = frac @ cell
    r = np.linalg.norm(d, axis=-1)
    r[np.diag_indices(n)] = np.inf
    if exclude_pairs is not None:
        r[exclude_pairs] = np.inf
    return float(r.min())


def _random_atoms(cell, pbc, n=40, seed=3):
    from ase import Atoms

    rng = np.random.default_rng(seed)
    frac = rng.random((n, 3))
    return Atoms("C" * n, positions=frac @ np.asarray(cell), cell=cell, pbc=pbc)


def test_min_distance_matches_dense_reference_triclinic_periodic():
    cell = [[9.0, 0, 0], [2.5, 8.0, 0], [1.0, 1.5, 10.0]]
    a = _random_atoms(cell, True)
    assert min_distance(a) == pytest.approx(_dense_min_distance(a), abs=1e-9)
    rep = a.repeat((2, 1, 2))
    assert min_distance(rep) == pytest.approx(_dense_min_distance(rep), abs=1e-9)
    assert min_distance(rep) == pytest.approx(min_distance(a), abs=1e-9)


def test_min_distance_matches_dense_reference_non_periodic():
    a = _random_atoms([[12.0, 0, 0], [0, 12.0, 0], [0, 0, 12.0]], False)
    assert min_distance(a) == pytest.approx(_dense_min_distance(a), abs=1e-9)
    rep = a.repeat((2, 1, 1))
    assert min_distance(rep) == pytest.approx(_dense_min_distance(rep), abs=1e-9)
    # Sparse pair far beyond the first cutoff: the search must widen, not return inf.
    from ase import Atoms

    far = Atoms("CC", positions=[[0, 0, 0], [0, 0, 30.0]], pbc=False)
    assert min_distance(far) == pytest.approx(30.0, abs=1e-9)


def test_min_distance_matches_dense_reference_mixed_pbc_and_mask():
    a = _random_atoms([[10.0, 0, 0], [3.0, 9.0, 0], [0, 0, 20.0]], [True, True, False], n=30)
    assert min_distance(a) == pytest.approx(_dense_min_distance(a), abs=1e-9)
    group = np.arange(len(a)) % 2
    mask = group[:, None] == group[None, :]
    assert min_distance(a, exclude_pairs=mask) == pytest.approx(
        _dense_min_distance(a, exclude_pairs=mask), abs=1e-9)


# ---------------------------------------------------------------- machine independence
def test_bytes_do_not_depend_on_xtb_environment(tmp_path, monkeypatch):
    # Two builds on this machine, with and without ~/.nacre-envs/xtb, must give identical bytes;
    # both agree with the committed files to the stated tolerance on any platform. The scene
    # targets of the hero builder only assemble parts built by the builders checked here (their
    # chains come from the conformer record), so they are left out: each takes minutes to build,
    # and test_committed_files_regenerate_* rebuild them once.
    names = [n for n, spec in build.load_config()["targets"].items()
             if spec["builder"] != "hero" and spec.get("write", True)]
    shas = []
    for with_xtb_env in (False, True):
        home = tmp_path / f"home{int(with_xtb_env)}"
        (home / ".nacre-envs" / ("xtb" if with_xtb_env else "other")).mkdir(parents=True)
        monkeypatch.setenv("HOME", str(home))
        out = tmp_path / f"out{int(with_xtb_env)}"
        _, manifest = build.build_all(names, out_dir=out)
        shas.append({n: e["sha256"] for n, e in manifest.items()})
        assert _tolerance_report(out, manifest) == {}
    assert shas[0] == shas[1]


def test_no_machine_dependent_text_in_committed_files():
    import getpass
    import platform
    import re

    forbidden = [str(STRUCT_DIR.parents[1]), str(__import__("pathlib").Path.home()), ".nacre-envs",
                 platform.node(), getpass.getuser(), "xtb"]
    stamp_like = re.compile(r"\b20\d\d-\d\d-\d\d[T ]\d\d:\d\d")
    for name, path in committed_structures().items():
        text = path.read_text()
        for bad in filter(None, forbidden):
            assert bad not in text, (name, bad)
        assert not stamp_like.search(text), name
