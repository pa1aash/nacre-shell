"""Fig. 17: stability map of the candidates: K2 dose-dependent window by pH against the K1 upper bound."""
import numpy as np

from nacre.figs import k2ph, regimes, style
from nacre.figs.panels import panel_letters
from nacre.figs.symbols import axis_title, symbol

FIGURE = {
    "id": "fig17",
    "claim": ("Dissolution stability and oxidative stability are separate tests: the candidates that pass K2 over "
              "the widest pH range sit at K1 upper bounds below the two higher cutoff classes, and the "
              "condensed and aluminium phosphates, which have no pH-dependent K2 map, have an upper bound "
              "but no lower one."),
    "caption_key": (
        "(a) One row of markers per candidate that has both a K2 map and a K1 upper bound, at its tier-1 upper "
        "bound on the oxidation limit (vertical, V vs Li+/Li); horizontal: slurry pH of the K2 cell sets (acid-"
        "adjusted state, then the as-prepared slurry); rows ordered by upper bound, rows with equal bounds "
        "offset slightly. Marker area: fraction of cells that pass. Filled circle: the lowest passing dose is "
        "below 0.01 mol/dm^3; open circle: at or above it. Cross: thermodynamically excluded at that pH; plus: "
        "open; dot: undetermined. (b) Candidates without a pH-dependent K2 map: bar from the upper bound "
        "downward with no lower end, the lower bound being pending. Grey line and bands: the registered "
        "cutoff classes, lowest to highest."),
    "width": "double",
    "height_cm": 12.0,
    "schema": "figures/src/schemas/perph_ph2.schema.json",
    "mock_input": "figures/src/mock/perph_ph2.json",
    "input": "upstream:k2_perph_ph2",
    "aux": {
        "k2": {"mock": "figures/src/mock/k2_grid.json", "real": "upstream:k2_grid_ph"},
        "acid": {"mock": "figures/src/mock/k2_acid_ph2.json", "real": "upstream:k2_acid_ph2"},
        "alkaline": {"mock": "figures/src/mock/k2_alkaline_ph2.json", "real": "upstream:k2_alkaline_ph2"},
        "ladder": {"mock": "figures/src/mock/ladder_eub.json", "real": "upstream:ladder_v3"},
        "cutoffs": {"mock": "figures/src/mock/ladder_cutoffs.yaml", "real": "upstream:thresholds_screen_ph"},
    },
}

CLASSES = ("C_lo", "C_mid", "C_hi")
FRAMING = "crystalline"
AGGREGATE = ("ALL", "-")
K1_ON = {"CaCO3": "calcite"}  # the ladder's carbonate control row is drawn on the calcite row (as in Fig. 15)
MAP_ORDER = ("calcite", "a-TCP", "ACP", "b-TCP", "HAp", "brushite")  # tie order, bottom to top
NO_K2_MAP = ("CaSiO3", "Ca2SiO4", "Li2SiO3", "Ca2P2O7", "Ca(PO3)2 / Ca-polyphosphate glass",
             "(LiPO3)n Hydro-Quebec film", "AlPO4", "baked aluminophosphate (Tsinghua)")
TIE_STEP = 0.012  # V: vertical offset between rows of equal upper bound
MARKER_MAX_PT = 7.0  # diameter at a passing fraction of one
GREY = ("0.55", "0.85", "0.7")  # C_lo line, C_mid band, C_hi band
LABELS = {
    "CaSiO3": "CaSiO$_3$", "Ca2SiO4": "Ca$_2$SiO$_4$", "Li2SiO3": "Li$_2$SiO$_3$", "Ca2P2O7": "Ca$_2$P$_2$O$_7$",
    "Ca(PO3)2 / Ca-polyphosphate glass": "Ca(PO$_3$)$_2$", "(LiPO3)n Hydro-Quebec film": "(LiPO$_3$)$_n$",
    "AlPO4": "AlPO$_4$", "baked aluminophosphate (Tsinghua)": "baked Al phosphate",
}


def upper_bounds(ladder):
    """{ladder phase: E_ub in V}: the lowest computed upper bound over the reactions of the crystalline framing.

    Where the aggregate row carries a bound it is that minimum; where the aggregate is blank because the
    budget is incomplete (AlPO4 r4, the silicates), the bound of the reactions that were computed stands.
    A phase with no computed bound is absent.
    """
    out = {}
    for r in ladder["rows"]:
        if r["framing"] != FRAMING or r["reaction_id"] in AGGREGATE or r["stage"] == "conversion":
            continue
        if r["E_ub_V"] in ("", None):
            continue
        out[r["phase"]] = min(out.get(r["phase"], np.inf), float(r["E_ub_V"]))
    for r in ladder["rows"]:
        if r["framing"] == FRAMING and r["reaction_id"] == "ALL" and r["E_ub_V"] not in ("", None):
            if abs(float(r["E_ub_V"]) - out.get(r["phase"], np.inf)) > 5e-5:
                raise ValueError("fig17: aggregate bound of %s differs from the lowest reaction bound" % r["phase"])
    return out


