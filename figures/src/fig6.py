"""Fig. 6: Sobol first- and total-order ranking of the barrier inputs, beside the precision each requires."""
import numpy as np

from nacre.figs import style
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import axis_title, symbol

FIGURE = {
    "id": "fig6",
    "claim": ("A few inputs carry most of the variance of the predicted barrier, and those inputs need the "
              "tightest precision from first-principles validation."),
    "caption_key": ("(a) Filled circles: first-order index; open diamonds: total-order index; bars: "
                    "confidence intervals. Inputs are ranked by total-order index. (b) Precision each input "
                    "must reach, on a logarithmic scale, in the same order."),
    "width": "double",
    "height_cm": 6.5,
    "schema": "figures/src/schemas/fig6_sobol.schema.json",
    "mock_input": "figures/src/mock/fig6.json",
    "input": "results/preprint/screen/fig6_input.json",
}

_OFFSET = 0.17


def build(data, root):
    import matplotlib.pyplot as plt

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, sharey=True, gridspec_kw={"width_ratios": [3, 2]},
        figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root),
    )
    params = sorted(data["parameters"], key=lambda p: p["ST"], reverse=True)
    y = np.arange(len(params))[::-1].astype(float)
    first, total = style.categorical("blue", root), style.categorical("vermillion", root)
    lw = style.min_line_pt(root)
    for yi, p in zip(y, params):
        ax_a.errorbar(p["S1"], yi + _OFFSET, xerr=[[p["S1"] - p["S1_ci"][0]], [p["S1_ci"][1] - p["S1"]]],
                      fmt="o", color=first, elinewidth=lw)
        ax_a.errorbar(p["ST"], yi - _OFFSET, xerr=[[p["ST"] - p["ST_ci"][0]], [p["ST_ci"][1] - p["ST"]]],
                      fmt="D", color=total, markerfacecolor="white", markeredgecolor=total,
                      elinewidth=lw)
    ax_a.set_xlim(0.0, 1.0)
    ax_a.set_yticks(y, [symbol(p["symbol"], root) for p in params])
    ax_a.set_ylim(y.min() - 0.6, y.max() + 0.6)
    ax_a.set_xlabel(axis_title("sobol_index", root))

    prec = np.array([p["required_precision"] for p in params])
    left = 10 ** np.floor(np.log10(prec.min()))
    ax_b.barh(y, prec - left, left=left, height=0.5, color=style.categorical("bluishgreen", root),
              edgecolor="black", linewidth=lw)
    ax_b.set_xscale("log")
    ax_b.set_xlim(left, 10 ** np.ceil(np.log10(prec.max())))
    ax_b.set_xlabel(axis_title("required_precision", root))
    ax_b.tick_params(axis="y", left=False)
    panel_letters([ax_a, ax_b])
    return fig
