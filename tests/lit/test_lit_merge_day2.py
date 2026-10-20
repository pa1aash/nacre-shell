"""Day 2 merge rules: the D1 dedupe key, the Day 2 threads and the ledger record."""
import json
import subprocess

from lit_helpers import good_row
from nacre.lit import evidence as E
from nacre.lit import merge as M


def test_d1_key_ignores_range_and_unit():
    a = good_row(row_id="TC-001")
    b = good_row(row_id="TF-001", thread="T-F", range_or_uncertainty="±0.05")
    kept, dups = E.merge([[a], [b]])
    assert [r["row_id"] for r in kept] == ["TC-001"] and dups == [("TF-001", "TC-001")]


def test_d1_key_keeps_distinct_values_and_symbols():
    a = good_row(row_id="TC-001")
    b = good_row(row_id="TC-002", value="-8.30")
    c = good_row(row_id="TC-003", symbol="pKsp")
    kept, dups = E.merge([[a, b, c]])
    assert len(kept) == 3 and dups == []


def test_day2_threads_validate():
    for t in ("T-F", "T-G", "T-H", "T-I", "T-J"):
        rid = t.replace("-", "") + "-001"
        assert E.validate_row(good_row(row_id=rid, thread=t)) == []
    assert E.validate_row(good_row(row_id="TU-001", thread="T-U"))


def test_day3_threads_validate():
    for t in ("T-K", "T-L", "T-M"):
        rid = t.replace("-", "") + "-001"
        assert E.validate_row(good_row(row_id=rid, thread=t)) == []
    assert E.validate_row(good_row(row_id="TK-001", thread="T-L"))


def test_day4_threads_validate():
    for t in ("T-N", "T-O", "T-P", "T-Q"):
        rid = t.replace("-", "") + "-001"
        assert E.validate_row(good_row(row_id=rid, thread=t)) == []
    assert E.validate_row(good_row(row_id="TU-001", thread="T-U"))


def test_merge_skips_unstarted_threads_and_writes_ledger(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                    "commit", "-q", "--allow-empty", "-m", "init"], cwd=tmp_path, check=True)
    d = tmp_path / "lit" / "corpus" / "T-C"
    d.mkdir(parents=True)
    E.write_csv(d / "rows.csv", [good_row()])
    (d / "gaps.md").write_text("# T-C gaps\n\n- none\n")
    assert M.run(tmp_path, session="P0-TEST") == 0
    rec = json.loads((tmp_path / "jobs" / "ledger" / "p0-w1.jsonl").read_text().splitlines()[-1])
    assert rec["session"] == "P0-TEST" and rec["job"] == "lit-merge"
    assert {o["path"] for o in rec["outputs"]} == {"lit/evidence_table.csv", "lit/corpus/coverage.yaml",
                                                    "lit/corpus/gaps.md"}
    assert [i["path"] for i in rec["inputs"]] == ["lit/corpus/T-C/rows.csv"]
    assert "### T-F" not in (tmp_path / "lit" / "corpus" / "gaps.md").read_text()


def test_d1_key_uses_the_range_of_range_only_rows():
    a = good_row(row_id="TH-008", thread="T-H", value="", range_or_uncertainty="111..142")
    b = good_row(row_id="TH-009", thread="T-H", value="", range_or_uncertainty="120..147")
    kept, dups = E.merge([[a, b]])
    assert len(kept) == 2 and dups == []
