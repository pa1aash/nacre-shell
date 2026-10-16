"""nacre preprint lint-numbers: digits in prose and captions must come from macros."""
import pytest

from nacre.preprint import lint_numbers
from preprint_helpers import REPO, write


def _lint(tmp_path, body):
    f = write(tmp_path / "t.tex", body)
    return lint_numbers.lint(REPO, [f])


def test_skeleton_is_clean():
    assert lint_numbers.lint(REPO) == []


@pytest.mark.parametrize("body", [
    "The barrier is 12 kJ per mole.",
    "\\caption{Contact angle of 45 degrees.}",
    "A value of $10^{-3}$ appears.",
    "\\section{Step 2 of the chain}",
    "We used 4096 draws.",
    "The ratio is 0.5 here.",
    "Ca2+ written without mhchem.",
])
def test_planted_digits_fail(tmp_path, body):
    problems = _lint(tmp_path, body)
    assert len(problems) == 1 and "digit outside a macro" in problems[0]


@pytest.mark.parametrize("body", [
    "The median is \\NumThetaMedian{} in this regime.",
    "As shown in Fig.~\\ref{fig:2} and eqn~\\eqref{eq:1}.\\label{sec:3}",
    "As reported before.\\cite{smith2020,jones1999}",
    "Calcite, \\ce{CaCO3}, binds \\ce{Ca^2+} and \\ce{CO3^2-}.",
    "The ion $\\mathrm{Ca}^{2+}$ and the exponent in $\\mathrm{J\\,m^{-2}}$ and $x_1$.",
    "% a comment with 42 numbers",
    "$f(\\theta) = (2 + \\cos\\theta)(1 - \\cos\\theta)^2 / 4$",
    "$\\Delta G^* = \\frac{16\\pi}{3}\\gamma^3$",
    "\\begin{tabular}{p{4.5cm}l} a & b \\end{tabular}",
    "\\begin{figure}[t]\\includegraphics[width=0.9\\columnwidth]{fig2}\\end{figure}",
    "\\IfFileExists{../../theory/derivation_body.tex}{}{}",
])
def test_exempt_forms_pass(tmp_path, body):
    assert _lint(tmp_path, body) == []


def test_allowlist_ids_are_explicit():
    rules = lint_numbers.allowlist(REPO)
    assert rules and all(rid.startswith("NA") for rid, _ in rules)
