"""K2 over the registered grid, the acid-adjusted state and the provenance of the PH-W4.2 runs."""
import hashlib
import json

import numpy as np
import pytest

from nacre._util import repo_root
from nacre.screen import chain, decision, k2_grid as g, params_adapter, ph_prov, run, study
from nacre.screen import mineral as mineral_mod

ROOT = repo_root()
PARAMS = ROOT / params_adapter.PRODUCTION_PARAMS


@pytest.fixture(scope="module")
def ctx():
    return g.Context(ROOT)


def test_grid_axes_are_registered(ctx):
    cfg, res = ctx.cfg, ctx.resolver
    assert [v for _, v in g._axis(cfg, res, "pH_acid_adjusted")] == [4.5, 5.5, 6.5, 7.5, 8.5]
    assert [v for _, v in g._axis(cfg, res, "pH")] == [10.0, 12.0, 13.0]
    ii = [v for _, v in g._axis(cfg, res, "I_ionic")]
    assert ii == sorted(ii) and ii[0] == pytest.approx(0.033) and ii[-1] == pytest.approx(0.23)
    cells = g.carbonate_cells(cfg, res)
    assert len(cells) == 6 * 3 * 2 * 3 * 3                               # Ca_T x C_T x a_w(drying) x pH x I
    assert all(set(c[2]) == {"pH", "I_ionic"} for c in cells)
    assert len({c[0] for c in cells}) == len(cells)
    assert len(g.phosphate_cells(cfg, res, "pH", drying=True)) == 6 * 6 * 2 * 3 * 3
    assert len(g.phosphate_cells(cfg, res, "pH_acid_adjusted", drying=False)) == 6 * 6 * 5 * 3


def test_phosphate_phases_cover_the_slurry_stage_of_the_ladder(ctx):
    import csv
    ladder = {r["phase"] for r in csv.DictReader(open(ROOT / ph_prov.LADDER)) if r["stage"] == "slurry"}
    registered = {s["ladder"] for s in ctx.cfg["k2_phases"].values()}
    assert ladder == registered                                           # no slurry-stage phase of the ladder is left out
    for name, s in ctx.cfg["k2_phases"].items():
        if s["ksp"] is None:
            assert name in ("brushite", "atcp", "li3po4") and ctx.doc["params"].get(name) is None


def test_ksp_keys_exist_for_the_phases_that_name_one(ctx):
    for name, s in ctx.cfg["k2_phases"].items():
        if s["ksp"]:
            e = ctx.doc["params"][s["ksp"]]
            assert e["prior"]["family"] != "none", name


def test_phosphate_omega_equals_the_chain_omega_for_hap_and_tcp(ctx):
    """The ln IAP of k2_grid is the contract-v5 saturation ratio of the chain (hydroxyapatite and beta-TCP)."""
    cfg = ctx.cfg
    minerals = mineral_mod.registry(cfg)
    hap = minerals["hap"]
    spec = cfg["k2_phases"]["hap"]
    design = {"Ca_T": 1.0e-2 * 1e3, "P_T": 1.0e-3 * 1e3}
    fixed = {"pH": 9.0, "I_ionic": 0.0416}
    extra = [study._fixed(k, v, g.AXIS_SI[k], "design") for k, v in {**design, **fixed}.items()]
    extra.append(study._fixed("a_w", 1.0, "1", "state"))
    b = g.phosphate_bindings(cfg, spec)
    b = {k: v for k, v in b.items() if k not in ("pH", "I_ionic")}
    rp = params_adapter.regime_priors(PARAMS, "R-slurry", False, bindings=b, absent="gap", extra=extra)
    om = g.phosphate_omega(rp, spec, 4096, 7, 4096, 1.0, hap)["speciation"]["Omega_bulk"]
    x = rp.joint.sample(np.random.default_rng(1), 4)             # the sampled inputs of the first chunk are the same draws
    ref = chain.evaluate(dict(zip(rp.joint.symbols, x.T)), ["speciation"], hap)[0]["speciation"]["Omega_bulk"]
    assert np.all(np.isfinite(om))
    # same formula: check on one fixed draw set through the chain
    seq = np.random.SeedSequence(7).spawn(1)[0]
    xs = rp.joint.sample(np.random.default_rng(seq), 4096)
    o_chain = chain.evaluate(dict(zip(rp.joint.symbols, xs.T)), ["speciation"], hap)[0]["speciation"]["Omega_bulk"]
    assert np.allclose(om, o_chain, rtol=1e-9)
    assert ref.shape == (4,)


