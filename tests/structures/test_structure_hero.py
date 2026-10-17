"""Figure 1 hero scene: composition, charge balance, sourced Ca2+ geometry and the cell-edge crop."""
from __future__ import annotations

import json

import numpy as np
import pytest
import yaml

from nacre.structures import build, evidence
from nacre.structures.meta import read_structure

from structures_helpers import BLENDER_DIR, STRUCT_DIR, load_blender_module

config = load_blender_module("config")


@pytest.fixture(scope="module")
def hero():
    return read_structure(STRUCT_DIR / "hero_interface.extxyz")


@pytest.fixture(scope="module")
def parts(hero):
    comp = np.asarray(hero.arrays["component"]).astype(str)
    sym = np.array(hero.get_chemical_symbols())
    return comp, sym, hero.positions


# ---------------------------------------------------------------- sourced geometry (R2)
def test_hydration_geometry_comes_from_w1_rows():
    rec = evidence.load()
    assert rec["ref"] == "origin/preprint/p0-w1" and len(rec["commit"]) == 40
    assert {r["row_id"] for r in rec["rows"]} >= {"TE-072"}
    g = evidence.hydration_geometry()
    primary = next(r for r in rec["rows"] if r["row_id"] == g["row_ids"]["cn"])
    assert g["cn"] == round(float(primary["value"]))
    assert f"Ca-Ow {g['r_ca_o']}" in primary["notes"]
    assert g["row_ids"]["r_ca_o"] == g["row_ids"]["cn"]


def test_hydration_geometry_is_not_typed_in_build_config():
    cfg = build.load_config()
    for name in ("ca_hydrated", "hero_interface"):
        spec = cfg["targets"][name]
        assert spec["evidence"] == "ca_hydration", name
        assert not {"cn", "r_ca_o"} & set(spec.get("params") or {}), name
    with pytest.raises(ValueError):
        build._evidence_params({"evidence": "ca_hydration", "params": {"cn": 6}})


def test_selection_rule_prefers_best_grade_full_text_row():
    rec = evidence.load()
    rows = [dict(r) for r in rec["rows"]]
    worse = dict(rows[0], row_id="TX-1", grade="D", value="9", notes="Ca-Ow 2.60 A")
    g = evidence.hydration_geometry({"commit": "0" * 40, "rows": rows + [worse]})
    assert g["row_ids"]["cn"] != "TX-1"


def test_drawn_cn_inside_experimental_range():
    rec = evidence.load()
    bad = [dict(r) for r in rec["rows"]]
    for r in bad:
        if r["range_or_uncertainty"] and ".." in r["range_or_uncertainty"]:
            r["range_or_uncertainty"] = "1..2"
    with pytest.raises(ValueError):
        evidence.hydration_geometry({"commit": "0" * 40, "rows": bad})


def test_scene_metadata_records_row_ids(hero):
    g = evidence.hydration_geometry()
    src = hero.info["source_ids"]["ca_hydration"]
    assert src["row_ids"] == g["row_ids"] and src["evidence_commit"] == g["evidence_commit"]
    ion = read_structure(STRUCT_DIR / "ca_hydrated.extxyz")
    assert ion.info["source_ids"]["row_ids"] == g["row_ids"]
    assert ion.info["params"]["cn"] == g["cn"] and ion.info["params"]["r_ca_o"] == g["r_ca_o"]


# ---------------------------------------------------------------- composition and physics
def test_charge_is_balanced_by_carbonate(hero, parts):
    comp, sym, _ = parts
    ledger = json.loads(hero.info["charge_ledger"])
    assert sum(q for _, q in ledger) == hero.info["total_charge"] == 0
    ca_sites = [c for c in set(comp) if c.startswith(("bound", "bridge")) and not c.endswith("_water")]
    carbonates = {c for c in comp if c.startswith("carbonate")}
    # Each Ca2+ on a catechol monoanion is +1; each dissolved carbonate is -2 (D5).
    assert len(ca_sites) == 2 * len(carbonates)
    for c in carbonates:
        assert sorted(sym[comp == c]) == ["C", "O", "O", "O"]


def test_few_bound_ions_and_one_bridge(parts):
    comp, sym, _ = parts
    outside = [c for c in set(comp[sym == "Ca"]) if c != "nucleus"]
    assert 2 <= len(outside) <= 5  # a few bound ions, not a cloud (derivation section 7)
    assert sum(c == "bridge" for c in outside) == 1


def test_every_ca_shell_has_the_evidence_geometry(parts):
    comp, sym, pos = parts
    g = evidence.hydration_geometry()
    for c in set(comp):
        if c.startswith(("bound", "bridge")) and not c.endswith("_water"):
            i = np.where(comp == c)[0][0]
            d = np.linalg.norm(pos - pos[i], axis=1)
            shell = np.where((sym == "O") & (d < g["r_ca_o"] + 0.05))[0]
            assert len(shell) == g["cn"], c
            assert np.allclose(d[shell], g["r_ca_o"], atol=1e-3), c
            assert sum(comp[j].startswith("chain") for j in shell) == 2, c  # bidentate catecholate


