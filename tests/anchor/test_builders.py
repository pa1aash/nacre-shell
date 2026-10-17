"""Anchor builders: charge, atom counts, numerical hygiene and seed determinism."""
import json
import math

import numpy as np
import pytest
from scipy import constants

from nacre.anchor import build, builders as b, cycle

# Numerical hygiene, not physical contact distances: no two atoms may overlap (0.8 A), and
# atoms of different fragments (ligand, Ca, each water) must not interpenetrate (1.5 A).
MIN_ANY_A = 0.8
MIN_INTERFRAGMENT_A = 1.5

LIGAND_ATOMS = {"catecholate_monoanion": {"C": 6, "H": 5, "O": 2},
                "catecholate_dianion": {"C": 6, "H": 4, "O": 2},
                "acetate": {"C": 2, "H": 3, "O": 2}}


@pytest.fixture(scope="module")
def species():
    return {s.name: s for s in b.all_species(seed=7)}


def _count(st):
    from collections import Counter

    return Counter(st.symbols)


def test_every_species_is_built(species):
    expected = {"Ca_catecholate_monoanion_bidentate_w4", "Ca_catecholate_dianion_bidentate_w4",
                "Ca_acetate_monodentate_w5", "Ca_acetate_bidentate_w4", "Ca_aqua_w6",
                "ligand_catecholate_monoanion", "ligand_catecholate_dianion", "ligand_acetate",
                "water_w1", "water_w2"}
    assert set(species) == expected


def test_charge_and_atom_counts(species):
    for st in species.values():
        c = _count(st)
        meta = st.meta
        nw = meta["n_water"]
        if meta["kind"] == "complex":
            lig = LIGAND_ATOMS[meta["ligand"]]
            assert c["Ca"] == 1
            for el, k in lig.items():
                assert c[el] == k + {"H": 2 * nw, "O": nw}.get(el, 0), (st.name, el)
            assert st.charge == 2 + b.LIGANDS[meta["ligand"]][1]
        elif meta["role"] == "hydrated Ca2+ cluster":
            assert c == {"Ca": 1, "O": nw, "H": 2 * nw} and st.charge == 2
        elif meta["role"] == "free ligand":
            assert dict(c) == LIGAND_ATOMS[meta["ligand"]]
            assert st.charge == b.LIGANDS[meta["ligand"]][1]
        else:
            assert c == {"O": nw, "H": 2 * nw} and st.charge == 0
        assert st.multiplicity == 1
        assert len(st.symbols) == len(st.coords) == len(st.fragments)


def test_no_clashes(species):
    for st in species.values():
        any_min, inter_min = b.min_distances(st)
        assert any_min >= MIN_ANY_A, (st.name, any_min)
        assert inter_min >= MIN_INTERFRAGMENT_A, (st.name, inter_min)


def test_binding_mode_geometry(species):
    d0 = b.ca_o_distance()
    for st in species.values():
        if st.meta.get("kind") != "complex":
            continue
        x = np.asarray(st.coords)
        ca = st.symbols.index("Ca")
        lig_o = [i for i, (s, f) in enumerate(zip(st.symbols, st.fragments)) if s == "O" and f == 0]
        d = sorted(float(np.linalg.norm(x[i] - x[ca])) for i in lig_o)
        bound = [v for v in d if abs(v - d0) < 1e-6]
        assert len(bound) == st.meta["denticity"], (st.name, d)
        waters = [i for i, (s, f) in enumerate(zip(st.symbols, st.fragments)) if s == "O" and f >= 2]
        assert len(waters) == st.meta["n_water"]
        for i in waters:
            assert np.linalg.norm(x[i] - x[ca]) == pytest.approx(d0, abs=1e-9)


def test_fixed_seed_gives_identical_geometry():
    a = b.all_species(seed=11)
    c = b.all_species(seed=11)
    for s1, s2 in zip(a, c):
        assert s1.symbols == s2.symbols
        assert np.array_equal(np.asarray(s1.coords), np.asarray(s2.coords)), s1.name


