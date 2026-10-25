"""Patent citations for the cp6 Q2 waiver (PH-W8.7): conditions (a) and (d) checked against the PH-W2.7 record.

(a) every patent is cited in the text by number and kind code as printed, and no missing-input marker for the patent
citations remains; (d) no patent is in refs.bib. The record is lit/novelty.md section PR-1, read here independently of
the macro layer; the text is the manuscript with its macros expanded from a fresh numbers.tex.
"""
import re

from nacre.preprint import macros, paths, refs, texscan
from preprint_helpers import REPO

NOVELTY = REPO / "lit" / "novelty.md"
PR1 = "### PR-1. What was read, and the bibliographic data as printed"


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def printed_strings():
    """['US <number> <kind code>', ...] in PR-1 column order, from the 'Field' and 'Kind code as printed' rows."""
    text = NOVELTY.read_text(encoding="utf-8")
    section = text[text.index(PR1):]
    section = section[:section.index("\n### ", len(PR1))]
    rows = {(_cells(l)[0]): _cells(l)[1:] for l in section.splitlines() if l.startswith("| ")}
    numbers = rows["Field"]
    kinds = [re.match(r"([A-Z][0-9]?)\b", k).group(1) for k in rows["Kind code as printed"]]
    assert len(numbers) == len(kinds) == 4
    return ["%s %s" % (n, k) for n, k in zip(numbers, kinds)]


def _values():
    return dict(re.findall(r"\\newcommand\{\\(Num[A-Za-z]+)\}\{\\nacre(?:Mock)?Text\{([^}]*)\}\}", macros.render(REPO)))


def _expanded_prose():
    vals = _values()
    out = []
    for f in texscan.manuscript_tex(REPO):
        text = "\n".join(texscan.strip_comment(l) for l in f.read_text(encoding="utf-8").splitlines())
        text = re.sub(r"\\(Num[A-Za-z]+)(?:\{\})?\\?", lambda m: vals.get(m.group(1), "\\" + m.group(1)), text)
        out.append(text.replace("~", " "))
    return "\n".join(out)


def test_the_record_prints_four_kind_codes():
    assert printed_strings() == ["US 8,252,463 B2", "US 8,821,969 B2", "US 6,485,866 B1", "US 6,844,114 B2"]


def test_every_patent_in_the_text_carries_the_kind_code_of_the_record():
    prose = _expanded_prose()
    printed = printed_strings()
    for s in printed:
        assert s in prose, s
    cited = re.findall(r"US ([0-9]{1,2},[0-9]{3},[0-9]{3})(?: ([A-Z][0-9]?)\b)?", prose)
    assert cited, "no patent cited"
    for number, kind in cited:
        assert "US %s %s" % (number, kind) in printed, (number, kind or "no kind code")


def test_no_missing_input_marker_for_the_patent_citations():
    for f in texscan.manuscript_tex(REPO):
        text = "\n".join(texscan.strip_comment(l) for l in f.read_text(encoding="utf-8").splitlines())
        assert not re.search(r"\\nacreMissing\{patent", text), f.name


def test_no_patent_in_refs_bib():
    bib = refs.source(REPO).read_text(encoding="utf-8")
    assert not re.search(r"@patent\s*\{", bib, re.I)
    for s in printed_strings():
        number = s.split()[1]
        assert number not in bib and number.replace(",", "") not in bib, s


def test_claims_and_examples_are_named_and_the_false_test_sentence_is_gone():
    intro = (paths.paper(REPO) / "sections" / "introduction.tex").read_text(encoding="utf-8")
    assert "only test printed" not in intro and "NumPatentAcidHours" not in intro
    for m in ("AlPhosAClaimPoFour", "AlPhosAClaimPoThree", "AlPhosAClaimPlate", "AlPhosAClaimPlateParent",
              "AlPhosBClaimMethodA", "AlPhosBClaimMethodB", "AlPhosBClaimCure", "LiPolyAClaimA", "LiPolyAClaimB",
              "LiPolyAClaimC", "LiPolyBClaimA", "LiPolyBClaimB", "LiPolyBClaimC"):
        assert "\\NumPatent" + m in intro, m
    assert intro.count("of the description") == 2 and "not in the claims" in intro
