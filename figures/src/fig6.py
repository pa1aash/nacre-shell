"""Fig. 6: which inputs govern the barrier on the template, and the precision each must reach."""
import numpy as np

from nacre.figs import style
from nacre.figs.axes import log_axis
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import symbol

FIGURE = {
    "id": "fig6",
    "claim": ("A few inputs carry most of the variance of the predicted barrier on the template, and those "
              "inputs need the tightest precision from first-principles validation."),
    "caption_key": (
        "(a) Variance share of each input in log10 of f(theta) DG*_hom(Omega_bulk)/k_B T (link nucleate, "
        "primary state of R-slurry), ranked from the top. With correlated inputs (dependence method "
        "gaussian_copula) the share is the Shapley effect (filled circles); with independent inputs it is the "
        "Sobol first-order (filled circles) and total-order (open diamonds) index. Bars: confidence "
        "intervals at the record's level. (b) Required width of each input's prior relative to its present "
        "width, on a logarithmic scale, in the same order (configs/preprint/precision_method.md): bars, status "
        "ok; open circle at 1, already clears; cross at the left axis limit, unreachable at any width. The "
        "caption names the threshold nearest to each input."),
    "width": "double",
    "height_cm": 6.5,
    "schema": "upstream:results_schema",
    "mock_input": "figures/src/mock/screen_summary.json",
    "input": "results/preprint/screen/summary.json",
}

REGIME = "R-slurry"
LINK = "nucleate"
QUANTITY = "barrier_het_template_kT"
_OFFSET = 0.17


def indices(regime):
    """('shapley', {p: ci}) for correlated inputs when Shapley effects exist, else ('sobol', {p: indices})."""
    link = regime["links"][LINK]
    dep = regime.get("dependence", {}).get("method", "independent")
    if dep != "independent" and QUANTITY in link.get("shapley", {}):
        return "shapley", link["shapley"][QUANTITY]
    return "sobol", link["sobol"][QUANTITY]


def _rank_value(kind, v):
    return v["estimate"] if kind == "shapley" else v["total_order"]["estimate"]


def _xerr(ci):
    return [[ci["estimate"] - ci["ci_low"]], [ci["ci_high"] - ci["estimate"]]]


def build(data, root, aux):
    import matplotlib.pyplot as plt

    regime = data["regimes"][REGIME]
    kind, idx = indices(regime)
    order = sorted(idx, key=lambda p: _rank_value(kind, idx[p]), reverse=True)
    y = np.arange(len(order))[::-1].astype(float)

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, sharey=True, gridspec_kw={"width_ratios": [3, 2]},
        figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    blue, verm = style.categorical("blue", root), style.categorical("vermillion", root)
    lw = style.min_line_pt(root)
    for yi, p in zip(y, order):
        v = idx[p]
        if kind == "shapley":
            ax_a.errorbar(v["estimate"], yi, xerr=_xerr(v), fmt="o", color=blue, elinewidth=lw)
        else:
            s1, st = v["first_order"], v["total_order"]
            ax_a.errorbar(s1["estimate"], yi + _OFFSET, xerr=_xerr(s1), fmt="o", color=blue, elinewidth=lw)
            ax_a.errorbar(st["estimate"], yi - _OFFSET, xerr=_xerr(st), fmt="D", color=verm, elinewidth=lw,
                          markerfacecolor="white", markeredgecolor=verm)
    ax_a.set_xlim(0.0, 1.0)
    ax_a.set_yticks(y, [symbol(p, root) for p in order])
    ax_a.set_ylim(y.min() - 0.6, y.max() + 0.6)
    ax_a.set_xlabel("Variance share")

    prec = data.get("required_precision", {}).get(REGIME, {})
    ratios = [prec[p]["width_ratio"] for p in order if p in prec and prec[p]["status"] == "ok"]
    left = 10 ** np.floor(np.log10(min(ratios))) if ratios else 1e-2
    green = style.categorical("bluishgreen", root)
    for yi, p in zip(y, order):
        r = prec.get(p)
        if r is None:
            continue
        if r["status"] == "ok":
            ax_b.barh(yi, r["width_ratio"] - left, left=left, height=0.5, color=green, edgecolor="black",
                      linewidth=lw)
        elif r["status"] == "already_clears":
            ax_b.plot([1.0], [yi], linestyle="none", marker="o", markerfacecolor="white", markeredgecolor="black",
                      clip_on=False)
        else:
            ax_b.plot([left], [yi], linestyle="none", marker="x", color="black", clip_on=False)
    ax_b.set_xscale("log")
    log_axis(ax_b.xaxis)
    ax_b.set_xlim(left, 1.0)
    ax_b.set_xlabel("Required prior width / present width")
    ax_b.tick_params(axis="y", left=False)
    panel_letters([ax_a, ax_b])
    return fig
