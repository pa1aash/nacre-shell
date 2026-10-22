"""Fig. 12: K2 dissolution map of the registered slurry grid per polymorph, with the acid-adjusted comparator."""
import re

from matplotlib.patches import Rectangle

from nacre.figs import dosegrid, regimes, style
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import axis_title, symbol

FIGURE = {
    "id": "fig12",
    "claim": ("In the registered alkaline slurry every polymorph passes K2 over part of the dose window and the "
              "Omega_bulk = 1 line runs through it; in the acid-adjusted state the carbonates are "
              "thermodynamically excluded at the low pH values and pass only near the top of the registered "
              "range, and the calcium phosphates differ among themselves."),
    "caption_key": (
        "(a to c) K2 verdict of calcite, aragonite and ACC over the registered total calcium dose (horizontal, "
        "log scale) and total dissolved carbonate (vertical) at the registered slurry pH value, ionic strength "
        "value and the wet-film water activity; fill and hatching: suitable against dissolution (dots), "
        "undetermined (plain), open (single hatching), thermodynamically excluded (cross hatching); line: "
        "Omega_bulk = 1 at the median activities. (d) Comparator: the acid-adjusted slurry state at each of "
        "its registered pH values; one row per carbonate and Ca-phosphate phase; a cell takes the regime of "
        "its grid cells (suitable where any cell passes, otherwise open where any is inconclusive, otherwise "
        "excluded); K2 only, no K3 or K4 verdict is drawn from this state."),
    "width": "double",
    "height_cm": 11.0,
    "schema": "figures/src/schemas/k2_grid.schema.json",
    "mock_input": "figures/src/mock/k2_grid.json",
    "input": "upstream:k2_grid_ph",
    "aux": {"params": {"mock": "figures/src/mock/params.yaml", "real": "lit/params.yaml"}},
}

POLYMORPHS = ("calcite", "aragonite", "ACC")
STATED = {"pH": "pH@value", "I": "I@value", "a_w": "wet_film"}  # the stated state of panels a to c
COMPETING = {"Li3PO4"}  # a competing phase of K3, not a Ca phosphate: not a comparator row
LABELS = {"HAp": "HAp", "ACP": "ACP", "OCP": "OCP", "b-TCP": "$\\beta$-TCP", "a-TCP": "$\\alpha$-TCP",
          "brushite": "brushite", "calcite": "calcite", "aragonite": "aragonite", "ACC": "ACC"}


def k2(data):
    return data["extensions"]["p0-w4"]["k2_grid"]


def _draw_cells(ax, cas, cts, cells, fills, lw):
    xe, ye = dosegrid.edges_log(cas), dosegrid.edges_lin(cts)
    for (i, j), c in cells.items():
        w = regimes.word(c["verdict"])
        ax.add_patch(Rectangle((xe[j], ye[i]), xe[j + 1] - xe[j], ye[i + 1] - ye[i], facecolor=fills[w],
                               edgecolor="black", linewidth=lw, hatch=regimes.HATCH[w]))
    ax.set_xscale("log")
    ax.set_xlim(xe[0], xe[-1])
    ax.set_ylim(ye[0], ye[-1])
    ax.set_xticks(cas, ["%g" % c for c in cas])
    ax.minorticks_off()
    ax.set_yticks(cts, ["%g" % c for c in cts])


def comparator_rows(data):
    """[(label, {pH: regime word})] for the carbonates and Ca phosphates of the acid-adjusted state."""
    acid = k2(data)["acid_adjusted"]
    blocks = [(n, acid["carbonate"][n]) for n in POLYMORPHS]
    blocks += [(b["ladder_phase"], b) for b in acid["phosphate"].values() if b["ladder_phase"] not in COMPETING]
    rows = []
    for name, blk in blocks:
        by_ph = {}
        for c in blk["cells"].values():
            by_ph.setdefault(c["axes"]["pH"], []).append(c["verdict"])
        if name not in LABELS:
            raise ValueError("fig12: no display label for %r" % name)
        rows.append((LABELS[name], {ph: regimes.aggregate(v) for ph, v in by_ph.items()}))
    return rows


def ph_value(text):
    m = re.match(r"^([0-9.]+)", text)
    return float(m.group(1))


def build(data, root, aux):
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    params = aux["params"]
    fills = regimes.fills(root)
    lw = style.min_line_pt(root)
    data_lw = float(style.applied(root)["line_width_data"]["value"])
    fig = plt.figure(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    gs = GridSpec(2, 3, figure=fig, height_ratios=[1.0, 1.15])
    axes = [fig.add_subplot(gs[0, k]) for k in range(3)] + [fig.add_subplot(gs[1, :])]
    for k, name in enumerate(POLYMORPHS):
        ax = axes[k]
        blk = k2(data)["carbonate"]["polymorphs"][name]
        cas, cts, cells = dosegrid.grid(blk["cells"], params, **STATED)
        _draw_cells(ax, cas, cts, cells, fills, lw)
        ksp = dosegrid.param_value(params, blk["ksp_key"])
        for seg in dosegrid.omega_one_line(cas, cts, cells, ksp):
            ax.plot(seg[:, 0], seg[:, 1], color="black", linewidth=data_lw)
        ax.set_xlabel(axis_title("Ca_T", root, unit=r"mol m$^{-3}$"))
        if k == 0:
            ax.set_ylabel(axis_title("C_T", root, unit=r"mol m$^{-3}$"))
        else:
            ax.tick_params(axis="y", labelleft=False)
    ax = axes[3]
    rows = comparator_rows(data)
    phs = sorted({p for _l, r in rows for p in r}, key=ph_value)
    for i, (_label, r) in enumerate(rows):
        for j, ph in enumerate(phs):
            w = r[ph]
            ax.add_patch(Rectangle((j - 0.5, -i - 0.5), 1.0, 1.0, facecolor=fills[w], edgecolor="black",
                                   linewidth=lw, hatch=regimes.HATCH[w]))
    ax.set_xlim(-0.5, len(phs) - 0.5)
    ax.set_ylim(-len(rows) + 0.5, 0.5)
    ax.set_xticks(range(len(phs)), ["%g" % ph_value(p) for p in phs])
    ax.set_yticks([-i for i in range(len(rows))], [l for l, _r in rows])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel(symbol("pH", root) + " of the acid-adjusted slurry")
    panel_letters(axes)
    return fig
