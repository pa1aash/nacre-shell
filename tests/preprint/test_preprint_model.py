"""sections/model.tex and sections/methods.tex (P0-W8.3; regime frame at PH-W8.2): order, ledger markers, wording,
figures.

The Physical model follows the derivation as audited at cp2 and cp3 in physical order; the Methods
follows the order of the P0-W8.3 prompt (Task C). Every prose sentence carries a ledger marker, and
the wording that the cp2 bookkeeping and lane note N5 rule out does not appear.
"""
import re

import pytest
import yaml

from nacre.preprint import paths, texscan
from preprint_helpers import REPO

SECTIONS = paths.paper(REPO) / "sections"
MODEL = SECTIONS / "model.tex"
METHODS = SECTIONS / "methods.tex"
SI = paths.paper(REPO) / "si" / "main_si.tex"
MARKER = re.compile(r"%\s*(CL-[A-Z]\d{2}(?:,\s*CL-[A-Z]\d{2})*)\s*$")

MODEL_ORDER = [  # the seven steps of the prompt, each opened by its comment
    "% (1) The two regimes", "% (2) Adhesion in water", "% (3) Ca2+ binding as a descriptor",
    "% (4) Heterogeneous nucleation", "% (5) Film coverage", "% (6) Stability",
    "% (7) What the model leaves out",
]
METHODS_ORDER = [  # PH-W8.2: the main-text Methods; the carbonate-era detail is in the SI section si:methods
    r"\paragraph*{Parameters and priors.}", r"\paragraph*{Oxidation onsets.}",
    r"\paragraph*{Solubility and the aluminium window.}", r"\paragraph*{Thresholds and decision rules.}",
    r"\paragraph*{Propagation and sensitivity.}", r"\paragraph*{Materials Project data.}",
    r"\paragraph*{Baselines, control and retrodiction.}", r"\paragraph*{Transparency.}",
    r"\paragraph*{Reproducibility.}",
]
SI_METHODS_ORDER = [
    r"\paragraph*{Priors.}", r"\paragraph*{Propagation and sensitivity.}",
    r"\paragraph*{Thresholds and the decision rule.}", r"\paragraph*{Retrodiction.}",
    r"\paragraph*{Pourbaix and window settings.}", r"\paragraph*{Compute anchor.}",
    r"\paragraph*{Disclosures of the carbonate screen.}",
]
FORBIDDEN = {
    "engineered out (lane note N5)": r"engineered\s+out",
    "thresholds set before the calculation (N5)": r"(threshold|criteri)[^.]{0,80}\bbefore (the|any) calculation",
    "binding or enrichment raising the supersaturation": r"(binding|enrich\w*|sequestration)[^.]{0,60}\b(raises?|increases?|boosts?) the (local )?supersaturation",
    "a local supersaturation as a quantity of the model": r"\bS_\\mathrm\{local\}|\\Oml\b|\\Omega_\\mathrm\{local\}",
    "C2 as a gate": r"\bC2\b[^.]{0,40}\b(gate|kill|falsif)",
}


def _si_methods_text():
    text = SI.read_text(encoding="utf-8")
    start = text.index(r"\section{Methods detail and the carbonate control}")
    return text[start:text.index(r"\section{", start + 1)]


def _prose_lines(path, text=None):
    """Sentence lines: not comments, not blank, outside floats and displayed equations."""
    out, skip = [], 0
    text = path.read_text(encoding="utf-8") if text is None else text
    for no, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if re.match(r"\\begin\{(figure\*?|table\*?|equation)\}", s):
            skip += 1
        if skip:
            if re.match(r"\\end\{(figure\*?|table\*?|equation)\}", s):
                skip -= 1
            continue
        if not s or s.startswith("%") or s.startswith("\\section") or s.startswith("\\subsection") or re.fullmatch(r"\\paragraph\*?\{[^}]*\}", s):
            continue
        out.append((no, line))
    return out


@pytest.fixture(scope="module")
def ledger():
    claims = yaml.safe_load(paths.claims_yaml(REPO).read_text(encoding="utf-8"))["claims"]
    return {c["id"]: c for c in claims}


