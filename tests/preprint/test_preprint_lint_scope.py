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


def test_warn_block_is_loaded_from_the_charter():
    assert [rid for rid, _ in lint_scope.warn_rules(REPO)] == ["SG17W", "SG26W", "SG27W"]
    assert "SG17W" not in [rid for rid, _ in lint_scope.rules(REPO)]


def test_sg17w_fails_a_planted_sentence_without_thermodynamic(tmp_path):
    f = write(tmp_path / "t.tex", "The film is stable up to 4.5 V in the cell.\n")
    problems = lint_scope.lint(REPO, [f])
    assert len(problems) == 1 and "SG17W" in problems[0]
    c = write(tmp_path / "c.tex", "\\caption{The phase is stable above 4.2 V.}\n")
    assert any("SG17W" in p for p in lint_scope.lint(REPO, [c]))


def test_sg17w_passes_when_the_same_sentence_says_thermodynamic(tmp_path):
    f = write(tmp_path / "t.tex", "The phase is thermodynamically stable up to 4.5 V against the sink.\n")
    assert lint_scope.lint(REPO, [f]) == []
    g = write(tmp_path / "g.tex", "Thermodynamic onset only. The film is stable to 4.5 V.\n")
    assert len(lint_scope.lint(REPO, [g])) == 1       # another sentence does not count


def test_sg17w_applies_to_claim_statements(tmp_path):
    root = copy_tree(tmp_path)
    claims = root / "preprint" / "claims.yaml"
    claims.write_text(claims.read_text(encoding="utf-8") + (
        "  - id: CL-R98\n    statement: The phase is stable up to 4.5 V.\n"
        "  - id: CL-R97\n    statement: The phase is thermodynamically stable up to 4.5 V.\n"), encoding="utf-8")
    problems = lint_scope.lint(root)
    assert any("CL-R98" in p and "SG17W" in p for p in problems)
    assert not any("CL-R97" in p for p in problems)


def test_sg26w_fails_novel_or_first_without_audit(tmp_path):
    f = write(tmp_path / "t.tex", "This is a novel interface.\n")
    assert any("SG26W" in p for p in lint_scope.lint(REPO, [f]))
    g = write(tmp_path / "g.tex", "The first experiment tests the film.\n")
    assert any("SG26W" in p for p in lint_scope.lint(REPO, [g]))


def test_sg26w_passes_when_the_sentence_rests_on_the_audit(tmp_path):
    f = write(tmp_path / "t.tex", "Within the audited scan, no earlier report of the combination is found, and the claim is novel only in that sense.\n")
    assert lint_scope.lint(REPO, [f]) == []
    g = write(tmp_path / "g.tex", "The novelty audit found it. This is novel.\n")
    assert len(lint_scope.lint(REPO, [g])) == 1       # another sentence does not count


def test_sg27w_fails_self_heal_without_hypothesis_or_criterion(tmp_path):
    f = write(tmp_path / "t.tex", "The film is self-healing at a pit.\n")
    assert any("SG27W" in p for p in lint_scope.lint(REPO, [f]))


def test_sg27w_passes_with_hypothesis_or_criterion(tmp_path):
    f = write(tmp_path / "t.tex", "Self-healing is a design hypothesis, not a result.\n")
    assert lint_scope.lint(REPO, [f]) == []
    g = write(tmp_path / "g.tex", "The criterion for a self-healing film is stated in Section 2.\n")
    assert lint_scope.lint(REPO, [g]) == []


def test_allow_marker_skips_only_the_nacre_pattern(tmp_path):
    bare = write(tmp_path / "a.tex", "The start is nacre-inspired.\n")
    assert any("SG19" in p for p in lint_scope.lint(REPO, [bare]))
    marked = write(tmp_path / "b.tex", "<!-- sg:allow nacre -->\nThe start is nacre-inspired.\n")
    assert lint_scope.lint(REPO, [marked]) == []
    other = write(tmp_path / "c.tex", "<!-- sg:allow nacre -->\nThe nacre-inspired film protects the foil.\n")
    problems = lint_scope.lint(REPO, [other])
    assert problems and not any("SG19" in p for p in problems)
    unmarked_next = write(tmp_path / "d.tex", "<!-- sg:allow nacre -->\nA.\n\nThe start is nacre-inspired.\n")
    assert any("SG19" in p for p in lint_scope.lint(REPO, [unmarked_next]))
