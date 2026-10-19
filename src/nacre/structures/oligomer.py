"""A generic catechol-bearing oligomer standing in for the polydopamine-type layer.

The true structure of polydopamine-type material is debated, so the drawing uses a
generic chain: ``n_units`` 5,6-dihydroxyindole units (catechol form) joined 2-7'.
The geometry comes from RDKit ETKDG embedding (seeded) and MMFF94 relaxation.

Conformer record. ETKDG embedding is not reproducible across platforms: the same seed
and RDKit version give a different conformer on Linux than on macOS (1.3 A apart, MMFF
energies 39.5 and 44.5 kcal/mol for the four-unit chain). The conformer is therefore
generated once and kept in ``structures/preprint/sources/oligomer_conformers.json``,
keyed by its parameters and seed, with the platform it was generated on; ``build``
reads that record, so the committed files are the same on every platform. Regenerate
the record with ``python -m nacre.structures.oligomer --generate`` (all oligomer targets
of build.yaml); ``generate`` gives a fresh conformer without touching the record.

Each atom carries ``catechol``: the unit index (0 at the chain end listed first in the
SMILES, the anchoring end) for the two catechol O of a unit and their H, -1 otherwise.

End group. With ``end_group: COOH`` the free C2 of the last unit carries a carboxylic
acid (a 5,6-dihydroxyindole-2-carboxylic acid end unit, as in polydopamine- and
eumelanin-type material), the carboxylate site of Figure 2b. Such a chain also carries
``carboxyl``: 0 for the two carboxyl O and the acid H, -1 otherwise. Without the
parameter the chain, its conformer key and its arrays are unchanged.

No semi-empirical refinement is applied: the output must not depend on which software
is installed on the machine. If a refinement step is added, it is requested explicitly
through a parameter and the file records that it was applied and the pinned tool
version; tool availability is never written to a structure file.
"""
from __future__ import annotations

import argparse
import json
import platform

import numpy as np

from nacre.structures.meta import SOURCE_DIR, library_versions, stamp

DEFAULTS = {"n_units": 4, "force_field": "MMFF94", "ff_max_iters": 5000}

CONFORMERS = SOURCE_DIR / "oligomer_conformers.json"


END_GROUPS = {None: "", "COOH": "(C(=O)O)"}


def _rc(k: int) -> str:
    """SMILES ring-closure label: digits below 10, %nn from 10 on."""
    return str(k) if k < 10 else f"%{k}"


def dhi_chain_smiles(n_units: int, end_group=None) -> str:
    """SMILES of n 5,6-dihydroxyindole units linked C2 -> C7' (catechol form).

    ``end_group`` "COOH" puts a carboxylic acid on the free C2 of the last unit.
    """
    if n_units < 1:
        raise ValueError("n_units must be at least 1")
    if end_group not in END_GROUPS:
        raise ValueError(f"end_group must be one of {sorted(k for k in END_GROUPS if k)}")
    end = END_GROUPS[end_group]
    a, b = _rc(2 * (n_units - 1) + 1), _rc(2 * (n_units - 1) + 2)
    # Last unit, entered through its C7 (or the whole molecule when n_units == 1).
    if n_units == 1:
        return f"Oc1cc2cc{end}[nH]c2cc1O"
    smi = f"c{a}c(O)c(O)cc{b}cc{end}[nH]c{a}{b}"
    for k in range(n_units - 2, 0, -1):
        a, b = _rc(2 * k + 1), _rc(2 * k + 2)
        smi = f"c{a}c(O)c(O)cc{b}cc(-{smi})[nH]c{a}{b}"
    return f"Oc1cc2cc(-{smi})[nH]c2cc1O"


def conformer_key(params, seed) -> str:
    p = {**DEFAULTS, **(params or {})}
    end = f"_{p['end_group'].lower()}" if p.get("end_group") else ""
    return f"n{int(p['n_units'])}{end}_{p['force_field']}_it{int(p['ff_max_iters'])}_seed{int(seed)}"


def _catechol_units(mol):
    """Per-atom unit index of catechol O and their H (-1 elsewhere), unit 0 holding atom 0."""
    from rdkit import Chem

    pairs = mol.GetSubstructMatches(Chem.MolFromSmarts("[OX2H]c:c[OX2H]"))
    dist = Chem.GetDistanceMatrix(mol)
    pairs = sorted(((m[0], m[3]) for m in pairs), key=lambda pr: min(dist[0, pr[0]], dist[0, pr[1]]))
    unit = np.full(mol.GetNumAtoms(), -1, dtype=int)
    for k, (o1, o2) in enumerate(pairs):
        for o in (o1, o2):
            unit[o] = k
            for nb in mol.GetAtomWithIdx(o).GetNeighbors():
                if nb.GetSymbol() == "H":
                    unit[nb.GetIdx()] = k
    return unit


