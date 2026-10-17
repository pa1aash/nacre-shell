"""Fig. 5: heterogeneous barrier over the wetting angle and the bulk saturation ratio."""
import numpy as np
from matplotlib.colors import LogNorm

from nacre.figs import style
from nacre.figs.axes import log_axis
from nacre.figs.symbols import axis_title, per_kT
from nacre.physics import nucleation, wetting

FIGURE = {
    "id": "fig5",
    "claim": ("At equilibrium the template acts on the barrier only through the wetting angle: at a given bulk "
              "saturation ratio the barrier on the template falls as the angle closes, and it is accessible only "
              "where both the angle and the bulk driving force allow it."),
    "caption_key": (
        "Colour: f(theta) DG*_hom(Omega_bulk)/k_B T on a logarithmic scale (colour bar), evaluated with the "
        "contract functions at the primary state's reference prefactor: the median homogeneous barrier at "
        "the median Omega_bulk, scaled to every Omega_bulk at fixed nucleus-liquid energy, molar volume and "
        "temperature (the caption states this reference). The vertical axis is the bulk saturation ratio; the "
        "template never changes it. Vertical black line: the C3a edge f(theta) = f at cos(theta) = m_cos "
        "(configs/preprint/thresholds.yaml). Curved black line: the C3b accessibility bound "
        "DG*_het = B_acc at the median B_acc/k_B T. Markers with bars: the screen's median and 5 % to 95 % "
        "range of theta and Omega_bulk for each registered state (filled circle, the primary state; open "
        "square, each further state in the order of the record). The caption reports the cos(theta) "
        "boundary mass of each state (draws clipped to theta = 0 and theta = 180 deg), which is not drawn."),
    "width": "single",
    "height_cm": 7.0,
    "schema": "upstream:results_schema",
    "mock_input": "figures/src/mock/screen_summary.json",
    "input": "results/preprint/screen/summary.json",
    "aux": {
        "thresholds": "upstream:thresholds",
        "params": {"mock": "figures/src/mock/params.yaml", "real": "lit/params.yaml"},
    },
}

REGIME = "R-slurry"
LINK = "nucleate"
STATE_MARKERS = ("o", "s", "^", "v")  # primary state filled, further states open, in record order


def param(params, dotted):
    """A row of the parameter table by its dotted key (thresholds.C3.margin_cos_theta, ...)."""
    node = params
    for part in dotted.split("."):
        node = node[part]
    return node


def c3a_edge_cos(thresholds, params):
    """cos(theta) at the C3a edge: f(theta) <= f(arccos m_cos), i.e. theta <= arccos(m_cos)."""
    test = next(t for t in thresholds["links"]["C3"]["tests"] if t["id"] == "C3a")
    m = param(params, test["params"]["m_cos"])["value"]
    if m is None:
        return None
    return float(m)


def states(regime):
    """[(name, nucleate quantities, boundary mass)]: the primary state first, then the others."""
    out = [(regime.get("primary_state", "primary"), regime["links"][LINK]["quantities"],
            regime.get("boundary_mass", {}).get(LINK, {}))]
    for name, st in regime.get("states", {}).items():
        if LINK in st["quantities"]:
            out.append((name, st["quantities"][LINK], st["boundary_mass"].get(LINK, {})))
    return out


def _theta_deg(cos_q):
    return float(np.degrees(np.arccos(np.clip(cos_q, -1.0, 1.0))))


def barrier_map(theta_deg, omega, hom_ref_kT, omega_ref):
    """f(theta) DG*_hom(Omega)/k_B T with DG*_hom scaled from the reference point by the contract.

    nucleation.homogeneous_barrier_from_saturation carries the Omega dependence at fixed
    gamma_nl, V_m and T; its ratio to the reference point does not depend on their values.
    """
    unit = nucleation.homogeneous_barrier_from_saturation(1.0, 1.0, omega, 1.0)
    ref = nucleation.homogeneous_barrier_from_saturation(1.0, 1.0, omega_ref, 1.0)
    hom = hom_ref_kT * np.asarray(unit) / ref
    f = wetting.shape_factor(np.radians(theta_deg))
    return np.asarray(f)[None, :] * hom[:, None]


def build(data, root, aux):
    import matplotlib.pyplot as plt

    regime = data["regimes"][REGIME]
    sts = states(regime)
    primary = sts[0][1]
    om_ref = primary["Omega_bulk"]["quantiles"]["0.5"]
    hom_ref = primary["barrier_hom_bulk_kT"]["quantiles"]["0.5"]

    om_lo = min(q["Omega_bulk"]["quantiles"]["0.05"] for _n, q, _m in sts)
    om_hi = max(q["Omega_bulk"]["quantiles"]["0.95"] for _n, q, _m in sts)
    y_lo, y_hi = max(om_lo / 2.0, 1.0 + 1e-3), om_hi * 2.0
    theta = np.linspace(0.5, 179.5, 359)
    omega = np.geomspace(y_lo, y_hi, 240)
    z = barrier_map(theta, omega, hom_ref, om_ref)

    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    lw = style.min_line_pt(root)
    vmin = 10 ** np.floor(np.log10(max(z[z > 0].min(), 1e-2)))
    vmax = 10 ** np.ceil(np.log10(min(z.max(), 1e6)))
    norm = LogNorm(vmin=vmin, vmax=vmax)
    mesh = ax.pcolormesh(theta, omega, np.clip(z, vmin, vmax), norm=norm, cmap=style.colormap("sequential", root),
                         shading="nearest", rasterized=True)

    thresholds, params = aux["thresholds"], aux["params"]
    m_cos = c3a_edge_cos(thresholds, params)
    if m_cos is not None:
        ax.axvline(np.degrees(np.arccos(m_cos)), color="black", linewidth=plt.rcParams["lines.linewidth"])
    b_acc = primary.get("B_acc_kT", {}).get("quantiles", {}).get("0.5")
    if b_acc is not None and np.isfinite(b_acc):
        ax.contour(theta, omega, z, levels=[b_acc], colors="black", linewidths=plt.rcParams["lines.linewidth"])

    for (name, q, _mass), marker in zip(sts, STATE_MARKERS):
        cq, oq = q["cos_theta"]["quantiles"], q["Omega_bulk"]["quantiles"]
        t50, t_lo, t_hi = _theta_deg(cq["0.5"]), _theta_deg(cq["0.95"]), _theta_deg(cq["0.05"])
        o50 = oq["0.5"]
        filled = marker == STATE_MARKERS[0]
        err = {"xerr": [[t50 - t_lo], [t_hi - t50]], "yerr": [[o50 - oq["0.05"]], [oq["0.95"] - o50]]}
        # White underlay, then black: the bars read over both ends of the sequential map.
        ax.errorbar(t50, o50, fmt="none", ecolor="white", elinewidth=3 * lw, **err)
        ax.errorbar(t50, o50, fmt=marker, color="black", ecolor="black", elinewidth=lw, markeredgecolor="white",
                    markerfacecolor="black" if filled else "white", markeredgewidth=lw, **err)

    ax.set_xlim(0.0, 180.0)
    ax.set_xticks([0, 30, 60, 90, 120, 150, 180])
    ax.set_ylim(y_lo, y_hi)
    ax.set_yscale("log")
    log_axis(ax.yaxis)
    ax.set_xlabel(axis_title("theta", root, unit="°"))
    ax.set_ylabel(axis_title("Omega_bulk", root))
    cbar = fig.colorbar(mesh, ax=ax, extend="max" if z.max() > vmax else "neither")
    cbar.set_label(per_kT("DG_het", root))
    cbar.outline.set_linewidth(lw)
    return fig
