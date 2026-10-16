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
    assert cfg["engine"]["threads"] == 4
    assert cfg["film_transparent"] is True
    assert cfg["colour_management"]["view_transform"] == "Standard"


def test_palette_is_a_single_path_value():
    cfg = config.load_render_config()
    assert isinstance(cfg["palette"], str)
    assert cfg["palette"].endswith("palette.yaml")


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
    if not path.exists():
        pytest.skip("local palette copy absent (it lives under .local/)")
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
    assert kinds.count("H-O") == 12 and kinds.count("Ca-O") == 6 and len(kinds) == 18


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
