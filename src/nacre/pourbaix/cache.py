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

# Day 2 additions (P0-W5.2), fetched by `extend` without touching the Day 1 files.
# The sinks of the registered electrolyte salts (lit/params.yaml key electrolyte_salts: LiClO4,
# LiBOB = LiB(C2O4)2, LiPCP = Li pentacyanopropenide, C8N5Li).
CELL_CHEMSYS_DAY2 = ["Li-Ca-Cl-O", "Li-Al-Cl-O", "Li-Ca-B-C-O", "Li-Al-B-C-O", "Li-Ca-C-N",
                     "Li-Al-C-N"]
# Condensed-phase JANAF tables: the carbonate benchmark reactions of the gas-reference
# benchmark (Li2CO3, Li2O, Na2CO3, Na2O, CaO) and sink salts (LiClO4, LiCl, CaCl2, AlCl3).
# Table ids follow the JANAF formula index (https://janaf.nist.gov/formula.html).
JANAF_DAY2 = {
    "Li2CO3": "https://janaf.nist.gov/tables/C-076.txt",
    "Li2O": "https://janaf.nist.gov/tables/Li-014.txt",
    "Na2CO3": "https://janaf.nist.gov/tables/C-090.txt",
    "Na2O": "https://janaf.nist.gov/tables/Na-012.txt",
    "CaO": "https://janaf.nist.gov/tables/Ca-027.txt",
    "LiClO4": "https://janaf.nist.gov/tables/Cl-046.txt",
    "LiCl": "https://janaf.nist.gov/tables/Cl-041.txt",
    "CaCl2": "https://janaf.nist.gov/tables/Ca-009.txt",
    "AlCl3": "https://janaf.nist.gov/tables/Al-025.txt",
}

