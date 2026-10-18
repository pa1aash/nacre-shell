"""Render scene system without Blender: configs, palette, extxyz reader, bonds, geometry, smoke log."""
from __future__ import annotations

import json
import struct

import numpy as np
import pytest
import yaml

from structures_helpers import BLENDER_DIR, REPO, RENDER_DIR, committed_structures, load_blender_module

config = load_blender_module("config")
geometry = load_blender_module("geometry")
rig = load_blender_module("rig")
build_elements = load_blender_module("build_elements")


def _write(tmp_path, doc, name="demo"):
    p = tmp_path / f"{name}.yaml"
    p.write_text(yaml.safe_dump(doc))
    return p


def _scene(**over):
    doc = {"name": "demo", "resolution": [320, 240],
           "components": [{"file": "structures/preprint/ca_hydrated.extxyz", "style": "ball_and_stick"}]}
    doc.update(over)
    return doc


# ---------------------------------------------------------------- render settings
def test_render_config_is_reproducible_and_transparent():
    cfg = config.load_render_config()
    assert cfg["engine"]["name"] == "CYCLES" and cfg["engine"]["device"] == "CPU"
    assert cfg["engine"]["threads"] == 4  # R10: four threads on the shared 8 GB machines
    assert cfg["film_transparent"] is True
    assert cfg["colour_management"]["view_transform"] == "Standard"


def test_palette_is_the_tracked_style_palette():
    cfg = config.load_render_config()
    assert cfg["palette"] == "figures/style/palette.yaml"
    assert config.repo_path(cfg["palette"]).is_file()
    assert ".local" not in config.RENDER_CONFIG.read_text().split("palette:")[-1].splitlines()[0]


def test_render_wrapper_follows_the_memory_rule():
    sh = (BLENDER_DIR / "render.sh").read_text()
    assert "--threads 4" in sh and "--threads 2" not in sh
    assert "pct < 25" in sh and "waited >= 60" in sh


def test_render_config_rejects_gpu(tmp_path):
    cfg = yaml.safe_load(config.RENDER_CONFIG.read_text())
    cfg["engine"]["device"] = "GPU"
    p = tmp_path / "render.yaml"
    p.write_text(yaml.safe_dump(cfg))
    with pytest.raises(config.ConfigError):
        config.load_render_config(p)


# ---------------------------------------------------------------- palette
def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def test_palette_loader_returns_linear_rgb(tmp_path):
    doc = {"elements": {"Al": {"srgb": [0.8419, 0.7566, 0.6633], "linear_rgb": [0.6773, 0.5329, 0.3975]}}}
    p = tmp_path / "palette.yaml"
    p.write_text(yaml.safe_dump(doc))
    cols, _ = config.load_palette(p)
    assert cols["Al"] == (0.6773, 0.5329, 0.3975)


def test_palette_loader_refuses_missing_linear(tmp_path):
    p = tmp_path / "palette.yaml"
    p.write_text(yaml.safe_dump({"elements": {"O": {"srgb": [1, 0, 0]}}}))
    with pytest.raises(config.ConfigError):
        config.load_palette(p)


def test_configured_palette_linear_matches_srgb():
    path = config.repo_path(config.load_render_config()["palette"])
    cols, doc = config.load_palette(path)
    for el, entry in doc["elements"].items():
        expect = [_srgb_to_linear(c) for c in entry["srgb"]]
        assert cols[el] == pytest.approx(expect, abs=6e-4), el
    assert {"H", "C", "N", "O", "Al", "Ca"} <= set(cols)


# ---------------------------------------------------------------- scene configs
def test_every_scene_config_parses():
    scenes = sorted((BLENDER_DIR / "scenes").glob("*.yaml"))
    assert scenes
    for p in scenes:
        s = config.parse_scene(p)
        for c in s["components"]:
            assert config.repo_path(c["file"]).exists(), c["file"]


