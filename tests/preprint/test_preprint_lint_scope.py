"""nacre preprint lint-scope: no claim that the barrier works and no out-of-scope wording."""
import pytest

from nacre.preprint import lint_scope
from preprint_helpers import REPO, copy_tree, write


def test_skeleton_briefs_and_claims_are_clean():
    assert lint_scope.lint(REPO) == []


@pytest.mark.parametrize("suffix,body", [
    (".tex", "We show that the barrier protects the collector."),
    (".tex", "The film prevents dissolution of the oxide in the slurry."),
    (".tex", "\\caption{The coating works under these conditions.}"),
    (".tex", "% the corrosion rate falls by half"),
    (".tex", "This improves capacity retention."),
    (".tex", "A longer cycle life follows."),
    (".tex", "The device is stable."),
    (".tex", "Battery performance improves."),
    (".tex", "A protective layer forms."),
    (".tex", "This is the optimal interface."),
    (".tex", "The result was experimentally validated."),
    (".md", "- Fig 5 shows that the shell inhibits pitting."),
    (".md", "| Fig 6 | performance ranking |"),
    (".tex", "The barrier\nworks across the whole window."),
])
def test_planted_violations_fail(tmp_path, suffix, body):
    f = write(tmp_path / ("t" + suffix), body + "\n")
    assert lint_scope.lint(REPO, [f]), body


def test_allowlisted_does_not_claim_sentences_pass(tmp_path):
    body = ("This paper does not claim that the barrier works.\n"
            "This paper does not claim any corrosion rate, capacity or device performance.\n")
    f = write(tmp_path / "t.tex", body)
    assert lint_scope.lint(REPO, [f]) == []


def test_altered_does_not_claim_sentence_fails(tmp_path):
    f = write(tmp_path / "t.tex", "This paper does not claim that the barrier works, but it does.\n")
    assert lint_scope.lint(REPO, [f])


def test_neutral_physics_passes(tmp_path):
    body = ("The heterogeneous nucleation barrier falls as the contact angle falls. "
            "The Pourbaix result is a thermodynamic proxy for film stability.\n")
    f = write(tmp_path / "t.tex", body)
    assert lint_scope.lint(REPO, [f]) == []


def test_allowlist_refuses_lines_without_does_not_claim(tmp_path):
    root = copy_tree(tmp_path)
    allow = root / "preprint" / "paper" / "lint" / "scope_allowlist.txt"
    allow.write_text(allow.read_text(encoding="utf-8") + "The barrier works.\n", encoding="utf-8")
    with pytest.raises(lint_scope.ScopeConfigError):
        lint_scope.lint(root)


def test_claim_statements_are_linted(tmp_path):
    root = copy_tree(tmp_path)
    claims = root / "preprint" / "claims.yaml"
    claims.write_text(claims.read_text(encoding="utf-8") + (
        "  - id: CL-R99\n    statement: The film protects the foil.\n"), encoding="utf-8")
    problems = lint_scope.lint(root)
    assert any("CL-R99" in p for p in problems)


def test_charter_patterns_are_loaded():
    ids = [rid for rid, _ in lint_scope.rules(REPO)]
    assert "SG01" in ids and "SG14" in ids and "PS01" in ids
