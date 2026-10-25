"""Fig. 14: the required-precision map, one row per quantity of the screen."""
import re

import numpy as np
from matplotlib.patches import Rectangle

from nacre.figs import style
from nacre.figs.panels import panel_letters

FIGURE = {
    "id": "fig14",
    "claim": ("Few quantities can settle a verdict by measurement alone: most flip values lie outside the "
              "present prior range or need a width well below it, and the rows without a registered prior "
              "have no required precision at all."),
    "caption_key": (
        "One row per quantity, grouped by the verdict link it settles (gaps between groups). (a) The prior "
        "range of the quantity, scaled to width one (grey band; log scale for a log-uniform prior), and the "
        "flip value with its 5 to 95 percent range where the output gives one. (b) The required width of the "
        "measurement as a fraction of the present prior width (bar from zero). (c) Rows with no numerical "
        "required width: left, no flip in the physical range or closed by definition; middle, unreachable at "
        "the prior; right, gap or not computable. Marker: evidence grade of the present input (circle A, "
        "square B, triangle C, inverted triangle D, diamond ignorance prior, cross no grade); open marker and "
        "dashed line: gap row, no registered prior."),
    "width": "double",
    "height_cm": 13.0,
    "schema": "figures/src/schemas/precision_map.schema.json",
    "mock_input": "figures/src/mock/precision_map.json",
    "input": "upstream:precision_map_ph",
}

MARKERS = {"A": "o", "B": "s", "C": "^", "D": "v", "ignorance": "D", "none": "x"}
FLIP_KEYS = ("q05_q50_q95", "flip_q05_q50_q95", "upper_bound_q05_q50_q95")
PRIOR_PAIRS = (("central95_J_m2",), ("low_high_J_m2",), ("registered_interval",))
STATUS_COLUMNS = {  # status word of the output -> column of panel c
    "no_flip": 0, "no_flip_in_physical_range": 0, "closed": 0, "no_inconclusive_cell_before_control": 0,
    "unreachable": 1,
    "gap": 2, "not_computable": 2,
}
GAP_GROUP = 0.7
K1_ROW = "k1"  # the one row that stands for every K1 row of the output


PHASE = {"hap": "HAp", "btcp": r"$\beta$-TCP", "acp": "ACP", "ocp": "OCP", "brushite": "brushite",
         "atcp": r"$\alpha$-TCP", "li3po4": r"Li$_3$PO$_4$"}
KSP = r"$K_{\mathrm{sp}}$"
# Typeset tick label of each output row id; the quantity names are those of the output's own `quantity` field.
LABELS = {
    "gamma_sn": r"$\gamma_{\mathrm{sn}}$", "gamma_nv": r"$\gamma_{\mathrm{nv}}$", "gamma_nl": r"$\gamma_{\mathrm{nl}}$",
    "A_patch": r"$A_{\mathrm{patch}}$", "c1_dupre_gamma_ow": r"C1 $\gamma_{\mathrm{ow}}$",
    "c1_dupre_gamma_op": r"C1 $\gamma_{\mathrm{op}}$", "c1_dupre_joint": r"C1 $\gamma_{\mathrm{ow}},\gamma_{\mathrm{op}}$",
    "c1_analog_w_adh_wet": r"C1 $W_{\mathrm{adh,wet}}$", "c1_pmf": r"C1 $\Delta F_{\mathrm{pmf}}$, $A_{\mathrm{c}}$",
    "n_hyd_acp": r"$n_{\mathrm{hyd}}$ ACP", "t_wet": r"$t_{\mathrm{wet}}$", "f_min": r"$f_{\mathrm{min}}$",
    "ksp_alpp": KSP + " Al polyphosphate", "binodal_map": "binodal map",
    "gamma_nl_coacervate": r"$\gamma_{\mathrm{nl}}$ coacervate",
    K1_ROW: "K1",
}
LABELS.update({"k2_ksp_" + k: "K2 %s %s" % (KSP, v) for k, v in PHASE.items()})


