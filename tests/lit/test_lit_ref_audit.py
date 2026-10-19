"""Reference audit of the preprint bibliography (nacre.lit.ref_audit), offline."""
import csv
from pathlib import Path

import pytest
import yaml

from lit_helpers import good_row
from nacre.lit import evidence as E
from nacre.lit import ref_audit as A

BIB = """@article{alpha2020one, title={One title}, DOI={10.1000/one}, journal={J}, author={A, B}, year={2020} }

@article{beta2021two, title={Two title}, DOI={10.1000/two}, journal={J}, author={C, D}, year={2021} }

@book{gamma1995, url={http://dx.doi.org/10.1000/three}, DOI={10.1000/three}, institution={Survey}, year={1995} }

@article{delta2022dup, title={One title}, DOI={10.1000/one}, journal={J}, author={A, B}, year={2022} }
"""
SECTIONS = {
    "preprint/paper/sections/intro.tex":
        "First claim\\cite{alpha2020one,beta2021two}. Second claim\\cite{ghost2000}.\n% \\cite{gamma1995}\n",
    "preprint/paper/sections/methods.tex": "Data from a table\\cite{alpha2020one}.\n",
}
SI = "No citations here.\n"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "lit" / "corpus" / "audit").mkdir(parents=True)
    rows = [good_row(row_id="TA-001", thread="T-A", doi="10.1000/one", grade="B"),
            good_row(row_id="TA-002", thread="T-A", doi="10.1000/two", grade="C")]
    with (tmp_path / "lit" / "evidence_table.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=E.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    files = {A.BIB: BIB, A.SI: SI, **SECTIONS}
    monkeypatch.setattr(A, "git_show", lambda root, ref, path: files[path])
    monkeypatch.setattr(A, "git_ls", lambda root, ref, path: sorted(SECTIONS))
    return tmp_path


def _claims(root, data):
    (root / A.CLAIMS).write_text(yaml.safe_dump(data), encoding="utf-8")


def test_rows_per_key_support_and_problems(repo):
    _claims(repo, {"alpha2020one": {"claim": "c", "use": "data source", "rows": ["TA-001"]},
                   "beta2021two": {"claim": "c", "use": "paraphrase", "rows": []}})
    rows, missing = A.build(repo, offline=True)
    by = {r["key"]: r for r in rows}
    assert missing == ["ghost2000"]
    assert by["alpha2020one"]["supported"] == "y" and by["alpha2020one"]["best_grade"] == "B"
    assert by["alpha2020one"]["cited_in"] == "intro.tex:1; methods.tex:1"
    assert "duplicate DOI with delta2022dup" in by["alpha2020one"]["problems"]
    assert "duplicate title" in by["alpha2020one"]["problems"]
    assert by["beta2021two"]["supported"] == "n"
    assert "citation without supporting evidence row" in by["beta2021two"]["problems"]
    assert "not cited" in by["gamma1995"]["problems"]  # a commented-out \cite does not count
    assert "missing metadata: title" in by["gamma1995"]["problems"]
    assert by["ghost2000"]["problems"] == "cited but not in refs.bib"


def test_unknown_rows_and_wrong_doi_are_refused(repo):
    _claims(repo, {"alpha2020one": {"use": "paraphrase", "rows": ["TA-002"]}})
    with pytest.raises(SystemExit, match="carries 10.1000/two"):
        A.build(repo, offline=True)
    _claims(repo, {"alpha2020one": {"use": "summary", "rows": ["TA-404"]}})
    with pytest.raises(SystemExit, match="does not exist"):
        A.build(repo, offline=True)


def test_resolution_falls_back_to_datacite_and_reads_update_notices(repo):
    class Res:
        def __init__(self, body):
            self.body = body

        def json(self):
            return self.body

    class Http:
        def get(self, source, url, params=None):
            if url.startswith(A.DATACITE):
                return Res({"data": {"attributes": {"titles": [{"title": "Two title"}]}}})
            if params:
                return Res({"message": {"items": [{"DOI": "10.1000/notice",
                                                   "update-to": [{"DOI": "10.1000/one", "type": "retraction"}]}]}})
            if url.endswith("10.1000/two"):
                raise RuntimeError("404")
            return Res({"message": {"title": ["One title"]}})

    _claims(repo, {})
    rows, _ = A.build(repo, http=Http())
    by = {r["key"]: r for r in rows}
    assert (by["beta2021two"]["resolves"], by["beta2021two"]["resolved_by"]) == ("y", "datacite")
    assert by["alpha2020one"]["title_match"] == "y"
    assert by["alpha2020one"]["retraction_check"] == "retraction by 10.1000/notice"
    assert "update notice: retraction" in by["alpha2020one"]["problems"]


def test_committed_audit_covers_every_bib_key():
    root = Path(__file__).resolve().parents[2]
    path = root / A.OUT
    if not path.exists():
        pytest.skip("audit not generated")
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows and list(rows[0]) == A.COLUMNS
    assert all(r["use"] in A.USES + ("",) for r in rows)
    cited_unsupported = [r for r in rows if r["cited"] == "y" and r["supported"] == "n"]
    assert all("without supporting evidence row" in r["problems"] or "not in refs.bib" in r["problems"]
               for r in cited_unsupported)