def cutoff_classes(cutoffs):
    cls = cutoffs["screen_ph"]["margins_v6"]["cutoff_classes"]
    return {k: [float(x) for x in cls[k]["E_c_V"]] for k in CLASSES}


def map_rows(ladder, states):
    """[(phase, E_ub, {pH: State})] of the candidates with a K2 map and a K1 bound, with tie offsets applied later."""
    ub = upper_bounds(ladder)
    rows = []
    for lad, k2 in [(p, K1_ON.get(p, p)) for p in ub]:
        if k2 in states:
            by_ph = dict(states[k2]["acid"])
            by_ph.update(states[k2]["alkaline"])
            rows.append((k2, ub[lad], by_ph))
    rows.sort(key=lambda r: (r[1], MAP_ORDER.index(r[0])))
    return rows


def offsets(rows):
    """Vertical offset of each row: rows of equal bound (to 1e-4 V) are spread symmetrically by TIE_STEP."""
    out, i = {}, 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and abs(rows[j + 1][1] - rows[i][1]) < 1e-4:
            j += 1
        n = j - i + 1
        for k in range(n):
            out[rows[i + k][0]] = (k - (n - 1) / 2.0) * TIE_STEP
        i = j + 1
    return out


def bar_rows(ladder, mapped):
    ub = upper_bounds(ladder)
    rows = sorted(((p, v) for p, v in ub.items() if p in NO_K2_MAP and K1_ON.get(p, p) not in mapped),
                  key=lambda r: r[1])
    missing = [p for p in ub if p not in NO_K2_MAP and K1_ON.get(p, p) not in mapped]
    if missing:
        raise ValueError("fig17: no K2 map and not listed as without one: %s" % missing)
    return rows


def draw_bands(ax, classes, lw):
    lo, mid, hi = (classes[c] for c in CLASSES)
    ax.axhline(lo[0], color=GREY[0], linewidth=lw * 2)
    ax.axhspan(*mid, facecolor=GREY[1], edgecolor="none", zorder=0)
    ax.axhspan(*hi, facecolor=GREY[2], edgecolor="none", zorder=0)


def build(data, root, aux):
    import matplotlib.pyplot as plt

    states = k2ph.states(data, aux["k2"], aux["acid"], aux["alkaline"])
    rows = map_rows(aux["ladder"], states)
    off = offsets(rows)
    bars = bar_rows(aux["ladder"], {r[0] for r in rows})
    classes = cutoff_classes(aux["cutoffs"])
    fills = regimes.fills(root)
    lw = style.min_line_pt(root)
    data_lw = float(style.applied(root)["line_width_data"]["value"])
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root),
                                     gridspec_kw={"width_ratios": [3.0, 1.6]})
    for ax in (ax_a, ax_b):
        draw_bands(ax, classes, lw)
    suitable = regimes.FROM_VERDICT["feasible"]
    for phase, e_ub, by_ph in rows:
        y = e_ub + off[phase]
        for ph, s in sorted(by_ph.items()):
            if s.word == suitable:
                size = MARKER_MAX_PT * np.sqrt(s.fraction)
                ax_a.plot([ph], [y], marker="o", markersize=size, markeredgewidth=lw, markeredgecolor="black",
                          markerfacecolor="white" if s.high else fills[suitable], linestyle="none", zorder=3)
            else:
                mk = {"excluded": "x", "open": "+", "undetermined": "."}[s.word]
                ax_a.plot([ph], [y], marker=mk, markersize=3.6 if mk != "." else 5.0, markeredgewidth=data_lw,
                          markeredgecolor="black", markerfacecolor="black", linestyle="none", zorder=3)
    phs = sorted({p for _n, _e, by in rows for p in by})
    lows = [e for _p, e in bars] + [e for _n, e, _b in rows] + [classes["C_lo"][0]]
    ax_a.set_ylim(min(e for _n, e, _b in rows) - 0.1, max(classes["C_hi"]) + 0.1)
    ax_b.set_ylim(min(lows) - 0.15, max(lows + classes["C_hi"]) + 0.1)
    for k, (_phase, e_ub) in enumerate(bars):
        ax_b.plot([k, k], [e_ub, ax_b.get_ylim()[0]], color="black", linewidth=data_lw, zorder=3)
        ax_b.plot([k], [e_ub], marker="_", markersize=5.0, markeredgewidth=data_lw, markeredgecolor="black",
                  linestyle="none", zorder=3)
    ax_a.set_xticks(phs, ["%g" % p for p in phs])
    ax_a.set_xlim(min(phs) - 0.6, max(phs) + 0.6)
    ax_a.set_xlabel(symbol("pH", root) + " of the K2 slurry state")
    ax_a.set_ylabel(axis_title("E_ub", root, unit="V vs Li$^{+}$/Li"))
    ax_b.set_ylabel(axis_title("E_ub", root, unit="V vs Li$^{+}$/Li"))
    ax_b.set_xlim(-0.6, len(bars) - 0.4)
    ax_b.set_xticks(range(len(bars)), [LABELS[p] for p, _e in bars], rotation=90)
    for ax in (ax_a, ax_b):
        ax.spines[["top", "right"]].set_visible(False)
    panel_letters([ax_a, ax_b])
    return fig
