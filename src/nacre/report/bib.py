"""DOI-only bibliography pipeline.

Entries come from content negotiation at doi.org, with Crossref's transform endpoint
as the fallback. An entry is stored as fetched; only its citation key is replaced by a
deterministic one. There is no manual-entry path. Every entry has a provenance record in
paper/bib/provenance.jsonl.
"""
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote

from nacre.report.fetch import Fetcher

DOI_BASE = "https://doi.org/"
CROSSREF_BASE = "https://api.crossref.org/works/"
ACCEPT = "application/x-bibtex"
STOPWORDS = {"a", "an", "the", "on", "of", "in", "for", "and", "to", "with", "from", "by", "at", "as", "is",
             "are", "using", "via", "into", "its", "their", "toward", "towards", "new", "novel"}


class BibError(Exception):
    pass


def paths(root):
    p = Path(root) / "paper"
    return {"bib": p / "refs.bib", "prov": p / "bib" / "provenance.jsonl", "fetch": p / "build" / "_fetch"}


def normalise_doi(value):
    doi = (value or "").strip()
    doi = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I).strip().lower()
    if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
        raise BibError("not a DOI: %r" % value)
    return doi


# -- minimal BibTeX field access (no rewriting of the entry) -----------------------------
_HEAD = re.compile(r"^\s*@(\w+)\s*\{\s*([^,\s]+)\s*,", re.S)


def parse_head(entry):
    m = _HEAD.match(entry)
    if not m:
        raise BibError("response is not a BibTeX entry")
    return m.group(1), m.group(2), m


def field(entry, name):
    m = re.search(r"(?i)(?:^|[\s,{])%s\s*=\s*" % re.escape(name), entry)
    if not m:
        return None
    i, n = m.end(), len(entry)
    if i >= n:
        return None
    if entry[i] == "{":
        depth, j = 0, i
        while j < n:
            depth += {"{": 1, "}": -1}.get(entry[j], 0)
            j += 1
            if depth == 0:
                break
        return entry[i + 1:j - 1]
    if entry[i] == '"':
        j = entry.find('"', i + 1)
        return entry[i + 1:j] if j > 0 else None
    m2 = re.match(r"[^,\n}]+", entry[i:])
    return m2.group(0).strip() if m2 else None


def _ascii(text):
    text = re.sub(r"\\[`'^\"~=.uvHcdbkr]\s*\{?(\w)\}?", r"\1", text)
    text = re.sub(r"[{}\\]", "", text)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def make_key(entry, taken):
    authors = field(entry, "author") or field(entry, "editor") or ""
    first = re.split(r"\s+and\s+", authors.strip())[0] if authors.strip() else ""
    surname = first.split(",")[0] if "," in first else (first.split() or [""])[-1]
    surname = re.sub(r"[^a-z]", "", _ascii(surname).lower()) or "anon"
    year = re.sub(r"\D", "", field(entry, "year") or "")[:4] or "nd"
    word = ""
    for w in re.findall(r"[A-Za-z][A-Za-z0-9]+", _ascii(field(entry, "title") or "")):
        if w.lower() not in STOPWORDS and len(w) > 2:
            word = w.lower()
            break
    base = surname + year + word
    key, n = base, 0
    while key in taken:
        key = base + chr(ord("a") + n) if n < 26 else base + str(n)
        n += 1
    return key


def _read_bib(path):
    return Path(path).read_text(encoding="utf-8") if Path(path).exists() else ""


def split_entries(text):
    """Split a .bib text into entry strings (each starts at a line beginning with @)."""
    parts = re.split(r"(?m)^(?=@\w+\s*\{)", text)
    return [p for p in parts if p.strip().startswith("@")]


def bib_index(root):
    """{key: doi or None} for every entry in refs.bib."""
    out = {}
    for e in split_entries(_read_bib(paths(root)["bib"])):
        _, key, _ = parse_head(e)
        raw = field(e, "doi")
        try:
            out[key] = normalise_doi(raw) if raw else None
        except BibError:
            out[key] = None
    return out


def read_provenance(root):
    p = paths(root)["prov"]
    rows = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


# -- retrieval ---------------------------------------------------------------------------
def _obtain(fetcher, doi, doi_base, crossref_base):
    attempts = []
    candidates = [(doi_base + quote(doi, safe="/"), "doi.org content negotiation"),
                  (crossref_base + quote(doi, safe="") + "/transform/" + ACCEPT, "Crossref transform")]
    for url, label in candidates:
        res = fetcher.get(url, accept=ACCEPT, wayback=False)
        if not res.ok:
            attempts.append("%s: %s" % (label, res.error))
            continue
        text = res.text().strip()
        if not text.startswith("@") or not _HEAD.match(text):
            attempts.append("%s: response is not BibTeX (%s)" % (label, res.content_type or "no content type"))
            continue
        return res, text
    raise BibError("could not fetch BibTeX for %s:\n  %s" % (doi, "\n  ".join(attempts)))


def add(root, doi_in, dry_run=False, fetcher=None, doi_base=DOI_BASE, crossref_base=CROSSREF_BASE, out=print):
    root = Path(root)
    doi = normalise_doi(doi_in)
    p = paths(root)
    index = bib_index(root)
    prov = read_provenance(root)
    if doi in index.values() or any(r["doi"] == doi for r in prov):
        out("already present: %s" % doi)
        return 0
    fetcher = fetcher or Fetcher(venue_dir=p["fetch"])
    res, text = _obtain(fetcher, doi, doi_base, crossref_base)
    typ, original_key, m = parse_head(text)
    taken = set(index) | {r["key"] for r in prov}
    key = make_key(text, taken)
    entry = text[:m.start(2)] + key + text[m.end(2):]
    entry = entry.strip() + "\n"
    record = {"doi": doi, "key": key, "original_key": original_key, "url": res.final_url or res.url,
              "retrieved_utc": res.retrieved_utc, "sha256": res.sha256}
    if dry_run:
        out(entry)
        out(json.dumps(record, sort_keys=True))
        out("dry run: nothing written")
        return 0
    p["bib"].parent.mkdir(parents=True, exist_ok=True)
    existing = _read_bib(p["bib"])
    sep = "" if not existing or existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    with open(p["bib"], "a", encoding="utf-8", newline="\n") as fh:
        fh.write(sep + entry + "\n")
    p["prov"].parent.mkdir(parents=True, exist_ok=True)
    with open(p["prov"], "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    out("added %s as %s" % (doi, key))
    return 0


def check(root, out=print):
    index = bib_index(root)
    prov = read_provenance(root)
    by_key = {r["key"]: r for r in prov}
    problems = []
    for key, doi in index.items():
        if key not in by_key:
            problems.append("refs.bib entry %s has no provenance record" % key)
        elif doi is not None and doi != by_key[key]["doi"]:
            problems.append("refs.bib entry %s doi differs from its provenance record" % key)
    for r in prov:
        if r["key"] not in index:
            problems.append("provenance record %s (doi %s) is not in refs.bib" % (r["key"], r["doi"]))
    for p in problems:
        out("bib check: " + p)
    out("bib check: %s (%d entries, %d records)" % ("FAIL" if problems else "PASS", len(index), len(prov)))
    return 1 if problems else 0