def test_ocp_uses_the_hydrogen_ion_activity_and_acp_ignores_n_at_unit_water_activity(ctx):
    cfg = ctx.cfg
    assert cfg["k2_phases"]["ocp"]["nu"] == {"a_Ca": 8, "a_PO4": 6, "a_H": 2}        # 8 Ca2+ + 2 H+ + 6 PO4(3-) per the K_sp key
    assert cfg["k2_phases"]["ocp"]["n_hyd"] == 5
    minerals = mineral_mod.registry(cfg)
    design, fixed = {"Ca_T": 1.0e1, "P_T": 1.0e1}, {"pH": 9.0, "I_ionic": 0.0416}
    r_wet = g.phosphate_point(PARAMS, cfg, cfg["k2_phases"]["acp"], design, fixed, 2 ** 11, 1, 2 ** 11, 0.9, minerals["hap"],
                              ("slurry",))
    assert r_wet["verdict"] in ("feasible", "falsified", "inconclusive") and "gap" not in r_wet     # n_hyd_acp is a gap
    r_dry = g.phosphate_point(PARAMS, cfg, cfg["k2_phases"]["acp"], dict(design, **{"a_w@drying": 0.0013}), fixed, 2 ** 11, 1,
                              2 ** 11, 0.9, minerals["hap"], ("slurry", "drying"))
    assert r_dry["verdict"] == "undetermined"                                # a_w < 1 needs n, which is a gap


def test_a_phase_without_a_ksp_key_is_undetermined(ctx):
    minerals = mineral_mod.registry(ctx.cfg)
    r = g.phosphate_point(PARAMS, ctx.cfg, ctx.cfg["k2_phases"]["brushite"], {"Ca_T": 1.0, "P_T": 1.0},
                          {"pH": 7.0, "I_ionic": 0.04}, 256, 1, 256, 0.9, minerals["hap"], ("slurry",))
    assert r["verdict"] == "undetermined" and "no K_sp key" in r["gap"]


def test_controls_gate_the_cells():
    cells = {"a": {"verdict": "feasible"}, "b": {"verdict": "falsified"}, "c": {"verdict": "undetermined"}}
    out = g.apply_controls(cells, False)
    assert {k: v["verdict"] for k, v in out.items()} == {"a": "inconclusive", "b": "inconclusive", "c": "undetermined"}
    assert out["a"]["verdict_before_control"] == "feasible"
    assert {k: v["verdict"] for k, v in g.apply_controls(cells, True).items()} == {k: v["verdict"] for k, v in cells.items()}


def test_window_and_headline_rules():
    mk = lambda *v: {str(i): {"verdict": x} for i, x in enumerate(v)}
    assert g.window_of(mk("feasible", "falsified"))[1] == "feasible"
    assert g.window_of(mk("falsified", "falsified"))[1] == "falsified"
    assert g.window_of(mk("falsified", "inconclusive"))[1] == "inconclusive"
    assert g.window_of(mk("undetermined", "undetermined"))[1] == "undetermined"
    assert g.REGIME == {"feasible": "suitable against dissolution", "falsified": "excluded", "inconclusive": "open",
                        "undetermined": "undetermined"}


def test_onset_along_a_scan():
    assert g.onset({10.0: {"verdict": "falsified"}, 11.0: {"verdict": "falsified"}})["pattern"] == "undersaturated throughout the scan"
    assert g.onset({10.0: {"verdict": "feasible"}})["pattern"] == "not undersaturated anywhere in the scan"
    o = g.onset({10.0: {"verdict": "falsified"}, 11.0: {"verdict": "falsified"}, 12.0: {"verdict": "feasible"}})
    assert o["crossing_pH"] == [[11.0, 12.0]]


def test_carbonate_cell_flags_undersaturation_at_the_low_dose_corner_and_not_at_high_dose(ctx):
    cfg, res = ctx.cfg, ctx.resolver
    cells = g.carbonate_cells(cfg, res)
    low = next(c for c in cells if c[0].startswith("Ca_T=1e-06 mol dm^-3; C_T=dic_slurry@min; a_w=wet_film; pH=pH@min; I=I@min"))
    high = next(c for c in cells if c[0].startswith("Ca_T=0.1 mol dm^-3; C_T=dic_slurry@max; a_w=wet_film; pH=pH@max; I=I@max"))
    for pol in ("calcite", "aragonite", "ACC"):
        r = g.carbonate_point(PARAMS, cfg, pol, low[1], low[2], 2 ** 11, 1, 2 ** 11, 0.9)
        assert r["verdict"] == "falsified"
        r = g.carbonate_point(PARAMS, cfg, pol, high[1], high[2], 2 ** 11, 1, 2 ** 11, 0.9)
        assert r["verdict"] == "feasible"


