"""Templates without data: layout, axes scaffolding and style, with a visibly empty placeholder.

A figure template whose FIGURE carries "status": "template" has no input yet. It is drawn by
build.render_template into figures/out/templates/ and registered in the manifest under
"templates"; the release check (build.release_problems) fails for as long as one is registered.
The placeholder is two grey diagonals across each plot area, tagged with gid PLACEHOLDER_GID:
graphics only, so the figure still carries no text inside the axes.
"""
PLACEHOLDER_GID = "template-placeholder"


def placeholder(ax, root=None):
    """Mark an axes as empty: tick labels removed, grey corner-to-corner diagonals drawn over it."""
    from nacre.figs import style
    grey = style.palette(root)["categorical"]["okabe_ito"]["gray"]["hex"]
    ax.set_xticks([])
    ax.set_yticks([])
    for ys in ((0, 1), (1, 0)):
        line, = ax.plot([0, 1], ys, transform=ax.transAxes, color=grey, linewidth=style.min_line_pt(root) * 1.5,
                        solid_capstyle="butt", clip_on=True, zorder=1)
        line.set_gid(PLACEHOLDER_GID)


def placeholder_axes(fig):
    """[(axes, number of placeholder lines)] for every plot axes of a figure."""
    from nacre.figs.checker import _is_colorbar
    out = []
    for ax in fig.axes:
        if _is_colorbar(ax):
            continue
        n = sum(1 for ln in ax.lines if ln.get_gid() == PLACEHOLDER_GID)
        out.append((ax, n))
    return out