def test_smoke_scene_parses_by_name():
    s = config.parse_scene("smoke")
    assert s["name"] == "smoke"
    assert s["resolution"][0] * s["resolution"][1] <= 640 * 480
    assert s["components"][0]["style"] in config.STYLES
    assert s["camera"]["margin"] > 1.0


@pytest.mark.parametrize("bad", [
    {"label": "Ca"},
    {"components": [{"file": "x.extxyz", "style": "ball_and_stick", "text": "OH"}]},
    {"camera": {"direction": [0, 1, 0], "up": [0, 1, 0]}},
    {"components": [{"file": "x.extxyz", "style": "wireframe"}]},
    {"resolution": [4000, 3000]},
    {"resolution": [640]},
    {"samples": 0},
    {"arrows": [[0, 0, 0]]},
    {"components": []},
])
def test_invalid_scene_configs_are_refused(tmp_path, bad):
    with pytest.raises(config.ConfigError):
        config.parse_scene(_write(tmp_path, _scene(**bad)))


def test_scene_name_must_match_file(tmp_path):
    with pytest.raises(config.ConfigError):
        config.parse_scene(_write(tmp_path, _scene(name="other")))


def test_scene_defaults(tmp_path):
    s = config.parse_scene(_write(tmp_path, _scene()))
    assert s["samples"] is None
    assert s["components"][0]["translate"] == [0.0, 0.0, 0.0]
    assert s["camera"]["up"] == [0.0, 0.0, 1.0]


# ---------------------------------------------------------------- extxyz reader
def test_reader_matches_ase_on_committed_files():
    import ase.io

    for name, path in committed_structures().items():
        ref = ase.io.read(path, format="extxyz")
        got = config.read_extxyz(path)
        assert got["symbols"] == ref.get_chemical_symbols(), name
        assert np.allclose(got["positions"], ref.positions), name
        assert got["info"]["illustrative"] == "T", name
        if "component" in ref.arrays:
            assert got["component"] == list(ref.arrays["component"]), name
        if any(ref.pbc):
            assert np.allclose(got["lattice"], np.asarray(ref.cell)), name


def test_select_atoms_filters():
    st = config.read_extxyz(committed_structures()["al2o3_0001_oh_water"])
    water = config.select_atoms(st, ["water"], [])
    assert len(water) % 3 == 0 and all(st["component"][i] == "water" for i in water)
    no_h = config.select_atoms(st, [], ["H"])
    assert all(st["symbols"][i] != "H" for i in no_h)


def test_bonds_hydrated_ca():
    cfg = config.load_render_config()
    radii = config.load_radii(config.repo_path(cfg["elements"]))
    st = config.read_extxyz(committed_structures()["ca_hydrated"])
    bonds = config.find_bonds(st["symbols"], st["positions"], radii, cfg["bonds"]["factor"], cfg["bonds"]["pairs"])
    kinds = sorted("-".join(sorted((st["symbols"][i], st["symbols"][j]))) for i, j in bonds)
    cn = st["symbols"].count("O")  # the evidence coordination number (rows in the file's source ids)
    assert kinds.count("H-O") == 2 * cn and kinds.count("Ca-O") == cn and len(kinds) == 3 * cn


def test_bonds_respect_pair_whitelist():
    cfg = config.load_render_config()
    radii = config.load_radii(config.repo_path(cfg["elements"]))
    st = config.read_extxyz(committed_structures()["acc_cluster"])
    bonds = config.find_bonds(st["symbols"], st["positions"], radii, cfg["bonds"]["factor"], [["C", "O"]])
    assert len(bonds) == 24  # three C-O per carbonate, nothing else


# ---------------------------------------------------------------- elements table
def test_elements_table_is_generated():
    assert (BLENDER_DIR / "elements.yaml").read_text() == build_elements.render()


# ---------------------------------------------------------------- geometry and rig
def test_sphere_and_cylinder_templates():
    v, f = geometry.uv_sphere(8, 4)
    assert len(v) == 2 + 8 * 3 and np.allclose(np.linalg.norm(v, axis=1), 1.0)
    assert len(f) == 8 * 2 + 8 * 2
    v, f = geometry.cylinder(6)
    assert len(v) == 12 and len(f) == 6


