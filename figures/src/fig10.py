"""Fig. 10: DFT minus experiment formation enthalpy per phase against the registered error band."""
import numpy as np
from matplotlib.patches import Rectangle

from nacre.figs import style

FIGURE = {
    "id": "fig10",
    "claim": ("The DFT formation enthalpies lie inside the registered error band for the ionic orthophosphates "
              "and outside it, always on the over-bound side, for the condensed, acid and hydrated phosphates, the "
              "aluminium hydroxide and the sink salt, so the phosphate benchmark does not pass as a set."),
    "caption_key": (
        "One row per phase with a like-for-like formation enthalpy, grouped by family (gaps between groups: "
        "phosphates, silicates, Al-O-H phases, the sink salt) and ordered by error within a group. Horizontal "
        "axis: DFT minus tabulated formation enthalpy per atom. Grey band: the registered error band. "
        "Marker: filled circle, inside the band (benchmarked); open square, outside the band; open diamond, no "
        "like-for-like experimental phase (the tabulated phase is a glass). The caption states the uniform "
        "oxide correction per oxygen as the explanation of the outside rows."),
    "width": "single",
    "height_cm": 8.5,
    "schema": "figures/src/schemas/benchmark_w51.schema.json",
    "mock_input": "figures/src/mock/benchmark_w51.json",
    "input": "upstream:benchmark_w51",
    "aux": {"summary": {"mock": "figures/src/mock/benchmark_w51_summary.json",
                        "real": "upstream:benchmark_w51_summary"}},
}

VALUE = "dft_minus_dfH_kJ_per_atom"
FAMILIES = ("phosphate", "silicate", "Al-O-H", "sink salt")
STATUS = (("dft-benchmarked", "o", True), ("dft-benchmark-failed", "s", False), ("dft-unbenchmarked", "D", False))
LABELS = {
    "P2O5": "P$_2$O$_5$", "HAp": "HAp", "b-TCP": "$\\beta$-TCP", "a-TCP": "$\\alpha$-TCP", "brushite": "brushite",
    "monetite": "monetite", "Ca2P2O7": "Ca$_2$P$_2$O$_7$", "AlPO4": "AlPO$_4$", "Li3PO4": "Li$_3$PO$_4$",
    "LiPO3": "LiPO$_3$", "LiPO3 glass": "LiPO$_3$ glass", "Ca(PO3)2 glass": "Ca(PO$_3$)$_2$ glass",
    "CaSiO3": "CaSiO$_3$", "Ca2SiO4": "Ca$_2$SiO$_4$", "Li2SiO3": "Li$_2$SiO$_3$", "gibbsite": "gibbsite",
    "LiClO4": "LiClO$_4$",
}
GAP = 0.8


def status_of(display):
    for name, marker, filled in STATUS:
        if display.startswith(name):
            return name, marker, filled
    raise ValueError("fig10: unknown benchmark status %r" % display)


def points(data, band):
    """[(family, phase, error, status)] for the rows that have a like-for-like value.

    A benchmarked row must lie inside the band and a row marked as outside it must lie outside;
    the figure is refused otherwise, so the markers and the band always agree.
    """
    out = []
    for r in data["rows"]:
        if not r[VALUE].strip():
            continue
        v = float(r[VALUE])
        name = status_of(r["display"])[0]
        if r["family"] not in FAMILIES:
            raise ValueError("fig10: no group for family %r" % r["family"])
        if r["phase"] not in LABELS:
            raise ValueError("fig10: no display label for phase %r" % r["phase"])
        if name == "dft-benchmarked" and abs(v) > band:
            raise ValueError("fig10: %s is marked benchmarked but |%g| exceeds the band %g" % (r["phase"], v, band))
        if name == "dft-benchmark-failed" and abs(v) <= band:
            raise ValueError("fig10: %s is marked outside the band but |%g| is within %g" % (r["phase"], v, band))
        out.append((r["family"], r["phase"], v, name))
    return out


def build(data, root, aux):
    import matplotlib.pyplot as plt

    band = float(aux["summary"]["summary"]["e_form"]["max"])
    pts = points(data, band)
    lw = style.min_line_pt(root)
    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    y, ticks, labels, cur, first = {}, [], [], 0.0, True
    for fam in FAMILIES:
        rows = sorted((p for p in pts if p[0] == fam), key=lambda p: p[2], reverse=True)
        if not rows:
            continue
        if not first:
            cur -= GAP
        first = False
        for _f, ph, v, st in rows:
            y[ph] = cur
            ticks.append(cur)
            labels.append(LABELS[ph])
            cur -= 1.0
    lo = np.floor(min(p[2] for p in pts) / 5.0) * 5.0 - 2.0
    hi = max(band, max(p[2] for p in pts)) + 3.0
    ax.add_patch(Rectangle((-band, min(y.values()) - 0.7), 2 * band, max(y.values()) - min(y.values()) + 1.4,
                           facecolor=style.palette(root)["categorical"]["okabe_ito"]["gray"]["hex"], alpha=0.3,
                           edgecolor="none", linewidth=0, zorder=0))
    ax.axvline(0.0, color="black", linewidth=lw, zorder=1)
    for _f, ph, v, st in pts:
        _n, marker, filled = status_of(st)
        ax.plot([v], [y[ph]], linestyle="none", marker=marker, markersize=4.5, markerfacecolor="black" if filled else "white",
                markeredgecolor="black", markeredgewidth=lw, zorder=3)
    ax.set_xlim(lo, hi)
    ax.set_ylim(min(y.values()) - 0.7, max(y.values()) + 0.7)
    ax.set_yticks(ticks, labels)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("DFT $-$ experiment (kJ mol$^{-1}$ atom$^{-1}$)")
    return fig
