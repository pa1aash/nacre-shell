"""Fig. 7: where CaCO3 is stable, in the slurry over the design axes and in the cell window."""
import re

import numpy as np
from matplotlib.patches import Rectangle

from nacre.figs import style
from nacre.figs.colours import distinct_fills
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import axis_title, symbol

FIGURE = {
    "id": "fig7",
    "claim": ("CaCO3 resists dissolution in the slurry only where the calcium dose and the dissolved carbonate keep "
              "the bulk supersaturated, and in the cell it is oxidised below the charge cutoffs of most cathode "
              "classes; the aluminium-oxide phases have no determined oxidation limit."),
    "caption_key": (
        "(a) R-slurry, C5 dissolution test (Omega_bulk >= 1 with the calcite K_sp and the contract speciation) "
        "at each design point: total calcium dose Ca_T (horizontal) by total dissolved carbonate C_T at the "
        "parameter table's minimum, value and maximum (vertical). Fill and hatching: verdict of the point "
        "(in the caption's order: feasible, plain; inconclusive, single hatching; falsified, cross "
        "hatching); the two water-activity points give the same verdict everywhere. Black line: Omega_bulk = 1 "
        "at the credible boundary P(Omega_bulk >= 1) = 1/2, interpolated in log Ca_T and C_T between the "
        "design points. (b) R-cell, potential vs Li+/Li, the sink of the C5 crossover (the caption names "
        "it and states that every other sink is undetermined under every scheme). One group of rows per gated "
        "phase (tick label), one row per gas-reference scheme: black, the all-experimental route (governing); "
        "blue, JANAF-based and vermillion, MP-based DFT schemes (comparators), dashed where corrected by the "
        "benchmark error. Left end: reduction limit; right end: oxidation limit; end tick, determined. An "
        "open circle at the axis edge: limit undetermined; an open square: no route for that limit (absent). "
        "Grey segment after the governing oxidation limit: the margin m_expt, ending at the falsification "
        "bound. Thin dashed vertical lines: the cathode classes' charge cutoffs E_cell_max (class values; the "
        "caption identifies them left to right). The 4.025 V bound is stated through a macro."),
    "width": "double",
    "height_cm": 7.0,
    "schema": "upstream:results_schema",
    "mock_input": "figures/src/mock/screen_c5.json",
    "input": "upstream:screen_table_r2",
    "aux": {"params": {"mock": "figures/src/mock/params.yaml", "real": "lit/params.yaml"}},
}

VERDICTS = ("feasible", "inconclusive", "falsified")
HATCH = {"feasible": None, "inconclusive": "////", "falsified": "xxxx"}
WORST = {v: i for i, v in enumerate(VERDICTS)}
CA_UNITS = {"mol dm^-3": 1e3, "mol m^-3": 1.0}  # to the register's unit for Ca_T, mol m^-3 (1 dm^3 = 1e-3 m^3)
# Scheme -> (Okabe-Ito colour or black, dashed). Two hue families keep every pair clear of the
# palette's CVD threshold; the benchmark-corrected variant of a DFT scheme is its hue, dashed.
SCHEMES = {
    "expt": ("black", False),
    "janaf": ("blue", False),
    "janaf_corrected": ("blue", True),
    "mp": ("vermillion", False),
    "mp_corrected": ("vermillion", True),
}
FORMULA = {"corundum": "Al2O3", "boehmite": "AlOOH"}  # tick labels by phase name (W4 AM2: corundum is mp-1143)


def c5(data):
    return data["claims"]["C5"]


# ------------------------------------------------------------------------------- panel a

def _ca_t(text):
    """Ca_T in mol m^-3 from a design-axis value such as '0.0001 mol dm^-3'."""
    m = re.fullmatch(r"\s*([0-9.eE+-]+)\s*(.+?)\s*", text)
    if not m or m.group(2) not in CA_UNITS:
        raise ValueError("fig7: cannot read the Ca_T design value %r" % text)
    return float(m.group(1)) * CA_UNITS[m.group(2)]


def _c_t(text, params):
    """C_T in mol m^-3 from a design-axis value such as 'dic_slurry@min' (parameter-table row)."""
    key, at = text.split("@")
    row = params["params"][key]
    if row["unit"] != "mol m^-3":
        raise ValueError("fig7: %s is in %s, not mol m^-3" % (key, row["unit"]))
    return float(row["value"] if at == "value" else row["range"][at])


