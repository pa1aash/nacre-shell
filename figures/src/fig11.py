"""Fig. 11: the pH window in which an Al oxide film stays, at the registered dissolved-Al levels."""
from matplotlib.patches import Rectangle

from nacre.figs import style
from nacre.figs.symbols import axis_title

FIGURE = {
    "id": "fig11",
    "claim": ("The pH window of an aluminium oxide film narrows as the allowed dissolved aluminium falls: the "
              "amorphous hydroxide that governs the film has its window inside the crystalline boehmite window "
              "and none at the lowest level."),
    "caption_key": (
        "Horizontal axis: pH. Top group: the two published statements (grey bars, no stated Al level for the "
        "first). Below it one group per dissolved-Al level (tick labels, mM), highest first; within a group the "
        "upper bar (black) is amorphous Al(OH)3, the governing film phase, and the lower bar (blue, hatched) is "
        "boehmite, the crystalline reference. A bar ends at the computed pH limit; an open circle at the right "
        "edge: the window continues beyond the computed pH range; an open square at the left edge: no pH at "
        "which the film stays at that level. Computed at 298.15 K with activities equal to concentrations."),
    "width": "single",
    "height_cm": 6.5,
    "schema": "figures/src/schemas/passivation_window_v3.schema.json",
    "mock_input": "figures/src/mock/passivation_window_v3.json",
    "input": "upstream:passivation_window_v3",
    "aux": {"al_window": {"mock": "figures/src/mock/al_window.json", "real": "upstream:al_window"}},
}

SERIES = (("governing", "Al(OH)3 am", "black", None), ("reference", "boehmite", "blue", "////"))
BAR = 0.7
GAP = 0.9


def _ph(text, hi):
    """(value or None, clipped) for a pH cell: a number, '>10' (clipped at the range end) or empty."""
    text = text.strip()
    if not text:
        return None, False
    if text.startswith(">"):
        if float(text[1:]) != hi:
            raise ValueError("fig11: %r is not clipped at the pH range end %g" % (text, hi))
        return hi, True
    return float(text), False


def windows(data, ph_range):
    """{level: {series: (lower, upper, upper_clipped) or None}} for the governing and reference solids."""
    out = {}
    for r in data["rows"]:
        for role, solid, _c, _h in SERIES:
            if r["solid"] == solid and r["role"].startswith(role):
                lo, _ = _ph(r["ph_lower"], ph_range[1])
                up, clipped = _ph(r["ph_upper"], ph_range[1])
                if (lo is None) != (up is None):
                    raise ValueError("fig11: %s at %s has one pH limit only" % (solid, r["al_level_M"]))
                lvl = float(r["al_level_M"])
                if (role in out.get(lvl, {})):
                    raise ValueError("fig11: two rows for %s at %g M" % (solid, lvl))
                out.setdefault(lvl, {})[role] = None if lo is None else (lo, up, clipped)
    for lvl, d in out.items():
        if set(d) != {s[0] for s in SERIES}:
            raise ValueError("fig11: level %g M lacks a series" % lvl)
    if not out:
        raise ValueError("fig11: no governing or reference rows")
    return out


def build(data, root, aux):
    import matplotlib.pyplot as plt

    info = aux["al_window"]
    ph_range = [float(x) for x in info["conventions"]["ph_range"]]
    wins = windows(data, ph_range)
    pub = [(k, info["published"][k]) for k in sorted(info["published"])]
    lw = style.min_line_pt(root)
    grey = style.palette(root)["categorical"]["okabe_ito"]["gray"]["hex"]
    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    cur = 0.0

    def bar(y, lo, up, face, hatch):
        ax.add_patch(Rectangle((lo, y - BAR / 2), up - lo, BAR, facecolor=face, edgecolor="black", linewidth=lw,
                               hatch=hatch))

    for _k, p in pub:
        bar(cur, float(p["lower"]), float(p["upper"]), grey, None)
        cur -= 1.0
    ticks, labels = [], []
    blue = style.categorical("blue", root)
    for lvl in sorted(wins, reverse=True):
        cur -= GAP - 1.0 + 0.0
        top = cur
        for k, (role, _s, colour, hatch) in enumerate(SERIES):
            y, w = cur, wins[lvl][role]
            face = "black" if colour == "black" else blue
            if w is None:
                ax.plot([ph_range[0]], [y], linestyle="none", marker="s", markerfacecolor="white",
                        markeredgecolor="black", markeredgewidth=lw, clip_on=False, zorder=4)
            else:
                bar(y, w[0], w[1], face, hatch)
                if w[2]:
                    ax.plot([ph_range[1]], [y], linestyle="none", marker="o", markerfacecolor="white",
                            markeredgecolor="black", markeredgewidth=lw, clip_on=False, zorder=4)
            cur -= 1.0
        ticks.append(top - 0.5)
        labels.append("%g" % (lvl * 1e3))
    ax.set_xlim(*ph_range)
    ax.set_ylim(cur + 0.4, 0.7)
    ax.set_yticks(ticks, labels)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel(axis_title("pH", root))
    ax.set_ylabel("Dissolved Al (mM)")
    return fig
