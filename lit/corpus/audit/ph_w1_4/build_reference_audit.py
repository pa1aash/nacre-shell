"""Build lit/corpus/audit/ph_w1_4/reference_audit.csv and lit/corpus/audit/ph_w1_4/bib_uncited.csv.

Inputs: lit/corpus/audit/ph_w1_4/inputs/*, lit/corpus/audit/ph_w1_4/doi_responses.json (fetch_audit.py), lit/corpus/audit/ph_w1_4/judgments.yaml,
lit/evidence_table.csv. Every column except `supported`, `use`, `evidence_rows` and the judgment
part of `problems` is computed. Run:  uv run python lit/corpus/audit/ph_w1_4/build_reference_audit.py
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
GRADE_ORDER = "ABCD"


def norm(s: str | None) -> str:
    s = re.sub(r"<[^>]+>|&amp;", "", (s or "").lower())
    return re.sub(r"[^a-z0-9 ]", "", s.replace("-", " ").replace("\u2010", " ").replace("\n", " "))


def parse_bib(text: str) -> dict[str, dict]:
    out = {}
    for e in re.split(r"\n(?=@)", text):
        m = re.match(r"@(\w+)\{([^,]+),", e.strip())
        if not m:
            continue

        def field(name):
            f = re.search(rf"\b{name}\s*=\s*\{{(.*?)\}}\s*(?:,|\n|\}})", e, re.I | re.S)
            return re.sub(r"\s+", " ", f.group(1)) if f else None

        out[m.group(2)] = {"type": m.group(1), "doi": field("doi"), "title": field("title"),
                           "author": field("author"), "year": field("year"), "raw": e}
    return out


def uses(text: str) -> dict[str, list[tuple[str, str, list[str]]]]:
    res = defaultdict(list)
    for line in text.splitlines():
        f, n, body = line.split(":", 2)
        claims = re.findall(r"CL-[A-Z]\d+", body)
        for m in re.finditer(r"\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]*)\}", body):
            for k in m.group(1).split(","):
                res[k.strip()].append((Path(f).name, n, claims))
    return res


def main() -> int:
    bib = parse_bib((HERE / "inputs/refs_p0w8.bib").read_text())
    cites = uses((HERE / "inputs/cites_p0w8.grep").read_text())
    resp = json.loads((HERE / "doi_responses.json").read_text())["responses"]
    judg = yaml.safe_load((HERE / "judgments.yaml").read_text())
    rows = {r["row_id"]: r for r in csv.DictReader((ROOT / "lit/evidence_table.csv").open())}

    errors = []
    unknown = sorted(set(cites) - set(judg))
    if unknown:
        errors.append(f"cited keys without a judgment: {unknown}")
    extra = sorted(set(judg) - set(cites))
    if extra:
        errors.append(f"judgments for keys that are not cited: {extra}")

    doi_count = defaultdict(list)
    title_count = defaultdict(list)
    for k, v in bib.items():
        if v["doi"]:
            doi_count[v["doi"].lower()].append(k)
        if v["title"]:
            title_count[norm(v["title"])].append(k)

    out = []
    for k in sorted(cites):
        b = bib[k]
        j = judg[k]
        r = resp[k]
        problems = []
        for rid in j["rows"]:
            if rid not in rows:
                errors.append(f"{k}: row {rid} does not exist")
            elif rows[rid]["doi"].lower() != (b["doi"] or "").lower():
                errors.append(f"{k}: row {rid} carries DOI {rows[rid]['doi']}")
        grades = [rows[x]["grade"] for x in j["rows"] if x in rows]
        best = min(grades, key=GRADE_ORDER.index) if grades else ""

        resolves = "y" if r.get("status") == 200 else "n"
        sim = difflib.SequenceMatcher(None, norm(b["title"]), norm(" ".join(filter(None, [r.get("title"), r.get("subtitle")])))).ratio()
        sim_main = difflib.SequenceMatcher(None, norm(b["title"]), norm(r.get("title"))).ratio()
        title_match = "y" if max(sim, sim_main) >= 0.9 or norm(r.get("title")) in norm(b["title"]) else f"n ({max(sim, sim_main):.2f})"
        if resolves == "y" and str(r.get("year")) != str(b["year"]):
            problems.append(f"year differs (bib {b['year']}, registry {r.get('year')})")
        notice = "none"
        if r.get("update_to") or r.get("updated_by"):
            notice = f"update notice: {r.get('update_to') or r.get('updated_by')}"
            problems.append("retraction or correction notice in metadata")
        retraction = f"{r.get('agency')}: {notice}" if resolves == "y" else "not checked"
        if r.get("type") in ("Preprint", "posted-content"):
            problems.append("DOI is a preprint record")
        rel = [t for t in r.get("relation_types") or [] if t in ("is-preprint-of", "has-preprint", "IsVersionOf", "IsPreprintOf")]
        if "IsPreprintOf" in rel or "is-preprint-of" in rel:
            problems.append("preprint record with a published version")
        if k == "iooss2017shapley":
            pub = resp.get("_iooss_published", {})
            if pub.get("status") == 200:
                problems.append(f"journal version {pub['doi']} resolves ({pub['agency']}, {pub['year']}); the bib entry is the arXiv record")
        missing = [f for f in ("title", "author", "year") if not b[f]]
        if missing:
            problems.append("missing metadata: " + ", ".join(missing))
        if len(doi_count[(b["doi"] or "").lower()]) > 1:
            problems.append("duplicate DOI in bib: " + " ".join(doi_count[b["doi"].lower()]))
        if len(title_count[norm(b["title"])]) > 1:
            problems.append("duplicate title in bib: " + " ".join(title_count[norm(b["title"])]))
        if resolves == "n":
            problems.append("DOI does not resolve")
        if title_match != "y":
            problems.append(f"registry title differs from bib title: {r.get('title')!r}")
        if j["supported"] == "n":
            problems.append("citation without support")
        elif j["supported"] == "partial":
            problems.append("partial support")
        if j["supported"] != "n" and best == "D":
            problems.append("abstract-only evidence (grade D)")
        problems.append(j["note"])

        where = cites[k]
        files = {f for f, _, _ in where}
        out.append({
            "key": k, "doi": b["doi"], "resolves": resolves, "resolved_by": r.get("agency") or "",
            "title_match": title_match, "retraction_check": retraction,
            "scope": "main+SI" if len(files) > 1 and "main_si.tex" in files else ("SI" if files == {"main_si.tex"} else "main"),
            "cited_in": "; ".join(f"{f}:{n}" for f, n, _ in where),
            "claims": " ".join(sorted({c for _, _, cl in where for c in cl})),
            "use": j["use"], "evidence_rows": " ".join(j["rows"]), "best_grade": best,
            "supported": j["supported"], "problems": " | ".join(problems),
        })

    if errors:
        print("\n".join(errors))
        return 1
    with (HERE / "reference_audit.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, lineterminator="\n", fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    unc = []
    for k in sorted(set(bib) - set(cites)):
        b = bib[k]
        r = resp.get(k)
        miss = [f for f in ("title", "author", "year") if not b[f]]
        unc.append({"key": k, "doi": b["doi"] or "", "title": b["title"] or "", "missing_metadata": " ".join(miss)})
    with (HERE / "bib_uncited.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, lineterminator="\n", fieldnames=["key", "doi", "title", "missing_metadata"])
        w.writeheader()
        w.writerows(unc)

    n = len(out)
    c = lambda f: sum(1 for x in out if f(x))
    print(f"keys audited {n}; unresolved {c(lambda x: x['resolves'] == 'n')}; "
          f"supported n {c(lambda x: x['supported'] == 'n')}; partial {c(lambda x: x['supported'] == 'partial')}; "
          f"notices {c(lambda x: 'update notice' in x['retraction_check'] and 'none' not in x['retraction_check'])}; "
          f"title mismatch {c(lambda x: x['title_match'] != 'y')}; uncited bib entries {len(unc)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
