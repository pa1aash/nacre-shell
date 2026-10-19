"""Day 3 supplement data (P0-W5.4): fetched additions kept apart from the production cache.

The production cache (results/preprint/pourbaix/cache/) is an input of runs that W4's screens
already read, so it is never extended here (rule R7). This module writes a second, additive cache:

- results/preprint/pourbaix/supplement_d3/cache/: the NIST-JANAF tables the boehmite window needs
  (water, and the lithiation products of the all-experimental cross-check), and the manifest.
- .local/w5/cache_d3/: the Materials Project entries of the Li-Al-O-H system (the boehmite
  lithiation hull). Raw MP entries are not pushed (Materials Project terms, standing rule R12): the
  file stays local and the committed manifest records it by sha256, size and request.

    uv run python -m nacre.pourbaix.supplement_cache fetch     # network: MP (key from .env) and JANAF
    uv run python -m nacre.pourbaix.supplement_cache verify

The Materials Project key is read from .env at fetch time and is never printed, logged or written.
"""
import argparse
import json
import sys
from pathlib import Path

from nacre.pourbaix import cache
from nacre.pourbaix.paths import POURBAIX_RESULTS, REPO

SUPP_DIR = POURBAIX_RESULTS / "supplement_d3"
SUPP_CACHE = SUPP_DIR / "cache"
LOCAL_CACHE = REPO / ".local" / "w5" / "cache_d3"
MANIFEST = "manifest.json"
SESSION = "P0-W5.4"

# The boehmite lithiation hull (Li-open grand potential). Its subsystems come with it.
CELL_CHEMSYS_D3 = ["Li-Al-O-H"]

# NIST-JANAF tables, ids from the formula index (https://janaf.nist.gov/formula.html): the
# table id is the element block and the page offset within it, checked against each header.
JANAF_D3 = {
    "H2O": "https://janaf.nist.gov/tables/H-064.txt",       # H2O(g)
    "H2O_l": "https://janaf.nist.gov/tables/H-063.txt",     # H2O(l), comparator of the W1 key
    "LiOH": "https://janaf.nist.gov/tables/H-018.txt",      # LiOH(cr)
    "LiH": "https://janaf.nist.gov/tables/H-014.txt",       # LiH(cr)
    "LiAlO2": "https://janaf.nist.gov/tables/Al-068.txt",   # LiAlO2(cr)
}
# The phase each table must name in its header line (a wrong table id is refused).
JANAF_HEADER = {"H2O": "H2O1(g)", "H2O_l": "H2O1(l)", "LiOH": "H1Li1O1(cr)", "LiH": "H1Li1(cr)",
                "LiAlO2": "Al1Li1O2(cr)"}


# Sink-salt thermochemistry found in open pages (P0-W5.4 task 1b). Only the quoted sentence, the page
# hash and the Crossref metadata are kept, never the publisher's page. `pattern` must match the
# sentence exactly once; the number is parsed from the stored quote (calorie = scipy.constants.calorie).
LITERATURE_D3 = {
    "krivtsov1973_al_clo4_3": {
        "doi": "10.1007/BF00926423",
        "url": "https://link.springer.com/article/10.1007/BF00926423",
        "what": "dfH of anhydrous Al(ClO4)3 (cr), Conclusions item 1 (free abstract page; full text not open)",
        "pattern": r"The standard enthalpy for the formation of anhydrous aluminum perchlorate was determined "
                   r"\([^)]*\)\.",
        "value": r"\(([−-]?\d+(?:\.\d+)?)\s*(?:\+-|±)\s*(\d+(?:\.\d+)?)\s*kcal/M\)",
        "formula": "Al(ClO4)3",
    },
}


def _literature_payload(rid, spec):
    import html
    import re

    import requests

    r = requests.get(spec["url"], timeout=60, headers={"User-Agent": "nacre-shell headless fetch"})
    r.raise_for_status()
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text)))
    hits = sorted(set(re.findall(spec["pattern"], text)))
    if len(hits) != 1:
        raise SystemExit("%s: expected one quoted sentence, found %d" % (spec["url"], len(hits)))
    cr = requests.get("https://api.crossref.org/works/%s" % spec["doi"], timeout=60).json()["message"]
    meta = {"title": (cr.get("title") or [""])[0], "container": (cr.get("container-title") or [""])[0],
            "volume": cr.get("volume"), "issue": cr.get("issue"), "page": cr.get("page"),
            "year": (cr.get("issued") or {}).get("date-parts", [[None]])[0][0],
            "authors": ["%s %s" % (a.get("given", ""), a.get("family", "")) for a in cr.get("author") or []]}
    return {"kind": "literature_quote", "id": rid, "doi": spec["doi"], "formula": spec["formula"],
            "request": {"method": "HTTP GET", "url": spec["url"]}, "retrieved_utc": cache._now(),
            "page_sha256": cache.sha256_bytes(r.content), "quote": hits[0], "what": spec["what"],
            "value_pattern": spec["value"], "crossref": meta}


def literature_dfh_kj(rid, cache_dir=None):
    """(dfH kJ mol^-1, half-width kJ mol^-1, locator) parsed from a stored literature quote."""
    import re

    from scipy import constants

    doc = json.loads((Path(cache_dir or SUPP_CACHE) / ("lit_%s.json" % rid)).read_text(encoding="utf-8"))
    m = re.search(doc["value_pattern"], doc["quote"])
    if not m:
        raise ValueError("%s: no value in the stored quote" % rid)
    kcal = float(m.group(1).replace("−", "-"))
    u = float(m.group(2))
    kj = constants.calorie  # thermochemical calorie in J per cal, which is kJ per kcal
    loc = "%s, doi:%s, %s; quote: %r" % (", ".join(doc["crossref"]["authors"]), doc["doi"], doc["what"], doc["quote"])
    return kcal * kj, u * kj, loc


