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
    text = re.sub(r"\\begin\{(figure|table\*?)\}.*?\\end\{\1\}", "", INTRO.read_text(encoding="utf-8"), flags=re.S)
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
    assert len(paras) == 7      # PH-W8.13: problem, incumbents, lineage, templates, framework, applied phases, question and scope
    assert 600 <= sum(_words(p) for p in paras) <= 880   # about 700 (brief), plus the qualifiers of the PH-W8.4 rulings and review fixes, the cp6 F6 wording (12 words); the patent sentences of PH-W8.7 removed at PH-W8.9; the count includes marker text


def test_lineage_and_polymorph_statements_are_the_supported_ones():
    prose = " ".join(_prose().split())
    assert "partly deacetylated derivative of chitin" in prose
    assert "name this lineage only" in prose
    assert "The screen does not test layered architecture or polymorph structure" in prose
    assert "alternating aragonite and calcite layers are not nacre-like" in prose
    # PH-W1.9: hanifa2025 and nahi2022 support only this much (TP-010 to TP-014); "not reported to form" was stronger than the rows
    assert "formed at no pH tested at room temperature in one study, only on heating" in prose
    assert "is a minor product of additive-free solutions, generated by magnesium ions and polyamines" in prose


def test_excluded_is_always_thermodynamic_and_carries_the_footnote():
    prose = " ".join(_prose().split())
    hits = re.findall(r"[^.]*\bexclud\w*[^.]*\.", prose)
    assert hits
    for s in hits:
        if "does not claim" in s:
            continue
        if not re.sub(r"not thermodynamically excluded", "", s).count("exclud"):
            continue    # "not thermodynamically excluded" is the prose of the table word open, not an exclusion (as in the Design rules)
        assert "thermodynamically excluded" in s, s
        assert "fn:excluded" in s or "\\nacreExcludedMark" in s, s
    assert r"\label{fn:excluded}\NumExcludedNote" in prose


def test_bone_mineral_and_carbonate_numbers_are_macros():
    prose = _prose()
    for macro in (r"\NumOnsetBoneLow", r"\NumOnsetBoneHigh", r"\NumCarbonateCrossover"):
        assert macro in prose, macro


def test_hero_figure_is_cited_and_labelled():
    text = INTRO.read_text(encoding="utf-8")
    assert "\\label{fig:hero}" in text and "Fig.~\\ref{fig:hero}" in text


TERMS = ("screen", "processing stage", "cell stage", "cutoff class", "sink (solid-salt reference state)", "upper bound $E_\\mathrm{ub}$",
         "thermodynamically excluded\\nacreExcludedMark", "not thermodynamically excluded", "open",
         "suitable against dissolution (a necessary condition)", "inconclusive", "undetermined", "break-even ratio $r^*$",
         "tier-one and tier-two evidence")


def test_terms_table_defines_each_term_in_one_sentence_before_first_use():
    """PH-W8.13: the Terms table sits in the Introduction, is cited in its first paragraph, and defines each term once."""
    text = INTRO.read_text(encoding="utf-8")
    table = text[text.index("\\begin{table*}"):text.index("\\end{table*}")]
    assert "\\caption{Terms used in this paper.}" in table and "\\label{tab:terms}" in table
    lines = [r.replace("\\hline", "").strip() for r in table.split("\\\\\n")]
    rows = {r.split(" & ", 1)[0]: r.split(" & ", 1)[1] for r in lines if " & " in r and "Definition" not in r}
    assert tuple(rows) == TERMS
    for term, definition in rows.items():
        assert definition.strip().count(". ") == 0 and definition.strip().endswith("."), term
    first = _paragraphs()[0]
    assert "Table~\\ref{tab:terms}" in first
    assert text.index("\\label{tab:terms}") < text.index("\\label{fn:excluded}")
