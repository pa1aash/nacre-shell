"""Generated title, author block and declarations (no CRediT statement: ChemRxiv does not require one)."""
import pytest
import yaml

from nacre.preprint import declarations, paths
from preprint_helpers import REPO, copy_tree


def _authors(root, authors):
    paths.authors_yaml(root).write_text(yaml.safe_dump({"authors": authors}), encoding="utf-8")


def _a(**kw):
    base = {"given_name": "Ada", "family_name": "Byron", "email": "a@b.c", "affiliation": "Inst A",
            "corresponding": False, "credit_roles": "TBD", "status": "given"}
    base.update(kw)
    return base


def test_tbd_and_to_confirm_become_markers(tmp_path):
    root = copy_tree(tmp_path)
    _authors(root, [_a(corresponding=True),
                    _a(given_name="Bo", family_name="Chen", family_name_status="to-confirm", affiliation="TBD"),
                    _a(given_name="Cy", status="YOU-confirm", affiliation="Inst A")])
    block = declarations.author_block(root)
    assert r"\nacrePending{Chen}" in block
    assert r"\nacrePlaceholder{affiliation TBD}" in block
    assert r"\nacrePending{Cy Byron}" in block
    assert block.count(r"\footnotetext{\textit{$^{a}$~Inst A}}") == 1
    assert r"$^{\ast}$\textit{$^{a}$}" in block


def test_no_credit_statement_is_generated(tmp_path):
    assert not hasattr(declarations, "credit_statement")
    assert "credit.tex" not in declarations.GENERATED
    root = copy_tree(tmp_path)
    assert not (paths.generated(root) / "credit.tex").exists()
    text = (paths.paper(root) / "sections" / "declarations.tex").read_text(encoding="utf-8")
    assert "nacreCredit" not in text and "Author contributions" not in text


def test_exactly_one_corresponding_author(tmp_path):
    root = copy_tree(tmp_path)
    _authors(root, [_a(), _a(given_name="Bo")])
    with pytest.raises(declarations.DeclarationsError, match="corresponding"):
        declarations.author_block(root)


def test_declaration_values(tmp_path):
    root = copy_tree(tmp_path)
    paths.declarations_yaml(root).write_text(yaml.safe_dump({
        "repository_url": "https://example.org/repo", "zenodo_doi": "10.5281/zenodo.1",
        "competing_interests": "There are no conflicts to declare.", "funding": "TBD"}), encoding="utf-8")
    text = declarations.declarations(root)
    assert r"\newcommand{\nacreRepoURL}{\url{https://example.org/repo}}" in text
    assert r"\href{https://doi.org/10.5281/zenodo.1}" in text
    assert r"\newcommand{\nacreCompetingInterests}{There are no conflicts to declare.}" in text
    assert r"\newcommand{\nacreFunding}{\nacrePlaceholder{" in text
    assert r"\newcommand{\nacreSIDOI}{\nacrePlaceholder{" in text


def test_title_comes_from_the_track_ledger():
    meta = yaml.safe_load(paths.track_yaml(REPO).read_text(encoding="utf-8"))["meta"]
    assert " ".join(meta["title_working"].split()) in declarations.front_matter(REPO)


# --- build-time generation: determinism and content-keyed provenance ----------------------------

def _generate_all(root):
    return {n: fn(root) for n, fn in declarations.GENERATED.items()}


def _fixture(tmp_path):
    root = copy_tree(tmp_path)
    paths.authors_yaml(root).write_text(yaml.safe_dump({
        "authors": [_a(corresponding=True, status="given"), _a(given_name="Bo", family_name="Chen", status="given")],
        "notes": "unconsumed", }), encoding="utf-8")
    return root


def test_generation_is_byte_deterministic(tmp_path):
    root = _fixture(tmp_path)
    first = _generate_all(root)
    assert _generate_all(root) == first
    (tmp_path / "second").mkdir()
    other = _fixture(tmp_path / "second")
    assert _generate_all(other) == first


def _edit(path, fn):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_unconsumed_ledger_changes_leave_the_output_alone(tmp_path):
    root = _fixture(tmp_path)
    before = _generate_all(root)
    _edit(paths.track_yaml(root), lambda d: d.update(sessions={"X1": {"status": "DONE"}}, day=99))
    _edit(paths.track_yaml(root), lambda d: d["meta"].update(unrelated_note="changed"))
    _edit(paths.authors_yaml(root), lambda d: d.update(notes="changed", ruling="a new ruling"))
    _edit(paths.authors_yaml(root), lambda d: d["authors"][0].update(internal_comment="x"))
    assert _generate_all(root) == before


def test_consumed_field_changes_alter_the_output(tmp_path):
    root = _fixture(tmp_path)
    before = _generate_all(root)
    _edit(paths.track_yaml(root), lambda d: d["meta"].update(title_working="A different title"))
    after = _generate_all(root)
    assert after["front.tex"] != before["front.tex"]
    assert {n for n in after if after[n] != before[n]} == {"front.tex"}
    _edit(paths.authors_yaml(root), lambda d: d["authors"][1].update(family_name="Chan"))
    after2 = _generate_all(root)
    assert after2["authors.tex"] != after["authors.tex"]
    assert after2["front.tex"] == after["front.tex"]
    _edit(paths.authors_yaml(root), lambda d: d["authors"][1].update(credit_roles=["Conceptualization"]))
    assert _generate_all(root) == after2             # a CRediT field is not read


def test_headers_name_fields_and_carry_no_file_blob(tmp_path):
    root = _fixture(tmp_path)
    for name, text in _generate_all(root).items():
        head = text.splitlines()[:2]
        assert "blob" not in "\n".join(head), name
        assert "Consumed fields:" in head[1] and "digest" in head[1], name
