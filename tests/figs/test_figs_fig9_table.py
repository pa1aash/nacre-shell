"""PH-W6.7: every drawn fig9 cell class equals regime_table.csv; undetermined is the palette grey."""
import csv
import re

from figs_helpers import REPO

from nacre.figs import build, paths, regimes, upstream

TABLE = REPO / "preprint/generated/regime_table.csv"
PHASE = {  # independent of the template: regime-table row id -> ladder phase
    "hap": "HAp", "acp": "ACP", "btcp": "b-TCP", "atcp": "a-TCP", "ocp": "OCP", "brushite": "brushite",
    "li_ortho": "Li3PO4", "ca_pyro": "Ca2P2O7", "ca_meta_crystal": "Ca(PO3)2 / Ca-polyphosphate glass",
    "ca_meta_glass": "Ca(PO3)2 / Ca-polyphosphate glass", "al_ortho": "AlPO4", "al_meta": "Al(PO3)3",
    "al_polyp": "Al-polyphosphate (R1 gel)", "lipo3n": "(LiPO3)n Hydro-Quebec film",
    "baked": "baked aluminophosphate (Tsinghua)", "carbonate_ctl": "CaCO3"}


def _mod():
    return build.load_template(paths(REPO)["src"] / "fig9.py")


def _fig9(table=None):
    mod = _mod()
    data, _p = build.load_input(REPO, mod, False)
    aux = build.load_aux(REPO, mod, False)
    if table is not None:
        aux = dict(aux, regime_table=(table, "test"))
    return build.make_figure(REPO, mod, data, aux)[1]


def _drawn(fig):
    by_look = {}
    for w, c in regimes.fills(REPO).items():
        by_look[(tuple(c), regimes.hatch(w))] = w
    return {p.cell_id: by_look[(tuple(round(float(x), 4) for x in p.get_facecolor()[:3]), p.get_hatch())]
            for p in fig.axes[0].patches if getattr(p, "cell_id", None)}


def _table_cells():
    out = {}
    for r in csv.DictReader(TABLE.open()):
        if r["column"] not in ("C_lo", "C_mid", "C_hi") or not r["words"] or r["row_id"] not in PHASE:
            continue
        words = [w.strip() for w in r["words"].split(";")]
        framings = ["crystalline", "amorphous"] if len(words) == 2 else [re.search(r"framing (\w+)", r["note"]).group(1)]
        for fr, w in zip(framings, words):
            out[(PHASE[r["row_id"]], fr, r["column"])] = w
    return out


def _disagreements(fig):
    drawn = _drawn(fig)
    return [(k, w, drawn.get(k)) for k, w in sorted(_table_cells().items()) if drawn.get(k) != w]


def test_every_fig9_cell_class_equals_the_regime_table():
    fig = _fig9()
    assert len(_table_cells()) == 60 and not _disagreements(fig)
    assert len(_drawn(fig)) == 108  # 18 phases x 2 framings x 3 classes


def test_the_comparison_fails_when_one_cell_disagrees():
    table = upstream.load("regime_table", REPO)
    bad = {"columns": table["columns"], "rows": [dict(r) for r in table["rows"]]}
    row = next(r for r in bad["rows"] if r["row_id"] == "hap" and r["column"] == "C_hi")
    row["words"] = "excluded; undetermined"
    assert _disagreements(_fig9(bad)) == [(("HAp", "amorphous", "C_hi"), "excluded", "undetermined")]


def test_fig9_draws_undetermined_in_the_palette_grey():
    fills = _mod().verdict_fills(REPO)
    r, g, b = fills["undetermined"]
    assert r == g == b
    assert {v for v in _drawn(_fig9()).values()} <= set(regimes.ORDER)
