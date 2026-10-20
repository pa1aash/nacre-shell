"""Materials Project entries of the phosphate and silicate systems (P0-W5 PH-K1), kept apart from the
production and supplement caches.

Raw entries stay under .local/w5/cache_ph/ (Materials Project terms); the committed manifest in
results/preprint/pourbaix/ph_k1/cache/ records each file by request, size and sha256. Only BY-C
entries are admitted into any computation; the licence tag of every entry is checked at load.

    uv run python -m nacre.pourbaix.ph_cache fetch
    uv run python -m nacre.pourbaix.ph_cache verify

The Materials Project key is read from .env at fetch time and is never printed, logged or written.
"""
import argparse
import json
import sys

from nacre.pourbaix import cache
from nacre.pourbaix.paths import POURBAIX_RESULTS, REPO

PH_DIR = POURBAIX_RESULTS / "ph_k1"
PH_CACHE = PH_DIR / "cache"
LOCAL_CACHE = REPO / ".local" / "w5" / "cache_ph"
MANIFEST = "manifest.json"
SESSION = "PH-K1"
# NIST-JANAF tables (ids from the formula index, header checked): the silica residue of the silicate comparators.
JANAF_PH = {"SiO2": "https://janaf.nist.gov/tables/O-037.txt"}
JANAF_HEADER = {"SiO2": "Quartz"}
CHEMSYS = ["Li-Ca-P-O-H", "Li-Al-P-O", "Li-Ca-Si-O", "Li-Cl-O"]


def manifest(cache_dir=PH_CACHE):
    p = cache_dir / MANIFEST
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def fetch(env_path=REPO / ".env"):
    from mp_api.client import MPRester

    PH_CACHE.mkdir(parents=True, exist_ok=True)
    LOCAL_CACHE.mkdir(parents=True, exist_ok=True)
    prod = cache.manifest()
    man = manifest() or {"session": SESSION, "mp_database_version": None,
                         "thermo_types": cache.THERMO_TYPES, "files": [],
                         "note": "additive PH-K1 cache from the database version named here, which is newer than the "
                                 "production cache's; the two are never pooled in one energy book"}
    have = {f["file"] for f in man["files"]}
    libs = cache.library_versions()
    todo = [cs for cs in CHEMSYS if "mp_entries_ph_%s.json" % cs not in have]
    if todo:
        key = cache._read_key(env_path)
        with MPRester(key) as mpr:
            db_version = mpr.db_version
            if man.get("mp_database_version") not in (None, db_version):
                raise SystemExit("database version %s differs from this cache's %s; not mixing versions"
                                 % (db_version, man["mp_database_version"]))
            man["mp_database_version"] = db_version
            man["production_cache_database_version"] = prod["mp_database_version"]
            for cs in todo:
                elements = sorted(cs.split("-"))
                req = {"method": "MPRester.get_entries_in_chemsys", "elements": elements, "compatible_only": True,
                       "additional_criteria": {"thermo_types": cache.THERMO_TYPES}, "use_gibbs": None}
                got = mpr.get_entries_in_chemsys(elements, compatible_only=True,
                                                 additional_criteria={"thermo_types": cache.THERMO_TYPES})
                got = sorted(got, key=lambda e: (str(e.entry_id), e.energy))
                name = "mp_entries_ph_%s.json" % cs
                payload = {"kind": "mp_entries", "request": req, "retrieved_utc": cache._now(),
                           "mp_database_version": db_version, "client_versions": libs,
                           "n": len(got), "response": [cache._entry_dict(e) for e in got]}
                sha = cache._write(LOCAL_CACHE / name, payload)
                licences = sorted({str((e.data or {}).get("license")) for e in got})
                n_ok = sum(1 for e in got if (e.data or {}).get("license") in cache.ADMITTED_LICENCES)
                man["files"].append({"file": name, "kind": "mp_entries", "request": req, "n": len(got),
                                     "n_admitted_by_c": n_ok, "retrieved_utc": payload["retrieved_utc"],
                                     "sha256": sha, "bytes": (LOCAL_CACHE / name).stat().st_size,
                                     "licences": licences, "local_only": True,
                                     "location": ".local/w5/cache_ph/" + name, "added_by": SESSION})
                print("  %-36s %5d entries (%d BY-C), local only" % (name, len(got), n_ok))
    have = {f["file"] for f in man["files"]}
    for species, url in JANAF_PH.items():
        name = "janaf_%s.json" % species
        if name in have:
            continue
        payload = cache._janaf_payload(species, url)
        head = payload["text"].splitlines()[0] if payload["text"] else ""
        if JANAF_HEADER[species] not in head:
            raise SystemExit("%s: table header %r does not name %s" % (url, head, JANAF_HEADER[species]))
        sha = cache._write(PH_CACHE / name, payload)
        man["files"].append({"file": name, "kind": "janaf_table", "request": payload["request"],
                             "retrieved_utc": payload["retrieved_utc"], "sha256": sha, "header": head.strip(),
                             "added_by": SESSION})
        print("  %-36s table" % name)
    man["client_versions"] = libs
    (PH_CACHE / MANIFEST).write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return man


def path_of(rec):
    return (REPO / rec["location"]) if rec.get("local_only") else (PH_CACHE / rec["file"])


def verify():
    man = manifest()
    if man is None:
        return ["no PH-K1 manifest"]
    bad = []
    for f in man["files"]:
        p = path_of(f)
        if not p.is_file():
            bad.append("absent (local only) " + f["file"])
        elif cache.sha256_bytes(p.read_bytes()) != f["sha256"]:
            bad.append("hash mismatch " + f["file"])
    return bad


def load_entries():
    """Admitted (BY-C) entries of every file in the manifest, and the (id, licence) of those left out."""
    from pymatgen.entries.computed_entries import ComputedStructureEntry

    man = manifest()
    bad = verify()
    if bad:
        raise SystemExit("PH-K1 cache problems: %s" % bad)
    ok, out = [], []
    for f in man["files"]:
        if f["kind"] != "mp_entries":
            continue
        doc = json.loads(path_of(f).read_text(encoding="utf-8"))
        for d in doc["response"]:
            if (d.get("data") or {}).get("license") in cache.ADMITTED_LICENCES:
                ok.append(ComputedStructureEntry.from_dict(d))
            else:
                out.append((str(d.get("entry_id")), (d.get("data") or {}).get("license")))
    return ok, out


def cache_hash():
    return cache.sha256_bytes((PH_CACHE / MANIFEST).read_bytes())


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.ph_cache")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    sub.add_parser("verify")
    args = ap.parse_args(argv)
    if args.cmd == "fetch":
        m = fetch()
        print("%d file(s) in the PH-K1 manifest" % len(m["files"]))
        return 0
    bad = verify()
    print("\n".join(bad) or "ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
