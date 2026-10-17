"""Fig. 7: where the carbonate phase is stable, in the slurry (pH, E) and in the cell window."""
import re

import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle

from nacre.figs import style
from nacre.figs.colours import distinct_fills
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import symbol

FIGURE = {
    "id": "fig7",
    "claim": ("CaCO3 is thermodynamically stable over a bounded (pH, E) region of the slurry and between two "
              "potential limits in the cell; whether each regime's operating range lies inside, and whether a "
              "limit is determined at all, decides the stability link."),
    "caption_key": (
        "(a) R-slurry, bulk state (regime activities of Ca2+ and CO3 2-), potential vs SHE. Fill: class of "
        "the predominant domain, in the caption's order: CaCO3 solid present; an Al solid without CaCO3; no "
        "solid. Thin black lines: boundaries between domains (the caption lists each domain's components by "
        "position). Dashed rectangle: the regime's design range of pH and potential (parameter table). The "
        "enriched state is not drawn: at equilibrium C5 is decided at the bulk state, and the caption reports "
        "the enriched state only as a labelled non-equilibrium sensitivity. (b) R-cell, potential vs Li+/Li. "
        "One group of rows per phase (tick label); top row, black: the window used (the lowest oxidation and "
        "highest reduction limit over the gas-reference schemes); rows below: each scheme, in the caption's "
        "colour order. Solid segment with end ticks: both limits determined. Dotted continuation to the axis "
        "edge from an open circle: the limit on that side is undetermined (status undetermined, never read as "
        "a pass; the caption gives the reason). Grey band: the regime's operating range E_min to E_max. The "
        "caption states the active sink assumption."),
    "width": "double",
    "height_cm": 7.0,
    "schema": "upstream:results_schema",
    "mock_input": "figures/src/mock/stability.json",
    "input": "results/preprint/pourbaix/stability.json",
    "aux": {"params": {"mock": "figures/src/mock/params.yaml", "real": "lit/params.yaml"}},
}

FRAMING_SOLID = "CaCO3"
CLASSES = ("framing_solid", "other_solid", "no_solid")
SCHEME_COLOURS = ("blue", "vermillion", "bluishgreen", "orange")


def domain_class(phase):
    """Class of a domain identity: CaCO3 solid present, another solid only, or no solid."""
    solids = [c["species"] for c in phase["components"] if c["kind"] == "solid"]
    if any(re.sub(r"\(s\)$", "", s) == FRAMING_SOLID for s in solids):
        return "framing_solid"
    return "other_solid" if solids else "no_solid"


def _edges(centres):
    c = np.asarray(centres, dtype=float)
    mid = (c[1:] + c[:-1]) / 2.0
    return np.concatenate([[c[0] - (mid[0] - c[0])], mid, [c[-1] + (c[-1] - mid[-1])]])


def boundary_segments(index_grid, ph, e):
    """Line segments on the cell edges between grid cells of different domain index."""
    g = np.asarray(index_grid)
    xe, ye = _edges(ph), _edges(e)
    segs = []
    for i in range(g.shape[0]):
        for j in range(g.shape[1] - 1):
            if g[i, j] != g[i, j + 1]:
                segs.append([(xe[j + 1], ye[i]), (xe[j + 1], ye[i + 1])])
    for i in range(g.shape[0] - 1):
        for j in range(g.shape[1]):
            if g[i, j] != g[i + 1, j]:
                segs.append([(xe[j], ye[i + 1]), (xe[j + 1], ye[i + 1])])
    return segs


def param(params, dotted):
    node = params
    for part in dotted.split("."):
        node = node[part]
    return node


def _formula_tick(name):
    return "$\\mathrm{%s}$" % re.sub(r"(\d+)", r"_{\1}", name)


def _panel_slurry(ax, regime, params, root, fills):
    ph, e = regime["axes"]["pH"], regime["axes"]["E_V"]
    st = regime["states"]["bulk"]
    cls_of = {p["index"]: CLASSES.index(domain_class(p)) for p in st["phases"]}
    g = np.asarray(st["domains"]["index_grid"])
    c = np.vectorize(lambda k: cls_of.get(int(k), -1))(g).astype(float)
    c = np.ma.masked_less(c, 0)
    ax.pcolormesh(_edges(ph), _edges(e), c, cmap=ListedColormap(fills), vmin=-0.5, vmax=len(CLASSES) - 0.5,
                  shading="flat", rasterized=False, edgecolors="none", linewidth=0)
    lw = style.min_line_pt(root)
    ax.add_collection(LineCollection(boundary_segments(g, ph, e), colors="black", linewidths=lw))
    p_rng = param(params, "regimes.R-slurry.parameters.pH_range")["range"]
    e_rng = param(params, "regimes.R-slurry.parameters.E_SHE_range")["range"]
    if p_rng and e_rng:
        ax.add_patch(Rectangle((p_rng["min"], e_rng["min"]), p_rng["max"] - p_rng["min"], e_rng["max"] - e_rng["min"],
                               fill=False, edgecolor="black", linewidth=style.applied(root)["line_width_data"]["value"],
                               linestyle=(0, (4, 2))))
    ax.set_xlim(_edges(ph)[0], _edges(ph)[-1])
    ax.set_ylim(_edges(e)[0], _edges(e)[-1])
    ax.set_xlabel(symbol("pH", root))
    ax.set_ylabel("%s (V vs SHE)" % symbol("E_SHE", root))


