"""Figure captions (PH-W8.7): at most three sentences, describing the figure only; the regime footnote and sink marks
belong to the body text, not to captions."""
import re

import pytest

from nacre.preprint import paths
from preprint_helpers import REPO

FILES = ("sections/introduction.tex", "sections/model.tex", "sections/results.tex", "si/main_si.tex")


def figure_captions():
    out = {}
    for f in FILES:
        text = (paths.paper(REPO) / f).read_text(encoding="utf-8")
        for m in re.finditer(r"\\begin\{(figure\*?)\}(.*?)\\end\{\1\}", text, re.S):
            body = m.group(2)
            start = body.index("\\caption{") + len("\\caption{")
            i, depth = start, 1
            while depth:
                depth += {"{": 1, "}": -1}.get(body[i], 0)
                i += 1
            out[re.search(r"\\label\{([^}]*)\}", body).group(1)] = body[start:i - 1]
    return out


def sentences(caption):
    flat = re.sub(r"Fig\.~?\\ref\{[^}]*\}|\\[A-Za-z]+\{[^}]*\}", "X", caption)
    return [s for s in re.split(r"(?<=[.])\s+(?=[A-Z(])", flat.strip()) if s]


def test_every_figure_caption_has_at_most_three_sentences():
    caps = figure_captions()
    assert len(caps) == 10
    for label, cap in caps.items():
        assert len(sentences(cap)) <= 3, (label, sentences(cap))


def test_captions_carry_no_footnote_or_sink_mark():
    for label, cap in figure_captions().items():
        assert "\\nacreExcludedMark" not in cap and "\\nacreSinkMark" not in cap, label


# PH-W8.8: one caption source. The paper captions are the W6 drafts, translated by nacre.preprint.captions.
from nacre.preprint import captions


# PH-W8.9 (cp6 re-audit G1, G4): the paper captions of fig2, fig15 and fig17 carry the new wording first; the W6 drafts
# follow in W6's own session. While a draft still holds the superseded text named here, its equality check waits
# (xfail); once the drafts are merged the marker is gone and equality is enforced again.
W6_PENDING = {"fig2": "dashed boxes are placeholders", "fig15": "cross hatching: excluded", "fig17": "cross: excluded;"}


def test_every_paper_caption_equals_its_w6_draft():
    caps = figure_captions()
    assert set(caps) == set(captions.USED.values())
    waiting = []
    for fig, label in captions.USED.items():
        if W6_PENDING.get(fig) and W6_PENDING[fig] in captions.draft_text(REPO, fig):
            waiting.append(fig)
            continue
        assert " ".join(caps[label].split()) == " ".join(captions.tex_caption(REPO, fig).split()), (fig, label)
    if waiting:
        pytest.xfail("W6 drafts not yet updated: " + ", ".join(waiting))


def test_no_caption_names_placeholders_or_dashed_boxes():
    caps = {k: " ".join(v.split()) for k, v in figure_captions().items()}
    for label, cap in caps.items():
        assert not re.search(r"placeholder|dashed box", cap, re.I), label


def test_every_draft_is_at_most_three_sentences_and_75_words_with_macros_expanded():
    if not (REPO / "preprint/generated/numbers.tex").exists():  # git-ignored; a fresh checkout has none
        from nacre.preprint import build
        build.generate(REPO)
    for fig in captions.USED:
        draft = captions.thermodynamic(captions.draft_text(REPO, fig))
        assert captions.word_count(draft, REPO) <= 75, (fig, captions.word_count(draft, REPO))
        assert len(sentences(captions.to_tex(draft))) <= 3, fig


def test_the_class_name_excluded_is_always_thermodynamically_excluded():
    for fig in captions.USED:
        assert not re.search(r"(?<!thermodynamically )\bexcluded\b" + captions.QUALIFIED, captions.tex_caption(REPO, fig)), fig


def test_paper_captions_carry_the_cp6_reaudit_wording():
    caps = {k: " ".join(v.split()) for k, v in figure_captions().items()}
    cross = r"cross: excluded ($K_2$: every cell dissolves; $K_1$: thermodynamically excluded$^\dagger$)"
    assert cross in caps["fig:ladder"] and cross in caps["fig:heatmap"]
    assert "single hatching: open ($K_1$) or inconclusive ($K_2$)" in caps["fig:heatmap"]
    assert (r"Brushite at \NumClassHiLow--\NumClassHiHigh\ is thermodynamically excluded only above "
            r"\NumRegCrossBrushiteHi.") in caps["fig:heatmap"]


def _w6_handoff():
    """{fig: draft} of preprint/paper/layout/captions_w6.md, the drafts W6 copies (PH-W8.9)."""
    text = (paths.paper(REPO) / "layout" / "captions_w6.md").read_text(encoding="utf-8")
    return dict(re.findall(r"^## (fig\d+)\n\n```text\n(.*?)\n```", text, re.M | re.S))


def test_handoff_drafts_translate_to_the_paper_captions_within_the_limits():
    if not (REPO / "preprint/generated/numbers.tex").exists():
        from nacre.preprint import build
        build.generate(REPO)
    caps = figure_captions()
    drafts = _w6_handoff()
    assert set(drafts) == {"fig2", "fig15", "fig17"}
    for fig, draft in drafts.items():
        label = captions.USED[fig]
        assert " ".join(caps[label].split()) == " ".join(captions.to_tex(draft).split()), fig
        assert captions.word_count(captions.thermodynamic(draft), REPO) <= 75, fig
        assert len(sentences(captions.to_tex(draft))) <= 3, fig


def test_translator_gives_the_sink_dagger_its_latex_form():
    out = captions.to_tex("thermodynamically excluded†).")
    assert out == r"thermodynamically excluded$^\dagger$)."   # the \dagger of \nacreSinkMark in the Results
    assert all(ord(c) < 128 for c in out)