def test_half_bonds_end_at_midpoint():
    v, f = geometry.cylinder(8)
    a, b = np.array([0.0, 0.0, 0.0]), np.array([1.0, 2.0, 2.0])
    (tr,) = geometry.half_bond_transforms([a], [b], 0.1)
    mv, _ = geometry.merge_instances((v, f), [tr])
    top = mv[8:].mean(axis=0)
    assert np.allclose(top, (a + b) / 2)


def test_ortho_scale_and_axes():
    assert geometry.ortho_scale(10, 5, (640, 480), 1.0) == pytest.approx(10.0)
    assert geometry.ortho_scale(4, 6, (640, 480), 1.0) == pytest.approx(8.0)
    assert geometry.ortho_scale(4, 6, (480, 640), 1.0) == pytest.approx(6.0)
    d, r, u = geometry.camera_axes([0, 1, 0], [0, 0, 1])
    assert np.allclose(np.cross(r, u), -d)


def test_rig_is_defined_once_and_in_camera_frame():
    assert set(rig.RIG) >= {"key", "fill", "rim", "world"}
    c = [0.0, 0.0, 0.0]
    d, r, u = [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]
    p = rig.light_position(c, d, r, u, 0.0, 0.0, 10.0)
    assert np.allclose(p, [0.0, -10.0, 0.0])  # azimuth 0 sits behind the camera
    scene_py = (BLENDER_DIR / "scene.py").read_text()
    assert "lights.new" not in scene_py and "rig.build(" in scene_py
    # Lights, world and occlusion shading are created in rig.py only.
    for made_in_rig in ("worlds.new", "AmbientOcclusion", "use_shadow"):
        assert made_in_rig not in scene_py
    assert "rig.shade(" in scene_py


def test_rig_has_soft_shadows_and_ambient_occlusion():
    assert rig.RIG["shadows"]["cast"] is True
    for name in rig.LIGHTS:
        assert rig.RIG[name]["size_frac"] > 0
        assert 5.0 < rig.penumbra_deg(name) < 25.0, name  # soft, but the shadow still reads
    ao = rig.RIG["ambient_occlusion"]
    assert 0.0 < ao["strength"] < 1.0 and ao["samples"] >= 8
    assert 1.0 <= ao["distance"] <= 4.0  # angstrom: local contacts, not whole regions
    assert rig.ao_factor(1.0) == 1.0  # unoccluded surfaces keep the palette colour exactly
    assert rig.ao_factor(0.0) == pytest.approx(1.0 - ao["strength"])
    d = rig.describe()
    assert set(d["penumbra_deg"]) == set(rig.LIGHTS)
    assert rig.RIG["key"]["irradiance"] > rig.RIG["rim"]["irradiance"] > rig.RIG["fill"]["irradiance"]


def test_rig_is_documented():
    doc = rig.__doc__
    for word in ("key", "fill", "rim", "Soft shadows", "Ambient occlusion", "World"):
        assert word in doc, word


def test_scene_runner_creates_no_text():
    src = (BLENDER_DIR / "scene.py").read_text()
    for forbidden in ("curves.new", "FONT", "text.new", "TextCurve"):
        assert forbidden not in src


# ---------------------------------------------------------------- smoke render
def _png_header(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    w, h, depth, ctype = struct.unpack(">IIBB", data[16:26])
    chunks, pos = [], 8
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos : pos + 4])
        chunks.append(data[pos + 4 : pos + 8])
        pos += 12 + n
    return w, h, depth, ctype, chunks