def test_acid_adjusted_state_is_the_wet_slurry_only(ctx):
    c = g.acid_cfg(ctx.cfg)
    assert list(c["bindings"]["R-slurry"]["states"]) == ["slurry"]
    assert list(ctx.cfg["bindings"]["R-slurry"]["states"]) == ["slurry", "drying"]        # the original is untouched


def test_provenance_fields_and_frozen_hashes():
    assert ph_prov.check_frozen(ROOT)
    ex = ph_prov.extra(ROOT)
    assert ex["ladder_hash"] == "sha256:" + ph_prov.LADDER_SHA256
    assert ex["thresholds_block_version"] == 11
    assert ex["thresholds_block_sha256"] == "sha256:660930a92fb77d4f34cc9f38783d0f5f7412f804cc9f04d68bafbedfdd014a16"
    assert ex["checkpoint_tag"] == "p0-cp5" and len(ex["checkpoint_tag_commit"]) == 40
    assert ex["symbol_bindings_hash"] == "sha256:" + hashlib.sha256((ROOT / ph_prov.BINDINGS).read_bytes()).hexdigest()
    assert set(ex["gap_table_hashes"]) == {p.as_posix() for p in ph_prov.GAP_TABLES}
    prov = run._provenance(ROOT, run.load_config(ROOT), ROOT / run.CONFIG,
                           [params_adapter.regime_priors(PARAMS, "R-slurry", False, bindings={"pH": "ph_slurry"})], run.THRESHOLDS, False)
    from nacre.screen import summary
    row = {"row_id": "r", "film_id": "f", "phase": "p", "stage": "slurry", "role": "baseline", "framing": None, "labels": [],
           "provisional": False, "retained_mass": None, "K2": {"verdict": "undetermined", "evidence": {"K_sp": "gap"}}}
    summary.validate(summary.build(None, prov, False, extensions={"p0-w4": {"x": {}}}, ph_rows=[row]))


def test_a_changed_ladder_stops_the_run(tmp_path):
    (tmp_path / ph_prov.LADDER.parent).mkdir(parents=True)
    (tmp_path / ph_prov.LADDER).write_text("phase,stage\nX,slurry\n")
    with pytest.raises(ph_prov.Frozen):
        ph_prov.check_frozen(tmp_path)


def test_production_output_must_be_a_new_ph_directory(tmp_path):
    with pytest.raises(run.ProductionRefused):
        g.run_k2_grid(ROOT, ROOT / "results/preprint/screen/no_such_run/summary.json", ("carbonate",))
    with pytest.raises(run.ProductionRefused):
        g.run_k2_grid(ROOT, ROOT / "results/preprint/screen/table_adm/summary.json", ("carbonate",))
    with pytest.raises(run.ProductionRefused):
        g.run_k2_grid(ROOT, ROOT / "results/preprint/screen/no_such_run_ph/summary.json", ("carbonate",), stride=7)


def test_dry_run_writes_only_under_dryrun_ph():
    with pytest.raises(run.ProductionRefused):
        g.run_k2_grid(ROOT, ROOT / "results/preprint/screen/k2_dry/summary.json", ("carbonate",), dry=True)


def test_phosphate_controls_are_registered_and_supersaturated_for_every_phase_with_a_ksp(ctx):
    minerals = mineral_mod.registry(ctx.cfg)
    ctl = g.phosphate_control_cells(ctx.cfg, ctx.resolver)
    assert set(ctl) == {"undersaturated", "supersaturated"}
    assert ctl["undersaturated"][2]["pH"] == "ph_slurry_modified@min" and ctl["supersaturated"][2]["pH"] == "ph_slurry_acid_adjusted@value"
    for name, spec in ctx.cfg["k2_phases"].items():
        if not spec["ksp"]:
            continue
        out = {}
        for cname, (design, fixed, labels) in ctl.items():
            out[cname] = g.phosphate_point(PARAMS, ctx.cfg, spec, design, fixed, 2 ** 12, 1, 2 ** 12, 0.9, minerals["hap"], ("slurry",))
        assert out["undersaturated"]["verdict"] == "falsified", name
        if name == "ocp":
            # The control does what it is for: with log10 K_sp = -48.4 read per Ca8H2(PO4)6.5H2O (the W1 key's recorded basis), OCP is
            # not supersaturated even at 0.1 mol dm^-3 Ca and P at pH 7.65, so K2 of OCP is inconclusive in every cell. The value
            # is half the classical 96.6 of the Ca8 formula unit, so it is probably per Ca4H(PO4)3.2.5H2O: a basis question for cp5b.
            assert out["supersaturated"]["verdict"] == "falsified"
            continue
        assert out["supersaturated"]["verdict"] == "feasible", name
