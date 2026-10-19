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
              "saturation ratio the barrier on the template falls as the angle closes, and only angles on the "
              "wetting side of the C3a edge halve it; the screen's ignorance prior sits on the non-wetting side."),
    "caption_key": (
        "Colour: DG*_het/k_B T = f(theta) DG*_hom(Omega_bulk)/k_B T on a logarithmic scale (colour bar), "
        "from the contract functions at the reference inputs of the record's barrier prefactor (reference "
        "nucleus-liquid energy, molar volume and temperature, the prior medians of the primary state); the "
        "template never changes Omega_bulk. Vertical black line: the C3a edge f(theta) = f at cos(theta) = "
        "m_cos (configs/preprint/thresholds.yaml, parameter table). The C3b absolute-barrier bound "
        "DG*_het = k_B T ln(J0_het t_proc A_patch / ln(1/(1 - p_cred))) is drawn as a black contour only when "
        "every input has a value; A_patch is a registered gap, so it is absent and the caption says so. "
        "Outlines: the central 90 % (5 % to 95 % quantiles) of the screen's draws in theta and Omega_bulk "
        "under the ignorance prior set, primary state solid, further states dashed in record order: a "
        "property of the prior, not a finding. The caption reports the cos(theta) boundary mass (draws "
        "clipped to theta = 180 deg and theta = 0) and the favourable-template condition gamma_sn < gamma_sl "
        "(model section)."),
    "width": "single",
    "height_cm": 7.0,
    "schema": "upstream:results_schema",
    "mock_input": "figures/src/mock/screen_summary.json",
    "input": "upstream:screen_ignorance",
    "aux": {
        "thresholds": "upstream:thresholds",
        "params": {"mock": "figures/src/mock/params.yaml", "real": "lit/params.yaml"},
    },
}

REGIME = "R-slurry"
LINK = "nucleate"
STATE_LINESTYLES = ("-", (0, (3, 1.5)), (0, (1, 1.5)))  # primary state solid, then the others in record order
REL_TOL = 1e-9
OUTLINE_MASS = 0.9  # house: the outlines enclose the central 90 % of the draws in each variable (caption macro)


def _q(p):
    """The record's quantile key for probability p ('0.05', '0.95', ...)."""
    return "%g" % round(p, 6)


def param(params, dotted):
    """A row of the parameter table by its dotted key (thresholds.C3.margin_cos_theta, ...)."""
    node = params
    for part in dotted.split("."):
        node = node[part]
    return node


def _test(thresholds, tid):
    return next(t for t in thresholds["links"]["C3"]["tests"] if t["id"] == tid)


def c3a_edge_cos(thresholds, params):
    """cos(theta) at the C3a edge: f(theta) <= f(arccos m_cos), i.e. theta <= arccos(m_cos)."""
    m = param(params, _test(thresholds, "C3a")["params"]["m_cos"])["value"]
    return None if m is None else float(m)


def c3b_edge_kT(thresholds, params):
    """The C3b single-state bound DG*_het/k_B T = ln(J0_het t_proc A_patch / ln(1/(1 - p_cred))).

    Returns (value or None, [keys without a value]); a missing input leaves the bound undrawn.
    """
    keys = _test(thresholds, "C3b")["params"]
    vals, missing = {}, []
    for sym, dotted in keys.items():
        v = param(params, dotted).get("value")
        if v is None:
            missing.append(dotted)
        vals[sym] = v
    if missing:
        return None, missing
    return float(np.log(vals["J0_het"] * vals["t_proc"] * vals["A_patch"] / np.log(1.0 / (1.0 - vals["p_cred"])))), []


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


