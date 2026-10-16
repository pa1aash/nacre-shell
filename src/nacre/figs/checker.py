"""Figure checker: walks every artist of a figure and enforces rule R7 and the RSC style limits.

R7: nothing is drawn inside a plot area except the data. Allowed outside the plot area: tick
labels, axis titles, colour-bar scales and panel letters. Not allowed anywhere: legends,
in-axes text, annotations, arrows, titles (other than panel letters), figure-level text.

The walk is an allow-list: an artist type the checker does not know is a failure, so a new
kind of decoration cannot slip through.

Style limits (from figures/style/rsc_spec.yaml, applied section): every visible text at least
font_size, all text in one font family, every visible stroke at least line_width_min, the
figure exactly one RSC column width and no taller than the RSC maximum.

The written PDF is checked as well, so that nothing added outside matplotlib's artist tree (or
by a later tool) escapes:
  data figures   every text span lies inside the box of a tick label, an axis title, a
                 colour-bar label or a panel letter (allowed_text_boxes, check_pdf_text);
  schematics     no text at all: no text spans, no fonts, no text operators (check_pdf_no_text),
                 every stroke at least the minimum width and the page one RSC column wide
                 (check_pdf_schematic).
"""
from matplotlib import font_manager
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.collections import Collection
from matplotlib.image import AxesImage
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.offsetbox import OffsetBox
from matplotlib.patches import Arrow, FancyArrow, FancyArrowPatch, Patch
from matplotlib.spines import Spine
from matplotlib.text import Annotation, Text

from nacre.figs.panels import PANEL_GID

ARROWS = (FancyArrow, FancyArrowPatch, Arrow)
_TOL_IN = 1e-3
_TOL_PT = 1e-6


class FigureCheckError(Exception):
    def __init__(self, problems):
        super().__init__("\n".join(problems))
        self.problems = problems


def _is_colorbar(ax):
    return getattr(ax, "_colorbar", None) is not None


def _titles(ax):
    return {id(ax.title): "center", id(ax._left_title): "left", id(ax._right_title): "right"}


def _name(ax, i):
    return "colorbar axes %d" % i if _is_colorbar(ax) else "axes %d" % i


def _walk_axes(ax, i, problems, letters):
    where = _name(ax, i)
    titles = _titles(ax)
    if ax.get_legend() is not None:
        problems.append("%s: legend" % where)
    for child in ax.get_children():
        if child is ax.patch or isinstance(child, (Spine, Axis)):
            continue
        if isinstance(child, Legend):
            continue  # reported above
        if isinstance(child, Annotation):
            problems.append("%s: annotation %r" % (where, child.get_text()))
        elif isinstance(child, Text):
            loc = titles.get(id(child))
            text = child.get_text()
            if loc is None:
                problems.append("%s: in-axes text %r" % (where, text))
            elif text.strip():
                if loc == "left" and child.get_gid() == PANEL_GID:
                    letters.append((ax, child))
                else:
                    problems.append("%s: %s title %r (keys and titles go in the caption)" % (where, loc, text))
        elif isinstance(child, ARROWS):
            problems.append("%s: arrow %s" % (where, type(child).__name__))
        elif isinstance(child, OffsetBox):
            problems.append("%s: offset box %s (callout or anchored text)" % (where, type(child).__name__))
        elif isinstance(child, (Line2D, Collection, Patch, AxesImage)):
            continue
        else:
            problems.append("%s: artist %s not on the allow-list" % (where, type(child).__name__))


def _walk_figure(fig, problems):
    if fig.legends:
        problems.append("figure: %d figure legend(s)" % len(fig.legends))
    sup = getattr(fig, "_suptitle", None)
    if sup is not None and sup.get_text().strip():
        problems.append("figure: suptitle %r" % sup.get_text())
    for attr in ("_supxlabel", "_supylabel"):
        t = getattr(fig, attr, None)
        if t is not None and t.get_text().strip():
            problems.append("figure: %s %r" % (attr.strip("_"), t.get_text()))
    for t in fig.texts:
        problems.append("figure: figure-level text %r" % t.get_text())
    for a in fig.artists + fig.patches + fig.lines + fig.images:
        problems.append("figure: figure-level artist %s" % type(a).__name__)
    for sub in getattr(fig, "subfigs", []):
        _walk_figure(sub, problems)


def _visible_texts(fig):
    out = []
    for t in fig.findobj(Text):
        if t.get_visible() and t.get_text().strip() and t.get_figure(root=True) is fig:
            out.append(t)
    return out


