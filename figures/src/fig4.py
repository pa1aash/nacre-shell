"""Fig. 4: retrodiction outcome, predicted barrier against the observed outcome for each case."""
import numpy as np

from nacre.figs import style
from nacre.figs.axes import log_axis
from nacre.figs.symbols import axis_title

FIGURE = {
    "id": "fig4",
    "claim": ("Cases in which a continuous carbonate layer was observed have predicted heterogeneous "
              "barriers below the critical barrier, and cases without a layer lie above it."),
    "caption_key": ("Filled circles: layer observed; open squares: no layer observed. Horizontal bars: "
                    "range of the predicted barrier over the parameter uncertainty. Vertical line: "
                    "critical barrier. Case identifiers on the vertical axis are defined in the caption."),
    "width": "single",
    "height_cm": 7.0,
    "schema": "figures/src/schemas/fig4_retrodiction.schema.json",
    "mock_input": "figures/src/mock/fig4.json",
    "input": "preprint/retrodiction/fig4_input.json",
}

# Observed outcome -> (marker, filled, Okabe-Ito colour). Shape and fill repeat the colour so the
# outcome survives greyscale and every simulated colour-vision deficiency.
_OUTCOME = {
    "layer_formed": ("o", True, "bluishgreen"),
    "no_layer": ("s", False, "vermillion"),
}


def build(data, root):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    cases = data["cases"]
    y = np.arange(len(cases))[::-1]
    for yi, c in zip(y, cases):
        marker, filled, cname = _OUTCOME[c["observed"]]
        colour = style.categorical(cname, root)
        ax.errorbar(
            c["predicted"], yi,
            xerr=[[c["predicted"] - c["predicted_lo"]], [c["predicted_hi"] - c["predicted"]]],
            fmt=marker, color=colour, ecolor=colour,
            markerfacecolor=colour if filled else "white", markeredgecolor=colour,
            elinewidth=style.min_line_pt(root),
        )
    ax.axvline(data["threshold"]["value"], color="black", linewidth=style.min_line_pt(root))
    ax.set_xscale("log")
    log_axis(ax.xaxis)
    ax.set_yticks(y, [c["label"] for c in cases])
    ax.set_ylim(y.min() - 0.6, y.max() + 0.6)
    ax.set_xlabel(axis_title(data["quantity"]["symbol"], root))
    ax.set_ylabel("Case")
    return fig
