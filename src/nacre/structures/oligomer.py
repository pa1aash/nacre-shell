"""A generic catechol-bearing oligomer standing in for the polydopamine-type layer.

The true structure of polydopamine-type material is debated, so the drawing uses a
generic chain: ``n_units`` 5,6-dihydroxyindole units (catechol form) joined 2-7'.
The geometry comes from RDKit ETKDG embedding (seeded) and MMFF94 relaxation.
Semi-empirical refinement is applied only if the local environment
``~/.nacre-envs/xtb`` already exists; it is never created here.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from nacre.structures.meta import stamp

DEFAULTS = {"n_units": 4, "force_field": "MMFF94", "ff_max_iters": 5000}

XTB_ENV = Path.home() / ".nacre-envs" / "xtb"


def dhi_chain_smiles(n_units: int) -> str:
    """SMILES of n 5,6-dihydroxyindole units linked C2 -> C7' (catechol form)."""
    if n_units < 1:
        raise ValueError("n_units must be at least 1")
    a, b = 2 * (n_units - 1) + 1, 2 * (n_units - 1) + 2
    # Last unit, entered through its C7 (or the whole molecule when n_units == 1).
    if n_units == 1:
        return "Oc1cc2cc[nH]c2cc1O"
    smi = f"c{a}c(O)c(O)cc{b}cc[nH]c{a}{b}"
    for k in range(n_units - 2, 0, -1):
        a, b = 2 * k + 1, 2 * k + 2
        smi = f"c{a}c(O)c(O)cc{b}cc(-{smi})[nH]c{a}{b}"
    return f"Oc1cc2cc(-{smi})[nH]c2cc1O"


def build(params=None, seed=0):
    from ase import Atoms
    from rdkit import Chem
    from rdkit.Chem import AllChem

    p = {**DEFAULTS, **(params or {})}
    smiles = dhi_chain_smiles(int(p["n_units"]))
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
    pos -= pos.mean(axis=0)
    symbols = [a.GetSymbol() for a in mol.GetAtoms()]
    atoms = Atoms(symbols=symbols, positions=pos, pbc=False)
    charge = sum(a.GetFormalCharge() for a in mol.GetAtoms())
    xtb = "not run: ~/.nacre-envs/xtb absent" if not XTB_ENV.exists() else "available, not applied on day 1"
    stamp(
        atoms,
        builder="nacre.structures.oligomer.build",
        params={**p, "smiles": smiles},
        seed=seed,
        total_charge=charge,
        notes="generic catechol-bearing oligomer (5,6-dihydroxyindole chain, 2-7' links) "
        "drawn for a polydopamine-type layer whose true structure is debated",
    )
    atoms.info["smiles"] = smiles
    atoms.info["inchikey"] = Chem.MolToInchiKey(Chem.RemoveHs(mol))
    atoms.info["ff_converged"] = bool(converged)
    atoms.info["ff_energy_kcal_mol"] = round(float(ff.CalcEnergy()), 4)
    atoms.info["xtb_refinement"] = xtb
    return atoms
