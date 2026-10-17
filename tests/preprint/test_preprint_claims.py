"""preprint/claims.yaml: schema, cross-references and the does-not-claim entries."""
import csv
import re

import pytest
import yaml

from nacre.preprint import lint_scope, macros, paths, refs
from nacre.report import bib as bibmod
from preprint_helpers import REPO

TYPES = {"physical relation": "R", "parameter bound": "B", "governing parameter": "G",
         "required precision": "P", "proxy result": "X", "retrodiction outcome": "T",
         "outlook": "O", "limitation": "LN", "background": "K", "novelty": "V",
         "contrary evidence": "E"}
LIT_RECORDS = ("lit/novelty.md", "lit/contrary.md")
FIGURES = {"Fig %d" % n for n in range(1, 9)} | {"Fig 2%s" % p for p in "abcd"}
TABLES = {"Table %d" % n for n in range(1, 4)}
CHECKPOINTS = {"cp1", "cp2", "cp3", "cp4", "cp5", "none"}
REQUIRED_NOT_CLAIMED = [
    "This paper does not claim that the barrier works.",
    "This paper does not claim any corrosion rate, capacity or device performance.",
    "This paper does not claim any result from the full first-principles or machine-learned-potential calculations.",
]


@pytest.fixture(scope="module")
def claims():
    return yaml.safe_load(paths.claims_yaml(REPO).read_text(encoding="utf-8"))["claims"]


def test_fields_and_vocabulary(claims):
    sections = {f.stem for f in (paths.paper(REPO) / "sections").glob("*.tex")}
    for c in claims:
        for key in ("id", "statement", "section", "type", "polarity", "evidence", "checkpoint",
                    "supplier", "scope_check", "status"):
            assert c.get(key), (c.get("id"), key)
        assert re.fullmatch(r"CL-[RBGPXTOLNKVE]\d{2}", c["id"]), c["id"]
        assert c["type"] in TYPES, c["id"]
        assert c["id"][3] in TYPES[c["type"]], c["id"]
        assert c["section"] in sections, c["id"]
        assert c["polarity"] in ("claims", "does-not-claim")
        assert c["checkpoint"] in CHECKPOINTS, c["id"]
        assert c["status"] in ("planned", "drafted", "verified", "withdrawn")
        assert not re.search(r"\d", c["statement"].replace("2020", "").replace("Ca2+", "")), c["id"]


def test_ids_unique(claims):
    ids = [c["id"] for c in claims]
    assert len(ids) == len(set(ids))


def _evidence_rows():
    with (REPO / "lit" / "evidence_table.csv").open(encoding="utf-8", newline="") as fh:
        return {r["row_id"]: r for r in csv.DictReader(fh)}


def _bib_dois():
    return {doi for doi in bibmod.bib_index(REPO, refs.source(REPO)).values() if doi}


def _recorded_dois(rows):
    """DOIs that W1's evidence table or W2's novelty and contrary records name."""
    text = " ".join((REPO / f).read_text(encoding="utf-8").lower() for f in LIT_RECORDS)
    return {r["doi"].lower() for r in rows.values()}, text


def test_evidence_resolves(claims):
    ids = {c["id"] for c in claims}
    rows = _evidence_rows()
    bib_dois = _bib_dois()
    table_dois, record_text = _recorded_dois(rows)
    sources = macros.load_sources(REPO)["macros"]
    si = (paths.paper(REPO) / "si" / "main_si.tex").read_text(encoding="utf-8")
    si_labels = set(re.findall(r"\\label\{(si:[^}]+)\}", si))
    for c in claims:
        for ev in c["evidence"]:
            kind, ref = ev["kind"], ev["ref"]
            if kind == "macro":
                assert ref in sources, (c["id"], ref)
            elif kind == "figure":
                assert ref in FIGURES, (c["id"], ref)
            elif kind == "table":
                assert ref in TABLES, (c["id"], ref)
            elif kind == "derivation":
                assert ref in si_labels, (c["id"], ref)
            elif kind == "claim":
                assert ref in ids, (c["id"], ref)
            elif kind == "row":
                assert ref in rows, (c["id"], ref)
            elif kind == "doi":
                doi = bibmod.normalise_doi(ref)
                assert doi in bib_dois, (c["id"], "not in refs.bib", ref)
                assert doi in table_dois or doi in record_text, (c["id"], "not in lit/ records", ref)
            elif kind == "dossier":
                f, _, anchor = ref.partition("#")
                assert f.startswith("lit/") and anchor, (c["id"], ref)
                assert anchor in (REPO / f).read_text(encoding="utf-8"), (c["id"], ref)
            else:
                assert kind == "reference", (c["id"], kind)


def test_sources_point_back_at_claims(claims):
    ids = {c["id"] for c in claims}
    for name, spec in macros.load_sources(REPO)["macros"].items():
        if spec.get("claim"):
            assert spec["claim"] in ids, name


def test_every_type_is_used(claims):
    assert {c["type"] for c in claims} == set(TYPES)


def test_required_does_not_claim_entries(claims):
    statements = {c["statement"] for c in claims if c["polarity"] == "does-not-claim"}
    for s in REQUIRED_NOT_CLAIMED:
        assert s in statements


def test_scope_check_field_matches_the_linter(claims):
    allowed = lint_scope.allowlist(REPO)
    for c in claims:
        if c["polarity"] == "does-not-claim":
            assert c["scope_check"] == "allowlisted", c["id"]
            assert lint_scope.normalise(c["statement"]) in allowed, c["id"]
        else:
            assert c["scope_check"] == "clean", c["id"]
    assert lint_scope.lint_claims(REPO) == []



def test_literature_claims_trace_to_a_row_or_a_doi(claims):
    """Rule R2: a background or contrary statement traces to an evidence row or a DOI; a novelty
    statement traces to its wording in lit/novelty.md."""
    for c in claims:
        kinds = {ev["kind"] for ev in c["evidence"]}
        if c["type"] in ("background", "contrary evidence"):
            assert kinds & {"row", "doi"}, c["id"]
        elif c["type"] == "novelty":
            assert any(ev["kind"] == "dossier" and ev["ref"].startswith("lit/novelty.md#")
                       for ev in c["evidence"]), c["id"]
