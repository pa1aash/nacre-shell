"""Generated title, author block, CRediT statement and declarations."""
import pytest
import yaml

from nacre.preprint import declarations, paths
from preprint_helpers import REPO, copy_tree


def test_committed_generated_files_are_up_to_date():
    for name, fn in declarations.GENERATED.items():
        assert (paths.generated(REPO) / name).read_text(encoding="utf-8") == fn(REPO), name


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
    assert r"\nacrePlaceholder{CRediT roles TBD}" in declarations.credit_statement(root)


def test_credit_roles_come_from_the_taxonomy(tmp_path):
    root = copy_tree(tmp_path)
    _authors(root, [_a(corresponding=True, credit_roles=["Conceptualization", "Software"])])
    assert r"\textbf{Ada Byron}: Conceptualization, Software." in declarations.credit_statement(root)
    _authors(root, [_a(corresponding=True, credit_roles=["Vibes"])])
    with pytest.raises(declarations.DeclarationsError, match="not in the taxonomy"):
        declarations.credit_statement(root)


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
