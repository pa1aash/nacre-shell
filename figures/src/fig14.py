"""Fig. 14 (template): required-precision map. No data yet: layout, axes scaffolding and style only."""
from nacre.figs import style
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import axis_title
from nacre.figs.template import placeholder

FIGURE = {
    "id": "fig14",
    "status": "template",
    "waits_for": "P0-W4.4 Sobol and required-precision output (Fig. 6 inputs)",
    "claim": "The precision each input must reach, relative to its present width, against each decision threshold.",
    "caption_key": "Rows: inputs, ranked as in Fig. 6; columns: decision thresholds; colour: required width of the input's prior relative to its present width (colour bar).",
    "width": "double",
    "height_cm": 7.0,
}


def build(data, root, aux):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    ax.set_xlabel("Decision threshold")
    ax.set_ylabel("Input")
    placeholder(ax, root)
    sm = plt.cm.ScalarMappable(cmap=style.colormap("sequential", root))
    cb = fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.03)
    cb.set_ticks([])
    cb.set_label("Required width ratio")
    return fig