def _families(texts):
    fams = set()
    for t in texts:
        path = font_manager.findfont(t.get_fontproperties())
        fams.add(font_manager.get_font(path).family_name)
    return fams


def _thin(lw, minimum):
    """A visible stroke thinner than the minimum (zero width means no stroke)."""
    return lw > _TOL_PT and lw + _TOL_PT < minimum


def _overlaps(a, b):
    return a.x0 < b.x1 and b.x0 < a.x1 and a.y0 < b.y1 and b.y0 < a.y1


def check(fig, min_font_pt=None, min_line_pt=None, widths_in=None, max_height_in=None):
    """Return a list of problems (empty when the figure passes)."""
    problems = []
    letters = []
    for i, ax in enumerate(fig.axes):
        _walk_axes(ax, i, problems, letters)
    _walk_figure(fig, problems)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    plot_axes = [ax for ax in fig.axes if not _is_colorbar(ax)]
    for ax, t in letters:
        box = t.get_window_extent(renderer)
        for other in fig.axes:
            if _overlaps(box, other.bbox):
                problems.append("panel letter %r overlaps a plot area" % t.get_text())
                break
    for ax in fig.axes:
        if _is_colorbar(ax):
            for p in plot_axes:
                if _overlaps(ax.bbox, p.bbox):
                    problems.append("colour bar overlaps a plot area")

    texts = _visible_texts(fig)
    if min_font_pt is not None:
        for t in texts:
            if t.get_fontsize() + _TOL_PT < min_font_pt:
                problems.append("text %r at %.2f pt is below %.1f pt" % (t.get_text(), t.get_fontsize(), min_font_pt))
    fams = _families(texts)
    if len(fams) > 1:
        problems.append("text uses %d font families: %s" % (len(fams), ", ".join(sorted(fams))))

    if min_line_pt is not None:
        for a in fig.findobj(Line2D):
            if a.get_visible() and a.get_linestyle() not in ("None", "none", "", " ") and len(a.get_xdata()) > 1:
                if _thin(a.get_linewidth(), min_line_pt):
                    problems.append("line at %.2f pt is below %.1f pt" % (a.get_linewidth(), min_line_pt))
            if a.get_visible() and a.get_marker() not in ("None", "none", "", " ", None):
                mew = a.get_markeredgewidth()
                if _thin(mew, min_line_pt):
                    problems.append("marker edge at %.2f pt is below %.1f pt" % (mew, min_line_pt))
        for c in fig.findobj(Collection):
            if not c.get_visible() or len(c.get_paths()) == 0 or len(c.get_edgecolor()) == 0:
                continue
            for lw in set(float(x) for x in c.get_linewidths()):
                if _thin(lw, min_line_pt):
                    problems.append("%s stroke at %.2f pt is below %.1f pt" % (type(c).__name__, lw, min_line_pt))
        for p in fig.findobj(Patch):
            if p.get_visible() and p.get_edgecolor()[3] > 0 and _thin(p.get_linewidth(), min_line_pt):
                problems.append("%s edge at %.2f pt is below %.1f pt" % (type(p).__name__, p.get_linewidth(), min_line_pt))

    w, h = fig.get_size_inches()
    if widths_in is not None and not any(abs(w - x) < _TOL_IN for x in widths_in):
        problems.append("figure width %.4f in is not an RSC column width" % w)
    if max_height_in is not None and h > max_height_in + _TOL_IN:
        problems.append("figure height %.4f in exceeds the RSC maximum" % h)
    return problems


def check_rsc(fig, root=None):
    """check() with the limits of figures/style/rsc_spec.yaml."""
    from nacre.figs import style
    return check(
        fig,
        min_font_pt=style.min_font_pt(root),
        min_line_pt=style.min_line_pt(root),
        widths_in=(style.width_in("single", root), style.width_in("double", root)),
        max_height_in=style.max_height_in(root),
    )


def assert_clean(fig, root=None):
    problems = check_rsc(fig, root)
    if problems:
        raise FigureCheckError(problems)


# ------------------------------------------------------------------------- PDF-level checks

_PT_PER_IN = 72.0
_BOX_PAD_PT = 1.0


def _fig_box_pt(fig, bbox):
    """A display-space bbox as (x0, y0, x1, y1) in PDF points, origin at the top left."""
    w_px, h_px = fig.bbox.width, fig.bbox.height
    w_pt, h_pt = (x * _PT_PER_IN for x in fig.get_size_inches())
    x0, x1 = bbox.x0 / w_px * w_pt, bbox.x1 / w_px * w_pt
    y0, y1 = h_pt - bbox.y1 / h_px * h_pt, h_pt - bbox.y0 / h_px * h_pt
    return (x0 - _BOX_PAD_PT, y0 - _BOX_PAD_PT, x1 + _BOX_PAD_PT, y1 + _BOX_PAD_PT)


