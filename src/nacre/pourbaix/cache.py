"""Offline cache of the thermodynamic data used by the Pourbaix and window code.

`python -m nacre.pourbaix.cache fetch` is the only code path that touches the network. It
writes one JSON file per request under results/preprint/pourbaix/cache/, each holding the
request parameters, the retrieval time, the Materials Project database version, the client
library versions and the raw response, plus a manifest with a sha256 per file. Every other
module, and every test, reads these files only.

The Materials Project key is read from .env (MP_API_KEY) at fetch time. It is never printed,
logged or written to the cache.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from nacre.pourbaix.paths import CACHE_DIR, REPO

# Element systems fetched for the aqueous diagram (R-slurry). The ion reference solids add
# their own elements at fetch time, exactly as the Materials Project client does.
SLURRY_ELEMENTS = ["Al", "C", "Ca"]

# Element systems fetched for the Li-referenced window (R-cell). Li-Ca-C-O and Li-Al-O carry
# the lithiation reactions; the others carry the candidate sinks for the oxidation reactions
# (fluorine-free anions: nitrate, sulfate, chloride).
CELL_CHEMSYS = ["Li-Ca-C-O", "Li-Al-O", "Li-Ca-N-O", "Li-Al-N-O", "Li-Ca-S-O", "Li-Al-S-O",
                "Li-Ca-Cl", "Li-Al-Cl"]

# NIST-JANAF thermochemical tables for the gas-phase species of the oxidation reactions.
JANAF = {
    "O2": "https://janaf.nist.gov/tables/O-029.txt",
    "CO2": "https://janaf.nist.gov/tables/C-095.txt",
}

THERMO_TYPES = ["GGA_GGA+U"]
MANIFEST = "manifest.json"
LIBRARIES = ["mp-api", "pymatgen", "emmet-core", "mpcontribs-client", "requests"]


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def library_versions(names=LIBRARIES):
    out = {}
    for n in names:
        try:
            out[n] = version(n)
        except PackageNotFoundError:
            out[n] = None
    return out


def _read_key(env_path):
    """MP_API_KEY from the .env file. The value is returned, never printed."""
    for line in Path(env_path).read_text(encoding="utf-8").splitlines():
        if line.startswith("MP_API_KEY="):
            value = line.split("=", 1)[1].strip()
            if value:
                return value
    raise SystemExit("MP_API_KEY is missing or empty in %s" % env_path)


def _plain(value):
    """Convert an MPContribs datum to plain JSON (value, unit, display)."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump())
    raise TypeError("cannot serialise %r" % type(value))


