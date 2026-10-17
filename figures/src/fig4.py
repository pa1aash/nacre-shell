"""Fig. 4: retrodiction, the predicted barrier difference of each case and the permutation null."""
import numpy as np

from nacre.figs import style
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import entry

FIGURE = {
    "id": "fig4",
    "claim": ("The model orders the two surfaces of a case as observed where the case's input acts on the "
              "template-nucleus contact (crystal-template adhesion, gamma_sn), and mostly fails where it acts on "
              "the template-liquid interface (gamma_sl); overall the retrodiction falls short of its registered "
              "pass count, and inputs shuffled across cases come close to it."),
    "caption_key": (
        "(a) One row per usable case, grouped by the interface its input acts on (the record's per-case "
        "interface): top group gamma_sn (crystal-template adhesion), then the net-energy case, then gamma_sl "
        "(Ca2+ binding and surface-energy cases); within a group by identifier (tick labels). Marker: median "
        "of the predicted difference Delta = DG*_het(test) - DG*_het(reference) over the Monte Carlo draws, "
        "in units of k_B T; bar: its 5 % to 95 % interval. Marker shape and colour give the verdict of the "
        "pass criterion: filled circle, correct; filled square, incorrect; open diamond, inconclusive (the "
        "interval contains zero; counted as a miss). Vertical line: Delta = 0. Horizontal axis linear within "
        "+-1 k_B T and logarithmic beyond. Narrow column: the observed ordering (right-pointing triangle, the "
        "test surface has the higher barrier). (b) Permutation null of the number of correct cases: the "
        "fraction of permutations giving each count, inputs shuffled within studies (solid outline) and "
        "across studies (dashed outline). Vertical line: the observed number correct. The swap check, N, "
        "the number correct, the registered pass count and the null's median and 95 % range are stated in "
        "the caption through macros."),
    "width": "single",
    "height_cm": 10.0,
    "schema": "figures/src/schemas/retro_results_v1.schema.json",
    "mock_input": "figures/src/mock/retro_results.json",
    "input": "upstream:retro_results",
}

# Verdict -> (marker, filled, Okabe-Ito colour). Shape and fill repeat the colour, so the verdict
# survives greyscale and every simulated colour-vision deficiency. "undetermined" counts as a
# miss (cp3, D17) and is drawn like an inconclusive case.
VERDICT = {
    "correct": ("o", True, "bluishgreen"),
    "incorrect": ("s", True, "vermillion"),
    "inconclusive": ("D", False, "black"),
    "undetermined": ("D", False, "black"),
}
DIRECTION = {"test_higher_barrier": ">", "test_lower_barrier": "<"}
# Interface routes in drawing order: crystal-template adhesion first, because the finding is
# that those cases do best (SCHEMA.md section 4: dupre -> gamma_sn; net; gibbs_langmuir and owrk -> gamma_sl).
ROUTES = ("gamma_sn", "f_theta", "net", "gamma_sl")
GROUP_GAP = 0.8  # extra row spacing between interface groups (house)
LINTHRESH_KT = 1.0  # house: the symmetric-log axis is linear within one k_B T of zero
NULLS = (("within_study", "blue", "-"), ("across_studies", "vermillion", (0, (3, 1.5))))


def delta_title(root):
    het = entry("DG_het", root)["latex"]
    kt = entry("k_B", root)["latex"] + entry("T", root)["latex"]
    # The register's DG_het already carries its Delta; the difference is named in words.
    return r"$%s/%s$, test $-$ reference" % (het, kt)


def ordered(cases):
    """Cases grouped by interface route (ROUTES order), by identifier within a group."""
    unknown = sorted({c["interface"] for c in cases} - set(ROUTES))
    if unknown:
        raise ValueError("fig4: no drawing order for interface route(s) %s" % ", ".join(unknown))
    return sorted(cases, key=lambda c: (ROUTES.index(c["interface"]), c["id"]))


def row_positions(cases):
    """y of each case, top to bottom, with a gap between interface groups."""
    y, cur, prev = [], 0.0, None
    for c in cases:
        if prev is not None and c["interface"] != prev:
            cur -= GROUP_GAP
        y.append(cur)
        cur -= 1.0
        prev = c["interface"]
    return np.asarray(y)


def _panel_delta(ax, ax_dir, cases, root):
    from matplotlib.ticker import FuncFormatter, SymmetricalLogLocator
    lw = style.min_line_pt(root)
    y = row_positions(cases)
    for yi, c in zip(y, cases):
        marker, filled, cname = VERDICT[c["verdict"]]
        colour = style.categorical(cname, root)
        d = c["delta"]
        ax.errorbar(d["median"], yi, xerr=[[d["median"] - d["q05"]], [d["q95"] - d["median"]]],
                    fmt=marker, color=colour, ecolor=colour, elinewidth=lw,
                    markerfacecolor=colour if filled else "white", markeredgecolor=colour)
        ax_dir.plot([0.0], [yi], linestyle="none", marker=DIRECTION[c["observed_relation"]], color="black")
    ax.axvline(0.0, color="black", linewidth=lw)
    ax.set_xscale("symlog", linthresh=LINTHRESH_KT)
    ax.xaxis.set_major_locator(SymmetricalLogLocator(base=10, linthresh=LINTHRESH_KT))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: "%g" % v))
    lo = min(c["delta"]["q05"] for c in cases)
    hi = max(c["delta"]["q95"] for c in cases)
    left = -max(abs(lo), 2 * LINTHRESH_KT) * 1.6 if lo < 0 else -2 * LINTHRESH_KT
    ax.set_xlim(left, max(hi, 10 * LINTHRESH_KT) * 1.6)
    ax.set_yticks(y, [c["id"] for c in cases])
    ax.set_ylim(y.min() - 0.6, y.max() + 0.6)
    ax.set_xlabel(delta_title(root))
    ax_dir.set_xlim(-1.0, 1.0)
    ax_dir.set_xticks([])
    ax_dir.tick_params(axis="y", left=False, labelleft=False)
    for side in ("bottom", "left"):
        ax_dir.spines[side].set_visible(False)


def _panel_null(ax, summary, root):
    data_lw = float(style.applied(root)["line_width_data"]["value"])
    n = int(summary["N"])
    edges = np.arange(-0.5, n + 1.5)
    top = 0.0
    for key, cname, ls in NULLS:
        null = summary["permutation_null"][key]
        counts = np.asarray(null["counts"], dtype=float)
        if len(counts) != n + 1:
            raise ValueError("fig4: permutation null %s has %d counts for N = %d" % (key, len(counts), n))
        frac = counts / float(null["n_perm"])
        top = max(top, frac.max())
        ax.stairs(frac, edges, fill=False, color=style.categorical(cname, root), linewidth=data_lw, linestyle=ls)
    ax.axvline(summary["correct"], color="black", linewidth=data_lw)
    ax.set_xlim(edges[0], edges[-1])
    ax.set_xticks(range(0, n + 1, 2))
    ax.set_ylim(0.0, top * 1.15)
    ax.set_xlabel("Number of correct cases")
    ax.set_ylabel("Fraction of permutations")


def build(data, root, aux):
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    gs = fig.add_gridspec(2, 2, width_ratios=[12, 1], height_ratios=[2.2, 1])
    ax = fig.add_subplot(gs[0, 0])
    ax_dir = fig.add_subplot(gs[0, 1], sharey=ax)
    ax_null = fig.add_subplot(gs[1, :])
    cases = ordered(data["cases"])
    _panel_delta(ax, ax_dir, cases, root)
    _panel_null(ax_null, data["summary"], root)
    panel_letters([ax, ax_null])
    return fig