def _rows(windows):
    """[(phase, label or None, colour name or 'black', limits {reduction, oxidation})] top to bottom."""
    rows = []
    schemes = sorted({s for w in windows.values() for s in list(w.get("oxidation_by_scheme", {}))
                      + list(w.get("reduction_by_scheme", {}))})
    for phase, w in windows.items():
        rows.append((phase, phase, "black", {"reduction": w["reduction"], "oxidation": w["oxidation"]}))
        for k, s in enumerate(schemes):
            red = w.get("reduction_by_scheme", {}).get(s, w["reduction"])
            ox = w.get("oxidation_by_scheme", {}).get(s, w["oxidation"])
            rows.append((phase, None, SCHEME_COLOURS[k % len(SCHEME_COLOURS)], {"reduction": red, "oxidation": ox}))
    return rows, schemes


def _panel_cell(ax, regime, params, root):
    lw = style.min_line_pt(root)
    data_lw = float(style.applied(root)["line_width_data"]["value"])
    rows, _schemes = _rows(regime["windows"])
    finite = [lim["value_V"] for _p, _l, _c, w in rows for lim in w.values() if lim["status"] == "ok"]
    e_min = param(params, "regimes.R-cell.parameters.E_min")["value"]
    e_max = param(params, "regimes.R-cell.parameters.E_max")["value"]
    span = finite + [v for v in (e_min, e_max) if v is not None]
    x_lo, x_hi = np.floor(min(span)) - 0.5, np.ceil(max(span)) + 0.5
    if e_min is not None and e_max is not None:
        ax.axvspan(e_min, e_max, color=style.palette(root)["categorical"]["okabe_ito"]["gray"]["hex"], alpha=0.35,
                   linewidth=0)
    y = np.arange(len(rows))[::-1].astype(float)
    ticks, labels = [], []
    for yi, (_phase, label, cname, w) in zip(y, rows):
        colour = "black" if cname == "black" else style.categorical(cname, root)
        red, ox = w["reduction"], w["oxidation"]
        lo = red["value_V"] if red["status"] == "ok" else None
        hi = ox["value_V"] if ox["status"] == "ok" else None
        dotted = {"color": colour, "linewidth": data_lw, "linestyle": (0, (1, 1.5)), "clip_on": False}
        if lo is not None and hi is not None:
            ax.plot([lo, hi], [yi, yi], color=colour, linewidth=data_lw, marker="|", markeredgewidth=data_lw)
        elif lo is None and hi is None:
            ax.plot([x_lo, x_hi], [yi, yi], **dotted)
        else:
            known, edge = (hi, x_lo) if lo is None else (lo, x_hi)
            ax.plot([known, edge], [yi, yi], **dotted)
            ax.plot([known], [yi], linestyle="none", marker="o", markerfacecolor="white", markeredgecolor=colour,
                    markeredgewidth=lw)
        if label is not None:
            ticks.append(yi)
            labels.append(_formula_tick(label))
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y.min() - 0.7, y.max() + 0.7)
    ax.set_yticks(ticks, labels)
    ax.set_xlabel("%s (V vs Li$^{+}$/Li)" % symbol("E_Li", root))


def build(data, root, aux):
    import matplotlib.pyplot as plt

    params = aux["params"]
    stab = data["stability"]
    fig, (ax_a, ax_b) = plt.subplots(1, 2, gridspec_kw={"width_ratios": [3, 2]},
                                     figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    fills, _names, _f, _d = distinct_fills(len(CLASSES), root)
    if "R-slurry" in stab:
        _panel_slurry(ax_a, stab["R-slurry"], params, root, fills)
    if "R-cell" in stab:
        _panel_cell(ax_b, stab["R-cell"], params, root)
    panel_letters([ax_a, ax_b])
    return fig
