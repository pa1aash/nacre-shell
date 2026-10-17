"""Fig. 4: retrodiction, the predicted barrier difference of each test-versus-reference case."""
import numpy as np

from nacre.figs import style
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import entry

FIGURE = {
    "id": "fig4",
    "claim": ("For each same-study pair, the sign of the predicted heterogeneous-barrier difference (test minus "
              "reference) agrees with the observed ordering of the two surfaces when its 90 % interval excludes "
              "zero on the observed side."),
    "caption_key": (
        "(a) One row per usable case (identifiers RC01 to RC12, defined in the caption with their surfaces "
        "and study). Marker: median of the predicted difference Delta = DG*_het(test) - DG*_het(reference) "
        "over the Monte Carlo draws, in units of k_B T; bar: its 5 % to 95 % interval. Marker shape and "
        "colour give the verdict of the pass criterion: filled circle, correct; filled square, incorrect; "
        "open diamond, inconclusive (the interval contains zero, which counts as not correct). Vertical "
        "line: Delta = 0. Horizontal axis linear within +-1 k_B T and logarithmic beyond. (b) Observed "
        "ordering of the same case: right-pointing triangle, test surface has the higher barrier; "
        "left-pointing, the lower. The caption states N, the number correct, k and the chance probability "
        "from the record's summary, and each case's boundary mass."),
    "width": "single",
    "height_cm": 8.0,
    "schema": "figures/src/schemas/retro_results_v1.schema.json",
    "mock_input": "figures/src/mock/retro_results.json",
    "input": "preprint/retrodiction/results.json",
}

# Verdict -> (marker, filled, Okabe-Ito colour). Shape and fill repeat the colour, so the verdict
# survives greyscale and every simulated colour-vision deficiency.
VERDICT = {
    "correct": ("o", True, "bluishgreen"),
    "incorrect": ("s", True, "vermillion"),
    "inconclusive": ("D", False, "black"),
}
DIRECTION = {"test_higher_barrier": ">", "test_lower_barrier": "<"}
LINTHRESH_KT = 1.0  # house: the symmetric-log axis is linear within one k_B T of zero


def delta_title(root):
    het = entry("DG_het", root)["latex"]
    kt = entry("k_B", root)["latex"] + entry("T", root)["latex"]
    return r"$\Delta %s/%s$, test $-$ reference" % (het, kt)


def build(data, root, aux):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, SymmetricalLogLocator

    fig, (ax, ax_dir) = plt.subplots(
        1, 2, sharey=True, gridspec_kw={"width_ratios": [12, 1]},
        figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    cases = data["cases"]
    y = np.arange(len(cases))[::-1].astype(float)
    lw = style.min_line_pt(root)
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
    span = max(abs(lo), abs(hi), 10 * LINTHRESH_KT)
    ax.set_xlim(-span * 1.6 if lo < 0 else -2 * LINTHRESH_KT, span * 1.6)
    ax.set_yticks(y, [c["id"] for c in cases])
    ax.set_ylim(y.min() - 0.6, y.max() + 0.6)
    ax.set_xlabel(delta_title(root))
    ax_dir.set_xlim(-1.0, 1.0)
    ax_dir.set_xticks([])
    ax_dir.tick_params(axis="y", left=False)
    for side in ("bottom", "left"):
        ax_dir.spines[side].set_visible(False)
    panel_letters([ax, ax_dir])
    return fig
