"""Materials Project entries and JANAF element tables added by PH-W5.1 (lane p0-w5).

Additive to the PH-K1 cache and from the same database version (2026.09.28), so that every row of the
K1 ladder shares one database book: the Al-O-H system (comparators of the passivation window) and the
Ca-C-O system (the carbonate DFT comparator of fix F7). A fetch that meets another database version
stops. JANAF element tables (white P, alpha Ca, Li) give the elemental entropies of the staged-product
route (fix F3).

Raw entries stay under .local/w5/cache_ph/ (Materials Project terms); the committed manifest in
results/preprint/pourbaix/ph_w51/cache/ records each file by request, size and sha256. Only BY-C
entries are admitted. The key is read from .env at fetch time and never printed or written.

    uv run python -m nacre.pourbaix.ph_w51_cache fetch
    uv run python -m nacre.pourbaix.ph_w51_cache verify
"""
import argparse
import json
import sys

from nacre.pourbaix import cache, ph_cache
from nacre.pourbaix.paths import POURBAIX_RESULTS, REPO

W51_DIR = POURBAIX_RESULTS / "ph_w51"
W51_CACHE = W51_DIR / "cache"
LOCAL_CACHE = ph_cache.LOCAL_CACHE
MANIFEST = "manifest.json"
SESSION = "PH-W5.1"
CHEMSYS = ["Al-O-H", "Ca-C-O"]
# NIST-JANAF element tables (header checked): the reference states of the tabulated formation data.
JANAF_W51 = {"P_white": "https://janaf.nist.gov/tables/P-002.txt",
             "Ca_alpha": "https://janaf.nist.gov/tables/Ca-002.txt",
             "Li_cr": "https://janaf.nist.gov/tables/Li-002.txt"}
JANAF_HEADER = {"P_white": "Phosphorus, White", "Ca_alpha": "Calcium, Alpha", "Li_cr": "Li1(cr)"}


def manifest(cache_dir=W51_CACHE):
    p = cache_dir / MANIFEST
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def fetch(env_path=REPO / ".env"):
    from mp_api.client import MPRester

    W51_CACHE.mkdir(parents=True, exist_ok=True)
    LOCAL_CACHE.mkdir(parents=True, exist_ok=True)
    want = ph_cache.manifest()["mp_database_version"]
    man = manifest() or {"session": SESSION, "mp_database_version": None, "thermo_types": cache.THERMO_TYPES,
                         "files": [], "note": "additive to the PH-K1 cache (same database version, checked at fetch)"}
    have = {f["file"] for f in man["files"]}
    libs = cache.library_versions()
    todo = [cs for cs in CHEMSYS if "mp_entries_w51_%s.json" % cs not in have]
    if todo:
        key = cache._read_key(env_path)
        with MPRester(key) as mpr:
            db_version = mpr.db_version
            if db_version != want:
                raise SystemExit("database version %s differs from the PH-K1 cache's %s; not mixing versions"
                                 % (db_version, want))
            man["mp_database_version"] = db_version
            for cs in todo:
                elements = sorted(cs.split("-"))
                req = {"method": "MPRester.get_entries_in_chemsys", "elements": elements, "compatible_only": True,
                       "additional_criteria": {"thermo_types": cache.THERMO_TYPES}, "use_gibbs": None}
                got = mpr.get_entries_in_chemsys(elements, compatible_only=True,
                                                 additional_criteria={"thermo_types": cache.THERMO_TYPES})
                got = sorted(got, key=lambda e: (str(e.entry_id), e.energy))
                name = "mp_entries_w51_%s.json" % cs
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
    for species, url in JANAF_W51.items():
        name = "janaf_%s.json" % species
        if name in have:
            continue
        payload = cache._janaf_payload(species, url)
        head = payload["text"].splitlines()[0] if payload["text"] else ""
        if JANAF_HEADER[species] not in head:
            raise SystemExit("%s: table header %r does not name %s" % (url, head, JANAF_HEADER[species]))
        sha = cache._write(W51_CACHE / name, payload)
        man["files"].append({"file": name, "kind": "janaf_table", "request": payload["request"],
                             "retrieved_utc": payload["retrieved_utc"], "sha256": sha, "header": head.strip(),
                             "added_by": SESSION})
        print("  %-36s table" % name)
    man["client_versions"] = libs
    (W51_CACHE / MANIFEST).write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return man


def path_of(rec):
    return (REPO / rec["location"]) if rec.get("local_only") else (W51_CACHE / rec["file"])


def verify():
    man = manifest()
    if man is None:
        return ["no PH-W5.1 manifest"]
    bad = []
    for f in man["files"]:
        p = path_of(f)
        if not p.is_file():
            bad.append("absent (local only) " + f["file"])
        elif cache.sha256_bytes(p.read_bytes()) != f["sha256"]:
            bad.append("hash mismatch " + f["file"])
    return bad


def load_entries():
    """Admitted (BY-C) entries of the PH-K1 and PH-W5.1 caches (one database version), and those left out."""
    from pymatgen.entries.computed_entries import ComputedStructureEntry

    man = manifest()
    bad = verify()
    if bad:
        raise SystemExit("PH-W5.1 cache problems: %s" % bad)
    if man["mp_database_version"] != ph_cache.manifest()["mp_database_version"]:
        raise SystemExit("PH-W5.1 and PH-K1 caches differ in database version")
    ok, out = ph_cache.load_entries()
    for f in man["files"]:
        if f["kind"] != "mp_entries":
            continue
        for d in json.loads(path_of(f).read_text(encoding="utf-8"))["response"]:
            if (d.get("data") or {}).get("license") in cache.ADMITTED_LICENCES:
                ok.append(ComputedStructureEntry.from_dict(d))
            else:
                out.append((str(d.get("entry_id")), (d.get("data") or {}).get("license")))
    return ok, out


def cache_hash():
    return cache.sha256_bytes((W51_CACHE / MANIFEST).read_bytes())


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.ph_w51_cache")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    sub.add_parser("verify")
    args = ap.parse_args(argv)
    if args.cmd == "fetch":
        m = fetch()
        print("%d file(s) in the PH-W5.1 manifest" % len(m["files"]))
        return 0
    bad = verify()
    print("\n".join(bad) or "ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