def _carboxyl_atoms(mol):
    """Per-atom 0 for the carboxyl O pair and the acid H, -1 elsewhere."""
    from rdkit import Chem

    mark = np.full(mol.GetNumAtoms(), -1, dtype=int)
    for _, o1, o2 in mol.GetSubstructMatches(Chem.MolFromSmarts("C(=O)[OX2H]")):
        for o in (o1, o2):
            mark[o] = 0
            for nb in mol.GetAtomWithIdx(o).GetNeighbors():
                if nb.GetSymbol() == "H":
                    mark[nb.GetIdx()] = 0
    return mark


def generate(params=None, seed=0) -> dict:
    """Embed and relax a fresh conformer (platform-dependent; see the module docstring)."""
    from rdkit import Chem
    from rdkit.Chem import AllChem

    p = {**DEFAULTS, **(params or {})}
    smiles = dhi_chain_smiles(int(p["n_units"]), p.get("end_group"))
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    ep = AllChem.ETKDGv3()
    ep.randomSeed = int(seed)
    ep.numThreads = 1
    if AllChem.EmbedMolecule(mol, ep) != 0:
        raise RuntimeError("ETKDG embedding failed")
    props = AllChem.MMFFGetMoleculeProperties(mol, mmffVariant=p["force_field"])
    ff = AllChem.MMFFGetMoleculeForceField(mol, props)
    converged = ff.Minimize(maxIts=int(p["ff_max_iters"])) == 0
    pos = mol.GetConformer().GetPositions()
    pos = np.round(pos - pos.mean(axis=0), 6) + 0.0
    extra = {"carboxyl": _carboxyl_atoms(mol).tolist()} if p.get("end_group") == "COOH" else {}
    return {
        **extra,
        "key": conformer_key(p, seed),
        "params": p,
        "seed": int(seed),
        "smiles": smiles,
        "inchikey": Chem.MolToInchiKey(Chem.RemoveHs(mol)),
        "symbols": [a.GetSymbol() for a in mol.GetAtoms()],
        "positions": pos.tolist(),
        "catechol": _catechol_units(mol).tolist(),
        "formal_charge": int(sum(a.GetFormalCharge() for a in mol.GetAtoms())),
        "ff_converged": bool(converged),
        "ff_energy_kcal_mol": round(float(ff.CalcEnergy()), 4),
        "generated_on": {"system": platform.system(), "machine": platform.machine()},
        "library_versions": library_versions(("rdkit", "numpy")),
    }


def load_record(path=CONFORMERS) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def to_atoms(rec):
    from ase import Atoms

    atoms = Atoms(symbols=rec["symbols"], positions=np.array(rec["positions"], dtype=float), pbc=False)
    atoms.new_array("catechol", np.array(rec["catechol"], dtype=int))
    if "carboxyl" in rec:
        atoms.new_array("carboxyl", np.array(rec["carboxyl"], dtype=int))
    return atoms


def build(params=None, seed=0, record=None):
    """The oligomer from the conformer record (raises if the record has no entry)."""
    p = {**DEFAULTS, **(params or {})}
    key = conformer_key(p, seed)
    rec = (load_record() if record is None else record).get(key)
    if rec is None:
        raise LookupError(f"no conformer {key} in {CONFORMERS.name}; "
                          "run python -m nacre.structures.oligomer --generate")
    atoms = to_atoms(rec)
    stamp(
        atoms,
        builder="nacre.structures.oligomer.build",
        params={**p, "smiles": rec["smiles"]},
        seed=seed,
        source_ids={"conformer_record": CONFORMERS.name, "conformer": key,
                    "generated_on": rec["generated_on"]},
        total_charge=rec["formal_charge"],
        notes="generic catechol-bearing oligomer (5,6-dihydroxyindole chain, 2-7' links) "
        "drawn for a polydopamine-type layer whose true structure is debated",
    )
    atoms.info["smiles"] = rec["smiles"]
    atoms.info["inchikey"] = rec["inchikey"]
    atoms.info["ff_converged"] = rec["ff_converged"]
    atoms.info["ff_energy_kcal_mol"] = rec["ff_energy_kcal_mol"]
    return atoms


def main(argv=None):
    from nacre.structures import build as build_mod

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--generate", action="store_true",
                    help="regenerate the conformer of every oligomer target in build.yaml")
    args = ap.parse_args(argv)
    targets = [s for s in build_mod.load_config()["targets"].values() if s["builder"] == "oligomer"]
    if not args.generate:
        rec = load_record()
        for spec in targets:
            key = conformer_key(spec.get("params"), spec.get("seed", 0))
            print(f"{key}: {'recorded' if key in rec else 'MISSING'}")
        return
    rec = {}
    for spec in targets:
        entry = generate(spec.get("params"), spec.get("seed", 0))
        rec[entry["key"]] = entry
        print(f"{entry['key']}: MMFF {entry['ff_energy_kcal_mol']} kcal/mol, converged {entry['ff_converged']}")
    CONFORMERS.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
