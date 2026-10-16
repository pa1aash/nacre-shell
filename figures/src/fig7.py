"""Fig. 7: Pourbaix diagrams for the two regimes."""
from matplotlib.patches import Polygon

from nacre.figs import style
from nacre.figs.colours import distinct_fills
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import axis_title

FIGURE = {
    "id": "fig7",
    "claim": ("The window of pH and potential in which the protective solid phase is stable differs between "
              "the two regimes."),
    "caption_key": ("(a) First regime, (b) second regime, with their conditions. Fill colour identifies the "
                    "predominant species; the same species has the same colour in both panels and the "
                    "caption names each colour. Dashed lines: stability limits of water."),
    "width": "double",
    "height_cm": 7.0,
    "schema": "figures/src/schemas/fig7_pourbaix.schema.json",
    "mock_input": "figures/src/mock/fig7.json",
    "input": "results/preprint/pourbaix/fig7_input.json",
}



def species_colours(regimes, root):
    """Species -> fill colour, the same in both panels.

    Species are ordered by first appearance across the regimes and given the CVD-checked fills
    of nacre.figs.colours.distinct_fills (every pair clears the palette's delta_e_min under
    normal vision and simulated deuteranopia, protanopia and tritanopia).
    """
    order = []
    for r in regimes:
        for d in r["domains"]:
            if d["species"] not in order:
                order.append(d["species"])
    fills, _names, _f, _d = distinct_fills(len(order), root)
    return dict(zip(order, fills))


def build(data, root):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, sharey=True, figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    colours = species_colours(data["regimes"], root)
    lw = style.min_line_pt(root)
    for ax, regime in zip(axes, data["regimes"]):
        for d in regime["domains"]:
            ax.add_patch(Polygon(d["polygon"], closed=True, facecolor=colours[d["species"]],
                                 edgecolor="black", linewidth=lw))
        for w in regime["water_lines"]:
            xs, ys = zip(*w["points"])
            ax.plot(xs, ys, color="black", linestyle=(0, (4, 2)))
        ax.set_xlim(*regime["ph_range"])
        ax.set_ylim(*regime["potential_range"])
        ax.set_xlabel(axis_title("ph", root))
    axes[0].set_ylabel(axis_title("potential", root))
    axes[1].tick_params(axis="y", left=True)
    panel_letters(axes)
    return fig
