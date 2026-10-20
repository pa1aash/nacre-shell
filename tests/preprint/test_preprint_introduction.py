"""The Introduction (P0-W8.2): ledger markers, citations of its evidence, and the wording it must avoid."""
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
)
# Wording the Introduction must not use (prompt P0-W8.2, lane notes N4 and N5, lit/novelty.md U1 to U12).
FORBIDDEN = {
    "supersaturation (the sequestration route is settled at cp2)": r"supersaturat",
    "enrichment asserted by this paper": r"\benrichment\b",
    "chitosan as dissolved chains (N4)": r"chitosan",
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


def test_novelty_wording_keeps_its_qualifiers():
    prose = " ".join(_prose().split())
    assert "patent literature not searched" in prose
    assert "within the searched literature" in prose


def test_length_and_paragraphs_follow_the_brief():
    paras = _paragraphs()
    assert len(paras) == 6
    assert 550 <= sum(_words(p) for p in paras) <= 700


def test_hero_figure_is_cited_and_labelled():
    text = INTRO.read_text(encoding="utf-8")
    assert "\\label{fig:hero}" in text and "Fig.~\\ref{fig:hero}" in text
