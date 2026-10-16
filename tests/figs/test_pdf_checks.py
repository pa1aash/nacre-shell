"""PDF-level checks: data figures hold only tick labels, axis titles, colour-bar text and panel
letters; schematics hold no text at all. Every rule is exercised with a planted violation."""
import shutil

import pytest
from figs_helpers import REPO, clean_figure, plt

from nacre.figs import checker, schematic, style
from nacre.figs.panels import panel_letters


@pytest.fixture(autouse=True)
def _close():
    yield
    plt().close("all")


def _save(fig, path):
    boxes = checker.allowed_text_boxes(fig)
    fig.savefig(path, format="pdf")
    return boxes


def _blank_pdf(path, width_pt, height_pt=100.0, stroke=0.5, text=None):
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page(width=width_pt, height=height_pt)
    page.draw_line((10, 50), (90, 50), width=stroke)
    if text:
        page.insert_text((20, 30), text, fontsize=7)
    doc.save(str(path))


def _single_pt():
    return style.width_in("single", REPO) * 72.0


def _schematic_check(path, text_free=True):
    return checker.check_pdf_schematic(path, style.min_line_pt(REPO), (_single_pt(),),
                                       style.max_height_in(REPO) * 72.0, text_free=text_free)


# ---------------------------------------------------------------------------- data figures

def test_clean_data_figure_pdf_passes(tmp_path):
    fig, ax = clean_figure()
    panel_letters([ax])
    boxes = _save(fig, tmp_path / "f.pdf")
    assert checker.check_pdf_text(tmp_path / "f.pdf", boxes) == []
    kinds = {k for k, _t, _b in boxes}
    assert {"tick label", "axis title", "panel letter"} <= kinds


def test_colour_bar_text_is_allowed(tmp_path):
    import numpy as np
    fig, ax = clean_figure()
    mesh = ax.pcolormesh(np.arange(4.0).reshape(2, 2))
    fig.colorbar(mesh, ax=ax).set_label("z")
    boxes = _save(fig, tmp_path / "f.pdf")
    assert any(k.startswith("colour-bar") for k, _t, _b in boxes)
    assert checker.check_pdf_text(tmp_path / "f.pdf", boxes) == []


def test_planted_in_axes_text_found_in_the_pdf(tmp_path):
    fig, ax = clean_figure()
    ax.text(1.0, 2.0, "planted")
    boxes = _save(fig, tmp_path / "f.pdf")
    probs = checker.check_pdf_text(tmp_path / "f.pdf", boxes)
    assert any("planted" in p for p in probs)


def test_text_added_to_the_pdf_after_saving_is_found(tmp_path):
    import pymupdf
    fig, _ax = clean_figure()
    boxes = _save(fig, tmp_path / "f.pdf")
    doc = pymupdf.open(tmp_path / "f.pdf")
    page = doc[0]
    page.insert_text((page.rect.width / 2, page.rect.height / 2), "callout", fontsize=7)
    doc.save(tmp_path / "g.pdf")
    probs = checker.check_pdf_text(tmp_path / "g.pdf", boxes)
    assert any("callout" in p for p in probs)


def test_figure_level_text_found_in_the_pdf(tmp_path):
    fig, _ax = clean_figure()
    fig.text(0.5, 0.5, "note")
    boxes = _save(fig, tmp_path / "f.pdf")
    assert any("note" in p for p in checker.check_pdf_text(tmp_path / "f.pdf", boxes))


def test_build_runs_the_pdf_check(tmp_path, monkeypatch):
    from nacre.figs import build
    mod = build.load_template(REPO / "figures/src/fig4.py")
    data, path = build.load_input(REPO, mod, mock=True)
    real = mod.build

    def planted(d, root, aux):
        fig = real(d, root, aux)
        fig.axes[0].figure.canvas.draw()
        return fig

    monkeypatch.setattr(mod, "build", planted)
    monkeypatch.setattr(checker, "check_pdf_text", lambda pdf, boxes: ["planted PDF text"])
    with pytest.raises(checker.FigureCheckError, match="planted PDF text"):
        build.render(REPO, mod, data, path, REPO / "figures/out/mock", cvd=False)


# ---------------------------------------------------------------------------- schematics

def test_text_free_schematic_passes(tmp_path):
    _blank_pdf(tmp_path / "s.pdf", _single_pt())
    assert _schematic_check(tmp_path / "s.pdf") == []


def test_planted_text_in_schematic_rejected(tmp_path):
    _blank_pdf(tmp_path / "s.pdf", _single_pt(), text="a")
    probs = _schematic_check(tmp_path / "s.pdf")
    assert any("contains text" in p for p in probs)
    assert any("font" in p for p in probs)
    assert any("BT operator" in p for p in probs)


def test_text_allowed_in_a_variant(tmp_path):
    _blank_pdf(tmp_path / "s.pdf", _single_pt(), text="a")
    assert _schematic_check(tmp_path / "s.pdf", text_free=False) == []


def test_thin_stroke_in_schematic_rejected(tmp_path):
    _blank_pdf(tmp_path / "s.pdf", _single_pt(), stroke=0.3)
    assert any("strokes below" in p for p in _schematic_check(tmp_path / "s.pdf"))


def test_wrong_page_width_rejected(tmp_path):
    _blank_pdf(tmp_path / "s.pdf", 300.0)
    assert any("column width" in p for p in _schematic_check(tmp_path / "s.pdf"))


def test_too_tall_page_rejected(tmp_path):
    _blank_pdf(tmp_path / "s.pdf", _single_pt(), height_pt=800.0)
    assert any("exceeds" in p for p in _schematic_check(tmp_path / "s.pdf"))


@pytest.mark.parametrize("sid", ["fig2", "fig3", "fig3_symbols"])
def test_committed_schematics_pass(sid):
    entry = schematic.table(REPO)[sid]
    pdf = REPO / "figures/out" / entry["out"]
    assert schematic.check(REPO, pdf, entry) == []


def test_default_schematics_are_text_free_and_the_variant_is_not():
    t = schematic.table(REPO)
    assert t["fig2"]["text_free"] and t["fig3"]["text_free"]
    assert not t["fig3_symbols"]["text_free"] and t["fig3_symbols"]["variant_of"] == "fig3"
    variant = REPO / "figures/out" / t["fig3_symbols"]["out"]
    texts = {s for _p, s, _b in checker.pdf_text_spans(variant)}
    assert texts and checker.check_pdf_no_text(variant)


@pytest.mark.skipif(shutil.which("latexmk") is None, reason="latexmk not installed")
def test_schematic_rebuild_is_byte_identical():
    entry = schematic.table(REPO)["fig3"]
    assert schematic.compile_pdf(REPO, entry) == (REPO / "figures/out" / entry["out"]).read_bytes()


def test_pictograms_are_current():
    from nacre.figs import pictograms
    assert pictograms.out_path(REPO).read_text() == pictograms.text(REPO)
