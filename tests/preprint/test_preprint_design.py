"""sections/design.tex and the regime-frame wording of PH-W8.2 across the Introduction, Design rules and Methods.

Every prose sentence of the Design rules carries a ledger marker; the four conditions, the stage rule and the
route layer say what the contract says; and the wording policy of the session holds: no process or
registration language except one plain sentence in the Methods, "excluded" only as "thermodynamically
excluded" with the footnote, no "nacre-type" label, and no result stated without a cross-reference.
"""
import re

import pytest
import yaml

from nacre.preprint import paths, texscan
from preprint_helpers import REPO

SECTIONS = paths.paper(REPO) / "sections"
DESIGN = SECTIONS / "design.tex"
FRAME_FILES = ("introduction", "design", "model", "methods")
MARKER = re.compile(r"%\s*(CL-[A-Z]\d{2}(?:,\s*CL-[A-Z]\d{2})*)\s*$")
PROCESS = re.compile(r"\b(register\w*|registration|pre-regist\w*|checkpoint\w*|frozen|freez\w*|deviations?|"
                     r"sessions?|rulings?|lanes?|planning chat)\b", re.I)


def _prose(name):
    text = (SECTIONS / (name + ".tex")).read_text(encoding="utf-8")
    return " ".join(texscan.strip_comment(line) for line in text.splitlines())


def _sentences(name):
    return [s for s in re.split(r"(?<=[.?!])\s+", " ".join(_prose(name).split())) if s.strip()]


@pytest.fixture(scope="module")
def ledger():
    claims = yaml.safe_load(paths.claims_yaml(REPO).read_text(encoding="utf-8"))["claims"]
    return {c["id"]: c for c in claims}


def test_every_design_sentence_names_a_drafted_ledger_entry(ledger):
    used, skip = set(), 0
    for no, line in enumerate(DESIGN.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if re.match(r"\\begin\{(figure\*?|table\*?|equation)\}", s):
            skip += 1
        if skip:
            if re.match(r"\\end\{(figure\*?|table\*?|equation)\}", s):
                skip -= 1
            continue
        if not s or s.startswith(("%", "\\section", "\\subsection", "\\input")):
            continue
        m = MARKER.search(line)
        assert m, "design.tex:%d has no ledger marker" % no
        for cid in re.findall(r"CL-[A-Z]\d{2}", m.group(1)):
            assert ledger[cid]["status"] in ("drafted", "verified"), cid
            used.add(cid)
    own = {cid for cid, c in ledger.items() if c["section"] == "design" and c["status"] in ("drafted", "verified")}
    assert own <= used, sorted(own - used)


def test_four_conditions_stage_rule_and_label():
    text = " ".join(_prose("design").split())
    for k in ("$K_1$", "$K_2$", "$K_3$", "$K_4$"):
        assert k in text, k
    assert "never presented as one film" in text
    assert "proceeding is not passing" in text
    assert ("thermodynamically suitable against dissolution (a necessary condition) for that phase in that grid"
            in text)
    assert "is not evidence of protection" in text
    assert "the condition reduces to $\\gamma_\\mathrm{sn}^\\mathrm{c}\\le\\gamma_\\mathrm{sl}^\\mathrm{c}$" in text   # review m7: the registered route symbols
    assert "stays a labelled hypothesis" in text
    assert "undetermined and never passes" in text


def test_process_language_is_one_plain_sentence_in_the_methods():
    # ruling (2) of PH-W8.4: the dilute-electrolyte correction is "registered but unevaluated", said once in Methods and in the limits
    hits = [(name, s) for name in FRAME_FILES for s in _sentences(name) if PROCESS.search(s.replace("is registered but unevaluated", ""))]
    assert len(hits) == 1, hits
    assert hits[0][0] == "methods" and "fixed with content hashes before the production screen" in hits[0][1]


@pytest.mark.parametrize("name", FRAME_FILES)
def test_excluded_is_thermodynamic_and_marked(name):
    for s in _sentences(name):
        if "does not claim" in s:
            continue
        for m in re.finditer(r"\bexclud\w*", s):
            before = s[max(0, m.start() - 20):m.start()]
            after = s[m.end():m.end() + 40]
            if s[max(0, m.start() - 22):m.start()] == "not thermodynamically ":
                continue    # ruling (1) of PH-W8.4: "not thermodynamically excluded" is the prose of the table word open, not an exclusion
            if "excluded" in m.group(0) and ("thermodynamically" in before):
                assert "nacreExcludedMark" in after or "fn:excluded" in after, s
            elif name in ("introduction", "design"):
                # the verb used for a K-verdict must be the thermodynamic one; other senses are allowed elsewhere
                assert not re.search(r"\b(is|are) excluded\b", s) or "thermodynamically" in s, s


@pytest.mark.parametrize("name", FRAME_FILES)
def test_wording_policy(name):
    text = " ".join(s for s in _sentences(name) if "does not claim" not in s)
    assert not re.search(r"nacre-type", text, re.I)
    assert not re.search(r"\bfirst\b|\bnovel|self-heal", text, re.I)
    assert not re.search(r"\b(barrier|film|layer|coating)s? (works|protects|prevents|outperforms)\b|"
                         r"\b(protects|prevents|outperforms)\b", text, re.I)
