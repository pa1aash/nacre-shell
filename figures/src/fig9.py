"""Fig. 9: the K1 tier-1 ladder at the registered cutoff classes, by regime and framing."""
import numpy as np
from matplotlib.patches import Rectangle

from nacre.figs import style
from nacre.figs.colours import distinct_fills
from nacre.figs.symbols import symbol

FIGURE = {
    "id": "fig9",
    "claim": ("The tier-1 verdict depends on the cutoff class and on the framing: crystalline calcium "
              "orthophosphates and the carbonate control are excluded at the two higher classes and not at the "
              "lowest, Ca2SiO4 is excluded at all three, and the amorphous framing is undetermined except for two "
              "phases."),
    "caption_key": (
        "One row per phase, grouped top to bottom by regime and role: R-slurry phases, R-cell phases, silicate "
        "comparators, the carbonate control (gaps between groups). Three pairs of columns, one pair per "
        "registered cutoff class (tick labels, V vs Li+/Li; the lowest class is the nominal value, and the "
        "sensitivity with the sourced upper cutoff leaves every verdict unchanged); within a pair, crystalline "
        "framing left and amorphous framing right. Fill and hatching: verdict of the tier-1 aggregate at the "
        "class (excluded, cross hatching; inconclusive, single hatching; undetermined, plain)."),
    "width": "double",
    "height_cm": 9.0,
    "schema": "figures/src/schemas/ladder_v3.schema.json",
    "mock_input": "figures/src/mock/ladder_v3.json",
    "input": "upstream:ladder_v3",
    "aux": {"sens40": {"mock": "figures/src/mock/ladder_v3_sens40.json", "real": "upstream:ladder_v3_sens40"},
            "cutoffs": {"mock": "figures/src/mock/ladder_cutoffs.yaml", "real": "upstream:thresholds_screen_ph"}},
}

STAGES = ("slurry", "cell", "comparator", "control")  # regime and role, in drawing order
FRAMINGS = ("crystalline", "amorphous")
AGGREGATE = ("ALL", "-")  # the aggregate row of a (phase, framing, stage): ALL over reactions, '-' for a gap
CLASS_COLUMNS = (("C_lo", "k1_class_lfp"), ("C_mid", "k1_class_42_43"), ("C_hi", "k1_class_44_45"))
# The data's verdict word -> the registered word, drawing order, fill hue and hatching.
VERDICTS = {"falsified": "excluded", "inconclusive": "inconclusive", "undetermined": "undetermined"}
ORDER = ("falsified", "inconclusive", "undetermined")
HUE = {"falsified": "vermillion", "inconclusive": "yellow", "undetermined": "blue"}
HATCH = {"falsified": "xxxx", "inconclusive": "////", "undetermined": None}
LABELS = {
    "brushite": "brushite", "ACP": "ACP", "HAp": "HAp", "OCP": "OCP", "b-TCP": "$\\beta$-TCP",
    "a-TCP": "$\\alpha$-TCP", "Li3PO4": "Li$_3$PO$_4$", "Ca2P2O7": "Ca$_2$P$_2$O$_7$",
    "Ca(PO3)2 / Ca-polyphosphate glass": "Ca(PO$_3$)$_2$ glass", "AlPO4": "AlPO$_4$",
    "Al(PO3)3": "Al(PO$_3$)$_3$", "Al-polyphosphate (R1 gel)": "Al polyphosphate gel",
    "(LiPO3)n Hydro-Quebec film": "(LiPO$_3$)$_n$ film", "baked aluminophosphate (Tsinghua)": "baked aluminophosphate",
    "CaSiO3": "CaSiO$_3$", "Ca2SiO4": "Ca$_2$SiO$_4$", "Li2SiO3": "Li$_2$SiO$_3$", "CaCO3": "CaCO$_3$",
}
GAP_CLASS, GAP_GROUP = 0.7, 0.8  # column gap between class pairs; row gap between groups


