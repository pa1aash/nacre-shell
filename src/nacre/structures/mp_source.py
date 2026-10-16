"""Fetch bulk crystal structures from the Materials Project and cache them in the repository.

The cached record (``structures/preprint/sources/<name>.json``) keeps the material id,
the database version and the query, so builders run offline and stay reproducible.
The API key is read from ``.env`` (``MP_API_KEY``) and never printed or written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

from nacre.structures.meta import REPO_ROOT, SOURCE_DIR, library_versions

CORUNDUM = {
    "name": "al2o3_corundum",
    "formula": "Al2O3",
    "spacegroup_number": 167,
    "pick": "lowest energy_above_hull",
}


def _api_key() -> str:
    key = os.environ.get("MP_API_KEY")
    if not key:
        env = REPO_ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("MP_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        raise SystemExit("MP_API_KEY is not set in the environment or .env")
    return key


def fetch(query=CORUNDUM) -> dict:
    from mp_api.client import MPRester

    with MPRester(_api_key(), mute_progress_bars=True) as mpr:
        db_version = mpr.db_version
        docs = mpr.materials.summary.search(
            formula=query["formula"],
            spacegroup_number=query["spacegroup_number"],
            fields=["material_id", "structure", "energy_above_hull", "symmetry"],
        )
    if not docs:
        raise SystemExit("no Materials Project record matched the query")
    doc = min(docs, key=lambda d: d.energy_above_hull)
    structure = doc.structure.as_dict()
    payload = json.dumps(structure, sort_keys=True)
    return {
        "name": query["name"],
        "source": "Materials Project API (summary endpoint)",
        "material_id": str(doc.material_id),
        "database_version": db_version,
        "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query": query,
        "candidates": sorted(str(d.material_id) for d in docs),
        "energy_above_hull_eV_per_atom": doc.energy_above_hull,
        "spacegroup_symbol": doc.symmetry.symbol if doc.symmetry else None,
        "client_versions": library_versions(("mp-api", "pymatgen", "emmet-core")),
        "structure_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "structure": structure,
    }


def cached_path(name=CORUNDUM["name"]):
    return SOURCE_DIR / f"{name}.json"


def load(name=CORUNDUM["name"]) -> dict:
    path = cached_path(name)
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run python -m nacre.structures.mp_source --fetch")
    record = json.loads(path.read_text())
    payload = json.dumps(record["structure"], sort_keys=True)
    if hashlib.sha256(payload.encode()).hexdigest() != record["structure_sha256"]:
        raise ValueError(f"{path}: structure sha256 mismatch")
    return record


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help="query the API and overwrite the cache")
    args = ap.parse_args(argv)
    if not args.fetch:
        rec = load()
        print(f"cached {rec['material_id']} (database {rec['database_version']})")
        return
    rec = fetch()
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    cached_path(rec["name"]).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(f"fetched {rec['material_id']} (database {rec['database_version']}, "
          f"candidates {rec['candidates']}, e_hull {rec['energy_above_hull_eV_per_atom']})")


if __name__ == "__main__":
    main()
