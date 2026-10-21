"""Fig. 12 (template): slurry dissolution map with the acid-adjusted pH state as the comparator. No data yet: layout, axes scaffolding and style only."""
from nacre.figs import style
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import axis_title
from nacre.figs.template import placeholder

FIGURE = {
    "id": "fig12",
    "status": "template",
    "waits_for": "slurry dissolution outputs for the as-prepared and the acid-adjusted pH states (PH-W4 and PH-W5 follow-ups)",
    "claim": "Where the slurry dissolves the carbonate over the calcium dose and the dissolved carbonate, and how the acid-adjusted pH state moves that boundary.",
    "caption_key": "(a) as-prepared slurry; (b) acid-adjusted pH state, the comparator. Same axes as the dose window of Fig. 7a: total calcium dose (horizontal) by total dissolved carbonate (vertical); fill and hatching: verdict at each design point.",
    "width": "double",
    "height_cm": 7.0,
}


def build(data, root, aux):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    for ax in axes:
        ax.set_xlabel(axis_title("Ca_T", root, unit=r"mol m$^{-3}$"))
        ax.set_ylabel(axis_title("C_T", root, unit=r"mol m$^{-3}$"))
        placeholder(ax, root)
    panel_letters(axes)
    return fig
