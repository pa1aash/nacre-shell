"""Fig. 15 (template): candidate-by-condition (regime) heatmap. No data yet: layout, axes scaffolding and style only."""
from nacre.figs import style
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import axis_title
from nacre.figs.template import placeholder

FIGURE = {
    "id": "fig15",
    "status": "template",
    "waits_for": "candidate list and regime verdicts from the screen (PH-W4 follow-ups)",
    "claim": "The verdict of each candidate coating under each registered condition, so the regime in which each candidate is excluded, inconclusive or undetermined can be read across a row.",
    "caption_key": "Rows: candidates; columns: conditions (regimes, in the caption); fill and hatching as in Fig. 9: excluded, inconclusive, undetermined.",
    "width": "double",
    "height_cm": 8.0,
}


def build(data, root, aux):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    ax.set_xlabel("Condition (regime)")
    ax.set_ylabel("Candidate")
    placeholder(ax, root)
    return fig
