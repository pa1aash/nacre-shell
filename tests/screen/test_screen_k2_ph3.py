"""PH-W4.6: the Ca:P ratio grid (P_T = Ca_T / ratio) on the decade Ca_T grid."""
import pytest

from nacre._util import repo_root
from nacre.screen import k2_grid as g, k2_ph3 as p3

ROOT = repo_root()


@pytest.fixture(scope="module")
def ctx():
    return g.Context(ROOT)


def test_ratio_cells_hit_the_stoichiometric_ratios(ctx):
    ph3 = p3.load(ROOT)
    cells = p3.ratio_cells(ctx.cfg, ctx.resolver, ph3, "pH", True)
    assert len(cells) == 324 and len({c[0] for c in cells}) == 324
    assert {round(c[1]["Ca_T"] / c[1]["P_T"], 9) for c in cells} == {1.67, 1.5, 1.0}
    assert len(p3.ratio_cells(g.acid_cfg(ctx.cfg), ctx.resolver, ph3, "pH_acid_adjusted", False)) == 270


def test_labels_carry_the_doses_the_tables_parse(ctx):
    ph3 = p3.load(ROOT)
    lab = p3.ratio_cells(ctx.cfg, ctx.resolver, ph3, "pH", False)[0][3]
    assert float(lab["P_T"].split()[0]) == pytest.approx(float(lab["Ca_T"].split()[0]) / float(lab["CaP"]), rel=1e-5)