# The NBS tables (Wagman et al. 1982, J. Phys. Chem. Ref. Data 11, Suppl. 2), open scanned PDF
# at NIST. The text layer is empty, so the pages that hold the missing sink salts are rendered
# and read by OCR; the cache stores the OCR text of each page with the PDF's sha256. The
# machine-readable NIST release (doi:10.18434/M32124, data.nist.gov mds2-2124) returned HTTP 524
# and connection resets on 2026-10-17 and is logged as an attempt.
NBS_1982 = {
    "url": "https://srd.nist.gov/JPCRD/jpcrdS2Vol11.pdf",
    # pdf page -> printed page and what it holds
    "pages": {136: ("2-128", "Al table: AlCl3"), 137: ("2-129", "Al table: Al(NO3)3, hydrates"),
              276: ("2-268", "Ca table: Ca(ClO4)2")},
    "dpi": 200,
    "ocr": ["tesseract", "--psm", "6"],
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


def _janaf_payload(species, url):
    import requests

    r = requests.get(url, timeout=60)
    r.raise_for_status()
    header = r.text.splitlines()[0] if r.text else ""
    return {"kind": "janaf_table", "species": species,
            "request": {"method": "HTTP GET", "url": url}, "retrieved_utc": _now(),
            "locator": "NIST-JANAF Thermochemical Tables, table for %s (%s), row T=298.15 K "
                       "and neighbours" % (species, header.strip()),
            "text_sha256": sha256_bytes(r.content), "text": r.text}


def _nbs_payload():
    """OCR text of the NBS 1982 pages listed in NBS_1982 (network, pymupdf and tesseract)."""
    import subprocess
    import tempfile

    import pymupdf
    import requests

    r = requests.get(NBS_1982["url"], timeout=300)
    r.raise_for_status()
    pages = {}
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "nbs.pdf"
        pdf.write_bytes(r.content)
        doc = pymupdf.open(pdf)
        for pno, (printed, what) in sorted(NBS_1982["pages"].items()):
            png = Path(tmp) / ("p%d.png" % pno)
            doc[pno - 1].get_pixmap(dpi=NBS_1982["dpi"]).save(png)
            out = subprocess.run(NBS_1982["ocr"][:1] + [str(png), "-"] + NBS_1982["ocr"][1:],
                                 capture_output=True, text=True, check=True).stdout
            pages[str(pno)] = {"printed_page": printed, "holds": what, "ocr_text": out}
        version = subprocess.run([NBS_1982["ocr"][0], "--version"], capture_output=True,
                                 text=True).stdout.splitlines()[:1]
    return {"kind": "nbs_ocr", "request": {"method": "HTTP GET", "url": NBS_1982["url"]},
            "retrieved_utc": _now(), "pdf_sha256": sha256_bytes(r.content),
            "citation": "Wagman, Evans, Parker, Schumm, Halow, Bailey, Churney and Nuttall, The NBS "
                        "tables of chemical thermodynamic properties, J. Phys. Chem. Ref. Data 11, "
                        "Suppl. 2 (1982); erratum doi:10.1063/1.555845",
            "render": {"dpi": NBS_1982["dpi"], "library": "pymupdf %s" % version_or_none("pymupdf")},
            "ocr": {"command": NBS_1982["ocr"], "version": version},
            "pages": pages}


def version_or_none(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def extend(out_dir=CACHE_DIR, env_path=REPO / ".env", session="P0-W5.2"):
    """Fetch the Day 2 additions that the manifest does not list yet (network access).

    Existing cache files are never rewritten: only new files are written and appended to the
    manifest, with the session that added them. The cache hash changes because the manifest
    does, and every run records the hash it used.
    """
    from mp_api.client import MPRester

    out_dir = Path(out_dir)
    man = manifest(out_dir)
    have = {f["file"] for f in man["files"]}
    libs = library_versions()
    added = []
    todo = [cs for cs in CELL_CHEMSYS_DAY2 if "mp_entries_cell_%s.json" % cs not in have]
    if todo:
        key = _read_key(env_path)
        with MPRester(key) as mpr:
            db_version = mpr.get_database_version()
            if db_version != man["mp_database_version"]:
                raise SystemExit("database version %s differs from the cache's %s; refetch the "
                                 "whole cache instead of mixing versions"
                                 % (db_version, man["mp_database_version"]))
            for cs in todo:
                elements = sorted(cs.split("-"))
                req = {"method": "MPRester.get_entries_in_chemsys", "elements": elements,
                       "compatible_only": True, "additional_criteria": {"thermo_types": THERMO_TYPES},
                       "use_gibbs": None}
                got = mpr.get_entries_in_chemsys(elements, compatible_only=True,
                                                 additional_criteria={"thermo_types": THERMO_TYPES})
                got = sorted(got, key=lambda e: (str(e.entry_id), e.energy))
                name = "mp_entries_cell_%s.json" % cs
                payload = {"kind": "mp_entries", "request": req, "retrieved_utc": _now(),
                           "mp_database_version": db_version, "client_versions": libs,
                           "n": len(got), "response": [_entry_dict(e) for e in got]}
                sha = _write(out_dir / name, payload)
                added.append({"file": name, "kind": "mp_entries", "request": req, "n": len(got),
                              "retrieved_utc": payload["retrieved_utc"], "sha256": sha,
                              "added_by": session})
                print("  %-34s %5d entries" % (name, len(got)))
    if "nbs1982_ocr.json" not in have:
        payload = _nbs_payload()
        sha = _write(out_dir / "nbs1982_ocr.json", payload)
        added.append({"file": "nbs1982_ocr.json", "kind": "nbs_ocr", "request": payload["request"],
                      "retrieved_utc": payload["retrieved_utc"], "sha256": sha, "added_by": session})
        print("  %-34s %d pages" % ("nbs1982_ocr.json", len(payload["pages"])))
    for species, url in JANAF_DAY2.items():
        name = "janaf_%s.json" % species
        if name in have:
            continue
        payload = _janaf_payload(species, url)
        sha = _write(out_dir / name, payload)
        added.append({"file": name, "kind": "janaf_table", "request": payload["request"],
                      "retrieved_utc": payload["retrieved_utc"], "sha256": sha, "added_by": session})
        print("  %-34s table" % name)
    if added:
        man["files"] = man["files"] + added
        man.setdefault("extensions", []).append({"session": session, "utc": _now(),
                                                 "files": [a["file"] for a in added],
                                                 "client_versions": libs})
        (out_dir / MANIFEST).write_text(json.dumps(man, indent=1, sort_keys=True) + "\n",
                                        encoding="utf-8")
    return added


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


# Materials Project licence tags admitted into any computation. GNoME-derived entries are tagged
# BY-NC (CC BY-NC 4.0) and are excluded (standing rule on the Materials Project terms; NOTICE.md).
ADMITTED_LICENCES = ("BY-C",)


def excluded_entries(name, cache_dir=CACHE_DIR):
    """(entry id, licence) of every cached entry in `name` that is not admitted."""
    return [(str(d.get("entry_id")), (d.get("data") or {}).get("license"))
            for d in load(name, cache_dir)["response"]
            if (d.get("data") or {}).get("license") not in ADMITTED_LICENCES]


def load_entries(name, cache_dir=CACHE_DIR):
    """ComputedStructureEntry objects from one cached entries file; entries without an admitted
    licence tag (BY-NC, or none) are left out."""
    from pymatgen.entries.computed_entries import ComputedStructureEntry

    return [ComputedStructureEntry.from_dict(d) for d in load(name, cache_dir)["response"]
            if (d.get("data") or {}).get("license") in ADMITTED_LICENCES]


def files_of_kind(kind, cache_dir=CACHE_DIR):
    return [f["file"] for f in manifest(cache_dir)["files"] if f["kind"] == kind]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.cache")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fetch the Materials Project and JANAF data (network)")
    f.add_argument("--out", default=str(CACHE_DIR))
    x = sub.add_parser("extend", help="fetch the Day 2 additions only (network)")
    x.add_argument("--out", default=str(CACHE_DIR))
    sub.add_parser("verify", help="check cached files against the manifest")
    args = ap.parse_args(argv)
    if args.cmd == "fetch":
        m = fetch(Path(args.out))
        print("database version %s, %d files" % (m["mp_database_version"], len(m["files"])))
        return 0
    if args.cmd == "extend":
        added = extend(Path(args.out))
        print("%d file(s) added" % len(added))
        return 0
    bad = verify()
    print("cache OK" if not bad else "\n".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