def dose_grid(points, params):
    """(ca values, ct values, verdict grid [ct][ca], P_good grid [ct][ca]) over the design points.

    Points that differ only in further design axes (the water activity) must agree on the
    verdict; the caption says so, and a disagreement refuses the figure. P_good is the
    smallest over them.
    """
    cells = {}
    for name, pt in points.items():
        ca, ct = _ca_t(pt["axes"]["Ca_T"]), _c_t(pt["axes"]["C_T"], params)
        cells.setdefault((ca, ct), []).append((name, pt))
    cas = sorted({k[0] for k in cells})
    cts = sorted({k[1] for k in cells})
    verdict = np.empty((len(cts), len(cas)), dtype=object)
    p_good = np.full((len(cts), len(cas)), np.nan)
    for (ca, ct), pts in cells.items():
        vs = {pt["verdict"] for _n, pt in pts}
        if len(vs) != 1:
            raise ValueError("fig7: design points at Ca_T=%g, C_T=%g disagree: %s"
                             % (ca, ct, ", ".join("%s %s" % (n, p["verdict"]) for n, p in pts)))
        verdict[cts.index(ct), cas.index(ca)] = vs.pop()
        p_good[cts.index(ct), cas.index(ca)] = min(pt["P_good"] for _n, pt in pts)
    if any(v is None for v in verdict.flat):
        raise ValueError("fig7: the design points do not fill the Ca_T by C_T grid")
    return np.asarray(cas), np.asarray(cts), verdict, p_good


def _edges_log(c):
    lc = np.log10(c)
    mid = (lc[1:] + lc[:-1]) / 2.0
    return 10 ** np.concatenate([[lc[0] - (mid[0] - lc[0])], mid, [lc[-1] + (lc[-1] - mid[-1])]])


def _edges_lin(c):
    mid = (c[1:] + c[:-1]) / 2.0
    return np.concatenate([[c[0] - (mid[0] - c[0])], mid, [c[-1] + (c[-1] - mid[-1])]])


def omega_one_line(cas, cts, p_good):
    """Line segments of P(Omega_bulk >= 1) = 1/2, interpolated in (log10 Ca_T, C_T)."""
    import contourpy
    gen = contourpy.contour_generator(x=np.log10(cas), y=cts, z=p_good, line_type="Separate")
    return [np.column_stack([10 ** seg[:, 0], seg[:, 1]]) for seg in gen.lines(0.5)]


def _panel_slurry(ax, window, params, root, fills):
    cas, cts, verdict, p_good = dose_grid(window["points"], params)
    xe, ye = _edges_log(cas), _edges_lin(cts)
    lw = style.min_line_pt(root)
    for i in range(len(cts)):
        for j in range(len(cas)):
            v = verdict[i, j]
            ax.add_patch(Rectangle((xe[j], ye[i]), xe[j + 1] - xe[j], ye[i + 1] - ye[i],
                                   facecolor=fills[VERDICTS.index(v)], edgecolor="black", linewidth=lw,
                                   hatch=HATCH[v]))
    data_lw = float(style.applied(root)["line_width_data"]["value"])
    for seg in omega_one_line(cas, cts, p_good):
        ax.plot(seg[:, 0], seg[:, 1], color="black", linewidth=data_lw)
    ax.set_xscale("log")
    ax.set_xlim(xe[0], xe[-1])
    ax.set_ylim(ye[0], ye[-1])
    ax.set_xticks(cas, ["%g" % c for c in cas])
    ax.minorticks_off()
    ax.set_yticks(cts, ["%g" % c for c in cts])
    ax.set_xlabel(axis_title("Ca_T", root, unit=r"mol m$^{-3}$"))
    ax.set_ylabel(axis_title("C_T", root, unit=r"mol m$^{-3}$"))


# ------------------------------------------------------------------------------- panel b

def drawn_sinks(ox):
    """The sinks of the C5 crossovers (where a determined oxidation limit decides the test).

    Every other sink must have no determined oxidation limit under any scheme, which the
    caption states; otherwise the figure is refused.
    """
    sinks = sorted({s for per in ox.get("crossovers", {}).values() for s in per})
    others = {r["sink"] for r in ox["scheme_table"]} - set(sinks)
    det = sorted({"%s/%s/%s" % (r["phase"], r["sink"], r["scheme"]) for r in ox["scheme_table"]
                  if r["sink"] in others and r["status"] == "ok"})
    if det:
        raise ValueError("fig7: sinks outside the crossovers have determined oxidation limits: %s" % ", ".join(det))
    return sinks


def window_rows(ox, red, sinks):
    """[(phase, scheme, reduction row or None, oxidation row or None)] in drawing order."""
    rows, phases = {}, []
    for which, table in (("red", red["scheme_table"]), ("ox", ox["scheme_table"])):
        for r in table:
            if r["sink"] not in sinks:
                continue
            if r["phase"] not in phases:
                phases.append(r["phase"])
            rows.setdefault((r["phase"], r["scheme"]), {})[which] = r
    unknown = sorted({s for _p, s in rows} - set(SCHEMES))
    if unknown:
        raise ValueError("fig7: no drawing style for scheme(s) %s" % ", ".join(unknown))
    order = list(SCHEMES)
    out = []
    for ph in phases:
        for sc in sorted({s for p, s in rows if p == ph}, key=order.index):
            r = rows[(ph, sc)]
            out.append((ph, sc, r.get("red"), r.get("ox")))
    return out


