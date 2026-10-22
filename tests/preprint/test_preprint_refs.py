"""nacre.preprint.refs: citation keys, the build copy of refs.bib and the release check on pages."""
import pytest

from nacre.preprint import build, paths, refs
from nacre.report import bib as bibmod
from preprint_helpers import REPO, copy_tree, write

ENTRY_NO_PAGES = ("@article{doe2024thing, title={A Thing}, volume={15}, DOI={10.1000/x1}, "
                  "journal={Crystal Growth &amp; Design}, author={Doe, Jane}, year={2024} }\n")
ENTRY_PAGES = ("@article{roe2020other, title={Other}, volume={5}, DOI={10.1000/x2}, journal={J}, "
               "author={Roe, Richard}, year={2020}, pages={1--2} }\n")


def _tree(tmp_path, bib, intro):
    root = copy_tree(tmp_path)
    write(refs.source(root), bib)
    for section in (paths.paper(root) / "sections").glob("*.tex"):   # only the given text cites
        write(section, "\\section{%s}\n" % section.stem)
    write(paths.paper(root) / "sections" / "introduction.tex", intro)
    write(paths.paper(root) / "si" / "main_si.tex", "\\section{S}\n")   # the SI cites since PH-W8.2
    return root


def test_unresolved_key_is_reported(tmp_path):
    root = _tree(tmp_path, ENTRY_PAGES, "\\section{I}\nText\\cite{roe2020other,typed2024key}. % \\cite{ignored}\n")
    problems = refs.unresolved(root)
    assert len(problems) == 1 and "typed2024key" in problems[0]
    assert "ignored" not in refs.cited(root)


def test_prepare_refuses_an_unresolved_key(tmp_path, monkeypatch):
    root = _tree(tmp_path, ENTRY_PAGES, "\\section{I}\nText\\cite{typed2024key}.\n")
    monkeypatch.setattr(build, "resolve_template", lambda r, out=print: (REPO / "paper", 0))
    monkeypatch.setattr(build.template, "render_head", lambda tdir: "")
    with pytest.raises(build.PrepareError, match="typed2024key"):
        build.prepare(root, "draft", out=lambda *_: None)


def test_build_copy_marks_missing_pages_and_keeps_the_source(tmp_path):
    root = _tree(tmp_path, ENTRY_NO_PAGES + "\n" + ENTRY_PAGES, "\\section{I}\n\\cite{doe2024thing,roe2020other}\n")
    before = refs.source(root).read_bytes()
    dest, marked = refs.write_build_copy(root)
    assert marked == ["doe2024thing"]
    assert refs.source(root).read_bytes() == before                # the fetched source is untouched
    copy = dest.read_text(encoding="utf-8")
    entries = dict((bibmod.parse_head(e)[1], e) for e in bibmod.split_entries(copy))
    assert bibmod.field(entries["doe2024thing"], "pages") == refs.MISSING_PAGES
    assert bibmod.field(entries["roe2020other"], "pages") == "1--2"
    assert "Crystal Growth \\& Design" in copy and "&amp;" not in copy
    assert dest.name == refs.BUILD_BIB != refs.BIB


def test_tex_safe_composes_accents_and_maps_known_characters():
    entry = "@article{k, author={Go\u0301mez\u2010Mart\u00edn, A}, title={\u03b3-alumina \u2013 water} }\n"
    out = refs.tex_safe(entry)
    assert "G\u00f3mez-Mart\u00edn" in out and "$\\gamma$-alumina \u2013 water" in out
    out = refs.tex_safe("@article{k, author={Stevanovi\u0107, V}, title={GFN2-xTB\u2500An Accurate} }\n")
    assert "Stevanovi\\'{c}" in out and "GFN2-xTB---An Accurate" in out


def test_tex_safe_names_a_character_it_cannot_place():
    with pytest.raises(refs.RefsError, match="U\\+2192"):
        refs.tex_safe("@article{k, title={a \u2192 b} }\n")


def test_release_guard_reports_cited_entries_without_pages(tmp_path):
    root = _tree(tmp_path, ENTRY_NO_PAGES + "\n" + ENTRY_PAGES, "\\section{I}\n\\cite{doe2024thing,roe2020other}\n")
    problems = build.guard(root)
    assert any("doe2024thing has no pages" in p for p in problems)
    assert not any("roe2020other" in p for p in problems)
    write(paths.paper(root) / "sections" / "introduction.tex", "\\section{I}\n\\cite{roe2020other}\n")
    assert not any("has no pages" in p for p in build.guard(root))


def test_repository_bibliography_is_fetched_and_resolves():
    assert refs.unresolved(REPO) == []
    prov = {r["key"] for r in bibmod.read_provenance(REPO, refs.source(REPO))}
    assert {k for k, _ in refs.entries(REPO)} == prov              # every entry came through nacre bib add
    for _, e in refs.entries(REPO):
        refs.tex_safe(e)                                           # and every entry can be typeset


def test_main_and_si_read_the_build_copy():
    for f in (paths.paper(REPO) / "main.tex", paths.paper(REPO) / "si" / "main_si.tex"):
        text = f.read_text(encoding="utf-8")
        assert "\\bibliography{refs_build}" in text and "\\bibliography{refs}" not in text
    assert 'BIBINPUTS="$here/build/bib:"' in (paths.paper(REPO) / "build.sh").read_text(encoding="utf-8")


def test_only_articles_need_pages():
    book = "@book{rossini1971selected, title={Selected values}, institution={National Bureau of Standards}, year={1971} }\n"
    article = "@article{doe2024thing, title={T}, journal={J}, volume={1}, year={2024} }\n"
    assert not refs.needs_pages(book)
    assert refs.needs_pages(article)