def test_different_seed_changes_the_waters():
    a = {s.name: s for s in b.all_species(seed=7)}
    c = {s.name: s for s in b.all_species(seed=8)}
    assert not np.allclose(np.asarray(a["Ca_aqua_w6"].coords), np.asarray(c["Ca_aqua_w6"].coords))


# Ligand and water coordinates come from the conformer record, so no force field runs at build
# time and the remaining numpy steps agree across platforms far below this; D12's 1e-3 A is kept
# (lane note N19 allows up to 1e-2 A).
COORD_TOL_A = 1e-3


def _parse_xyz(text):
    """(symbols, coordinates) of an xyz file; the comment line is not compared."""
    lines = text.splitlines()
    n = int(lines[0])
    rows = [ln.split() for ln in lines[2:2 + n]]
    return [r[0] for r in rows], np.array([[float(v) for v in r[1:4]] for r in rows])


def test_committed_structures_match_a_fresh_build(species):
    idx = json.loads((build.OUT / "index.json").read_text(encoding="utf-8"))
    assert idx["builder_version"] == b.BUILDER_VERSION
    names = {s["name"] for s in idx["species"]}
    assert names == set(species)
    for name, st in species.items():
        on_disk = _parse_xyz((build.OUT / (name + ".xyz")).read_text(encoding="utf-8"))
        fresh = _parse_xyz(st.xyz())
        assert on_disk[0] == fresh[0], name                 # species and order are exact
        assert len(on_disk[1]) == len(fresh[1]), name       # so are the counts
        assert np.allclose(on_disk[1], fresh[1], rtol=0.0, atol=COORD_TOL_A), name
        meta = json.loads((build.OUT / (name + ".json")).read_text(encoding="utf-8"))
        for key in ("charge", "multiplicity", "coordination_mode", "n_water", "seed", "builder_version"):
            assert key in meta


def test_parameterised_water_count():
    st = b.complex_structure("acetate", "bidentate", 3, seed=7)
    assert _count(st)["O"] == 2 + 3 and st.meta["n_water"] == 3
    assert b.min_distances(st)[1] >= MIN_INTERFRAGMENT_A


def test_standard_state_correction_formula():
    T = 298.15
    expected = constants.R * T * math.log(1000.0 * constants.R * T / constants.atm)
    assert cycle.standard_state_correction(T) == pytest.approx(expected)
    assert cycle.standard_state_correction(T) > 0
    # bidentate, released waters as one cluster: 2 reactants -> complex + cluster
    assert cycle.net_standard_state_correction(T, 6, 4, "cluster") == pytest.approx(0.0)
    assert cycle.net_standard_state_correction(T, 6, 4, "monomers") == pytest.approx(expected)
    with pytest.raises(ValueError):
        cycle.stoichiometry(4, 6, "cluster")


def test_build_reads_the_conformer_record_and_never_embeds(monkeypatch):
    """Embedding is platform-dependent (lane note N19); building must not call it."""
    def refuse(*a, **k):
        raise AssertionError("embed called at build time")

    monkeypatch.setattr(b, "embed", refuse)
    monkeypatch.setattr(b, "_WATER", None)
    assert len(b.all_species(seed=7)) == 10


def test_conformer_record_matches_its_smiles_and_canonical_order():
    from rdkit import Chem

    rec = b.load_record()
    assert {"%s_seed7" % k for k in b.LIGANDS} | {"water_seed0"} <= set(rec)
    for key, e in rec.items():
        mol = Chem.AddHs(Chem.MolFromSmiles(e["smiles"]))
        assert Chem.MolToInchiKey(mol) == e["inchikey"], key
        ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=True))
        canon = [mol.GetAtomWithIdx(i).GetSymbol() for i in sorted(range(mol.GetNumAtoms()), key=lambda i: ranks[i])]
        assert canon == e["symbols"], key
        assert len(e["positions"]) == len(e["symbols"])


def test_missing_conformer_is_an_error_not_a_fresh_embedding():
    with pytest.raises(LookupError, match="--generate"):
        b.conformer("acetate", 12345)
