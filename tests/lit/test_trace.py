import json

from lit_helpers import good_row
from nacre.lit import trace as T

DOI = "10.1021/example.123"


def setup(tmp_path, text):
    d = tmp_path / "lit" / "corpus" / "T-C"
    d.mkdir(parents=True)
    local = tmp_path / ".local" / "lit" / "T-C"
    local.mkdir(parents=True)
    (local / "a.txt").write_text(text)
    (d / "sources.jsonl").write_text(json.dumps({"doi": DOI, "local_path": ".local/lit/T-C/a.pdf"}) + "\n")


def statuses(tmp_path, rows):
    return {rid: st for rid, st, _ in T.audit(tmp_path, rows)}


def test_traced_with_unicode_minus(tmp_path):
    setup(tmp_path, "log Ksp = −8.48 at 25 °C")
    assert statuses(tmp_path, [good_row(value="-8.48")]) == {"TC-001": "traced"}


def test_not_a_substring_of_a_longer_number(tmp_path):
    setup(tmp_path, "value 18.481 here")
    assert statuses(tmp_path, [good_row(value="8.48")]) == {"TC-001": "untraced"}


def test_scientific_notation(tmp_path):
    setup(tmp_path, "Ksp = 4.0 × 10−7 M2")
    assert statuses(tmp_path, [good_row(value="4.0e-7")]) == {"TC-001": "traced"}


def test_range_and_comparator(tmp_path):
    setup(tmp_path, "pH rose from 11.2 to 12.4; above 9")
    rows = [good_row(row_id="TC-001", value="", range_or_uncertainty="11.2..12.4"),
            good_row(row_id="TC-002", value=">9")]
    assert statuses(tmp_path, rows) == {"TC-001": "traced", "TC-002": "traced"}


def test_derived_and_qualitative_and_missing(tmp_path):
    setup(tmp_path, "density 1.62 g cm-3")
    rows = [good_row(row_id="TC-001", value="61.8", grade="C", notes="derived from density 1.62 and M=100.09"),
            good_row(row_id="TC-002", unit="qualitative", value="calcite formed"),
            good_row(row_id="TC-003", value="99.9"),
            good_row(row_id="TC-004", doi="10.1000/none", value="1")]
    assert statuses(tmp_path, rows) == {"TC-001": "derived", "TC-002": "qualitative", "TC-003": "untraced",
                                        "TC-004": "untraced"}
