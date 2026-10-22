"""PH-W4.5: post-freeze keys by name, the crossed Ca_T x P_T grid, and the rule-based supersaturated control."""
import numpy as np
import pytest

from nacre._util import repo_root
from nacre.screen import k2_grid as g, k2_ph2 as p2

ROOT = repo_root()


@pytest.fixture(scope="module")
def ctx():
    return g.Context(ROOT)


def test_post_freeze_keys_are_read_by_name(ctx):
    ph2 = p2.load(ROOT)
    ph = p2.phases_of(ctx.cfg, ph2)
    assert list(ph) == ph2["phase_order"]
    assert p2.ksp_value(ctx.resolver, ph["brushite"]["ksp"]) == pytest.approx(-6.592)
    assert p2.ksp_value(ctx.resolver, ph["ocp_ca4h"]["ksp"]) == pytest.approx(-48.4)
    assert p2.ksp_value(ctx.resolver, ph["li3po4"]["ksp_key_registered"]) == pytest.approx(-8.886)
    assert ph["ocp"]["ksp"] == "log10_ksp_ocp" and ph["ocp_ca4h"]["ksp"] == "log10_ksp_ocp_ca4h_basis"
    assert ph["li3po4"]["ksp"] is None and ph["atcp"]["ksp"] is None            # undetermined by rule
    assert ph["ocp_ca4h"]["nu"] == {"a_Ca": 4, "a_PO4": 3, "a_H": 1}               # half of the Ca8H2 unit
    assert {k: v // 2 for k, v in ph["ocp"]["nu"].items()} == ph["ocp_ca4h"]["nu"]


def test_ca_and_p_are_crossed_independently(ctx):
    cells = g.phosphate_cells(ctx.cfg, ctx.resolver, "pH", drying=True)
    pairs = {(c[1]["Ca_T"], c[1]["P_T"]) for c in cells}
    assert len(pairs) == 36 and len({c[1]["Ca_T"] / c[1]["P_T"] for c in cells}) > 6


def test_control_is_the_cell_of_maximum_omega():
    recs = {"a": {"verdict": "inconclusive", "by_state": {"slurry": "inconclusive"}, "omega_median_by_state": {"slurry": 0.5}},
            "b": {"verdict": "feasible", "by_state": {"slurry": "feasible"}, "omega_median_by_state": {"slurry": 7.0}},
            "c": {"verdict": "falsified", "by_state": {"slurry": "falsified"}, "omega_median_by_state": {"slurry": np.nan}}}
    c = p2.max_omega_control(recs)
    assert c["control_cell"] == "b" and c["verdict"] == "feasible" and c["omega_median"] == 7.0
    assert p2.max_omega_control({"a": {"verdict": "x", "omega_median_by_state": {"slurry": np.nan}}})["verdict"] == "undetermined"


def test_brushite_and_ocp_cells_evaluate(ctx):
    ph = p2.phases_of(ctx.cfg, p2.load(ROOT))
    cells = g.phosphate_cells(ctx.cfg, ctx.resolver, "pH", drying=False)[:1] + \
        [c for c in g.phosphate_cells(ctx.cfg, ctx.resolver, "pH", drying=False) if c[1]["Ca_T"] == 100.0 and c[1]["P_T"] == 100.0][:1]
    for name in ("brushite", "ocp_ca4h", "ocp"):
        rec = g.eval_phosphate(ctx.params_path, ctx.cfg, ctx.resolver, name, cells, ctx.p, ctx.minerals, ("slurry",),
                               supersaturated_from=p2.max_omega_control, phases=ph)
        assert rec["ksp_key"] == ph[name]["ksp"]
        assert all("omega_median_by_state" in c for c in rec["cells"].values())
        assert rec["controls"]["supersaturated_control_cell"]["control_cell"] in rec["cells"]


def test_per_ph_tables_reproduce_the_frozen_pass_counts():
    from nacre.screen import k2_perph as pe
    doc = pe.build(ROOT)
    h = doc["headline"]
    assert (h["alkaline"]["calcite"]["frozen_passing"], h["alkaline"]["hap"]["frozen_passing"]) == (218, 415)
    assert (h["acid"]["calcite"]["frozen_passing"], h["acid"]["btcp"]["frozen_passing"]) == (68, 145)
    for grid in h:
        for key in ("hap", "acp", "btcp", "ocp"):
            assert h[grid][key]["cells_changed"] == 0          # same keys: only the control rule differs, no cell moves
    assert doc["tables"]["acid"]["rerun"]["brushite"]["ksp_key"] == "log10_ksp_brushite"


def test_f3_numbers_reproduce_the_stored_band_mass():
    import json
    d = json.loads((ROOT / "results/preprint/screen/f3_ph2/f3_numbers.json").read_text())
    f = d["mass_gamma_sn_le_gamma_sl"]
    assert f["sourced_calcite_gamma_nv"] == pytest.approx(f["stored_C3a_P_good"], abs=1e-12)
    assert d["c3_link_by_design_point"]["counts"] == {"falsified": 24, "inconclusive": 12}
    assert d["sobol_nucleate"]["log2_base"] == 17 and d["sobol_nucleate"]["capped"]