def test_smoke_render_and_log():
    png = RENDER_DIR / "smoke" / "smoke.png"
    log = json.loads((RENDER_DIR / "smoke" / "smoke.json").read_text())
    w, h, depth, ctype, chunks = _png_header(png)
    assert png.stat().st_size < 500 * 1024
    assert ctype == 6 and depth == 8  # RGBA: transparent background possible
    assert [w, h] == log["render"]["resolution"]
    assert not {b"tEXt", b"zTXt", b"iTXt", b"tIME"} & set(chunks)
    assert log["render"]["film_transparent"] is True
    assert log["text_objects"] == 0
    assert "linear RGB" in log["palette"]["colour_space"]
    assert log["palette"]["path"] == config.load_render_config()["palette"]
    assert log["output_sha256"] == config.sha256(png)
    for item in log["inputs"]:
        assert config.sha256(REPO / item["file"]) == item["sha256"], item["file"]


def test_render_logs_hold_no_machine_dependent_values():
    import getpass
    import platform

    for log_path in sorted(RENDER_DIR.rglob("*.json")):
        text = log_path.read_text()
        log = json.loads(text)
        assert "timing_s" not in log, log_path
        for bad in (str(REPO), str(__import__("pathlib").Path.home()), platform.node(), getpass.getuser()):
            assert bad not in text, (log_path, bad)
        for item in log["inputs"]:
            assert "evidence_row_ids" in item, log_path


def test_every_render_log_names_current_inputs():
    logs = sorted(RENDER_DIR.rglob("*.json"))
    assert {lp.parent.name for lp in logs} >= {"smoke", "compare", "fig2"}
    for log_path in logs:
        log = json.loads(log_path.read_text())
        png = REPO / log["output"]
        assert log["output_sha256"] == config.sha256(png), log_path
        assert log["scene_config_sha256"] == config.sha256(REPO / log["scene_config"]), log_path
        for item in log["inputs"]:
            assert config.sha256(REPO / item["file"]) == item["sha256"], (log_path, item["file"])


# ---------------------------------------------------------------- day 3: crops, fade, focus, rig
def _cfg():
    cfg = config.load_render_config()
    return cfg, config.load_radii(config.repo_path(cfg["elements"]))


def test_chunked_bonds_equal_the_full_matrix():
    cfg, radii = _cfg()
    st = config.read_extxyz(committed_structures()["al2o3_0001_oh_water"])
    sym, pos = st["symbols"], st["positions"]
    got = config.find_bonds(sym, pos, radii, cfg["bonds"]["factor"], cfg["bonds"]["pairs"], chunk=97)
    rc = np.array([radii[x]["covalent"] for x in sym])
    d = np.linalg.norm(pos[:, None] - pos[None], axis=-1)
    ii, jj = np.where(np.triu(d < cfg["bonds"]["factor"] * (rc[:, None] + rc[None]), k=1))
    allowed = {frozenset(p) for p in cfg["bonds"]["pairs"]}
    want = [(int(i), int(j)) for i, j in zip(ii, jj) if frozenset((sym[i], sym[j])) in allowed]
    assert got == want


def test_molecule_clip_keeps_whole_molecules_only():
    cfg, radii = _cfg()
    st = config.read_extxyz(committed_structures()["hero_interface"])
    idx = config.select_atoms(st, ["chain", "water"], [])
    box = [[20.0, 50.0], [10.0, 30.0]]
    kept = set(config.clip_molecules(st["symbols"], st["positions"], idx, box, radii,
                                     cfg["bonds"]["factor"], cfg["bonds"]["pairs"]))
    comp = st["component"]
    for c in {comp[i] for i in idx if comp[i].startswith("chain")}:
        members = {i for i in idx if comp[i] == c}
        assert members <= kept or not (members & kept), c  # a chain is drawn whole or not at all
    water_o = [i for i in kept if comp[i] == "water" and st["symbols"][i] == "O"]
    water_h = [i for i in kept if comp[i] == "water" and st["symbols"][i] == "H"]
    assert len(water_h) == 2 * len(water_o)


