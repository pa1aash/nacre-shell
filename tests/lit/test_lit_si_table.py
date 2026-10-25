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
    for key in p.entries:
        assert S.texkey(S.display_key(key, labels)) in table, key
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


def test_display_key_overrides_the_printed_key_only(generated):
    assert S.display_key("v_m_calcite", {}) == "v_m_calcite"
    assert S.display_key("k", {"k": {"label": "x", "display_key": "shown"}}) == "shown"
    params_tex = generated["params_table.tex"]
    for shown in ("matrix_baseline_lipo3_film_thickness", "matrix_baseline_alpo4_baked_film_thickness"):
        assert S.texkey(shown) in params_tex
    for hidden in ("matrix_baseline_hq_film_thickness", "matrix_baseline_tsinghua_film_thickness"):
        assert S.texkey(hidden) not in params_tex
        assert S.texkey(hidden) not in generated["conflicts_table.tex"]
