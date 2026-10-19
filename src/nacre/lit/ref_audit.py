"""Reference audit of the preprint bibliography against the evidence table (P0-W1.4, Task C).

Reads W8's bibliography and section files read-only from a git ref (never from W8's worktree, and
never writing to them), and writes one row per bibliography key to
lit/corpus/audit/reference_audit.csv:

    uv run python -m nacre.lit.ref_audit [--ref origin/preprint/p0-w8] [--offline]

Per key it records the DOI; whether the DOI resolves (Crossref first, then DataCite); whether the
Crossref title matches the bib title; the retraction check (Crossref notices that update the DOI,
`filter=updates:<doi>`); the places the key is cited; the evidence rows that support the cited claim
and their best grade; whether the use is a quote, a paraphrase or a data source; and any problem
(unresolved DOI, missing metadata, duplicate DOI or title, uncited entry, citation without support).

Which rows support which claim, and how the text uses the work, are judgements recorded in
lit/corpus/audit/claims.yaml (one entry per key: claim, use, rows, note). The tool checks that every
listed row exists and carries the key's DOI or names it as its original; it never infers support from
a DOI match alone, so a key absent from claims.yaml is reported as unsupported.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

import yaml

from nacre import _util
from nacre.lit import evidence as E
from nacre.report import bib as B

REF = "origin/preprint/p0-w8"
BIB = "preprint/paper/refs.bib"
SECTIONS = "preprint/paper/sections"
SI = "preprint/paper/si/main_si.tex"
OUT = Path("lit") / "corpus" / "audit" / "reference_audit.csv"
CLAIMS = Path("lit") / "corpus" / "audit" / "claims.yaml"
CROSSREF = "https://api.crossref.org/works/"
DATACITE = "https://api.datacite.org/dois/"
USES = ("quote", "paraphrase", "data source")
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
COLUMNS = ["key", "doi", "resolves", "resolved_by", "title_match", "retraction_check", "cited", "cited_in",
           "claim", "use", "evidence_rows", "best_grade", "supported", "problems"]
_CITE = re.compile(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")
_REQUIRED = {"article": ("title", "author", "year", "journal"), "book": ("title", "year")}


def git_show(root, ref, path):
    res = _util.git(root, "show", "%s:%s" % (ref, path))
    if res.returncode != 0:
        raise SystemExit("cannot read %s:%s (%s)" % (ref, path, res.stderr.strip()))
    return res.stdout


def git_ls(root, ref, path):
    res = _util.git(root, "ls-tree", "--name-only", ref, path + "/")
    return [p for p in res.stdout.split() if p.endswith(".tex")]


def cite_sites(files):
    """{key: [(file, line, sentence)]} for every \\cite in the given {name: text}."""
    out = {}
    for name, text in files.items():
        for no, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("%"):
                continue
            for m in _CITE.finditer(line):
                for key in (k.strip() for k in m.group(1).split(",")):
                    if key:
                        out.setdefault(key, []).append((name, no, sentence_at(line, m.start())))
    return out


def sentence_at(line, pos):
    start = max(line.rfind(". ", 0, pos) + 2, 0)
    end = line.find(". ", pos)
    return re.sub(r"\s+", " ", line[start:(end + 1 if end > 0 else len(line))]).strip()[:300]


def bib_entries(text):
    out = []
    for e in B.split_entries(text):
        kind, key, _ = B.parse_head(e)
        raw = B.field(e, "doi")
        try:
            doi = B.normalise_doi(raw) if raw else None
        except B.BibError:
            doi = None
        out.append({"kind": kind.lower(), "key": key, "doi": doi, "raw_doi": raw,
                    "title": B.field(e, "title"), "fields": {f: B.field(e, f) for f in
                                                              ("title", "author", "year", "journal",
                                                               "institution", "publisher")}})
    return out


def norm_title(t):
    t = re.sub(r"\\[a-zA-Z]+|[{}$]", "", t or "")
    t = re.sub(r"&amp;", "&", t)
    return re.sub(r"[^a-z0-9]+", "", B._ascii(t).lower())


def resolve(http, doi):
    """(resolves, by, title) from Crossref, else DataCite."""
    try:
        res = http.get("crossref", CROSSREF + quote(doi, safe="/"))
        msg = res.json().get("message") or {}
        return True, "crossref", " ".join(msg.get("title") or [])
    except Exception:  # noqa: BLE001 - any failure falls through to DataCite
        pass
    try:
        res = http.get("datacite", DATACITE + quote(doi, safe="/"))
        attrs = (res.json().get("data") or {}).get("attributes") or {}
        titles = attrs.get("titles") or [{}]
        return True, "datacite", titles[0].get("title") or ""
    except Exception:  # noqa: BLE001
        return False, "", ""


def retraction_check(http, doi):
    """Crossref notices that update the DOI (retraction, correction, expression of concern...)."""
    try:
        res = http.get("crossref", CROSSREF.rstrip("/"), params={"filter": "updates:%s" % doi, "rows": 20})
        items = (res.json().get("message") or {}).get("items") or []
    except Exception as exc:  # noqa: BLE001
        return "not checked (%s)" % type(exc).__name__
    kinds = []
    for it in items:
        for up in it.get("update-to") or []:
            if (up.get("DOI") or "").lower() == doi:
                kinds.append("%s by %s" % (up.get("type") or "update", it.get("DOI")))
    return "; ".join(sorted(set(kinds))) if kinds else "no update notice in Crossref"


def check_claims(claims, rows_by_id, entries):
    """Problems in claims.yaml: unknown keys, bad use values, rows that do not exist or carry another DOI."""
    problems = []
    dois = {e["key"]: e["doi"] for e in entries}
    for key, c in claims.items():
        if key not in dois:
            problems.append("claims.yaml: %s is not a bib key" % key)
            continue
        if c.get("use") not in USES:
            problems.append("claims.yaml: %s use %r not in %s" % (key, c.get("use"), USES))
        for rid in c.get("rows") or []:
            r = rows_by_id.get(rid)
            if r is None:
                problems.append("claims.yaml: %s row %s does not exist" % (key, rid))
            elif dois[key] and r["doi"] != dois[key] and dois[key] not in (r.get("notes") or "").lower():
                problems.append("claims.yaml: %s row %s carries %s, not %s" % (key, rid, r["doi"], dois[key]))
    return problems


def build(root, ref=REF, http=None, offline=False):
    bib_text = git_show(root, ref, BIB)
    files = {Path(p).name: git_show(root, ref, p) for p in git_ls(root, ref, SECTIONS)}
    si_text = git_show(root, ref, SI)
    sites = cite_sites(files)
    si_sites = cite_sites({"si/main_si.tex": si_text})
    for k, v in si_sites.items():
        sites.setdefault(k, []).extend(v)
    entries = bib_entries(bib_text)
    _, rows = E.read_csv(Path(root) / "lit" / "evidence_table.csv")
    rows_by_id = {r["row_id"]: r for r in rows}
    claims = yaml.safe_load((Path(root) / CLAIMS).read_text(encoding="utf-8")) or {}
    problems_global = check_claims(claims, rows_by_id, entries)
    if problems_global:
        raise SystemExit("\n".join(problems_global))

    by_doi, by_title = {}, {}
    for e in entries:
        if e["doi"]:
            by_doi.setdefault(e["doi"], []).append(e["key"])
        if e["title"]:
            by_title.setdefault(norm_title(e["title"]), []).append(e["key"])

    out = []
    for e in entries:
        key, doi, probs = e["key"], e["doi"], []
        c = claims.get(key) or {}
        if not doi:
            probs.append("no DOI" if not e["raw_doi"] else "malformed DOI %r" % e["raw_doi"])
        need = _REQUIRED.get(e["kind"], ("title", "year"))
        missing = [f for f in need if not (e["fields"].get(f) or "").strip()]
        if e["kind"] == "book" and not (e["fields"].get("institution") or e["fields"].get("publisher")):
            missing.append("institution or publisher")
        if missing:
            probs.append("missing metadata: " + ", ".join(missing))
        if doi and len(by_doi[doi]) > 1:
            probs.append("duplicate DOI with " + ", ".join(k for k in by_doi[doi] if k != key))
        if e["title"] and len(by_title[norm_title(e["title"])]) > 1:
            probs.append("duplicate title with " + ", ".join(k for k in by_title[norm_title(e["title"])] if k != key))
        resolves, by, title_match, retr = "", "", "", ""
        if doi and not offline:
            ok, by, rtitle = resolve(http, doi)
            resolves = "y" if ok else "n"
            if not ok:
                probs.append("DOI does not resolve in Crossref or DataCite")
            elif e["title"] and rtitle:
                a, b = norm_title(e["title"]), norm_title(rtitle)
                title_match = "y" if (a == b or a in b or b in a) else "n"
                if title_match == "n":
                    probs.append("bib title differs from the registered title: %s" % rtitle[:120])
            elif not e["title"]:
                title_match = "no bib title"
            retr = retraction_check(http, doi) if by == "crossref" else "not in Crossref (DataCite record)"
            if re.search(r"retraction|withdrawal|expression_of_concern", retr):
                probs.append("update notice: " + retr)
        cited = sites.get(key) or []
        if not cited:
            probs.append("not cited in the sections or the SI")
        row_ids = list(c.get("rows") or [])
        grades = [rows_by_id[r]["grade"] for r in row_ids]
        best = min(grades, key=GRADE_ORDER.get) if grades else ""
        supported = "y" if row_ids else "n"
        if cited and not row_ids:
            probs.append("citation without supporting evidence row")
        if c.get("note"):
            probs.append(c["note"])
        out.append({
            "key": key, "doi": doi or "", "resolves": resolves, "resolved_by": by, "title_match": title_match,
            "retraction_check": retr, "cited": "y" if cited else "n",
            "cited_in": "; ".join("%s:%d" % (f, n) for f, n, _ in cited),
            "claim": c.get("claim") or (cited[0][2] if cited else ""),
            "use": c.get("use") or "", "evidence_rows": " ".join(row_ids), "best_grade": best,
            "supported": supported, "problems": "; ".join(probs)})
    missing = sorted(set(sites) - {e["key"] for e in entries})
    for key in missing:
        out.append({c: "" for c in COLUMNS} | {
            "key": key, "cited": "y", "cited_in": "; ".join("%s:%d" % (f, n) for f, n, _ in sites[key]),
            "claim": sites[key][0][2], "supported": "n", "problems": "cited but not in refs.bib"})
    return out, missing


def write(root, rows):
    path = Path(root) / OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m nacre.lit.ref_audit", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ref", default=REF)
    p.add_argument("--offline", action="store_true", help="skip DOI resolution and the retraction check")
    a = p.parse_args(argv)
    root = _util.repo_root()
    http = None
    if not a.offline:
        from nacre.lit.thread import ThreadSession
        http = ThreadSession("T-P").http
    rows, missing = build(root, a.ref, http, a.offline)
    path = write(root, rows)
    print("%s: %d keys; cited %d; unsupported citations %d; unresolved DOIs %d" % (
        path, len(rows), sum(r["cited"] == "y" for r in rows),
        sum(r["cited"] == "y" and r["supported"] == "n" for r in rows), sum(r["resolves"] == "n" for r in rows)))
    if missing:
        print("cite keys with no bib entry: " + ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
