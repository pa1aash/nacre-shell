"""Figure captions (PH-W8.7): at most three sentences, describing the figure only; the regime footnote and sink marks
belong to the body text, not to captions."""
import re

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


def test_every_paper_caption_equals_its_w6_draft():
    caps = figure_captions()
    assert set(caps) == set(captions.USED.values())
    for fig, label in captions.USED.items():
        assert " ".join(caps[label].split()) == " ".join(captions.tex_caption(REPO, fig).split()), (fig, label)


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
        assert not re.search(r"(?<!thermodynamically )\bexcluded\b", captions.tex_caption(REPO, fig)), fig
