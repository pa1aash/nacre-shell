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