def test_fade_gives_a_thin_shell():
    cfg, radii = _cfg()
    st = config.read_extxyz(committed_structures()["hero_interface"])
    idx = config.select_atoms(st, ["water"], [])
    ref = config.select_atoms(st, ["slab", "chain", "nucleus"], [])
    fade = {"reference": [], "near": 2.5, "far": 7.0, "alpha": 0.2}
    keep, alpha = config.fade_alpha(st["symbols"], st["positions"], idx, ref, fade, radii,
                                    cfg["bonds"]["factor"], cfg["bonds"]["pairs"])
    assert 0 < len(keep) < len(idx)  # far water is not drawn
    assert max(alpha) == pytest.approx(0.2) and min(alpha) >= config.MIN_ALPHA
    d = config.min_distances(st["positions"][keep], st["positions"][ref])
    assert d.max() < fade["far"] + 1.0  # O within far; its H at most a bond further
    for i, a in zip(keep, alpha):
        if st["symbols"][i] == "O":
            dd = config.min_distances(st["positions"][[i]], st["positions"][ref])[0]
            expect = 0.2 * np.clip((7.0 - dd) / 4.5, 0, 1)
            assert a >= expect - 1e-9  # the molecule's nearest atom sets it (H may be nearer)
            break


@pytest.mark.parametrize("bad", [
    {"camera": {"dof": {"focus": "nucleus"}}},
    {"camera": {"dof": {"focus": "nucleus", "fstop": 0}}},
    {"components": [{"file": "x.extxyz", "style": "ball_and_stick", "fade": {"near": 1, "far": 2}}]},
    {"components": [{"file": "x.extxyz", "style": "ball_and_stick",
                     "fade": {"reference": [], "near": 3, "far": 2, "alpha": 0.5}}]},
    {"components": [{"file": "x.extxyz", "style": "ball_and_stick", "bond_radius": 0.9}]},
    {"components": [{"file": "x.extxyz", "style": "ball_and_stick",
                     "clip": {"box": [[0, 1], [0, 1]], "molecules": False}}]},
    {"drawing_choices": ["a list"]},
])
def test_invalid_day3_options_are_refused(tmp_path, bad):
    with pytest.raises(config.ConfigError):
        config.parse_scene(_write(tmp_path, _scene(**bad)))


def test_rig_has_nucleus_rim_ground_shadow_and_depth_cue():
    r = rig.RIG
    assert r["nucleus_rim"]["linked"] is True  # lights the nucleus only
    assert 90.0 < r["nucleus_rim"]["azimuth"] < 270.0  # behind the subject
    assert r["nucleus_rim"]["irradiance"] < r["key"]["irradiance"]  # subtle
    assert r["ground"]["shadow_catcher"] is True
    assert rig.depth_cue_factor(0.0) == 0.0 and rig.depth_cue_factor(r["depth_cue"]["start"]) == 0.0
    assert rig.depth_cue_factor(1.0) == pytest.approx(r["depth_cue"]["strength"])
    assert r["depth_cue"]["strength"] < 1.0
    src = (BLENDER_DIR / "rig.py").read_text()
    for needle in ("light_linking.receiver_collection", "is_shadow_catcher", "View Z Depth"):
        assert needle in src, needle
    for word in ("Nucleus rim", "Ground shadow", "Depth cue"):
        assert word in rig.__doc__, word


FIG_SCENES = ("hero_a", "hero_b", "hero_c", "fig2_a", "fig2_b", "fig2_c", "fig2_d")


def test_figure_scenes_use_one_representation():
    for name in FIG_SCENES:
        s = config.parse_scene(name)
        assert {c["style"] for c in s["components"]} == {"ball_and_stick"}, name
        assert s["drawing_choices"], name


