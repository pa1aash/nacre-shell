"""Fetch the inputs of the PH-W1.4 reference audit and log every request.

Writes (all generated, none edited by hand):
  lit/corpus/audit/ph_w1_4/inputs/refs_p0w8.bib     refs.bib as on origin/preprint/p0-w8
  lit/corpus/audit/ph_w1_4/inputs/cites_p0w8.grep    every line with a cite command (git grep, main text and SI)
  lit/corpus/audit/ph_w1_4/inputs/source.json        the commit the two files above were read from
  lit/corpus/audit/ph_w1_4/doi_responses.json       Crossref (then DataCite) answer for each cited DOI
  lit/corpus/audit/ph_w1_4/retrieval_log.jsonl      one line per HTTP request of the probes below

Run:  uv run python lit/corpus/audit/ph_w1_4/fetch_audit.py
      uv run python lit/corpus/audit/ph_w1_4/fetch_audit.py --extra-doi <doi> ...   (adds DOIs to doi_responses.json, nothing else)
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = "origin/preprint/p0-w8"
UA = "nacre-audit/1.0 (mailto:research@example.com)"
LOG = HERE / "retrieval_log.jsonl"

PATENTS = ["US8252463", "US8821969", "US6485866", "US6844114"]
PROBES = {
    "tolchard2023_rsc_pdf": "https://pubs.rsc.org/en/content/articlepdf/2023/su/d3su00031a",
    "c5ta08574h_osti_pdf": "https://www.osti.gov/servlets/purl/1433677",
    "tolchard2023_nva_search": "https://api.nva.unit.no/search/resources?doi=10.1039/d3su00031a",
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def log(entry: dict) -> None:
    with LOG.open("a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def get(label: str, url: str, timeout: int = 60, attempts: int = 1):
    """GET with a logged line per attempt; returns (status, body bytes or None)."""
    for n in range(1, attempts + 1):
        t0 = time.time()
        status, body, ctype, err = None, None, None, None
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                status, body, ctype = r.status, r.read(), r.headers.get("content-type")
        except urllib.error.HTTPError as e:
            status, body, ctype = e.code, e.read(), e.headers.get("content-type")
        except Exception as e:  # timeout, DNS, TLS
            err = f"{type(e).__name__}: {e}"
        log({
            "label": label, "attempt": n, "url": url, "status": status, "content_type": ctype,
            "bytes": None if body is None else len(body),
            "sha256": None if body is None else hashlib.sha256(body).hexdigest(),
            "error": err, "seconds": round(time.time() - t0, 1), "at": now(),
        })
        if status == 200:
            return status, body
        if status == 404:
            break
        time.sleep(2)
    return status, body


def snapshot_inputs() -> None:
    d = HERE / "inputs"
    d.mkdir(exist_ok=True)
    sha = git("rev-parse", REF).strip()
    (d / "refs_p0w8.bib").write_text(git("show", f"{REF}:preprint/paper/refs.bib"))
    out = git("grep", "-n", "cite", REF, "--", "preprint/paper/sections/*.tex",
              "preprint/paper/main.tex", "preprint/paper/si/main_si.tex")
    prefix = f"{REF}:preprint/paper/"
    (d / "cites_p0w8.grep").write_text("".join(l.replace(prefix, "", 1) + "\n" for l in out.splitlines()))
    (d / "source.json").write_text(json.dumps({"ref": REF, "sha": sha, "read_at": now()}) + "\n")


def bib_dois(text: str) -> dict[str, str]:
    out = {}
    for e in re.split(r"\n(?=@)", text):
        m = re.match(r"@\w+\{([^,]+),", e.strip())
        d = re.search(r"\bdoi\s*=\s*\{([^}]*)\}", e, re.I)
        if m and d:
            out[m.group(1)] = d.group(1)
    return out


def cited_keys(text: str) -> list[str]:
    keys = []
    for m in re.finditer(r"\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]*)\}", text):
        keys += [k.strip() for k in m.group(1).split(",")]
    return sorted(set(keys))


def resolve(doi: str) -> dict:
    q = urllib.parse.quote(doi, safe="/")
    st, body = get("crossref", f"https://api.crossref.org/works/{q}", 40, attempts=3)
    if st == 200:
        m = json.loads(body)["message"]
        rel = m.get("relation") or {}
        return {
            "doi": doi, "agency": "crossref", "status": 200,
            "sha256": hashlib.sha256(body).hexdigest(),
            "title": " ".join((m.get("title") or [""])[:1]),
            "subtitle": " ".join((m.get("subtitle") or [""])[:1]),
            "year": ((m.get("issued") or {}).get("date-parts") or [[None]])[0][0],
            "type": m.get("type"), "container": " ".join((m.get("container-title") or [""])[:1]),
            "first_author": ((m.get("author") or [{}])[0]).get("family"),
            "update_to": m.get("update-to"), "updated_by": m.get("updated-by"),
            "relation_types": sorted(rel.keys()),
        }
    st2, body2 = get("datacite", f"https://api.datacite.org/dois/{q}", 40, attempts=3)
    if st2 == 200:
        a = json.loads(body2)["data"]["attributes"]
        return {
            "doi": doi, "agency": "datacite", "status": 200,
            "sha256": hashlib.sha256(body2).hexdigest(),
            "title": ((a.get("titles") or [{}])[0]).get("title"), "subtitle": "",
            "year": a.get("publicationYear"), "type": (a.get("types") or {}).get("resourceTypeGeneral"),
            "container": a.get("publisher"),
            "first_author": ((a.get("creators") or [{}])[0]).get("name"),
            "update_to": None, "updated_by": None,
            "relation_types": sorted({r.get("relationType") for r in a.get("relatedIdentifiers") or []}),
        }
    return {"doi": doi, "agency": None, "status": st, "datacite_status": st2}


def add_extra(dois: list[str]) -> int:
    """Resolve further DOIs and append them to doi_responses.json under `_extra` (no other request)."""
    path = HERE / "doi_responses.json"
    data = json.loads(path.read_text())
    data.setdefault("responses", {}).setdefault("_extra", {})
    for d in dois:
        data["responses"]["_extra"][d] = resolve(d)
    path.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False))
    return 0


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--extra-doi":
        return add_extra(sys.argv[2:])
    LOG.write_text("")
    snapshot_inputs()
    bib = bib_dois((HERE / "inputs/refs_p0w8.bib").read_text())
    keys = cited_keys((HERE / "inputs/cites_p0w8.grep").read_text())
    missing = [k for k in keys if k not in bib]
    if missing:
        print("cited but not in bib or without DOI:", missing)
    responses = {k: resolve(bib[k]) for k in keys if k in bib}
    # published version of the Shapley-effects preprint, named in evidence row TP-001
    extra = "10.1615/int.j.uncertaintyquantification.2019028372"
    responses["_iooss_published"] = resolve(extra)
    # Plummer and Busenberg 1982, found by bibliographic search rather than typed
    q = urllib.parse.urlencode({
        "query.bibliographic": "Plummer Busenberg 1982 solubilities of calcite, aragonite and vaterite in CO2-H2O solutions",
        "rows": 3, "select": "DOI,title,author,issued,container-title"})
    st, body = get("crossref_search_plummer", f"https://api.crossref.org/works?{q}", 40, attempts=3)
    plummer = []
    if st == 200:
        for it in json.loads(body)["message"]["items"]:
            plummer.append({"doi": it.get("DOI"), "title": " ".join(it.get("title") or []),
                            "first_author": (it.get("author") or [{}])[0].get("family"),
                            "year": ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]})
    responses["_plummer_search"] = plummer
    # open-access locations (OpenAlex) for the three works of the retrieval task
    oa = {}
    for label, doi in [("tolchard2023", "10.1039/d3su00031a"), ("c5ta08574h", "10.1039/c5ta08574h")]:
        st, body = get(f"openalex_{label}", f"https://api.openalex.org/works/doi:{doi}?select=title,open_access,locations", 40, attempts=3)
        if st == 200:
            j = json.loads(body)
            oa[label] = {"title": j.get("title"), "oa_status": (j.get("open_access") or {}).get("oa_status"),
                         "locations": [{"is_oa": l.get("is_oa"), "landing": l.get("landing_page_url"),
                                        "pdf": l.get("pdf_url"), "license": l.get("license")}
                                       for l in j.get("locations") or []]}
    if plummer:
        st, body = get("openalex_plummer", f"https://api.openalex.org/works/doi:{plummer[0]['doi']}?select=title,open_access", 40, attempts=3)
        if st == 200:
            oa["plummer1982"] = json.loads(body).get("open_access")
    responses["_openalex"] = oa
    (HERE / "doi_responses.json").write_text(json.dumps(
        {"retrieved_at": now(), "responses": responses}, indent=1, sort_keys=True, ensure_ascii=False))

    # probes: one logged request each (earlier same-session tries are counted in the report)
    for pn in PATENTS:
        get(f"patent_{pn}", f"https://patents.google.com/patent/{pn}/en")
    for label, url in PROBES.items():
        get(label, url, 90)
    return 0


if __name__ == "__main__":
    sys.exit(main())
