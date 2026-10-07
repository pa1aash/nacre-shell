from nacre.report import build


def _root(tmp_path, main="", sections=None):
    (tmp_path / "paper" / "sections").mkdir(parents=True)
    (tmp_path / "paper" / "main.tex").write_text(main, encoding="utf-8")
    for name, body in (sections or {}).items():
        (tmp_path / "paper" / "sections" / name).write_text(body, encoding="utf-8")
    return tmp_path


def test_digits_flagged_in_text_but_not_in_syntax_or_comments(tmp_path):
    root = _root(tmp_path, "\\usepackage[utf8]{inputenc}\n\\documentclass[11pt]{article}\n% comment 12\n"
                           "\\input{sections/a1}\n\\section{Intro}\n\\label{sec:1}\nTitle pending.\n",
                 {"a.tex": "% W1 stub\n", "b.tex": "The value is 42.\n"})
    problems = build.digit_problems(root)
    assert problems == ["paper/sections/b.tex:1 digit in text"]


def test_no_digit_problems_for_clean_skeleton(tmp_path):
    root = _root(tmp_path, "\\section{Introduction}\n\\input{sections/introduction}\n", {"introduction.tex": "% W1\n"})
    assert build.digit_problems(root) == []


def test_scope_words_flagged_and_template_dirs_skipped(tmp_path):
    root = _root(tmp_path, "The corrosion rate and capacity of a device.\n")
    (root / "paper" / "rsc_template").mkdir()
    (root / "paper" / "rsc_template" / "main.tex").write_text("capacity\n", encoding="utf-8")
    (root / "paper" / "build").mkdir()
    (root / "paper" / "build" / "x.tex").write_text("battery\n", encoding="utf-8")
    problems = build.scope_problems(root)
    assert len(problems) == 3 and all(p.startswith("paper/main.tex:1") for p in problems)


def test_log_classification_separates_expected_from_unexpected():
    log = "\n".join([
        "NACRE-WARNING: generated/macros.tex is absent",
        "LaTeX Warning: Reference `fig:x' on page 1 undefined on input line 9.",
        "LaTeX Warning: Citation `k' on page 1 undefined on input line 9.",
        "LaTeX Font Warning: Font shape not available",
        "Output written on build/main.pdf (3 pages, 1 bytes).",
    ])
    unexpected, expected = build.log_problems(log, "I found no \\citation commands---while reading file main.aux")
    assert len(unexpected) == 2 and "Reference" in unexpected[0] and "Citation" in unexpected[1]
    assert any("macros.tex" in e for e in expected) and any("no citations" in e for e in expected)
    assert build._pages(log) == 3


def test_missing_database_entry_is_unexpected():
    unexpected, _ = build.log_problems("", "Warning--I didn't find a database entry for \"k\"")
    assert unexpected