def label(row_id):
    """Typeset tick label of an output row id; refuses an id without one."""
    if row_id not in LABELS:
        raise ValueError("fig14: no typeset label for the row id %r" % row_id)
    return LABELS[row_id]


def collapse_k1(rows):
    """The K1 rows (ids k1_*) as one row, when they all draw the same; refuses a K1 row that differs.

    Returns (rows with the K1 block replaced by one row of id K1_ROW, number of K1 rows collapsed).
    """
    k1 = [r for r in rows if r["id"].startswith("k1_")]
    if not k1:
        return rows, 0
    sig = lambda r: {k: v for k, v in r.items() if k != "id"}  # noqa: E731
    if any(sig(r) != sig(k1[0]) for r in k1):
        raise ValueError("fig14: the K1 rows no longer draw identically; they cannot be collapsed")
    out, done = [], False
    for r in rows:
        if r["id"].startswith("k1_"):
            if not done:
                out.append(dict(k1[0], id=K1_ROW))
                done = True
        else:
            out.append(r)
    return out, len(k1)


def grade(row):
    """Evidence-grade class of the present input: A to D, 'ignorance' or 'none'."""
    g = (row.get("prior") or {}).get("evidence_grade")
    s = g if isinstance(g, str) else (row.get("evidence_grade") or "")
    if s.startswith("ignorance"):
        return "ignorance"
    if s.startswith("gap"):
        s = s.split(";")[-1]
    m = re.search(r"\b([A-D])\b", s)
    return m.group(1) if m else "none"


def is_gap(row):
    return row.get("kind") == "gap" or bool((row.get("prior") or {}).get("gap"))


def prior_range(row):
    """(low, high, log) of the registered prior, or None."""
    p = row.get("prior") or {}
    if is_gap(row):
        return None
    for (key,) in PRIOR_PAIRS:
        if key in p:
            lo, hi = (float(v) for v in p[key])
            return lo, hi, "loguniform" in p.get("family", "")
    if "low" in p and "high" in p:
        return float(p["low"]), float(p["high"]), False
    return None


def flip_values(row):
    """(q05, q50, q95) or (v, v, v) of the flip value where the output gives one, else None."""
    f = row.get("flip") or {}
    for key in FLIP_KEYS:
        if key in f:
            return tuple(float(v) for v in f[key])
    if isinstance(f.get("value"), (int, float)):
        return (float(f["value"]),) * 3
    return None


def scale(values, rng):
    """Positions of `values` with the prior range [lo, hi] mapped to [0, 1] (logarithmic if flagged)."""
    lo, hi, log = rng
    v = np.asarray(values, dtype=float)
    if log:
        if min(lo, hi, *v) <= 0:
            raise ValueError("fig14: a log-scaled prior needs positive values")
        v, lo, hi = np.log(v), np.log(lo), np.log(hi)
    return (v - lo) / (hi - lo)


def required_ratio(row, rng):
    """Required width as a fraction of the present prior width, with its source, or None.

    The output's own width_ratio where it has one (the row, else the median over the cells of a
    K2 row); for a row that gives only a required half-width h and a prior range, 2h over the
    prior width.
    """
    rp = row.get("required_precision") or {}
    if isinstance(rp.get("width_ratio"), (int, float)):
        return float(rp["width_ratio"])
    s = row.get("summary") or {}
    if isinstance(s.get("median_width_ratio"), (int, float)):
        return float(s["median_width_ratio"])
    h = rp.get("required_half_width_J_m2")
    if isinstance(h, (int, float)) and rng is not None and not rng[2]:
        return 2.0 * float(h) / abs(rng[1] - rng[0])
    return None


def status_column(row, ratio):
    """Column of panel c for a row with no numerical required width, else None."""
    if ratio is not None:
        return None
    rp = row.get("required_precision") or {}
    s = row.get("summary") or {}
    word = rp.get("status")
    if word is None and s.get("unreachable"):
        word = "unreachable"
    if word in STATUS_COLUMNS:
        return STATUS_COLUMNS[word]
    if word is None:
        raise ValueError("fig14: row %s has neither a required width nor a status" % row["id"])
    raise ValueError("fig14: row %s: no panel-c column for the status %r" % (row["id"], word))


