"""Per-pH K2 states of the candidates: verdict word, passing fraction and minimum passing dose.

Shared by the stability map (fig17) and the candidate-by-regime heatmap (fig15). Three kinds of
committed output meet here:

  perph.csv (k2_perph_ph2)    passing cells and the minimum passing Ca_T and P_T per phase and pH;
  the cells of the runs       the verdict of every cell, which tells an excluded pH (every cell
                              falsified) from an open one (some inconclusive) where no cell passes:
                              the carbonates in k2_grid_ph, the phosphates in k2_acid_ph2 and
                              k2_alkaline_ph2 (the post-freeze keys and the control rule of PH-W4.5);
  the pass counts of both     must agree cell for cell, or the module refuses.

The alkaline cells name their pH by position in the registered range (pH@min, pH@value, pH@max);
the numbers come from the sorted pH column of perph.csv for that grid.
"""
from collections import namedtuple

from nacre.figs import regimes

DOSE_HIGH = 0.01  # mol dm^-3: a minimum passing dose at or above this is a high dose
CARBONATES = ("calcite", "aragonite", "ACC")
# Cell keys of the phosphate runs -> ladder phase. The original-key OCP row fails its control and is
# superseded by the Ca4H-basis key (PH-W4.5), so the OCP row reads the Ca4H block.
RUN_PHASE = {"hap": "HAp", "acp": "ACP", "btcp": "b-TCP", "ocp_ca4h": "OCP", "brushite": "brushite",
             "atcp": "a-TCP", "li3po4": "Li3PO4"}
PERPH_PHASE = {"OCP (Ca4H key)": "OCP"}
PERPH_SKIP = ("OCP (original key)",)
PHOSPHATES = tuple(RUN_PHASE.values())
STATES = ("acid", "alkaline")
ALKALINE_AT = ("pH@min", "pH@value", "pH@max")

State = namedtuple("State", "word n_cells n_pass fraction min_ca min_p high")


def _num(text):
    return float(text) if text not in ("", None) else None


def perph(doc):
    """{(state, phase): {pH: row}} of the per-pH table; the rerun rows replace the frozen ones."""
    out, source = {}, {}
    for r in doc["rows"]:
        name = r["phase"]
        if name in PERPH_SKIP:
            continue
        phase = PERPH_PHASE.get(name, name)
        key = (r["grid"] if r["grid"] == "alkaline" else "acid", phase)
        # a rerun row of a phase wins over the frozen row of the same phase and grid
        if key in source and source[key] == "rerun" and r["source"] == "frozen":
            continue
        if key in source and source[key] == "frozen" and r["source"] == "rerun":
            out[key] = {}
        source[key] = r["source"]
        out.setdefault(key, {})[float(r["pH"])] = r
    return out


def dose(min_ca, min_p):
    """The dose of a passing cell set: the larger of the two minima (Ca_T alone for a carbonate)."""
    vals = [v for v in (min_ca, min_p) if v is not None]
    return max(vals) if vals else None


def _ph_of(axes, alkaline_ph):
    token = axes["pH"]
    if token in ALKALINE_AT:
        return alkaline_ph[ALKALINE_AT.index(token)]
    return float(token.split()[0])


def _words(cells, alkaline_ph):
    """{pH: [verdicts]} of a block's cells."""
    per = {}
    for c in cells.values():
        per.setdefault(_ph_of(c["axes"], alkaline_ph), []).append(c["verdict"])
    return per


def states(perph_doc, grid_doc, acid_doc, alkaline_doc):
    """{phase: {"acid": {pH: State}, "alkaline": {pH: State}}} for the carbonates and phosphates.

    Refuses a table whose pass counts differ from the cell verdicts, or a phase without cells.
    """
    table = perph(perph_doc)
    alk_ph = {p: sorted(ph for (s, q), v in table.items() if s == "alkaline" and q == p for ph in v)
              for p in {q for (_s, q) in table}}
    blocks = {}  # (state, phase) -> (cells, controls_pass)
    k2 = grid_doc["extensions"]["p0-w4"]["k2_grid"]
    for name in CARBONATES:
        blocks[("alkaline", name)] = (k2["carbonate"]["polymorphs"][name]["cells"], True)
        blocks[("acid", name)] = (k2["acid_adjusted"]["carbonate"][name]["cells"], True)
    for state, doc in (("acid", acid_doc), ("alkaline", alkaline_doc)):
        ph2 = doc["extensions"]["p0-w4"]["k2_ph2"]["states"][state]["phases"]
        for key, phase in RUN_PHASE.items():
            blocks[(state, phase)] = (ph2[key]["cells"], bool(ph2[key].get("controls_pass", True)))
    out = {}
    for (state, phase), (cells, controls) in sorted(blocks.items()):
        rows = table.get((state, phase))
        if not rows:
            raise ValueError("k2ph: no per-pH rows for %s %s" % (state, phase))
        alk = alk_ph[phase] if state == "alkaline" else None
        if state == "alkaline" and len(alk) != len(ALKALINE_AT):
            raise ValueError("k2ph: %s has %d alkaline pH values, expected %d" % (phase, len(alk), len(ALKALINE_AT)))
        per = _words(cells, alk)
        if sorted(per) != sorted(rows):
            raise ValueError("k2ph: %s %s pH values %s differ from the table %s" % (state, phase, sorted(per), sorted(rows)))
        for ph, verdicts in per.items():
            r = rows[ph]
            n_pass = sum(v == "feasible" for v in verdicts)
            if n_pass != int(r["n_passing"]) or len(verdicts) != int(r["n_cells"]):
                raise ValueError("k2ph: %s %s pH %g: %d of %d cells pass in the run, %s of %s in the table"
                                 % (state, phase, ph, n_pass, len(verdicts), r["n_passing"], r["n_cells"]))
            word = regimes.aggregate(verdicts)
            if not controls:
                word = regimes.FROM_VERDICT["inconclusive"]
            ca, p = _num(r["min_passing_Ca_T_mol_dm3"]), _num(r["min_passing_P_T_mol_dm3"])
            d = dose(ca, p)
            out.setdefault(phase, {}).setdefault(state, {})[ph] = State(
                word, len(verdicts), n_pass, n_pass / len(verdicts), ca, p, d is not None and d >= DOSE_HIGH)
    return out


def processing(by_ph):
    """The as-prepared (alkaline) slurry state of a phase: any passing pH passes, at its lowest dose."""
    word = regimes.aggregate(_verdict_of(s.word) for s in by_ph.values())
    passing = [s for s in by_ph.values() if s.n_pass]
    doses = [dose(s.min_ca, s.min_p) for s in passing]
    d = min(doses) if doses else None
    n, k = sum(s.n_cells for s in by_ph.values()), sum(s.n_pass for s in by_ph.values())
    return State(word, n, k, k / n, None, None, d is not None and d >= DOSE_HIGH)


def _verdict_of(word):
    return {w: v for v, w in regimes.FROM_VERDICT.items()}[word]