@pytest.mark.parametrize("path,section", [(MODEL, "model"), (METHODS, "methods")])
def test_every_sentence_line_names_a_ledger_entry_of_its_section(path, section, ledger):
    lines = _prose_lines(path)
    assert lines, path
    if path == METHODS:   # the carbonate-era Methods detail moved to the SI at PH-W8.2 and keeps its markers
        lines += _prose_lines(SI, _si_methods_text())
    used = set()
    for no, line in lines:
        m = MARKER.search(line)
        assert m, "%s:%d has no ledger marker" % (path.name, no)
        for cid in re.findall(r"CL-[A-Z]\d{2}", m.group(1)):
            assert cid in ledger, (path.name, no, cid)
            used.add(cid)
    own = {cid for cid, c in ledger.items()
           if c["section"] == section and c["status"] in ("drafted", "verified")}
    assert own <= used, sorted(own - used)          # every entry of the section is carried by a sentence
    for cid in used:
        assert ledger[cid]["status"] in ("drafted", "verified"), cid


@pytest.mark.parametrize("path,order", [(MODEL, MODEL_ORDER), (METHODS, METHODS_ORDER), (SI, SI_METHODS_ORDER)])
def test_sections_follow_the_registered_order(path, order):
    text = _si_methods_text() if path == SI else path.read_text(encoding="utf-8")
    positions = [text.index(s) for s in order]
    assert positions == sorted(positions)


@pytest.mark.parametrize("path", [MODEL, METHODS])
def test_wording_ruled_out_by_cp2_and_n5_is_absent(path):
    text = " ".join(texscan.strip_comment(line) for line in path.read_text(encoding="utf-8").splitlines())
    for what, rx in FORBIDDEN.items():
        assert not re.search(rx, text, re.I), what


def test_model_states_the_binding_consequence_and_the_single_entry_rule():
    text = " ".join(MODEL.read_text(encoding="utf-8").split())
    assert "binding alone raises the nucleation barrier" in text
    assert "only if the template--nucleus energy falls by more" in text
    assert "it cannot raise the driving force" in text
    assert "a neutral solute, is an approximation" in text
    assert "belongs to the template--nucleus energy" in text
    assert "Every template-dependent input enters once" in text
    si = " ".join(SI.read_text(encoding="utf-8").split())   # the wetting bound moved to si:templating at PH-W8.2c
    assert "Hydrophilic is meant here in that relative sense" in si and "The bound holds because" in si
    assert "cannot be wetted completely by a solid-like nucleus" in text
    assert r"\eqref{eq:stability}" in text and r"\ref{sec:conditions}" in text   # stability is K1 and K2


def test_model_equations_carry_the_argument_only():
    text = MODEL.read_text(encoding="utf-8")
    labels = re.findall(r"\\begin\{equation\}\\label\{(eq:[^}]+)\}", text)
    assert labels == ["eq:dmu", "eq:het", "eq:access", "eq:spread"]   # eq:dupre and eq:gibbs moved to si:templating
    assert r"\Dmu=\kB T\ln\Omb" in text                  # the bulk driving force, no local credit
    assert r"\cos\theta=\frac{\gslz+\dga-\gsn}{\gnl}" in text   # bare gamma_nl in Young


def test_methods_disclosures_and_conventions():
    text = " ".join(METHODS.read_text(encoding="utf-8").split())
    si = " ".join(_si_methods_text().split())
    assert "An earlier rough estimate under the calcite framing was available when the project was designed" in text
    assert "the framings were chosen on literature grounds" in text
    assert "were seen before the regime-matched frame of this paper was adopted" in text
    assert "amorphous \\ce{Al(OH)3} as the film solid that governs the passivation window" in text
    assert "glass-to-crystal correction of \\ce{Ca(PO3)2}" in text
    assert "were not set before every calculation the project made" in text
    assert "after the scheme values for calcium carbonate with lithium perchlorate had been seen" in si
    for macro in (r"\NumPcredSweepLow", r"\NumPcredSweepHigh", r"\NumMcosSweepLow", r"\NumMcosSweepHigh"):
        assert macro in si, macro    # the published sweeps moved to si:methods at PH-W8.2c
    for macro in (r"\NumPcred", r"\NumMcos", r"\NumPdeg", r"\NumRetroCorrect", r"\NumRetroUsableCases",
                  r"\NumRetroPassCount", r"\NumMpDatabaseVersionComparator", r"\NumDftTolerance"):
        assert macro in text, macro
    assert r"\NumSizingDrawCap" in si and r"\NumSizingBandHalfWidth" in si
    assert "is never reported as a finding" in text
    assert "does not imply endorsement by the Materials Project" in text
    assert r"\NumMpDatabaseVersion" in text and "creativecommons.org/licenses/by/" in text
    # review M14: E_lb is computed, and bounds the onset only under the transfer premise
    assert "bounds the onset only if $\\Delta G_\\mathrm{tr}^\\mathrm{rel}\\ge0$, which no measured datum tests" in text
    assert "the nucleation half is not validated" in text


