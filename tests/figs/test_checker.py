"""The figure checker rejects every decoration R7 forbids and accepts what it allows."""
import pytest
from figs_helpers import REPO, check, clean_figure, plt
from matplotlib.patches import FancyArrow, FancyArrowPatch
from matplotlib.offsetbox import AnchoredText

from nacre.figs import checker, style
from nacre.figs.panels import PANEL_GID, panel_letters


@pytest.fixture(autouse=True)
def _close():
    yield
    plt().close("all")


def _has(problems, word):
    return any(word in p for p in problems)


def test_clean_figure_passes():
    fig, _ = clean_figure()
    assert check(fig) == []


def test_planted_legend_rejected():
    fig, ax = clean_figure()
    ax.lines[0].set_label("series")
    ax.legend()
    probs = check(fig)
    assert _has(probs, "legend")


def test_planted_in_axes_text_rejected():
    fig, ax = clean_figure()
    ax.text(0.5, 0.5, "label inside")
    probs = check(fig)
    assert _has(probs, "in-axes text")


def test_in_axes_text_rejected_even_when_empty():
    fig, ax = clean_figure()
    ax.text(0.5, 0.5, "")
    assert _has(check(fig), "in-axes text")


def test_annotation_rejected():
    fig, ax = clean_figure()
    ax.annotate("peak", xy=(2, 4), xytext=(1, 3))
    assert _has(check(fig), "annotation")


def test_annotation_arrow_rejected():
    fig, ax = clean_figure()
    ax.annotate("", xy=(2, 4), xytext=(1, 3), arrowprops={"arrowstyle": "->"})
    assert _has(check(fig), "annotation")


def test_arrow_patches_rejected():
    for make in (lambda: FancyArrow(0, 0, 1, 1, width=0.05),
                 lambda: FancyArrowPatch((0, 0), (1, 1), arrowstyle="->")):
        fig, ax = clean_figure()
        ax.add_patch(make())
        assert _has(check(fig), "arrow"), make
        plt().close(fig)


def test_anchored_text_rejected():
    fig, ax = clean_figure()
    ax.add_artist(AnchoredText("callout", loc="upper left"))
    assert _has(check(fig), "offset box")


def test_axes_title_rejected():
    fig, ax = clean_figure()
    ax.set_title("A title")
    assert _has(check(fig), "title")


def test_left_title_without_panel_gid_rejected():
    fig, ax = clean_figure()
    ax.set_title("a", loc="left")
    assert _has(check(fig), "title")


def test_figure_text_and_suptitle_rejected():
    fig, _ = clean_figure()
    fig.text(0.5, 0.5, "note")
    fig.suptitle("Suptitle")
    probs = check(fig)
    assert _has(probs, "figure-level text") and _has(probs, "suptitle")


def test_figure_legend_rejected():
    fig, ax = clean_figure()
    ax.lines[0].set_label("series")
    fig.legend()
    assert _has(check(fig), "figure legend")


def test_panel_letters_accepted_and_outside_axes():
    from nacre.figs import style as st
    p = plt()
    fig, axes = p.subplots(1, 2, figsize=st.figsize("double", 6.0, REPO))
    for ax in axes:
        ax.plot([0, 1], [0, 1])
    letters = panel_letters(axes)
    assert [t.get_text() for t in letters] == ["a", "b"]
    assert all(t.get_gid() == PANEL_GID for t in letters)
    assert check(fig) == []
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for ax, t in zip(axes, letters):
        assert t.get_window_extent(r).y0 >= ax.bbox.y1 - 1e-6


def test_colour_bar_accepted():
    import numpy as np
    fig, ax = clean_figure()
    m = ax.pcolormesh(np.arange(3), np.arange(2), np.arange(6).reshape(2, 3), shading="nearest")
    cb = fig.colorbar(m, ax=ax)
    cb.set_label("z")
    assert check(fig) == []


def test_small_text_rejected():
    fig, ax = clean_figure()
    ax.xaxis.label.set_fontsize(style.min_font_pt(REPO) - 1)
    assert _has(check(fig), "below")


def test_thin_line_rejected():
    fig, ax = clean_figure()
    ax.lines[0].set_linewidth(style.min_line_pt(REPO) / 2)
    assert _has(check(fig), "line at")


def test_second_font_family_rejected():
    fig, ax = clean_figure()
    ax.xaxis.label.set_family("monospace")
    assert _has(check(fig), "font families")


def test_wrong_width_rejected():
    p = plt()
    fig, ax = p.subplots(figsize=(5.0, 3.0))
    ax.plot([0, 1], [0, 1])
    assert _has(check(fig), "column width")


def test_unknown_artist_rejected():
    from matplotlib.artist import Artist

    class Odd(Artist):
        def draw(self, renderer):
            pass

    fig, ax = clean_figure()
    ax.add_artist(Odd())
    assert _has(check(fig), "allow-list")


def test_assert_clean_raises_with_problems():
    fig, ax = clean_figure()
    ax.text(0, 0, "x")
    with pytest.raises(checker.FigureCheckError) as exc:
        checker.assert_clean(fig, REPO)
    assert exc.value.problems
