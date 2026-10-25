"""Build citation_outcomes.csv, bib_dois.csv and doi_responses.json for PH-W1.9.

Inputs: judgments.yaml (hand-written), lit/corpus/audit/ph_w1_4/inputs/{refs_p0w8.bib,cites_p0w8.grep},
lit/evidence_table.csv, and a live Crossref request for every replacement or bib DOI named in judgments.yaml
(--offline reuses doi_responses.json). Every column except `outcome`, `support`, `evidence_rows` and
`note` is computed.  Run:  uv run python lit/corpus/audit/ph_w1_9/build_citation_outcomes.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
W14 = ROOT / "lit/corpus/audit/ph_w1_4"
OUTCOMES = {"supported", "recommend drop", "recommend replace"}
SUPPORT = {"full", "partial", "none"}


def bib_dois(text):
    out = {}
    for e in re.split(r"\n(?=@)", text):
        m = re.match(r"@(\w+)\{([^,]+),", e.strip())
        d = re.search(r"\bdoi\s*=\s*\{(.*?)\}", e, re.I | re.S)
        if m and d:
            out[m.group(2)] = d.group(1).strip().lower()
    return out


def cite_sites(text):
    res = {}
    for line in text.splitlines():
        f, n, body = line.split(":", 2)
        for m in re.finditer(r"\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]*)\}", body):
            for k in m.group(1).split(","):
                res.setdefault(k.strip(), []).append("%s:%s" % (Path(f).name, n))
    return res


def crossref(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/")
    req = urllib.request.Request(url, headers={"User-Agent": "nacre-audit/1.0 (mailto:research@example.com)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        msg = json.load(r)["message"]
    issued = ((msg.get("issued") or {}).get("date-parts") or [[None]])[0][0]
    return {"status": 200, "doi": msg.get("DOI", doi).lower(), "title": " ".join(msg.get("title") or []),
            "year": issued, "container": " ".join(msg.get("container-title") or []), "type": msg.get("type"),
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def main(argv):
    offline = "--offline" in argv
    judg = yaml.safe_load((HERE / "judgments.yaml").read_text())
    bib = bib_dois((W14 / "inputs/refs_p0w8.bib").read_text())
    sites = cite_sites((W14 / "inputs/cites_p0w8.grep").read_text())
    rows = {r["row_id"]: r for r in csv.DictReader((ROOT / "lit/evidence_table.csv").open())}
    respf = HERE / "doi_responses.json"
    resp = json.loads(respf.read_text()) if respf.exists() else {}

    errors = []
    for k, j in judg.items():
        if k not in bib:
            errors.append("%s: not in the bib" % k)
            continue
        if k not in sites:
            errors.append("%s: not cited" % k)
        if j["outcome"] not in OUTCOMES or j["support"] not in SUPPORT:
            errors.append("%s: bad outcome or support" % k)
        if j["outcome"] == "recommend replace" and not (j.get("replacement_doi") or j.get("bib_doi")):
            errors.append("%s: replace without a DOI" % k)
        ok_dois = {bib[k], (j.get("replacement_doi") or "").lower(), (j.get("bib_doi") or "").lower()}
        for rid in j["rows"]:
            if rid not in rows:
                errors.append("%s: row %s does not exist" % (k, rid))
            elif j["outcome"] != "recommend replace" and rows[rid]["doi"].lower() not in ok_dois:
                errors.append("%s: row %s carries DOI %s" % (k, rid, rows[rid]["doi"]))
        if j["outcome"] == "recommend replace":
            # rows may come from several works (the replacement and corroborating sources); one must carry the new DOI
            new = (j.get("replacement_doi") or j.get("bib_doi")).lower()
            if not any(rows[r]["doi"].lower() == new for r in j["rows"] if r in rows):
                errors.append("%s: no row carries the replacement DOI %s" % (k, new))
        if j["outcome"] == "supported" and not j["rows"]:
            errors.append("%s: supported without rows" % k)
    if errors:
        print("\n".join(errors))
        return 1

    need = sorted({d for j in judg.values() for d in (j.get("replacement_doi"), j.get("bib_doi")) if d})
    for d in need:
        if d not in resp or not offline:
            if offline:
                errors.append("no stored response for %s" % d)
                continue
            try:
                resp[d] = crossref(d)
            except Exception as exc:  # noqa: BLE001
                resp[d] = {"status": "error", "error": type(exc).__name__}
    if errors:
        print("\n".join(errors))
        return 1
    respf.write_text(json.dumps(resp, indent=1, sort_keys=True) + "\n")

    out = []
    for k in sorted(judg):
        j = judg[k]
        grades = [rows[r]["grade"] for r in j["rows"]]
        out.append({
            "key": k, "doi": bib[k], "cited_in": "; ".join(sites[k]), "outcome": j["outcome"], "support": j["support"],
            "evidence_rows": " ".join(j["rows"]), "best_grade": min(grades) if grades else "",
            "replacement_doi": j.get("replacement_doi") or "", "bib_doi": j.get("bib_doi") or "", "note": " ".join(j["note"].split())})
    with (HERE / "citation_outcomes.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, lineterminator="\n", fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    lst = []
    for k in sorted(judg):
        j = judg[k]
        for kind in ("replacement_doi", "bib_doi"):
            d = j.get(kind)
            if d:
                r = resp[d]
                lst.append({"for_key": k, "kind": "replaces" if kind == "replacement_doi" else "same work, journal record",
                            "doi": d, "resolves": "y" if r.get("status") == 200 else "n", "registry_title": r.get("title", ""),
                            "year": r.get("year", ""), "container": r.get("container", ""), "fetched_at": r.get("fetched_at", "")})
    with (HERE / "bib_dois.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, lineterminator="\n", fieldnames=list(lst[0]))
        w.writeheader()
        w.writerows(lst)
    c = lambda o: sum(1 for x in out if x["outcome"] == o)
    print("keys %d; supported %d; recommend drop %d; recommend replace %d; bib dois %d (%s)" % (
        len(out), c("supported"), c("recommend drop"), c("recommend replace"), len(lst),
        ", ".join("%s %s" % (x["doi"], x["resolves"]) for x in lst)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