def _strkeys(obj):
    """Copy of obj with every mapping key turned into a string (Element keys -> symbols)."""
    if isinstance(obj, dict):
        return {str(k): _strkeys(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_strkeys(v) for v in obj]
    return obj


def _entry_dict(entry):
    """as_dict of a computed entry with its free-form `data` keys stringified."""
    entry = entry.copy()
    entry.data = _strkeys(entry.data)
    return entry.as_dict()


def _write(path, payload):
    from monty.json import MontyEncoder

    text = json.dumps(payload, cls=MontyEncoder, indent=1, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def fetch(out_dir=CACHE_DIR, env_path=REPO / ".env"):
    """Fetch every request into out_dir and write the manifest. Network access."""
    import requests
    from mp_api.client import MPRester
    from pymatgen.core.ion import Ion

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    key = _read_key(env_path)
    libs = library_versions()
    files = []

    with MPRester(key) as mpr:
        db_version = mpr.get_database_version()

        def entries(elements, name):
            req = {"method": "MPRester.get_entries_in_chemsys", "elements": sorted(elements),
                   "compatible_only": True, "additional_criteria": {"thermo_types": THERMO_TYPES},
                   "use_gibbs": None}
            got = mpr.get_entries_in_chemsys(sorted(elements), compatible_only=True,
                                             additional_criteria={"thermo_types": THERMO_TYPES})
            got = sorted(got, key=lambda e: (str(e.entry_id), e.energy))
            payload = {"kind": "mp_entries", "request": req, "retrieved_utc": _now(),
                       "mp_database_version": db_version, "client_versions": libs,
                       "n": len(got), "response": [_entry_dict(e) for e in got]}
            sha = _write(out_dir / name, payload)
            files.append({"file": name, "kind": "mp_entries", "request": req, "n": len(got),
                          "retrieved_utc": payload["retrieved_utc"], "sha256": sha})
            print("  %-34s %5d entries" % (name, len(got)))

        # Aqueous ion reference data (MPContribs project ion_ref_data), all records.
        req = {"method": "MPRester.get_ion_reference_data", "project": "ion_ref_data"}
        ions = [{"identifier": d["identifier"], "formula": d["formula"], "data": _plain(d["data"])}
                for d in mpr.get_ion_reference_data()]
        ions.sort(key=lambda d: d["identifier"])
        project = mpr.contribs.get_project("ion_ref_data", fields=["title", "authors", "license",
                                                                    "references"])
        project = {"title": project.get("title"), "authors": project.get("authors"),
                   "license": project.get("license"),
                   "references": [{"label": r.get("label"), "url": r.get("url")}
                                  for r in (project.get("references") or [])]}
        payload = {"kind": "mp_ion_reference_data", "request": req, "retrieved_utc": _now(),
                   "mp_database_version": db_version, "client_versions": libs,
                   "project": project, "n": len(ions), "response": ions}
        sha = _write(out_dir / "mp_ion_reference_data.json", payload)
        files.append({"file": "mp_ion_reference_data.json", "kind": "mp_ion_reference_data",
                      "request": req, "n": len(ions), "retrieved_utc": payload["retrieved_utc"],
                      "sha256": sha})
        print("  %-34s %5d records" % ("mp_ion_reference_data.json", len(ions)))

        # Solid and gas entries for the aqueous diagram, in the element system of the ions'
        # reference solids plus O and H (the client's own construction).
        rel = [d for d in ions if d["data"]["MajElements"] in SLURRY_ELEMENTS]
        ref_elts = {str(el) for d in rel for el in Ion.from_formula(d["data"]["RefSolid"]).elements}
        slurry_elts = sorted(ref_elts | set(SLURRY_ELEMENTS) | {"O", "H"})
        entries(slurry_elts, "mp_entries_slurry_%s.json" % "-".join(slurry_elts))

        for cs in CELL_CHEMSYS:
            entries(cs.split("-"), "mp_entries_cell_%s.json" % cs)

    # NIST-JANAF gas tables.
    for species, url in JANAF.items():
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        name = "janaf_%s.json" % species
        payload = {"kind": "janaf_table", "species": species,
                   "request": {"method": "HTTP GET", "url": url}, "retrieved_utc": _now(),
                   "locator": "NIST-JANAF Thermochemical Tables, table for %s, row T=298.15 K "
                              "and neighbours" % species,
                   "text_sha256": sha256_bytes(r.content), "text": r.text}
        sha = _write(out_dir / name, payload)
        files.append({"file": name, "kind": "janaf_table", "request": payload["request"],
                      "retrieved_utc": payload["retrieved_utc"], "sha256": sha})
        print("  %-34s table" % name)

    manifest = {"mp_database_version": db_version, "client_versions": libs,
                "thermo_types": THERMO_TYPES, "files": files, "written_utc": _now()}
    (out_dir / MANIFEST).write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                                    encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------------- offline API
def manifest(cache_dir=CACHE_DIR):
    return json.loads((Path(cache_dir) / MANIFEST).read_text(encoding="utf-8"))


def verify(cache_dir=CACHE_DIR):
    """Check every manifest file against its sha256. Returns a list of problems."""
    bad = []
    for f in manifest(cache_dir)["files"]:
        p = Path(cache_dir) / f["file"]
        if not p.is_file():
            bad.append("missing " + f["file"])
        elif sha256_bytes(p.read_bytes()) != f["sha256"]:
            bad.append("hash mismatch " + f["file"])
    return bad


def cache_hash(cache_dir=CACHE_DIR):
    """sha256 over the manifest bytes; it pins every cached file through their hashes."""
    return sha256_bytes((Path(cache_dir) / MANIFEST).read_bytes())


def load(name, cache_dir=CACHE_DIR):
    return json.loads((Path(cache_dir) / name).read_text(encoding="utf-8"))


def load_entries(name, cache_dir=CACHE_DIR):
    """ComputedStructureEntry objects from one cached entries file."""
    from pymatgen.entries.computed_entries import ComputedStructureEntry

    return [ComputedStructureEntry.from_dict(d) for d in load(name, cache_dir)["response"]]


def files_of_kind(kind, cache_dir=CACHE_DIR):
    return [f["file"] for f in manifest(cache_dir)["files"] if f["kind"] == kind]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.cache")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fetch the Materials Project and JANAF data (network)")
    f.add_argument("--out", default=str(CACHE_DIR))
    sub.add_parser("verify", help="check cached files against the manifest")
    args = ap.parse_args(argv)
    if args.cmd == "fetch":
        m = fetch(Path(args.out))
        print("database version %s, %d files" % (m["mp_database_version"], len(m["files"])))
        return 0
    bad = verify()
    print("cache OK" if not bad else "\n".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
