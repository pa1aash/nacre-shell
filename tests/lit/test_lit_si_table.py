"""The SI parameter and conflicts tables are generated from lit/params.yaml and lit/conflicts.md."""
import re

import pytest
import yaml

from nacre import _util
from nacre.lit import evidence as E
from nacre.lit import params as P
from nacre.lit import si_table as S

ROOT = _util.repo_root()


@pytest.fixture(scope="module")
def generated():
    return S.generate(ROOT)


def test_committed_tables_are_current(generated):
    for name, text in generated.items():
        path = ROOT / S.OUT / name
        assert path.exists(), name
        assert path.read_text(encoding="utf-8") == text, "%s is stale: run python -m nacre.lit.si_table" % name


def test_every_key_has_a_row_and_every_doi_is_an_evidence_doi(generated):
    p = P.load_params(ROOT / P.PARAMS, ROOT)
    table = generated["params_table.tex"]
    labels = yaml.safe_load((ROOT / S.LABELS).read_text(encoding="utf-8"))
    symbols = P.load_symbols(ROOT)
    body = table.split(r"\begin{longtable}")[1].split(r"\end{longtable}")[0]
    rows = [r for r in body.split("\n") if r.endswith(r"\\") and r.count(" & ") == 5 and not r.startswith("Symbol")]
    assert len(rows) == len(p.entries)
    for key, e in p.entries.items():
        assert S.label_of(key, e, symbols, labels) in table, key
    dois = {r["doi"].lower() for r in E.read_csv(ROOT / P.TABLE)[1]}
    cited = set(re.findall(r"\\paramcite\{([^}]*)\}", table + generated["conflicts_table.tex"]))
    assert cited and cited <= dois
    assert set(generated["params_table_dois.csv"].split()[1:]) == cited


def test_conflict_prose_carries_no_typed_numbers():
    for c in S.conflicts_block(ROOT):
        for field in ("title", "reason", "resolution"):
            # digits may appear only inside chemical formulas or names (CaCO3, Ca(ClO4)2, Li2CO3, C16)
            bare = re.findall(r"(?<![A-Za-z0-9)(])[-+]?\d+(?:\.\d+)?(?![A-Za-z0-9(])", c[field])
            assert not bare, (c["title"], field, bare)


def test_number_formatting():
    assert S.num(0.0034) == "$0.0034$"
    assert S.num(-1129555.0) == r"$-1.13\times10^{6}$"
    assert S.num(4.2) == "$4.2$"
    assert S.num(0) == "0"
    assert S.num(2.1e14) == r"$2.1\times10^{14}$"


def test_display_conversion_uses_pint():
    v, lab = S.convert(0.0034, "J m^-2")
    assert v == pytest.approx(3.4) and "mJ" in lab
    v, _ = S.convert(-9500.0, "J mol^-1")
    assert v == pytest.approx(-9.5)


def test_tex_escapes_specials():
    assert S.tex("a_b & 50%") == r"a\_b \& 50\%"


def test_registry_keys_and_rule_codes_are_not_printed(generated):
    p = P.load_params(ROOT / P.PARAMS, ROOT)
    text = generated["params_table.tex"] + generated["conflicts_table.tex"]
    for key in ("gamma_nl_calcite", "matrix_baseline_hq_film_thickness", "matrix_baseline_tsinghua_film_thickness"):
        assert key in p.entries and key not in text and key.replace("_", r"\_") not in text
    assert not re.search(r"\((?:N|U|L|P|T|W|I|D|R|G|M|X|A)[0-9]\)", text)


def test_printed_tables_carry_no_process_vocabulary(generated):
    pattern = re.compile(r"regist|ruling|ruled|\bcp[0-9]|deviation|frozen|checkpoint|ledger|session|pre-reg|freeze",
                         re.I)
    for name in ("params_table.tex", "conflicts_table.tex"):
        assert not pattern.findall(generated[name]), (name, pattern.findall(generated[name]))


def test_conflicts_table_keeps_conflicts_that_bear_on_a_used_value(generated):
    entries = S.conflicts_block(ROOT)
    p = P.load_params(ROOT / P.PARAMS, ROOT).entries
    kept = [c for c in entries if any(S.screen_uses(p[k]) for k in c["keys"])]
    body = generated["conflicts_table.tex"].split(r"\endfoot")[1]
    assert body.count(r"\\") == len(kept)
    assert all(S.tex(c["title"]) in body for c in kept)


def test_conflict_lines_match_the_conflicts_block_and_carry_no_typed_numbers():
    lines = yaml.safe_load((ROOT / S.CONFLICT_LINES).read_text(encoding="utf-8"))
    assert set(lines) == {c["title"] for c in S.conflicts_block(ROOT)}
    for title, text in lines.items():
        bare = re.findall(r"(?<![A-Za-z0-9)(])[-+]?\d+(?:\.\d+)?(?![A-Za-z0-9(])", text)
        assert not bare, (title, bare)