def rows_of(data):
    out = []
    for r in data["rows"]:
        rng = prior_range(r)
        ratio = required_ratio(r, rng)
        flip = flip_values(r)
        out.append({
            "id": r["id"], "group": r["link"].split()[0], "gap": is_gap(r), "grade": grade(r), "range": rng,
            "flip": None if (flip is None or rng is None) else scale(flip, rng),
            "ratio": ratio, "column": status_column(r, ratio),
        })
    return out


def build(data, root, aux):
    import matplotlib.pyplot as plt

    rows, _n = collapse_k1(rows_of(data))
    y, cur, prev = {}, 0.0, None
    for r in rows:
        if prev is not None and r["group"] != prev:
            cur -= GAP_GROUP
        y[r["id"]] = cur
        cur -= 1.0
        prev = r["group"]
    lw = style.min_line_pt(root)
    data_lw = float(style.applied(root)["line_width_data"]["value"])
    fig, axes = plt.subplots(1, 3, figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root),
                             gridspec_kw={"width_ratios": [3.0, 2.2, 0.9]}, sharey=True)
    ax_a, ax_b, ax_c = axes
    for r in rows:
        yy = y[r["id"]]
        filled = not r["gap"]
        mk = MARKERS[r["grade"]]
        mkw = dict(marker=mk, markersize=3.6, markeredgewidth=lw, markeredgecolor="black",
                   markerfacecolor="black" if filled and mk != "x" else "white", linestyle="none")
        if r["range"] is not None:
            ax_a.add_patch(Rectangle((0.0, yy - 0.32), 1.0, 0.64, facecolor="0.85", edgecolor="none"))
        elif r["gap"]:
            ax_a.plot([0.0, 1.0], [yy, yy], color="black", linewidth=lw, linestyle=(0, (2, 2)))
        if r["flip"] is not None:
            lo, mid, hi = r["flip"]
            ax_a.plot([lo, hi], [yy, yy], color="black", linewidth=data_lw)
            ax_a.plot([mid], [yy], **mkw)
        if r["ratio"] is not None:
            ax_b.plot([0.0, r["ratio"]], [yy, yy], color="black", linewidth=data_lw)
            ax_b.plot([r["ratio"]], [yy], **mkw)
        if r["column"] is not None:
            ax_c.plot([r["column"]], [yy], **mkw)
        if r["range"] is None and r["flip"] is None and r["ratio"] is None and r["column"] is None:
            raise ValueError("fig14: row %s carries nothing to draw" % r["id"])
    ax_a.axvline(0.0, color="black", linewidth=lw)
    ax_a.axvline(1.0, color="black", linewidth=lw)
    xs = [v for r in rows if r["flip"] is not None for v in r["flip"]]
    ax_a.set_xlim(min(-0.1, min(xs) - 0.05), max(1.1, max(xs) + 0.05))
    ax_b.set_xlim(-0.05, 1.05)
    ax_b.set_xticks([0.0, 0.5, 1.0], ["0", "0.5", "1"])
    ax_c.set_xlim(-0.6, 2.6)
    ax_c.set_xticks([])
    ax_a.set_yticks([y[r["id"]] for r in rows], [label(r["id"]) for r in rows])
    ax_a.set_ylim(min(y.values()) - 0.8, max(y.values()) + 0.8)
    ax_a.set_xlabel("Prior range and flip value (prior width = 1)")
    ax_b.set_xlabel("Required width / present width")
    for ax in (ax_a, ax_b, ax_c):
        ax.tick_params(axis="y", length=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    for ax in (ax_b, ax_c):
        ax.tick_params(axis="y", labelleft=False)
    panel_letters(axes)
    return fig
