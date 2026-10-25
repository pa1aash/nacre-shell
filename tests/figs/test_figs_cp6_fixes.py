"""PH-W6.6: fig15 cell classes equal the regime table, the undetermined fill, fig17 panel b, fig14 labels."""
import copy
import csv
import re

import pytest
from figs_helpers import REPO

from nacre.figs import build, colours, paths, regimes, style, upstream

TABLE = REPO / "preprint/generated/regime_table.csv"


def _mod(fid):
    return build.load_template(paths(REPO)["src"] / (fid + ".py"))


def _fig15(table=None):
    """The real fig15 figure, optionally with a substituted regime table."""
    mod = _mod("fig15")
    data, _p = build.load_input(REPO, mod, False)
    aux = build.load_aux(REPO, mod, False)
    if table is not None:
        aux = dict(aux, regime_table=(table, "test"))
    return mod, build.make_figure(REPO, mod, data, aux)[1]


def _drawn(fig):
    """{(row label, framing, class): registered word} read from the rectangles of the K1 cells."""
    fills, by_look = regimes.fills(REPO), {}
    for w, c in fills.items():
        for high in (False, True):
            if high and w != regimes.REGISTERED[0]:
                continue
            by_look[(tuple(c), regimes.hatch(w, high))] = w
    out = {}
    for p in fig.axes[0].patches:
        cid = getattr(p, "cell_id", None)
        if cid is not None and cid[2] is not None:
            look = (tuple(round(float(x), 4) for x in p.get_facecolor()[:3]), p.get_hatch())
            out[cid] = by_look[look]
    return out


def _table_cells():
    """{(ladder phase, framing, class): word} straight from regime_table.csv (the oracle of the test)."""
    mod = _mod("fig15")
    out = {}
    for r in csv.DictReader(TABLE.open()):
        if r["column"] not in ("C_lo", "C_mid", "C_hi") or not r["words"] or r["row_id"] not in mod.TABLE_K1_PHASE:
            continue
        words = [w.strip() for w in r["words"].split(";")]
        framings = ["crystalline", "amorphous"] if len(words) == 2 else [re.search(r"framing (\w+)", r["note"]).group(1)]
        phase = mod.TABLE_K1_PHASE[r["row_id"]]
        phase = mod.K1_ON if phase == "CaCO3" else phase
        for fr, w in zip(framings, words):
            out[(phase, fr, r["column"])] = w
    return out


def _disagreements(fig):
    drawn = _drawn(fig)
    return [(k, w, drawn.get(k)) for k, w in sorted(_table_cells().items()) if drawn.get(k) != w]


def test_every_fig15_cell_class_equals_the_regime_table():
    _mod15, fig = _fig15()
    cells = _table_cells()
    assert len(cells) == 60 and not _disagreements(fig)


def test_the_amorphous_cells_the_i17a_bound_excludes_are_drawn_excluded():
    _mod15, fig = _fig15()
    drawn = _drawn(fig)
    for phase in ("ACP", "HAp", "b-TCP", "a-TCP"):
        for cls in ("C_mid", "C_hi"):
            assert drawn[(phase, "amorphous", cls)] == "excluded"


def test_the_comparison_fails_when_one_cell_disagrees():
    table = upstream.load("regime_table", REPO)
    bad = {"columns": table["columns"], "rows": [dict(r) for r in table["rows"]]}
    row = next(r for r in bad["rows"] if r["row_id"] == "hap" and r["column"] == "C_hi")
    row["words"] = "excluded; undetermined"
    _mod15, fig = _fig15(bad)
    assert _disagreements(fig) == [(("HAp", "amorphous", "C_hi"), "excluded", "undetermined")]


def test_every_table_cell_is_drawn_and_the_ladder_fills_only_what_the_table_omits():
    mod = _mod("fig15")
    data, _p = build.load_input(REPO, mod, False)
    table = upstream.load("regime_table", REPO)
    cells, _g = mod.k1_cells(data, table)
    ladder, _g = mod.ladder_rows(data)
    stated = mod.table_k1(table)
    for key, by_class in cells.items():
        for cls, w in by_class.items():
            if w is not None and cls not in stated.get(key, {}):
                assert w == ladder[key][cls]


def test_a_table_row_the_ladder_lacks_is_refused():
    mod = _mod("fig15")
    data, _p = build.load_input(REPO, mod, False)
    table = upstream.load("regime_table", REPO)
    bad = {"columns": table["columns"], "rows": [dict(r, row_id="hap") for r in table["rows"][:0]]}
    bad["rows"] = [dict(r) for r in table["rows"]]
    mod.TABLE_K1_PHASE["zz"] = "no such phase"
    try:
        bad["rows"].append(dict(bad["rows"][0], row_id="zz", column="C_lo", words="open", note="framing crystalline"))
        with pytest.raises(ValueError, match="ladder does not"):
            mod.k1_cells(data, bad)
    finally:
        del mod.TABLE_K1_PHASE["zz"]


def test_undetermined_is_neutral_grey_and_all_regime_fills_stay_distinct():
    fills = regimes.fills(REPO)
    r, g, b = fills["undetermined"]
    assert r == g == b
    assert colours.min_delta_e(list(fills.values())) >= float(style.palette(REPO)["delta_e_min"])
    assert fills["suitable against dissolution"] != fills["undetermined"]


def test_fig17_panel_b_draws_open_ended_hatched_bars():
    mod = _mod("fig17")
    data, _p = build.load_input(REPO, mod, False)
    fig = build.make_figure(REPO, mod, data, build.load_aux(REPO, mod, False))[1]
    ax_b = fig.axes[1]
    bars = [p for p in ax_b.patches if p.get_hatch()]
    assert len(bars) == 8
    assert {p.get_hatch() for p in bars} == {mod.HATCH_COMPLETE, mod.HATCH_PARTIAL}
    assert sum(p.get_hatch() == mod.HATCH_PARTIAL for p in bars) == 4  # two silicates, AlPO4, baked baseline
    assert all(p.get_facecolor()[3] == 0.0 for p in bars)  # no solid fill from the floor
    assert not fig.texts and not ax_b.texts


def test_fig14_labels_are_typeset_and_the_k1_rows_collapse():
    mod = _mod("fig14")
    data = upstream.load("precision_map_ph", REPO)
    ids = [r["id"] for r in data["rows"]]
    rows, n = mod.collapse_k1(mod.rows_of(data))
    assert n == 10 and [r["id"] for r in rows].count(mod.K1_ROW) == 1 and len(rows) == len(ids) - 9
    for r in rows:
        lab = mod.label(r["id"])
        text = re.sub(r"\$.*?\$", "", lab)  # outside the math: words only, never a slug
        assert "_" not in text and not re.search(r"\b(ksp|wet|po3|hyd|min)\b", text)
    assert mod.label("t_wet") == r"$t_{\mathrm{wet}}$"
    with pytest.raises(ValueError, match="no typeset label"):
        mod.label("k1_made_up")


def test_fig14_refuses_to_collapse_k1_rows_that_differ():
    mod = _mod("fig14")
    rows = copy.deepcopy(mod.rows_of(upstream.load("precision_map_ph", REPO)))
    next(r for r in rows if r["id"].startswith("k1_"))["column"] = 0
    with pytest.raises(ValueError, match="cannot be collapsed"):
        mod.collapse_k1(rows)
