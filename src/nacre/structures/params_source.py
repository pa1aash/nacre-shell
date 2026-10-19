"""Drawing parameters taken from lane p0-w1's parameter table, by key (fetched, never typed).

``python -m nacre.structures.params_source --fetch`` reads ``lit/params.yaml`` from the
lane branch ``origin/preprint/p0-w1`` with ``git show`` (run ``git fetch origin`` first),
keeps the entries of the keys below verbatim, and writes
``structures/preprint/sources/params_w1.json`` with the commit and blob it read.
Builders read that record offline.

Amorphous CaCO3 nucleus (``acc_geometry``):

- packing: ``v_m_acc``, the molar volume per CaCO3 formula unit (structural water
  included), sets the number of formula units per volume, N_A / V_m. ``rho_acc`` (same
  paper, mass density with the structural water) is kept as the cross-check: the two
  must agree for the hydration states the rows name;
- carbonate C-O: ``c_o_bond_length_acc``, the key W1 sourced for the ACC framing.

The structural water of ACC is not drawn (the nucleus is drawn anhydrous); that is a
flagged drawing choice, recorded by the builders that use this geometry.
"""
from __future__ import annotations

import argparse
import json
import subprocess

import yaml

from nacre.structures.meta import REPO_ROOT, SOURCE_DIR

REF = "origin/preprint/p0-w1"
TABLE = "lit/params.yaml"
KEYS = ("v_m_acc", "rho_acc", "c_o_bond_length_acc")
RECORD = SOURCE_DIR / "params_w1.json"
AVOGADRO = 6.02214076e23
M_CACO3 = 100.0869  # g/mol, used only for the rho_acc cross-check
M_H2O = 18.0153


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True,
                          text=True).stdout


def fetch(ref=REF) -> dict:
    commit = _git("rev-parse", ref).strip()
    blob = _git("rev-parse", f"{commit}:{TABLE}").strip()
    doc = yaml.safe_load(_git("show", f"{commit}:{TABLE}"))
    table = doc.get("params", doc)
    missing = [k for k in KEYS if k not in table]
    if missing:
        raise SystemExit(f"keys {missing} not in {ref}:{TABLE}")
    return {"source": f"lane p0-w1 {TABLE}", "ref": ref, "commit": commit, "blob": blob,
            "keys": {k: table[k] for k in KEYS}}


def load(path=RECORD) -> dict:
    return json.loads(path.read_text())


def acc_geometry(record=None) -> dict:
    """Formula units per cubic angstrom and the C-O length of the drawn ACC, with their keys."""
    rec = load() if record is None else record
    v_m = rec["keys"]["v_m_acc"]
    rho = rec["keys"]["rho_acc"]
    d_co = rec["keys"]["c_o_bond_length_acc"]
    if v_m["unit"] != "m^3 mol^-1" or rho["unit"] != "kg m^-3" or d_co["unit"] != "m":
        raise ValueError("unexpected units in the params record")
    fu_per_a3 = AVOGADRO / (float(v_m["value"]) * 1e30)
    # Cross-check: rho over V_m per formula unit spans the hydration states of the rows
    # (CaCO3.nH2O, n from 0.5 to 1.1), so the implied mass per formula unit must too.
    mass = float(rho["value"]) * 1e3 * float(v_m["value"])  # g/mol per formula unit
    lo, hi = M_CACO3 + 0.4 * M_H2O, M_CACO3 + 1.2 * M_H2O
    if not lo <= mass <= hi:
        raise ValueError(f"rho_acc and v_m_acc disagree: {mass:.1f} g/mol per formula unit")
    return {
        "fu_per_a3": fu_per_a3,
        "r_co": float(d_co["value"]) * 1e10,
        "keys": {"packing": "v_m_acc", "packing_check": "rho_acc", "r_co": "c_o_bond_length_acc"},
        "sources": {k: list(rec["keys"][k]["sources"]) for k in KEYS},
        "params_commit": rec["commit"],
        "rule": "formula units per volume = N_A / v_m_acc (structural water included in V_m, not drawn); "
                "C-O = c_o_bond_length_acc value",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help=f"read {REF}:{TABLE} and rewrite the record")
    args = ap.parse_args(argv)
    if args.fetch:
        rec = fetch()
        RECORD.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
        print(f"recorded {list(rec['keys'])} from {rec['ref']} at {rec['commit'][:10]}")
    g = acc_geometry()
    print(f"ACC: {g['fu_per_a3']:.5f} formula units per A^3, C-O {g['r_co']:.4f} A ({g['keys']})")


if __name__ == "__main__":
    main()