def test_methods_has_one_reproducibility_paragraph_and_no_procedure():
    text = METHODS.read_text(encoding="utf-8")
    assert text.count(r"\paragraph*{Reproducibility.}") == 1
    prose = " ".join(texscan.strip_comment(line) for line in text.splitlines())
    assert not re.search(r"\buv run\b|\bnacre (preprint|screen|bib)\b|\.py\b|(?<![A-Za-z])--[a-z]", prose)


def test_fig2_panel_letters_are_set_by_the_layout_at_the_artwork_geometry():
    """The letters sit over the left edge of each panel of figures/tikz/fig2.tex, outside the artwork."""
    tikz = (REPO / "figures" / "tikz" / "fig2.tex").read_text(encoding="utf-8")
    width = float(re.search(r"\\useasboundingbox \(0,0\) rectangle \(([0-9.]+),", tikz).group(1))
    starts = [float(x) for x in re.search(r"\\foreach \\x in \{([0-9.,]+)\} \{\\fill\[statebox\]", tikz).group(1).split(",")]
    layout = (paths.paper(REPO) / "layout" / "panel_letters.tex").read_text(encoding="utf-8")
    offsets = re.findall(r"\\nacrePanelLetter\{\\dimexpr\\linewidth\*([0-9]+)/([0-9]+)\\relax\}\{([a-d])\}", layout[layout.index(r"\newcommand{\nacreFigTwoPanelLetters}"):layout.index(r"\newcommand{\nacreFigOnePanelLetters}")])
    assert [o[2] for o in offsets] == list("abcd")
    for (num, den, _), start in zip(offsets, starts):
        assert abs(int(num) / int(den) - start / width) < 1e-9
    model = MODEL.read_text(encoding="utf-8")
    fig = model[model.index(r"\begin{figure*}"):model.index(r"\label{fig:chain}")]
    assert fig.index(r"\nacreFigTwoPanelLetters") < fig.index(r"\includegraphics")
    main = (paths.paper(REPO) / "main.tex").read_text(encoding="utf-8")
    assert r"\input{layout/panel_letters}" in main


def test_hero_is_hooked_with_panel_letters_outside_the_image():
    """fig:hero shows the two-panel render; letters a and b sit above the left edge of each panel (977 and 1023 of 2000 units)."""
    layout = (paths.paper(REPO) / "layout" / "panel_letters.tex").read_text(encoding="utf-8")
    block = layout[layout.index(r"\newcommand{\nacreFigOnePanelLetters}"):]
    offsets = re.findall(r"\\nacrePanelLetter\{\\dimexpr\\linewidth\*([0-9]+)/2000\\relax\}\{([ab])\}", block)
    assert [o[1] for o in offsets] == ["a", "b"] and int(offsets[0][0]) < 977 < 1023 <= int(offsets[1][0])
    intro = (paths.paper(REPO) / "sections" / "introduction.tex").read_text(encoding="utf-8")
    fig = intro[intro.index(r"\begin{figure}"):intro.index(r"\label{fig:hero}")]
    assert fig.index(r"\nacreFigOnePanelLetters") < fig.index(r"\includegraphics") and "figures/out/fig1.pdf" in fig
    # PH-W8.8: the caption is the W6 draft (tests/preprint/test_preprint_captions.py); its honesty statements stay
    assert "are not tested by the screen" in fig and "not a result" in fig and "oxide not drawn" in fig
    assert "Whether or how a film forms" in fig and "schematic positions" in fig