def test_bridge_ca_touches_template_and_nucleus(parts):
    comp, sym, pos = parts
    i = np.where(comp == "bridge")[0][0]
    d = np.linalg.norm(pos - pos[i], axis=1)
    near = comp[(sym == "O") & (d < 2.5)]
    assert any(c.startswith("chain") for c in near) and "nucleus" in near


def test_nucleus_is_a_neutral_low_contact_angle_cap(hero, parts):
    comp, sym, pos = parts
    nuc = comp == "nucleus"
    assert (sym[nuc] == "Ca").sum() == (sym[nuc] == "C").sum() == hero.info["nucleus_fu_placed"] > 5
    p = hero.info["params"]["nucleus"]
    assert p["contact_angle_deg"] <= 60  # wets the template
    th = np.radians(p["contact_angle_deg"])
    radius = p["base_radius"] / np.sin(th)
    top = pos[comp == "slab", 2].max()
    z_b = top + p["base_height"]
    # Every carbonate C and Ca of the nucleus lies inside the cap (O may reach just past it).
    cxy = (p["centre"][0] * np.asarray(hero.cell)[0] + p["centre"][1] * np.asarray(hero.cell)[1])[:2]
    centre = np.r_[cxy, z_b + radius * (1 - np.cos(th)) - radius]
    # The bridging carbonate (the first four nucleus atoms) sits on the bridging Ca shell at the
    # rim of the base, so it is exempt; every other Ca and C lies inside the cap.
    first = np.where(nuc)[0][:4]
    assert sorted(sym[first]) == ["C", "O", "O", "O"]
    ca_b = pos[comp == "bridge"][0]
    assert np.linalg.norm(pos[first] - ca_b, axis=1).min() == pytest.approx(
        evidence.hydration_geometry()["r_ca_o"], abs=1e-3)
    core = nuc & (sym != "O")
    core[first] = False
    assert np.all(pos[core, 2] >= z_b - 1e-6)
    assert np.all(np.linalg.norm(pos[core] - centre, axis=1) <= radius + 1e-6)
    # The cap is wide and low: base diameter well above its height.
    assert 2 * p["base_radius"] > 3 * radius * (1 - np.cos(th))


def test_chains_are_anchored_bidentate(parts):
    comp, sym, pos = parts
    al = pos[(comp == "slab") & (sym == "Al")]
    for c in sorted({c for c in comp if c.startswith("chain")}):
        o = pos[(comp == c) & (sym == "O")]
        d = np.linalg.norm(o[:, None, :] - al[None, :, :], axis=-1).min(axis=1)
        assert (d < 2.15).sum() == 2, c


def test_water_only_behind_the_cut(hero, parts):
    comp, sym, pos = parts
    y_cut = hero.info["params"]["water"]["y_cut"] * np.asarray(hero.cell)[1][1]
    assert np.all(pos[(comp == "water") & (sym == "O"), 1] >= y_cut - 1e-6)
    assert hero.info["n_water_placed"] > 100


def test_no_overlaps_between_parts(parts):
    comp, sym, pos = parts
    from scipy.spatial import cKDTree

    group = np.array([c.split("_")[0] for c in comp])
    bonded = {frozenset(p) for p in (("Al", "O"), ("Ca", "O"))}
    for i, j in cKDTree(pos).query_pairs(1.5):
        if group[i] != group[j]:
            assert frozenset((sym[i], sym[j])) in bonded, (comp[i], sym[i], comp[j], sym[j])


# ---------------------------------------------------------------- scene config and crop
def test_hero_scene_parses_and_is_draft_sized():
    s = config.parse_scene("hero")
    assert s["resolution"][0] * s["resolution"][1] <= 1280 * 960
    assert all(c["clip"] for c in s["components"])
    cam = s["camera"]["direction"]
    assert cam[2] < 0  # looks down onto the template


def test_crop_keeps_no_detached_hydroxyl():
    s = config.parse_scene("hero")
    rcfg = config.load_render_config()
    radii = config.load_radii(config.repo_path(rcfg["elements"]))
    comp = s["components"][0]
    st = config.read_extxyz(config.repo_path(comp["file"]))
    idx = config.select_atoms(st, comp["include"], comp["exclude_elements"])
    kept = config.clip_selection(st["symbols"], st["positions"], idx, comp["clip"], radii,
                                 rcfg["bonds"]["factor"], rcfg["bonds"]["pairs"])
    sym = [st["symbols"][i] for i in kept]
    pos = st["positions"][kept]
    bonds = config.find_bonds(sym, pos, radii, rcfg["bonds"]["factor"], rcfg["bonds"]["pairs"])
    partners = {i: set() for i in range(len(kept))}
    for i, j in bonds:
        partners[i].add(sym[j])
        partners[j].add(sym[i])
    slab_o = [k for k, i in enumerate(kept) if sym[k] == "O" and st["component"][i] == "slab"]
    assert slab_o and all("Al" in partners[k] for k in slab_o)  # every slab O hangs on an Al
    assert all(partners[k] for k in range(len(kept)) if sym[k] == "H")  # no lone H
    al = [k for k in range(len(kept)) if sym[k] == "Al"]
    assert all(sum(1 for i, j in bonds if k in (i, j)) == 6 for k in al)  # cut inside the cell
    cell = np.array([float(x) for x in st["info"]["Lattice"].split()]).reshape(3, 3)
    (x0, x1), (y0, y1) = comp["clip"]["box"]
    assert 0 < x0 < x1 < cell[0][0] and 0 < y0 < y1 < cell[1][1]


