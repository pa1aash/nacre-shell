"""Fig. 15: candidate-by-regime heatmap from the K1 ladder and the K2 production outputs."""
from matplotlib.patches import Rectangle

from nacre.figs import regimes, style

FIGURE = {
    "id": "fig15",
    "claim": ("The phosphates that pass K2 in the as-prepared slurry (HAp, ACP, beta-TCP) and the carbonate are "
              "thermodynamically excluded at the two higher cutoff classes and open at the lowest, while most "
              "amorphous framings and the aluminium phosphates are open or undetermined: passing dissolution stability "
              "does not settle the cell regime."),
    "caption_key": (
        "One row per phase or baseline, grouped top to bottom: R-slurry phases, R-cell phases, silicate "
        "comparators, the carbonate polymorphs (gaps between groups). Columns: K2 in the as-prepared "
        "(processing) slurry; K2 in the acid-adjusted slurry state (suitable where any grid cell passes); then "
        "one pair of columns per registered K1 cutoff class (tick labels, V vs Li+/Li; the lowest is the "
        "nominal class), crystalline framing left and amorphous right. Fill and hatching: suitable against "
        "dissolution (dots), undetermined (plain), open (single hatching), thermodynamically excluded (cross "
        "hatching); no fill: not tested in that column. K1 of the carbonate is drawn on the calcite row."),
    "width": "double",
    "height_cm": 10.0,
    "schema": "figures/src/schemas/ladder_v3.schema.json",
    "mock_input": "figures/src/mock/ladder_v3.json",
    "input": "upstream:ladder_v3",
    "aux": {"k2": {"mock": "figures/src/mock/k2_grid.json", "real": "upstream:k2_grid_ph"},
            "films": {"mock": "figures/src/mock/phosphate_films.json", "real": "upstream:phosphate_films_ph"},
            "cutoffs": {"mock": "figures/src/mock/ladder_cutoffs.yaml", "real": "upstream:thresholds_screen_ph"}},
}

STAGES = ("slurry", "cell", "comparator")  # the ladder groups drawn; the carbonate control group follows
FRAMINGS = ("crystalline", "amorphous")
AGGREGATE = ("ALL", "-")
CLASS_COLUMNS = (("C_lo", "k1_class_lfp"), ("C_mid", "k1_class_42_43"), ("C_hi", "k1_class_44_45"))
POLYMORPHS = ("calcite", "aragonite", "ACC")
K1_ON = "calcite"  # the ladder's CaCO3 control row is drawn on this carbonate row
K2_COLUMNS = ("processing", "acid-adjusted")
LABELS = {
    "brushite": "brushite", "ACP": "ACP", "HAp": "HAp", "OCP": "OCP", "b-TCP": "$\\beta$-TCP",
    "a-TCP": "$\\alpha$-TCP", "Li3PO4": "Li$_3$PO$_4$", "Ca2P2O7": "Ca$_2$P$_2$O$_7$",
    "Ca(PO3)2 / Ca-polyphosphate glass": "Ca(PO$_3$)$_2$ glass", "AlPO4": "AlPO$_4$",
    "Al(PO3)3": "Al(PO$_3$)$_3$", "Al-polyphosphate (R1 gel)": "Al polyphosphate gel",
    "(LiPO3)n Hydro-Quebec film": "(LiPO$_3$)$_n$ film", "baked aluminophosphate (Tsinghua)": "baked aluminophosphate",
    "CaSiO3": "CaSiO$_3$", "Ca2SiO4": "Ca$_2$SiO$_4$", "Li2SiO3": "Li$_2$SiO$_3$",
    "calcite": "calcite", "aragonite": "aragonite", "ACC": "ACC",
}
GAP_COL, GAP_GROUP = 0.6, 0.8
W_K2 = 1.5  # width of a K2 column (its tick label is a word)


