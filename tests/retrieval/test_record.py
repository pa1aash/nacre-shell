import pytest

from nacre.retrieval import record as R


@pytest.mark.parametrize("raw,want", [
    ("10.1000/ABC.123", "10.1000/abc.123"),
    ("https://doi.org/10.1000/ABC.123", "10.1000/abc.123"),
    ("http://dx.doi.org/10.1000/abc", "10.1000/abc"),
    ("doi:10.1000/abc", "10.1000/abc"),
    ("  DOI: 10.1000/abc.  ", "10.1000/abc"),
    ("not a doi", None), ("", None), (None, None),
])
def test_normalize_doi(raw, want):
    assert R.normalize_doi(raw) == want


@pytest.mark.parametrize("raw,want", [
    ("2101.00001v3", "2101.00001"), ("arXiv:2101.00001", "2101.00001"),
    ("https://arxiv.org/abs/2101.00001v2", "2101.00001"),
    ("https://arxiv.org/pdf/2101.00001.pdf", "2101.00001"),
    ("cond-mat/0101001v1", "cond-mat/0101001"), ("hello", None), (None, None),
])
def test_normalize_arxiv(raw, want):
    assert R.normalize_arxiv(raw) == want


def test_normalize_title_strips_case_accents_punctuation():
    assert R.normalize_title("  Mussel-inspired  Adhésion: A Study! ") == "mussel inspired adhesion a study"


def test_split_name():
    assert R.split_name("Ada Marie Lovelace") == ("Lovelace", "Ada Marie")
    assert R.split_name("Lovelace, Ada") == ("Lovelace", "Ada")
    assert R.split_name("Plato") == ("Plato", "")


def test_make_record_rejects_unknown_fields_and_normalises():
    rec = R.make_record("x", 1, "t", "k", doi="https://doi.org/10.1001/AB", year="2020",
                        urls=["b", "a", None, "a"])
    assert rec["doi"] == "10.1001/ab" and rec["year"] == 2020 and rec["urls"] == ["a", "b"]
    assert set(rec) == set(R.FIELDS)
    with pytest.raises(KeyError):
        R.make_record("x", 1, "t", "k", abstract="no")