def barrier_map(theta_deg, omega, prefactor):
    """DG*_het/k_B T over (Omega, theta) from the contract at the record's reference inputs.

    The record's B_kT must equal DG*_hom ln^2(Omega)/k_B T of the same contract function; a
    mismatch means the record and the contract disagree, and the figure is refused.
    """
    g, vm, t = prefactor["reference_gamma_nl"], prefactor["V_m"], prefactor["T"]
    hom = np.array([nucleation.barrier_in_kT(nucleation.homogeneous_barrier_from_saturation(g, vm, o, t), t)
                    for o in omega])
    implied = hom * np.log(omega) ** 2
    if not np.allclose(implied, prefactor["B_kT"], rtol=REL_TOL, atol=0.0):
        raise ValueError("fig5: barrier_prefactor.B_kT %.6g differs from the contract at its reference inputs (%.6g)"
                         % (prefactor["B_kT"], float(implied[0])))
    f = wetting.shape_factor(np.radians(theta_deg))
    return np.asarray(f)[None, :] * hom[:, None]


def build(data, root, aux):
    import matplotlib.pyplot as plt

    regime = data["regimes"][REGIME]
    sts = states(regime)
    om_lo = min(q["Omega_bulk"]["quantiles"]["0.05"] for _n, q, _m in sts)
    om_hi = max(q["Omega_bulk"]["quantiles"]["0.95"] for _n, q, _m in sts)
    y_lo, y_hi = max(om_lo / 2.0, 1.0 + 1e-3), om_hi * 2.0
    theta = np.linspace(0.5, 179.5, 359)
    omega = np.geomspace(y_lo, y_hi, 240)
    z = barrier_map(theta, omega, regime["barrier_prefactor"])

    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    lw = style.min_line_pt(root)
    data_lw = float(style.applied(root)["line_width_data"]["value"])
    vmin = 10 ** np.floor(np.log10(max(z[z > 0].min(), 1e-2)))
    vmax = 10 ** np.ceil(np.log10(min(z.max(), 1e6)))
    norm = LogNorm(vmin=vmin, vmax=vmax)
    mesh = ax.pcolormesh(theta, omega, np.clip(z, vmin, vmax), norm=norm, cmap=style.colormap("sequential", root),
                         shading="nearest", rasterized=True)

    thresholds, params = aux["thresholds"], aux["params"]
    m_cos = c3a_edge_cos(thresholds, params)
    if m_cos is not None:
        ax.axvline(np.degrees(np.arccos(m_cos)), color="black", linewidth=data_lw)
    b_kT, _missing = c3b_edge_kT(thresholds, params)
    if b_kT is not None and z.min() < b_kT < z.max():
        ax.contour(theta, omega, z, levels=[b_kT], colors="black", linewidths=data_lw)

    for (_name, q, _mass), ls in zip(sts, STATE_LINESTYLES):
        cq, oq = q["cos_theta"]["quantiles"], q["Omega_bulk"]["quantiles"]
        lo, hi = _q((1.0 - OUTLINE_MASS) / 2.0), _q((1.0 + OUTLINE_MASS) / 2.0)
        t_lo, t_hi = _theta_deg(cq[hi]), _theta_deg(cq[lo])
        o_lo, o_hi = oq[lo], oq[hi]
        xs, ys = [t_lo, t_hi, t_hi, t_lo, t_lo], [o_lo, o_lo, o_hi, o_hi, o_lo]
        # White underlay, then black: the outline reads over both ends of the sequential map.
        ax.plot(xs, ys, color="white", linewidth=3 * lw, linestyle="-", solid_joinstyle="miter", clip_on=False)
        ax.plot(xs, ys, color="black", linewidth=data_lw, linestyle=ls, solid_joinstyle="miter", clip_on=False)

    ax.set_xlim(0.0, 180.0)
    ax.set_xticks([0, 30, 60, 90, 120, 150, 180])
    ax.set_ylim(y_lo, y_hi)
    ax.set_yscale("log")
    log_axis(ax.yaxis, subs=(1.0, 2.0, 3.0, 5.0))
    ax.set_xlabel(axis_title("theta", root, unit="°"))
    ax.set_ylabel(axis_title("Omega_bulk", root))
    cbar = fig.colorbar(mesh, ax=ax, extend="max" if z.max() > vmax else "neither")
    cbar.set_label(per_kT("DG_het", root))
    cbar.outline.set_linewidth(lw)
    return fig
