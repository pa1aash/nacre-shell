"""Drawing parameters taken from lane p0-w1's evidence table, by row_id (fetched, never typed).

``python -m nacre.structures.evidence --fetch`` reads ``lit/evidence_table.csv`` from the
lane branch ``origin/preprint/p0-w1`` with ``git show`` (run ``git fetch origin`` first),
keeps the rows of the quantities below verbatim, and writes
``structures/preprint/sources/ca_hydration_w1.json`` with the commit and blob it read.
Builders read that record offline.

Ca2+ first hydration shell (``hydration_geometry``):

- primary row: among the ``ca_hydration_number`` rows with a numeric value read from
  the full text, the best grade (A before B before C before D); ties keep table order;
- coordination number: that row's value, rounded to the nearest integer (a drawn shell
  has whole molecules);
- Ca-O distance: the Ca-Ow distance printed in the same row (its notes, "Ca-Ow <d> A"),
  so both numbers come from one source and one method;
- every other ``ca_hydration_number`` row is kept as context, and the drawn coordination
  number must lie inside any experimental range among them.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess

from nacre.structures.meta import REPO_ROOT, SOURCE_DIR

REF = "origin/preprint/p0-w1"
TABLE = "lit/evidence_table.csv"
QUANTITIES = ("ca_hydration_number",)
RECORD = SOURCE_DIR / "ca_hydration_w1.json"
GRADES = "ABCD"
_CA_OW = re.compile(r"Ca-Ow\s+([0-9]+(?:\.[0-9]+)?)\s*A\b")
_RANGE = re.compile(r"^\s*([0-9.]+)\s*\.\.\s*([0-9.]+)\s*$")


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True,
                          text=True).stdout


def fetch(ref=REF) -> dict:
    commit = _git("rev-parse", ref).strip()
    blob = _git("rev-parse", f"{commit}:{TABLE}").strip()
    rows = [r for r in csv.DictReader(io.StringIO(_git("show", f"{commit}:{TABLE}")))
            if r["quantity"] in QUANTITIES]
    if not rows:
        raise SystemExit(f"no rows of {QUANTITIES} in {ref}:{TABLE}")
    return {"source": f"lane p0-w1 {TABLE}", "ref": ref, "commit": commit, "blob": blob,
            "quantities": list(QUANTITIES), "rows": rows}


def load(path=RECORD) -> dict:
    return json.loads(path.read_text())


def _numeric(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def hydration_geometry(record=None) -> dict:
    """Coordination number and Ca-O distance of the drawn Ca2+ shell, with their row_ids."""
    rec = load() if record is None else record
    rows = [r for r in rec["rows"] if r["quantity"] == "ca_hydration_number"]
    usable = [r for r in rows if _numeric(r["value"]) is not None and r["extraction_route"] == "full text"]
    if not usable:
        raise ValueError("no full-text numeric ca_hydration_number row")
    primary = min(usable, key=lambda r: GRADES.index(r["grade"]))
    m = _CA_OW.search(primary["notes"])
    if not m:
        raise ValueError(f"{primary['row_id']}: no Ca-Ow distance printed in the row")
    cn = int(round(float(primary["value"])))
    for r in rows:
        rng = _RANGE.match(r["range_or_uncertainty"] or "")
        if r is not primary and _numeric(r["value"]) is None and rng:
            lo, hi = float(rng.group(1)), float(rng.group(2))
            if not lo <= cn <= hi:
                raise ValueError(f"drawn CN {cn} outside {r['row_id']} range {lo}..{hi}")
    return {
        "cn": cn,
        "r_ca_o": float(m.group(1)),
        "row_ids": {"cn": primary["row_id"], "r_ca_o": primary["row_id"]},
        "context_row_ids": [r["row_id"] for r in rows if r is not primary],
        "evidence_commit": rec["commit"],
        "rule": "best-grade full-text ca_hydration_number row; CN rounded to an integer; "
                "Ca-O is the Ca-Ow distance printed in the same row",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help=f"read {REF}:{TABLE} and rewrite the record")
    args = ap.parse_args(argv)
    if args.fetch:
        rec = fetch()
        RECORD.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
        print(f"recorded {[r['row_id'] for r in rec['rows']]} from {rec['ref']} at {rec['commit'][:10]}")
    g = hydration_geometry()
    print(f"Ca2+ shell: CN {g['cn']}, Ca-O {g['r_ca_o']} A (rows {g['row_ids']}, context {g['context_row_ids']})")


if __name__ == "__main__":
    main()