def ladder_cells(data):
    """{(phase, framing): {class: data verdict}} and the phases by group in file order.

    Keeps the rows of the two framings in the four drawn stages that carry the aggregate of a
    (phase, framing, stage); refuses a duplicate aggregate, an unknown verdict, a phase without a
    display label and a phase that lacks one of the two framings.
    """
    cells, groups = {}, {s: [] for s in STAGES}
    for r in data["rows"]:
        if r["stage"] not in STAGES or r["framing"] not in FRAMINGS or r["reaction_id"] not in AGGREGATE:
            continue
        key = (r["phase"], r["framing"])
        if key in cells:
            raise ValueError("fig9: two aggregate rows for %s %s" % key)
        verdicts = {c: r[col] for c, col in CLASS_COLUMNS}
        bad = sorted({v for v in verdicts.values() if v not in VERDICTS})
        if bad:
            raise ValueError("fig9: unknown verdict %s for %s %s" % (bad, *key))
        if r["phase"] not in LABELS:
            raise ValueError("fig9: no display label for phase %r" % r["phase"])
        cells[key] = verdicts
        if r["phase"] not in groups[r["stage"]]:
            groups[r["stage"]].append(r["phase"])
    for stage, phases in groups.items():
        for ph in phases:
            if any((ph, f) not in cells for f in FRAMINGS):
                raise ValueError("fig9: %s lacks a framing" % ph)
    return cells, groups


def same_verdicts(data, sens):
    """Refuse the figure unless the 4.0 V sensitivity file gives every verdict of the main file."""
    def table(d):
        return {(r["phase"], r["framing"], r["stage"], r["reaction_id"]): tuple(r[c] for _k, c in CLASS_COLUMNS)
                for r in d["rows"]}
    a, b = table(data), table(sens)
    if a != b:
        diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        raise ValueError("fig9: the 4.0 V sensitivity changes verdicts (%d rows, first %s); the caption says it does not"
                         % (len(diff), diff[0]))


def class_labels(cutoffs):
    """Tick label per class from the registered cutoff classes: one value, or the range of two."""
    cls = cutoffs["screen_ph"]["margins_v6"]["cutoff_classes"]
    out = []
    for key, _col in CLASS_COLUMNS:
        v = [float(x) for x in cls[key]["E_c_V"]]
        out.append("%g" % v[0] if len(v) == 1 else "%g–%g" % (min(v), max(v)))
    return out


def verdict_fills(root):
    fills, names, _f, _d = distinct_fills(len(ORDER), root)
    by_name = dict(zip(names, fills))
    if set(HUE.values()) != set(names):
        return dict(zip(ORDER, fills))
    return {v: by_name[HUE[v]] for v in ORDER}


def build(data, root, aux):
    import matplotlib.pyplot as plt

    same_verdicts(data, aux["sens40"])
    cells, groups = ladder_cells(data)
    fills = verdict_fills(root)
    lw = style.min_line_pt(root)
    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    y, ticks, labels, cur = {}, [], [], 0.0
    for stage in STAGES:
        if not groups[stage]:
            continue
        if y:
            cur -= GAP_GROUP
        for ph in groups[stage]:
            y[ph] = cur
            ticks.append(cur)
            labels.append(LABELS[ph])
            cur -= 1.0
    x0 = [k * (len(FRAMINGS) + GAP_CLASS) for k in range(len(CLASS_COLUMNS))]
    for (ph, fr), verdicts in cells.items():
        for k, (cls, _col) in enumerate(CLASS_COLUMNS):
            v = verdicts[cls]
            ax.add_patch(Rectangle((x0[k] + FRAMINGS.index(fr), y[ph] - 0.5), 1.0, 1.0, facecolor=fills[v],
                                   edgecolor="black", linewidth=lw, hatch=HATCH[v]))
    ax.set_xlim(-0.2, x0[-1] + len(FRAMINGS) + 0.2)
    ax.set_ylim(min(y.values()) - 0.7, max(y.values()) + 0.7)
    ax.set_xticks([x + len(FRAMINGS) / 2 for x in x0], class_labels(aux["cutoffs"]))
    ax.set_yticks(ticks, labels)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("%s class (V vs Li$^{+}$/Li)" % symbol("E_cell_max", root))
    return fig
