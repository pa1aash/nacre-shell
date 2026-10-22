"""PH-W6.3: the Al-salt ladder table input."""
import csv
import hashlib

from figs_helpers import REPO

from nacre.figs import alsalt, upstream


def test_every_al_salt_row_reads_undetermined_with_a_reason():
    rows = alsalt.rows(REPO)
    assert len(rows) == 6 and {r["k1_verdict"] for r in rows} == {"undetermined"}
    assert all(r["reason"] and r["sink"] == "Al(ClO4)3" and "Al(ClO4)3" in r["reaction"] for r in rows)
    assert {r["phase"] for r in rows} == {"AlPO4", "Al(PO3)3", "Al-polyphosphate (R1 gel)", "baked aluminophosphate (Tsinghua)"}


def test_the_committed_csv_is_the_generated_one():
    path = REPO / "figures/out/tables/al_salt_ladder.csv"
    assert path.read_text() == alsalt.render(REPO)
    rec = [r for r in csv.DictReader(path.open())]
    assert {r["source_sha256"] for r in rec} == {upstream.entry("ladder_v3", REPO)["sha256"]}
    assert hashlib.sha256(path.read_bytes()).hexdigest()