def _status(row):
    return "absent" if row is None else row["status"]


def cutoff_values(ox):
    """{class: bound_V} at each cathode class's value point of the cutoff axis."""
    out = {}
    for key, v in ox["cutoff_axis"].items():
        cls, _sep, at = key.partition("@")
        if at == "value":
            out[cls] = float(v["bound_V"])
    return out


def _cap(ax, x, y, status, colour, lw):
    marker = "o" if status == "undetermined" else "s"
    ax.plot([x], [y], linestyle="none", marker=marker, markerfacecolor="white", markeredgecolor=colour,
            markeredgewidth=lw, clip_on=False, zorder=4)


def _panel_cell(ax, ox, red, root):
    lw = style.min_line_pt(root)
    data_lw = float(style.applied(root)["line_width_data"]["value"])
    sinks = drawn_sinks(ox)
    rows = window_rows(ox, red, sinks)
    cuts = cutoff_values(ox)
    margin = float(ox["margin_V"]) if ox.get("margin_V") is not None else None
    finite = [r["value_V"] for _p, _s, a, b in rows for r in (a, b) if r is not None and r["status"] == "ok"]
    span = finite + list(cuts.values())
    x_lo, x_hi = np.floor(2 * min(span)) / 2 - 0.5, np.ceil(2 * max(span)) / 2 + 0.5
    for v in sorted(set(cuts.values())):
        ax.axvline(v, color="black", linewidth=lw, linestyle=(0, (2, 2)), zorder=1)
    grey = style.palette(root)["categorical"]["okabe_ito"]["gray"]["hex"]
    y, cur, prev, ticks, labels = [], 0.0, None, [], []
    for ph, _sc, _a, _b in rows:
        if prev is not None and ph != prev:
            cur -= 0.8
        y.append(cur)
        cur -= 1.0
        prev = ph
    for yi, (ph, sc, rr, ro) in zip(y, rows):
        cname, dashed = SCHEMES[sc]
        colour = "black" if cname == "black" else style.categorical(cname, root)
        ls = (0, (3, 1.5)) if dashed else "-"
        lo = rr["value_V"] if _status(rr) == "ok" else None
        hi = ro["value_V"] if _status(ro) == "ok" else None
        a = lo if lo is not None else x_lo
        b = hi if hi is not None else x_hi
        ax.plot([a, b], [yi, yi], color=colour, linewidth=data_lw, linestyle=ls, clip_on=False, zorder=3)
        for val, st, edge in ((lo, _status(rr), x_lo), (hi, _status(ro), x_hi)):
            if val is not None:
                ax.plot([val], [yi], linestyle="none", marker="|", color=colour, markeredgewidth=data_lw, zorder=4)
            else:
                _cap(ax, edge, yi, st, colour, lw)
        if sc == "expt" and hi is not None and margin:
            ax.plot([hi, hi + margin], [yi, yi], color=grey, linewidth=data_lw, zorder=3)
            ax.plot([hi + margin], [yi], linestyle="none", marker="|", color=grey, markeredgewidth=data_lw, zorder=4)
        if not ticks or labels[-1] != ph:
            ticks.append(yi)
            labels.append(ph)
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(min(y) - 0.7, max(y) + 0.7)
    ax.set_yticks(ticks, [_formula_tick(FORMULA.get(p, p)) for p in labels])
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("%s (V vs Li$^{+}$/Li)" % symbol("E_Li", root))


def _formula_tick(name):
    return "$\\mathrm{%s}$" % re.sub(r"(\d+)", r"_{\1}", name)


PREFERRED_FILL = {"feasible": "blue", "inconclusive": "yellow", "falsified": "vermillion"}


def verdict_fills(root):
    """One fill per verdict (VERDICTS order) from the CVD-distinct set, by preferred hue where it is in it."""
    fills, names, _f, _d = distinct_fills(len(VERDICTS), root)
    by_name = dict(zip(names, fills))
    if set(PREFERRED_FILL.values()) == set(names):
        return [by_name[PREFERRED_FILL[v]] for v in VERDICTS]
    return fills


def build(data, root, aux):
    import matplotlib.pyplot as plt

    params = aux["params"]
    tests = c5(data)["tests"]
    fig, (ax_a, ax_b) = plt.subplots(1, 2, gridspec_kw={"width_ratios": [1, 1.3]},
                                     figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    fills = verdict_fills(root)
    # The claim's dose window holds every design point; the C5s test's own copy is its detail point.
    _panel_slurry(ax_a, c5(data)["dose_window"], params, root, fills)
    _panel_cell(ax_b, tests["C5c_ox"], tests["C5c_red"], root)
    panel_letters([ax_a, ax_b])
    return fig
