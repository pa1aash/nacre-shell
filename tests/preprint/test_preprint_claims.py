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
         "contrary evidence": "E", "method": "M", "design rule": "D",
         "screen result": "S", "prediction": "Q"}
LIT_RECORDS = ("lit/novelty.md", "lit/contrary.md")
# Legacy ids belong to the carbonate-era claims; the labels are those of the redirected paper (briefs).
FIGURES = ({"Fig %d" % n for n in range(1, 9)} | {"Fig 2%s" % p for p in "abcd"}
           | {"fig:" + n for n in ("hero", "pathway", "conditions", "ladder", "phmap", "nucmap", "precision",
                                   "heatmap", "alsalt", "k1panel")})
TABLES = ({"Table %d" % n for n in range(1, 4)}
          | {"tab:" + n for n in ("candidates", "thresholds", "parameters", "thermo", "baselines", "retrodiction")})
CHECKPOINTS = {"cp1", "cp2", "cp3", "cp4", "cp5", "cp5r", "cp6", "none"}
STAGES = {"slurry", "cell", "conversion"}
NS7_QUALIFIERS = ("in situ", "crosslinked", "water-insoluble", "aluminium foil", "fluorine-free")
REQUIRED_NOT_CLAIMED = [
    "This paper does not claim that the barrier works.",
    "This paper does not claim any corrosion rate, capacity or device performance.",
    "This paper does not claim any result from the full ab initio or machine-learned-potential calculations.",
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
        assert re.fullmatch(r"CL-[RBGPXTOLNKVEMDSQ]\d{2}", c["id"]), c["id"]
        assert c["type"] in TYPES, c["id"]
        assert c["id"][3] in TYPES[c["type"]], c["id"]
        assert c["section"] in sections, c["id"]
        assert c["polarity"] in ("claims", "does-not-claim")
        assert c["checkpoint"] in CHECKPOINTS, c["id"]
        assert c["status"] in ("planned", "drafted", "verified", "withdrawn")
        assert not re.search(r"\d", _without_identifiers(c["statement"])), c["id"]


_IDENT = re.compile(r"\b[A-Z][A-Za-z]*\d[A-Za-z0-9()+]*|\b[A-Z][a-z]?\([A-Za-z0-9]+\)\d*[A-Za-z0-9]*|\b2020\b")


def _without_identifiers(statement):
    """Statement text without identifiers that contain digits: K1, NS7, Ca2+, AlPO4, Al(PO3)3 and the year 2020."""
    return _IDENT.sub("", statement)


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
            elif kind == "record":
                f, _, anchor = ref.partition("#")
                assert anchor and (REPO / f).is_file(), (c["id"], ref)
                assert _tracked(f), (c["id"], "not tracked", f)
                assert anchor in _flat((REPO / f).read_text(encoding="utf-8")), (c["id"], ref)
            else:
                assert kind == "reference", (c["id"], kind)


def _tracked(rel):
    import subprocess
    return subprocess.run(["git", "-C", str(REPO), "ls-files", "--error-unmatch", rel],
                          capture_output=True).returncode == 0


def _flat(text):
    """Text with line breaks and indentation folded to single spaces, so an anchor may span a wrap."""
    return " ".join(text.split()) + "\n" + text


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


def test_origin_stage_and_conditional_fields(claims):
    for c in claims:
        assert c["origin"] in ("redirect", "carbonate control (frozen)"), c["id"]
        if "stage" in c:
            assert c["stage"] in STAGES, c["id"]
        if c.get("conditional"):
            assert c.get("depends_on"), (c["id"], "a conditional claim names what it depends on")
        if c["origin"] == "redirect" and c["section"] in ("results", "predictions") and c["polarity"] == "claims":
            assert c.get("conditional") or c["type"] in ("retrodiction outcome",) or c["id"] in ("CL-S03",), c["id"]


def test_new_ledger_has_conditional_predictions_and_does_not_claim_entries(claims):
    new = [c for c in claims if c["origin"] == "redirect"]
    assert sum(1 for c in new if c["type"] == "prediction" and c.get("conditional")) >= 3
    assert sum(1 for c in new if c["polarity"] == "does-not-claim") >= 6
    first = next(c for c in claims if c["id"] == "CL-Q01")
    text = " ".join(first["statement"].split())
    for part in ("route one or route two", "baked aluminophosphate", "hydroxyapatite", "bare foil",
                 "carbon-coated foil", "water insolubility", "aqueous-slurry immersion", "anodic potential hold",
                 r"\NumHoldLow", r"\NumHoldHigh", "fluorine-free electrolyte"):
        assert part in text, part


def test_ns7_is_stated_only_with_its_four_qualifiers(claims):
    for c in claims:
        refs_ns7 = any(ev["kind"] == "dossier" and ev["ref"].endswith("#NS7") for ev in c["evidence"])
        if refs_ns7:
            text = " ".join(c["statement"].split()).lower()
            for q in NS7_QUALIFIERS:
                assert q in text, (c["id"], q)
            assert len(c.get("qualifiers", [])) == 4 and c.get("conditional"), c["id"]


def test_priority_wording_is_absent_from_new_statements(claims):
    for c in claims:
        if c["origin"] == "redirect" and c["polarity"] == "claims":
            assert not re.search(r"\b(first|novel|unprecedented|pioneering)\b", c["statement"], re.I), c["id"]


def test_stage_rule_is_carried_by_the_stage_claim(claims):
    c = next(c for c in claims if c["id"] == "CL-D11")
    text = " ".join(c["statement"].split())
    assert "STAGE" in text and "slurry-stage" in text and "cell-stage" in text and "conversion-step" in text
    assert "never shown as one film" in text


def test_bone_mineral_framing_is_in_the_ledger(claims):
    by_id = {c["id"]: c for c in claims}
    assert "hydroxyapatite" in by_id["CL-S01"]["statement"] and "near that of carbonate" in by_id["CL-S01"]["statement"]
    assert "calcium orthophosphates only" in by_id["CL-D02"]["statement"]
    assert "prior art" in by_id["CL-V03"]["statement"] and "aluminium foil" in by_id["CL-V03"]["statement"]
