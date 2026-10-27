"""The generated break-even table of the saturated-sink exclusions (cp6 F10): pinned input, every row, macros only."""
import csv
import json
import re
import shutil

import pytest

from nacre.preprint import breakeven_table as bt
from nacre.preprint import macros, paths
from preprint_helpers import REPO

GEN = paths.generated(REPO)


def _csv_rows():
    with (REPO / bt.INPUTS["breakeven"]).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _tex():
    return (GEN / bt.OUT_TEX).read_text(encoding="utf-8")


def _body_rows():
    tex = _tex()
    body = tex[tex.index("\\midrule"):tex.index("\\bottomrule")]
    return [l for l in body.splitlines() if l.endswith(" \\\\")]


def test_committed_outputs_are_a_fresh_generation():
    assert bt.check(REPO) == []


def test_the_input_is_the_recorded_file():
    assert bt.sha256(REPO / bt.INPUTS["breakeven"]) == bt.BREAKEVEN_SHA256
    recorded = json.loads((GEN / bt.OUT_JSON).read_text(encoding="utf-8"))["inputs"]
    assert recorded[bt.INPUTS["breakeven"]] == bt.BREAKEVEN_SHA256


def test_a_changed_input_is_refused(tmp_path):
    root = tmp_path / "r"
    for rel in bt.INPUTS.values():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    p = root / bt.INPUTS["breakeven"]
    p.write_text(p.read_text(encoding="utf-8").replace("3.73408", "3.73409"), encoding="utf-8")
    with pytest.raises(bt.BreakevenTableError, match="recorded"):
        bt.read_inputs(root)


def test_every_row_of_the_file_is_in_the_table_with_its_values():
    """An independent read of the CSV against the macros the table prints, row by row."""
    rows, lines = _csv_rows(), _body_rows()
    assert len(rows) == len(lines) == 26
    values = {name: spec for name, spec in macros.load_sources(REPO)["macros"].items() if spec.get("source") == bt.JSON_SOURCE}
    numbers = json.loads((GEN / bt.OUT_JSON).read_text(encoding="utf-8"))

    def value(name):
        node = numbers
        for part in values[name]["key"].split("/"):
            node = node[part]
        return node

    for r, line in zip(rows, lines):
        cells = [c.strip() for c in line[:-3].split("&")]
        assert len(cells) == 4, line
        cut, head = re.fullmatch(r"\\(Num\w+)\{\}", cells[1]).group(1), re.fullmatch(r"\\(Num\w+)\{\}", cells[2]).group(1)
        assert value(cut) == float(r["E_c"]) and value(head) == float(r["headroom_V"]), (r, line)
        if r["r_star"] == bt.NOT_EXCLUDED:
            assert cells[3] == bt.NOT_EXCLUDED and float(r["headroom_V"]) < 0
        else:
            ratio = re.fullmatch(r"\\(Num\w+)\{\}", cells[3]).group(1)
            assert value(ratio) == float(r["r_star"]), (r, line)


def test_the_one_negative_headroom_row_keeps_its_words():
    rows = [r for r in _csv_rows() if r["r_star"] == bt.NOT_EXCLUDED]
    assert [(r["phase"], r["E_c"]) for r in rows] == [("brushite", "4.4")]
    assert _tex().count(bt.NOT_EXCLUDED) == 1


def test_no_digit_in_the_table_outside_macros_and_formulas():
    body = re.sub(r"\\ce\{[^}]*\}|\\Num[A-Za-z]+\{\}|\\addlinespace\[[^]]*\]|\\setlength\{[^}]*\}\{[^}]*\}|\\begin\{tabular\}.*", "",
                  _tex().split("\n", 2)[2])
    assert not re.search(r"[0-9]", body), re.findall(r".{20}[0-9].{20}", body)[:3]


def test_results_and_si_set_the_table_and_state_the_reading():
    results = (paths.paper(REPO) / "sections" / "results.tex").read_text(encoding="utf-8")
    si = (paths.paper(REPO) / "si" / "main_si.tex").read_text(encoding="utf-8")
    assert "\\input{../generated/breakeven_table}" in (paths.paper(REPO) / "main.tex").read_text(encoding="utf-8")
    # PH-W8.13: the SI no longer repeats the table; it points to the main-text table and states the reading
    assert "\\label{tab:breakeven}" in results and "tab:si-breakeven" not in si
    assert results.count("\\nacreBreakevenTable") == 1 and "\\nacreBreakevenTable" not in si
    assert "break-even table of the main text" in si
    reading = "an exclusion stands while the mean-activity ratio of saturated to actual \\ce{LiClO4} stays below $r^*$"
    assert reading in results and reading in si
    # the sink mark is defined once, in the Results opening; the SI, which does not define it, spells the qualifier out
    assert "\\nacreSinkMark" not in si and "\\ce{LiClO4}-saturated sink (solid-salt reference state)" in si
