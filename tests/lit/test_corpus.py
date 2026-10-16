"""Checks on the committed corpus: the evidence table validates and no file carries forbidden wording."""
from pathlib import Path

import pytest

from nacre.lit import evidence as E

REPO = Path(__file__).resolve().parents[2]
TABLE = REPO / "lit" / "evidence_table.csv"


@pytest.mark.skipif(not TABLE.exists(), reason="no evidence table yet")
def test_evidence_table_validates():
    assert E.validate_file(TABLE, REPO) == []


@pytest.mark.skipif(not TABLE.exists(), reason="no evidence table yet")
def test_every_row_has_doi_and_locator():
    _, rows = E.read_csv(TABLE)
    assert rows and all(r["doi"].strip() and r["locator"].strip() for r in rows)


def test_corpus_files_free_of_scope_patterns():
    pats = E.scope_patterns(REPO)
    hits = []
    for f in sorted((REPO / "lit").rglob("*")):
        if f.is_file() and f.suffix in (".md", ".csv", ".jsonl", ".yaml") and "cache" not in f.parts:
            text = f.read_text(encoding="utf-8")
            hits += ["%s %s" % (f.relative_to(REPO), pid) for pid, rx in pats if rx.search(text)]
    assert hits == []


def test_no_full_text_in_lit():
    assert not [p for p in (REPO / "lit").rglob("*") if p.suffix.lower() in (".pdf", ".txt", ".xml")]