def allowed_text_boxes(fig):
    """[(kind, text, box)] of every text a data figure may contain, in PDF points.

    Allowed: tick labels and the axis offset text (the scale), axis titles, colour-bar tick
    labels and title (a colour bar is an axes), and panel letters. Call after the figure has
    been laid out (check() draws it).
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    out = []
    for ax in fig.axes:
        cb = "colour-bar " if _is_colorbar(ax) else ""
        for axis in (ax.xaxis, ax.yaxis):
            texts = [("%stick label" % cb, t) for t in axis.get_ticklabels(which="both")]
            texts += [("%saxis title" % cb, axis.label), ("%sscale" % cb, axis.get_offset_text())]
            for kind, t in texts:
                if t.get_visible() and t.get_text().strip():
                    out.append((kind, t.get_text(), _fig_box_pt(fig, t.get_window_extent(r))))
        t = ax._left_title
        if t.get_visible() and t.get_text().strip() and t.get_gid() == PANEL_GID:
            out.append(("panel letter", t.get_text(), _fig_box_pt(fig, t.get_window_extent(r))))
    return out


def pdf_text_spans(pdf_path):
    """[(page, text, (x0, y0, x1, y1))] of every text span in a PDF, in points, top-left origin."""
    import pymupdf
    out = []
    with pymupdf.open(pdf_path) as doc:
        for pno, page in enumerate(doc):
            for block in page.get_text("rawdict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        text = "".join(c["c"] for c in span["chars"])
                        if text.strip():
                            out.append((pno, text, tuple(span["bbox"])))
    return out


def _inside(box, outer):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return outer[0] <= cx <= outer[2] and outer[1] <= cy <= outer[3]


def check_pdf_text(pdf_path, boxes):
    """Problems for text spans of a data-figure PDF that lie outside every allowed box."""
    problems = []
    for pno, text, bbox in pdf_text_spans(pdf_path):
        if not any(_inside(bbox, b) for _k, _t, b in boxes):
            problems.append("PDF text %r at (%.1f, %.1f) pt is not a tick label, axis title, colour-bar "
                            "label or panel letter" % (text, bbox[0], bbox[1]))
    return problems


def _content_has_text_operators(doc, page):
    import re
    data = b"".join(doc.xref_stream(x) or b"" for x in page.get_contents())
    return re.search(rb"(^|[\s\]])BT([\s]|$)", data) is not None


def check_pdf_no_text(pdf_path):
    """Problems for any text in a schematic PDF (R7: the default schematics carry no text)."""
    import pymupdf
    problems = []
    for pno, text, bbox in pdf_text_spans(pdf_path):
        problems.append("schematic PDF page %d contains text %r at (%.1f, %.1f) pt" % (pno, text, bbox[0], bbox[1]))
    with pymupdf.open(pdf_path) as doc:
        for pno, page in enumerate(doc):
            fonts = page.get_fonts(full=True)
            if fonts:
                problems.append("schematic PDF page %d embeds %d font(s): %s"
                                % (pno, len(fonts), ", ".join(sorted({f[3] for f in fonts}))))
            if _content_has_text_operators(doc, page):
                problems.append("schematic PDF page %d has a text object (BT operator)" % pno)
    return problems


def check_pdf_schematic(pdf_path, min_line_pt, widths_pt, max_height_pt, text_free=True):
    """No text (when text_free), strokes at least min_line_pt, one page at an RSC column width."""
    import pymupdf
    problems = check_pdf_no_text(pdf_path) if text_free else []
    with pymupdf.open(pdf_path) as doc:
        if doc.page_count != 1:
            problems.append("schematic PDF has %d pages" % doc.page_count)
        for pno, page in enumerate(doc):
            w, h = page.rect.width, page.rect.height
            if not any(abs(w - x) < 0.5 for x in widths_pt):
                problems.append("schematic page width %.2f pt is not an RSC column width" % w)
            if h > max_height_pt + 0.5:
                problems.append("schematic page height %.2f pt exceeds the RSC maximum" % h)
            # PDF user space is in PostScript points (1/72 in), the unit the spec's pt values use.
            thin = sorted({round(d["width"], 3) for d in page.get_drawings()
                           if d.get("type") in ("s", "fs") and d.get("width") is not None
                           and _thin(d["width"], min_line_pt)})
            if thin:
                problems.append("schematic strokes below %.1f pt: %s" % (min_line_pt, ", ".join("%g" % t for t in thin)))
    return problems