def test_figure_render_logs_cite_sourced_geometry_and_hold_no_text():
    for name, sub in [("hero_a", "hero/compare"), ("hero_b", "hero/compare"), ("hero_c", "hero/compare"),
                      ("fig2_a", "fig2"), ("fig2_b", "fig2"), ("fig2_c", "fig2"), ("fig2_d", "fig2")]:
        log = json.loads((RENDER_DIR / sub / f"{name}.json").read_text())
        png = RENDER_DIR / sub / f"{name}.png"
        assert log["text_objects"] == 0, name
        assert log["counts"]["cross_component_bonds"] > 0, name  # anchors and Ca shells are drawn
        assert log["styles_used"] == ["ball_and_stick"], name
        assert log["drawing_choices"] == config.parse_scene(name)["drawing_choices"], name
        w, h, *_ = _png_header(png)
        assert [w, h] == log["render"]["resolution"], name
        if name.startswith("hero"):
            assert png.stat().st_size <= 2_000_000, name  # 2 MB, decimal
        else:
            assert w == 800, name
        for item in log["inputs"]:
            assert item["drawing_choices"], (name, item["file"])
            if "Ca" in log["counts"]["elements"] and "fig2a" not in item["file"]:
                rows = {v["cn"] for v in item["evidence_row_ids"].values()}
                assert rows == {"TE-072"}, name
            if name in ("hero_a", "hero_b", "hero_c", "fig2_c", "fig2_d"):
                assert item["params_keys"]["acc"]["keys"]["r_co"] == "c_o_bond_length_acc", name


def _blender():
    import os
    import shutil

    exe = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
    return exe if os.path.exists(exe) else shutil.which("blender")


def _free_memory_pct():
    import re
    import subprocess

    try:
        out = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+)%\s*$", out.strip())
    return int(m.group(1)) if m else None


def test_render_is_reproducible(tmp_path):
    """Two renders of one small scene with the fixed seed and settings: identical bytes on the
    same platform; elsewhere (another build of the renderer) the pixels agree to a tolerance."""
    import platform
    import subprocess

    exe = _blender()
    if exe is None:
        pytest.skip("no Blender on this machine (renders are made on the Mac)")
    free = _free_memory_pct()
    if free is not None and free < 25:
        pytest.skip(f"memory rule R10: {free}% free, below 25%")
    scene = tmp_path / "repro.yaml"
    scene.write_text(yaml.safe_dump({
        "name": "repro", "resolution": [96, 72], "samples": 4,
        "components": [{"file": "structures/preprint/ca_hydrated.extxyz", "style": "ball_and_stick"}]}))
    outs = []
    for k in range(2):
        out = tmp_path / f"r{k}.png"
        subprocess.run([exe, "-b", "--threads", "4", "-P", str(BLENDER_DIR / "scene.py"), "--",
                        "--scene", str(scene), "--out", str(out)], check=True, capture_output=True,
                       timeout=600)
        outs.append(out)
    ref = json.loads((REPO / "structures" / "preprint" / "reference_platform.json").read_text())
    same = ref == {"system": platform.system(), "machine": platform.machine()}
    if same:
        assert config.sha256(outs[0]) == config.sha256(outs[1])
    else:
        from PIL import Image

        a, b = (np.asarray(Image.open(o).convert("RGBA"), dtype=float) for o in outs)
        assert np.abs(a - b).mean() < 1.0


def test_anchor_and_ca_bonds_cross_components():
    cfg, radii = _cfg()
    s = config.parse_scene("hero_a")
    atoms, comp_of = [], []
    for k, comp in enumerate(s["components"]):
        st = config.read_extxyz(config.repo_path(comp["file"]))
        a, _ = config.select_component(st, comp, cfg, radii)
        atoms += a
        comp_of += [k] * len(a)
    cross = config.cross_component_bonds(atoms, comp_of, radii, cfg["bonds"]["factor"])
    kinds = {frozenset((atoms[i][5].rstrip("0123456789").split("_")[0], atoms[j][5].rstrip("0123456789").split("_")[0]))
             for i, j in cross}
    for want in (("chain", "slab"), ("bound", "chain"), ("bridge", "chain"), ("bridge", "nucleus")):
        assert frozenset(want) in kinds, want
    assert all(atoms[i][3] == 1.0 and atoms[j][3] == 1.0 for i, j in cross)  # never to faded water