def test_clip_box_is_validated(tmp_path):
    doc = yaml.safe_load((BLENDER_DIR / "scenes" / "hero.yaml").read_text())
    doc["name"] = "bad"
    doc["components"][0]["clip"]["box"] = [[5.0, 1.0], [0.0, 1.0]]
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(doc))
    with pytest.raises(config.ConfigError):
        config.parse_scene(p)


def test_render_log_reads_row_ids_from_the_structure():
    st = config.read_extxyz(STRUCT_DIR / "hero_interface.extxyz")
    g = evidence.hydration_geometry()
    assert config.evidence_row_ids(st) == {"ca_hydration": g["row_ids"]}
    smoke = config.read_extxyz(STRUCT_DIR / "smoke_interface.extxyz")
    assert config.evidence_row_ids(smoke) == {"ion": g["row_ids"]}


def test_equidistant_anchor_site_is_refused():
    from nacre.structures import hero, slab

    s = slab.build({"nx": 2, "ny": 1, "n_o_layers": 3, "orthogonal": True}, seed=0)
    sym = np.array(s.get_chemical_symbols())
    top = np.where((sym == "O") & (s.positions[:, 2] > s.positions[sym == "O", 2].max() - 0.3))[0]
    d = np.linalg.norm(s.positions[top][:, None, :2] - s.positions[top][None, :, :2], axis=-1)
    np.fill_diagonal(d, np.inf)
    i, j = np.unravel_index(np.argmin(d), d.shape)  # nearest pair: its midpoint is a tie
    a, b = s.positions[top[i], :2], s.positions[top[j], :2]
    mid = (a + b) / 2 / np.diag(np.asarray(s.cell))[:2]
    sc = hero.Scene(s)
    p = hero._deep(hero.DEFAULTS, {})
    from nacre.structures import oligomer

    with pytest.raises(ValueError, match="equidistant"):
        hero.anchor_chain(sc, oligomer.build({"n_units": 4}, 7), list(mid), 0.0, p, "c")


def test_hero_regenerates_part_by_part(hero, parts):
    # Rebuild step by step and name the first part that departs from the committed file
    # (beyond the regeneration tolerance), or the step at which the build stops.
    from nacre.structures import compare, hero as hero_mod, oligomer, slab

    spec = build.load_config()["targets"]["hero_interface"]
    slab_spec = build.load_config()["targets"][spec["slab"]]
    trace, error = [], None
    try:
        hero_mod.build(slab.build(slab_spec["params"], slab_spec.get("seed", 0)),
                       oligomer.build({"n_units": 4}, 7), evidence.hydration_geometry(),
                       spec["params"], spec["seed"], trace=trace)
    except (RuntimeError, ValueError) as exc:
        error = str(exc)
    comp, sym, pos = parts
    # Each step is checked on the part it adds: a chain on its heavy atoms (a later Ca site
    # removes or turns one of its H), a Ca site on its ion and waters, the nucleus whole.
    added = {"bridge": ["bridge"], "nucleus": ["nucleus"]}
    for step, snap in trace:
        names = added.get(step, [step, f"{step}_water"] if step.startswith("bound") else [step])
        for c in names:
            xyz = snap[c]
            if step.startswith("chain"):
                heavy = sym[comp == c] != "H"
                ref = pos[comp == c][heavy]
                xyz = xyz[np.array([s != "H" for s in _snap_symbols(snap, c, comp, sym)])]
            else:
                ref = pos[comp == c]
            assert len(ref) == len(xyz), f"after step {step}: part {c} has {len(xyz)} atoms, not {len(ref)}"
            d = float(np.abs(ref - xyz).max()) if len(ref) else 0.0
            assert d <= compare.POSITION_TOL, f"after step {step}: part {c} moved {d:.3f} A"
    assert error is None, f"build stopped after {trace[-1][0] if trace else 'start'}: {error}"


def _snap_symbols(snap, c, comp, sym):
    """Element symbols of part c at a chain step: the committed heavy atoms keep their order,
    and the chain at that step still holds every H (one may go to a later Ca site)."""
    from nacre.structures import oligomer

    rec = oligomer.build({"n_units": 4}, 7)
    keep = np.setdiff1d(np.arange(len(rec)), np.where((rec.arrays["catechol"] == 0)
                                                       & (np.array(rec.get_chemical_symbols()) == "H"))[0])
    return list(np.array(rec.get_chemical_symbols())[keep])