def ladder_rows(data):
    """({phase: {class: registered word}} per framing, phases by group): the K1 aggregate rows."""
    cells, groups = {}, {s: [] for s in STAGES}
    for r in data["rows"]:
        if r["framing"] not in FRAMINGS or r["reaction_id"] not in AGGREGATE:
            continue
        verdicts = {c: r[col] for c, col in CLASS_COLUMNS}
        if r["stage"] == "control":
            if r["phase"] != "CaCO3":
                raise ValueError("fig15: unexpected control phase %r" % r["phase"])
            key = (K1_ON, r["framing"])
        elif r["stage"] in STAGES:
            key = (r["phase"], r["framing"])
            if r["phase"] not in LABELS:
                raise ValueError("fig15: no display label for phase %r" % r["phase"])
            if r["phase"] not in groups[r["stage"]]:
                groups[r["stage"]].append(r["phase"])
        else:
            continue
        if key in cells:
            raise ValueError("fig15: two aggregate rows for %s %s" % key)
        out = {}
        for c, v in verdicts.items():
            out[c] = None if v == "n/a" else regimes.word({"falsified": "falsified", "inconclusive": "inconclusive",
                                                          "undetermined": "undetermined"}[v])
        cells[key] = out
    return cells, groups


def k2_processing(k2, films):
    """{phase: registered word} of the as-prepared slurry: carbonates from the K2 grid, the rest from the film rows."""
    out = {}
    for name, blk in k2["extensions"]["p0-w4"]["k2_grid"]["carbonate"]["polymorphs"].items():
        out[name] = regimes.aggregate(c["verdict"] for c in blk["cells"].values())
    for r in films["ph_rows"]:
        if r["stage"] == "slurry" and "K2" in r:
            out[r["phase"]] = regimes.word(r["K2"]["verdict"])
    return out


def k2_acid(k2):
    acid = k2["extensions"]["p0-w4"]["k2_grid"]["acid_adjusted"]
    out = {n: regimes.aggregate(c["verdict"] for c in b["cells"].values()) for n, b in acid["carbonate"].items()}
    for b in acid["phosphate"].values():
        out[b["ladder_phase"]] = regimes.aggregate(c["verdict"] for c in b["cells"].values())
    return out


def class_labels(cutoffs):
    cls = cutoffs["screen_ph"]["margins_v6"]["cutoff_classes"]
    out = []
    for key, _col in CLASS_COLUMNS:
        v = [float(x) for x in cls[key]["E_c_V"]]
        out.append("%g" % v[0] if len(v) == 1 else "%g–%g" % (min(v), max(v)))
    return out


def match(table, phase):
    """The entry of `table` for a ladder phase: exact name, else the one entry whose name the phase starts with."""
    if phase in table:
        return table[phase]
    hits = [k for k in table if phase.startswith(k) and len(k) > 3]
    return table[hits[0]] if len(hits) == 1 else None


def build(data, root, aux):
    import matplotlib.pyplot as plt

    k1, groups = ladder_rows(data)
    proc, acid = k2_processing(aux["k2"], aux["films"]), k2_acid(aux["k2"])
    fills = regimes.fills(root)
    lw = style.min_line_pt(root)
    order = [list(groups[s]) for s in STAGES] + [list(POLYMORPHS)]
    y, ticks, labels, cur = {}, [], [], 0.0
    for grp in order:
        if not grp:
            continue
        if y:
            cur -= GAP_GROUP
        for ph in grp:
            y[ph] = cur
            ticks.append(cur)
            labels.append(LABELS[ph])
            cur -= 1.0
    x_k2 = [0.0, W_K2]
    x0 = [len(K2_COLUMNS) * W_K2 + GAP_COL + k * (len(FRAMINGS) + GAP_COL) for k in range(len(CLASS_COLUMNS))]
    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))

    def cell(x, ph, word, w=1.0):
        if word is not None:
            ax.add_patch(Rectangle((x, y[ph] - 0.5), w, 1.0, facecolor=fills[word], edgecolor="black",
                                   linewidth=lw, hatch=regimes.HATCH[word]))

    for ph in y:
        cell(x_k2[0], ph, match(proc, ph), W_K2)
        cell(x_k2[1], ph, match(acid, ph), W_K2)
        for fr in FRAMINGS:
            verdicts = k1.get((ph, fr))
            if verdicts:
                for k, (cls, _c) in enumerate(CLASS_COLUMNS):
                    cell(x0[k] + FRAMINGS.index(fr), ph, verdicts[cls])
    ax.set_xlim(-0.2, x0[-1] + len(FRAMINGS) + 0.2)
    ax.set_ylim(min(y.values()) - 0.7, max(y.values()) + 0.7)
    ax.set_xticks([x + W_K2 / 2 for x in x_k2] + [x + len(FRAMINGS) / 2 for x in x0],
                  list(K2_COLUMNS) + class_labels(aux["cutoffs"]))
    ax.set_yticks(ticks, labels)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("K2 state, then K1 cutoff class (V vs Li$^{+}$/Li)")
    return fig
