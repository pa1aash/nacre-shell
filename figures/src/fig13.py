"""Fig. 13 (template): the Al-salt ladder. No data yet: layout, axes scaffolding and style only."""
from nacre.figs import style
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import axis_title
from nacre.figs.template import placeholder

FIGURE = {
    "id": "fig13",
    "status": "template",
    "waits_for": "Al(ClO4)3 thermochemistry and the Al-salt sink budget (dfg_al_clo4_3 is a gap)",
    "claim": "The oxidation limit of each phase against each aluminium-salt sink, on the same potential axis as the cell window.",
    "caption_key": "One row per phase and Al-salt sink (to be named in the caption); horizontal: potential vs Li+/Li; end marks as in Fig. 7b.",
    "width": "single",
    "height_cm": 7.0,
}


def build(data, root, aux):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    ax.set_xlabel("%s (V vs Li$^{+}$/Li)" % axis_title("E_ox", root, unit=""))
    ax.set_ylabel("Phase and Al-salt sink")
    placeholder(ax, root)
    return fig
