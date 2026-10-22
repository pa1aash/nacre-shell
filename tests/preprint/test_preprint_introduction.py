"""The Introduction (P0-W8.2; regime frame at PH-W8.2): ledger markers, citations of its evidence, and the wording
it must avoid."""
import re

import pytest
import yaml

from nacre.preprint import paths, refs, texscan
from nacre.report import bib as bibmod
from preprint_helpers import REPO

INTRO = paths.paper(REPO) / "sections" / "introduction.tex"
SCOPE_SENTENCES = (
    "This paper does not claim that the barrier works.",
    "This paper does not claim any corrosion rate, capacity or device performance.",
    "This paper does not claim any result from the full ab initio or machine-learned-potential calculations.",
    "This paper does not claim that the nucleation or template half of the chain is validated.",
    "This paper does not claim priority for any film, route or combination.",
)
# Wording the Introduction must not use (prompt P0-W8.2, lane notes N4 and N5, lit/novelty.md U1 to U12).
FORBIDDEN = {
    "supersaturation (the sequestration route is settled at cp2)": r"supersaturat",
    "enrichment asserted by this paper": r"\benrichment\b",
    "chitosan as dissolved chains (N4) or as a component of nacre (PH-W2.4b)": r"chitosan(?![^.]*partly deacetylated)",
    "polyphosphate as a bone-mineral precursor (PH-W2.4b)": r"polyphosphate[^.]{0,60}precursor",
    "polyelectrolytes as a matrix class (PH-W2.4b)": r"polyelectrolyte",
    "the nacre-type label (cp5 closure ruling Q5)": r"nacre-type",
    "first, novel, self-heal (PH-W8.2 wording policy)": r"\bfirst\b|\bnovel|self-heal",
    "aragonite formation asserted at slurry pH (NU19)": r"aragonite (forms|precipitates|grows) (in|from|at)",
    "engineered out (N5)": r"engineered out",
    "thresholds set before the calculation (N5)": r"\b(set|fixed|chosen) (before|in advance)",
    "first as a priority claim (U1, U3 to U8)": (r"\bfirst (ever )?(report|study|demonstration|use|example|time|"
                                                 r"nacre|biomineral|templated|protective|bio-derived|"
                                                 r"computational|polydopamine|PDA)|\bfor the first time\b"),
    "intersection unoccupied (U2)": r"\bintersection\b",
    "carbonate passivates or protects aluminium (U9)": r"\bpassivat|\bprotect",
    "novel (U11)": r"\bnovel",
    "unprecedented, pioneering, never before (U12)": r"unprecedented|pioneering|never before",
}


def _prose():
    """The Introduction without comments, as one string."""
    return " ".join(texscan.strip_comment(line) for line in INTRO.read_text(encoding="utf-8").splitlines())


def _paragraphs():
    text = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", "", INTRO.read_text(encoding="utf-8"), flags=re.S)
    lines = [texscan.strip_comment(line) for line in text.splitlines() if not line.lstrip().startswith("%")]
    return [p for p in re.split(r"\n\s*\n", "\n".join(lines)) if p.strip() and "\\section" not in p]


def _words(text):
    text = re.sub(r"\\cite\{[^}]*\}", "", text)
    text = re.sub(r"\\ce\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\(ref|label)\{[^}]*\}", "X", text)
    return len(re.sub(r"\\[A-Za-z]+", "", text).split())


@pytest.fixture(scope="module")
def claims():
    return yaml.safe_load(paths.claims_yaml(REPO).read_text(encoding="utf-8"))["claims"]


def test_markers_and_ledger_agree(claims):
    marked = set(re.findall(r"CL-[A-Z]\d{2}", INTRO.read_text(encoding="utf-8")))
    by_id = {c["id"]: c for c in claims}
    assert marked <= set(by_id), sorted(marked - set(by_id))
    intro = {c["id"] for c in claims if c["section"] == "introduction" and c["status"] in ("drafted", "verified")}
    assert intro <= marked, sorted(intro - marked)


def test_each_cited_doi_of_an_introduction_claim_is_cited_in_the_text(claims):
    key_of = {doi: key for key, doi in bibmod.bib_index(REPO, refs.source(REPO)).items() if doi}
    cited = set(refs.cited(REPO, [INTRO]))
    for c in claims:
        if c["section"] != "introduction" or c["status"] not in ("drafted", "verified"):
            continue
        for ev in c["evidence"]:
            if ev["kind"] == "doi":
                assert key_of.get(bibmod.normalise_doi(ev["ref"])) in cited, (c["id"], ev["ref"])


def test_every_cite_key_resolves():
    assert refs.unresolved(REPO) == []


def test_scope_sentences_are_verbatim():
    prose = " ".join(_prose().split())
    for s in SCOPE_SENTENCES:
        assert s in prose, s


@pytest.mark.parametrize("what", sorted(FORBIDDEN))
def test_forbidden_wording_is_absent(what):
    m = re.search(FORBIDDEN[what], _prose(), re.I)
    assert m is None, "%s: %r" % (what, m.group(0))


def test_contrary_evidence_is_cited():
    cited = set(refs.cited(REPO, [INTRO]))
    assert "osoriocelestino2020influence" in cited      # lit/contrary.md B1
    assert "yu2023study" in cited                       # lit/contrary.md B10


def test_no_novelty_negative_is_stated():
    """PH-W8.2: the regime-frame Introduction states prior art plainly and makes no scan-limited negative
    (N1, NS5 and NS7 stay out; NS7 would need its four qualifiers and the patent-search gap)."""
    prose = " ".join(_prose().split())
    assert not re.search(r"no previous study|to our knowledge|none (reports|combines)", prose, re.I)


def test_length_and_paragraphs_follow_the_brief():
    paras = _paragraphs()
    assert len(paras) == 7      # PH-W8.2: problem, incumbents, lineage, control, frame, bone mineral, scope
    assert 600 <= sum(_words(p) for p in paras) <= 780   # about 700 (brief); the count includes marker text


def test_lineage_and_polymorph_statements_are_the_supported_ones():
    prose = " ".join(_prose().split())
    assert "partly deacetylated derivative of chitin" in prose
    assert "name this lineage only" in prose
    assert "The screen does not test layered architecture or polymorph structure" in prose
    assert "alternating aragonite and calcite layers are not nacre-like" in prose
    assert "not reported to form from solution at slurry pH and room temperature" in prose


def test_excluded_is_always_thermodynamic_and_carries_the_footnote():
    prose = " ".join(_prose().split())
    hits = re.findall(r"[^.]*\bexclud\w*[^.]*\.", prose)
    assert hits
    for s in hits:
        if "does not claim" in s:
            continue
        assert "thermodynamically excluded" in s, s
        assert "fn:excluded" in s or "\\nacreExcludedMark" in s, s
    assert r"\label{fn:excluded}\NumExcludedNote" in prose


def test_bone_mineral_and_carbonate_numbers_are_macros():
    prose = _prose()
    for macro in (r"\NumOnsetBoneLow", r"\NumOnsetBoneHigh", r"\NumCarbonateCrossover", r"\NumPatentAlPhosA",
                  r"\NumPatentAlPhosB", r"\NumPatentLiPolyA", r"\NumPatentLiPolyB"):
        assert macro in prose, macro


def test_hero_figure_is_cited_and_labelled():
    text = INTRO.read_text(encoding="utf-8")
    assert "\\label{fig:hero}" in text and "Fig.~\\ref{fig:hero}" in text