def manifest(cache_dir=SUPP_CACHE):
    p = Path(cache_dir) / MANIFEST
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def fetch(env_path=REPO / ".env", session=SESSION):
    """Fetch what the supplement manifest does not list yet (network access)."""
    from mp_api.client import MPRester

    SUPP_CACHE.mkdir(parents=True, exist_ok=True)
    LOCAL_CACHE.mkdir(parents=True, exist_ok=True)
    prod = cache.manifest()
    man = manifest() or {"session": session, "mp_database_version": prod["mp_database_version"],
                         "thermo_types": cache.THERMO_TYPES, "files": [],
                         "note": "additive Day 3 cache; the production cache is not changed"}
    have = {f["file"] for f in man["files"]}
    libs = cache.library_versions()
    todo = [cs for cs in CELL_CHEMSYS_D3 if "mp_entries_cell_%s.json" % cs not in have]
    if todo:
        key = cache._read_key(env_path)
        with MPRester(key) as mpr:
            db_version = mpr.get_database_version()
            if db_version != prod["mp_database_version"]:
                raise SystemExit("database version %s differs from the production cache's %s; not mixing "
                                 "versions" % (db_version, prod["mp_database_version"]))
            for cs in todo:
                elements = sorted(cs.split("-"))
                req = {"method": "MPRester.get_entries_in_chemsys", "elements": elements, "compatible_only": True,
                       "additional_criteria": {"thermo_types": cache.THERMO_TYPES}, "use_gibbs": None}
                got = mpr.get_entries_in_chemsys(elements, compatible_only=True,
                                                 additional_criteria={"thermo_types": cache.THERMO_TYPES})
                got = sorted(got, key=lambda e: (str(e.entry_id), e.energy))
                name = "mp_entries_cell_%s.json" % cs
                payload = {"kind": "mp_entries", "request": req, "retrieved_utc": cache._now(),
                           "mp_database_version": db_version, "client_versions": libs,
                           "n": len(got), "response": [cache._entry_dict(e) for e in got]}
                sha = cache._write(LOCAL_CACHE / name, payload)
                licences = sorted({str((e.data or {}).get("license")) for e in got})
                man["files"].append({"file": name, "kind": "mp_entries", "request": req, "n": len(got),
                                     "retrieved_utc": payload["retrieved_utc"], "sha256": sha,
                                     "bytes": (LOCAL_CACHE / name).stat().st_size, "licences": licences,
                                     "local_only": True, "location": ".local/w5/cache_d3/" + name,
                                     "added_by": session})
                print("  %-34s %5d entries (local only)" % (name, len(got)))
    for species, url in JANAF_D3.items():
        name = "janaf_%s.json" % species
        if name in have:
            continue
        payload = cache._janaf_payload(species, url)
        head = payload["text"].splitlines()[0] if payload["text"] else ""
        if JANAF_HEADER[species] not in head:
            raise SystemExit("%s: table header %r does not name %s" % (url, head, JANAF_HEADER[species]))
        sha = cache._write(SUPP_CACHE / name, payload)
        man["files"].append({"file": name, "kind": "janaf_table", "request": payload["request"],
                             "retrieved_utc": payload["retrieved_utc"], "sha256": sha, "header": head.strip(),
                             "added_by": session})
        print("  %-34s table" % name)
    for rid, spec in LITERATURE_D3.items():
        name = "lit_%s.json" % rid
        if name in have:
            continue
        payload = _literature_payload(rid, spec)
        sha = cache._write(SUPP_CACHE / name, payload)
        man["files"].append({"file": name, "kind": "literature_quote", "request": payload["request"],
                             "retrieved_utc": payload["retrieved_utc"], "sha256": sha, "doi": spec["doi"],
                             "added_by": session})
        print("  %-34s quote" % name)
    man["client_versions"] = libs
    (SUPP_CACHE / MANIFEST).write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return man


def path_of(rec):
    return (REPO / rec["location"]) if rec.get("local_only") else (SUPP_CACHE / rec["file"])


def verify(cache_dir=SUPP_CACHE):
    """Problems with the supplement cache. A local-only file that is absent is reported as such,
    not as a mismatch: a clean checkout does not have it."""
    man = manifest(cache_dir)
    if man is None:
        return ["no supplement manifest"]
    bad = []
    for f in man["files"]:
        p = path_of(f)
        if not p.is_file():
            bad.append(("absent (local only) " if f.get("local_only") else "missing ") + f["file"])
        elif cache.sha256_bytes(p.read_bytes()) != f["sha256"]:
            bad.append("hash mismatch " + f["file"])
    return bad


def local_files_present():
    man = manifest()
    return bool(man) and all(path_of(f).is_file() for f in man["files"] if f.get("local_only"))


def cache_hash():
    return cache.sha256_bytes((SUPP_CACHE / MANIFEST).read_bytes())


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.supplement_cache")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="fetch the Day 3 additions (network)")
    sub.add_parser("verify", help="check the supplement cache against its manifest")
    args = ap.parse_args(argv)
    if args.cmd == "fetch":
        m = fetch()
        print("%d file(s) in the supplement manifest" % len(m["files"]))
        return 0
    bad = verify()
    print("supplement cache OK" if not bad else "\n".join(bad))
    return 1 if [b for b in bad if not b.startswith("absent (local only)")] else 0


if __name__ == "__main__":
    sys.exit(main())
