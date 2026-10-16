"""Fig. 5: heterogeneous nucleation-barrier map over wetting angle and supersaturation."""
import numpy as np
from matplotlib.colors import LogNorm

from nacre.figs import style
from nacre.figs.axes import log_axis
from nacre.figs.symbols import axis_title

FIGURE = {
    "id": "fig5",
    "claim": ("The heterogeneous barrier falls below the critical barrier only at small wetting angle and "
              "high supersaturation; the threshold contours bound the region where a layer can nucleate."),
    "caption_key": ("Colour: heterogeneous barrier on a logarithmic scale (colour bar). Black contours: "
                    "the critical-barrier thresholds, whose values the caption gives; the barrier falls "
                    "towards small wetting angle and high supersaturation."),
    "width": "single",
    "height_cm": 7.0,
    "schema": "figures/src/schemas/fig5_barrier_map.schema.json",
    "mock_input": "figures/src/mock/fig5.json",
    "input": "results/preprint/screen/fig5_input.json",
}


def build(data, root):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    theta = np.asarray(data["wetting_angle_deg"], dtype=float)
    s = np.asarray(data["supersaturation"], dtype=float)
    z = np.asarray(data["barrier_kT"], dtype=float)
    if z.shape != (len(s), len(theta)):
        raise ValueError("barrier_kT must be len(supersaturation) x len(wetting_angle_deg)")
    positive = z[z > 0]
    norm = LogNorm(vmin=max(positive.min(), 1e-2), vmax=positive.max())
    mesh = ax.pcolormesh(theta, s, np.clip(z, norm.vmin, None), norm=norm,
                         cmap=style.colormap("sequential", root), shading="nearest", rasterized=True)
    ax.contour(theta, s, z, levels=sorted(data["thresholds_kT"]), colors="black",
               linewidths=plt.rcParams["lines.linewidth"])
    ax.set_yscale("log")
    log_axis(ax.yaxis)
    ax.set_xlabel(axis_title("wetting_angle", root))
    ax.set_ylabel(axis_title("supersaturation", root))
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label(axis_title("barrier_het", root))
    cbar.outline.set_linewidth(style.min_line_pt(root))
    return fig
