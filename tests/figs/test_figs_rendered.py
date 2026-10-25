"""Rendered (raster) figures: the raster rule of the checker, the palette, the wrapper, the scene
determinism and the manifest record of the hero figure (fig1)."""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from figs_helpers import REPO
from PIL import Image, PngImagePlugin

from nacre.figs import checker, colours, regimes, rendered, style

DPI = 600
WIDTHS = (style.width_in("single", REPO), style.width_in("double", REPO))
MAXH = style.max_height_in(REPO)
W_DOUBLE = round(WIDTHS[1] * DPI)


def _png(path, size=(W_DOUBLE, 300), mode="RGB", dpi=(DPI, DPI), text=None):
    info = PngImagePlugin.PngInfo()
    if text:
        info.add_text("Comment", text)
    Image.new(mode, size, (255,) * len(mode)).save(path, dpi=dpi, pnginfo=info)
    return path


def test_clean_raster_passes(tmp_path):
    assert checker.check_raster(_png(tmp_path / "a.png"), DPI, WIDTHS, MAXH) == []


@pytest.mark.parametrize("kw,needle", [
    ({"mode": "RGBA"}, "alpha"),
    ({"size": (W_DOUBLE - 40, 300)}, "RSC column width"),
    ({"size": (W_DOUBLE, int((MAXH + 1) * DPI))}, "maximum"),
    ({"dpi": (300, 300)}, "dpi"),
    ({"text": "a label"}, "metadata"),
])
def test_planted_raster_problems_rejected(tmp_path, kw, needle):
    probs = checker.check_raster(_png(tmp_path / "a.png", **kw), DPI, WIDTHS, MAXH)
    assert any(needle in p for p in probs), probs


def test_wrapper_pdf_is_text_free_and_deterministic(tmp_path):
    png = _png(tmp_path / "a.png")
    for n in ("1", "2"):
        rendered.wrap_pdf(png, tmp_path / (n + ".pdf"))
    assert (tmp_path / "1.pdf").read_bytes() == (tmp_path / "2.pdf").read_bytes()
    pt = 72.0
    assert checker.check_pdf_schematic(tmp_path / "1.pdf", style.min_line_pt(REPO), (WIDTHS[1] * pt,), MAXH * pt) == []


def test_hero_is_registered_and_names_an_existing_script():
    e = rendered.table(REPO)["fig1"]
    assert (REPO / e["script"]).is_file()
    assert e["panels"] == ["a", "b"] and e["width"] == "double"
    assert 2 * 1973 + e["gutter_px"] == W_DOUBLE


def test_palette_is_the_stability_map_palette_and_the_solids_stay_distinct():
    e = rendered.table(REPO)["fig1"]
    pal = rendered.palette(e, REPO)
    fills = regimes.fills(REPO)
    elements = style.palette(REPO)["elements"]
    assert pal["carbonate"] == list(fills["suitable against dissolution"])
    assert pal["phosphate"] == list(fills["open"])
    for el in ("O", "H", "C", "Ca", "Li"):
        assert pal[el] == list(elements[el]["srgb"]), el
    assert pal["Al"] == [round(x * e["al_shade"], 4) for x in elements["Al"]["srgb"]]
    problems, dmin, dall = rendered.palette_problems(pal, REPO)
    assert problems == [] and dmin >= float(style.palette(REPO)["delta_e_min"])
    assert dall[0] <= dmin


@pytest.fixture(scope="module")
def geometry():
    from nacre.figs import hero_geometry
    e = rendered.table(REPO)["fig1"]
    return hero_geometry.build(e, REPO, e["seed"])


def test_scene_script_builds_no_text_objects():
    src = (REPO / "figures/src/blender/hero.py").read_text()
    assert not re.search(r"text_add|font_curve|\.body\s*=", src)
    assert '"FONT"' in src and "FORBIDDEN & set(types)" in src  # the scene itself is checked, not only the source


def test_one_solid_phase_per_panel(geometry):
    a = {x[0] for x in geometry["panels"]["a"]["atoms"]}
    b = {x[0] for x in geometry["panels"]["b"]["atoms"]}
    assert {"Al", "carbonate", "Ca", "O", "H"} == a
    assert {"Al", "phosphate", "Li", "Cl", "C", "O", "H"} == b


def test_geometry_is_generated_and_deterministic(geometry):
    from nacre.figs import hero_geometry
    e = rendered.table(REPO)["fig1"]
    assert hero_geometry.build(e, REPO, e["seed"]) == geometry
    for panel in ("a", "b"):
        c = geometry["counts"][panel]
        assert c["solvent"] == c["solvent_target"] > 0
    assert "TM-030" in geometry["sources"]["carbonate"]
    assert geometry["sources"]["phosphate"].startswith("schematic")


def test_slab_is_fcc111_with_the_reference_lattice_constant(geometry):
    import numpy as np
    from ase.data import atomic_numbers, reference_states
    nn = reference_states[atomic_numbers["Al"]]["a"] / 2 ** 0.5
    al = np.array([x[2:] for x in geometry["panels"]["a"]["atoms"] if x[0] == "Al"])
    top = al[np.isclose(al[:, 2], 0.0)]
    d = np.linalg.norm(top[1:] - top[0], axis=1)
    assert abs(d.min() - nn) < 1e-3


def _lengths(atoms, bonds, cls):
    import numpy as np
    return [float(np.linalg.norm(np.subtract(atoms[i][2:], atoms[j][2:]))) for i, j in bonds
            if atoms[i][0] == cls and atoms[j][0] == cls]


def test_carbonate_and_phosphate_lengths_come_from_the_committed_value(geometry):
    from nacre.figs import hero_geometry
    d_co, _src = hero_geometry.c_o_length(REPO)
    e = rendered.table(REPO)["fig1"]
    a, b = geometry["panels"]["a"], geometry["panels"]["b"]
    assert all(abs(x - d_co) < 1e-3 for x in _lengths(a["atoms"], a["bonds"], "carbonate"))
    po = _lengths(b["atoms"], b["bonds"], "phosphate")
    assert po and all(abs(x - d_co * e["geometry"]["schematic_bond_factor"]) < 1e-3 for x in po)


def test_phosphate_chain_is_corner_sharing_tetrahedra():
    import math

    import numpy as np
    from nacre.figs import hero_geometry
    c = hero_geometry.phosphate_chain(5, 1.0, 3.0)
    pos, nb = np.array(c["pos"]), {}
    for i, j in c["bonds"]:
        nb.setdefault(i, []).append(j)
        nb.setdefault(j, []).append(i)
    for i, s in enumerate(c["symbols"]):
        if s == "P":
            assert len(nb[i]) == 4
            for x in nb[i]:
                for y in nb[i]:
                    if x < y:
                        ang = math.degrees(math.acos(np.dot(pos[x] - pos[i], pos[y] - pos[i])))
                        assert abs(ang - 109.4712) < 1e-3
    bridging = [i for i, s in enumerate(c["symbols"]) if s == "O" and len(nb[i]) == 2]
    assert len(bridging) == 4


def test_hero_caption_states_the_rulings():
    text = (REPO / "figures/src/captions/fig1.md").read_text()
    draft = re.search(r"^## Draft\n(.*?)(?=^## )", text, re.S | re.M).group(1).lower()
    for must in ("illustrative construction", "not tested by the screen", "open candidate", "not a result",
                 "schematic", "without quantitative meaning", "oxide not drawn", "layering and polymorph structure",
                 "whether or how a film forms", "p–o lengths normalised"):
        assert must in draft, must
    assert "thermodynamically excluded" not in draft
    assert len(draft.split()) <= 70


@pytest.mark.skipif(not any(Path(p).exists() for p in ("/Applications/Blender.app/Contents/MacOS/Blender",))
                    and shutil.which("blender") is None, reason="Blender not installed")
def test_scene_renders_deterministically_at_low_resolution(tmp_path):
    e = rendered.table(REPO)["fig1"]
    pal = tmp_path / "p.json"
    pal.write_text(json.dumps(rendered.palette(e, REPO)))
    exe, hashes = rendered.blender_exe(), []
    for i in range(2):
        rendered.render_panels(REPO, dict(e, panels=["b"]), pal, tmp_path / ("r%d" % i), exe, scale=0.05, samples=2)
        out = tmp_path / ("c%d.png" % i)
        rendered.compose([tmp_path / ("r%d" % i) / "hero_b.png"], 0, DPI, out)
        hashes.append(hashlib.sha256(out.read_bytes()).hexdigest())
    assert hashes[0] == hashes[1]


def _record():
    return json.loads((REPO / "figures/out/manifest.json").read_text())["renders"]["fig1"]


def test_manifest_records_the_render():
    r = _record()
    assert r["blender"]["version"].startswith("Blender ") and r["seed"] == 7 and r["threads"] == 1
    assert r["engine"] == "CYCLES" and r["device"] == "CPU" and r["denoise"] is False
    assert r["script_sha256"] == hashlib.sha256((REPO / r["script"]).read_bytes()).hexdigest()
    assert r["renders"] == 2 and len(r["render_hashes"]) == 2
    assert r["render_hashes_identical"] == (len(set(r["render_hashes"])) == 1)
    if r["render_hashes_identical"]:
        assert r["reproducibility"].startswith("byte-identical")
    else:
        assert r["reproducibility"] == "render not byte-reproducible; asset hash pinned"
    assert r["palette_min_delta_e_solids"] >= float(style.palette(REPO)["delta_e_min"])
    assert not {"FONT", "GPENCIL"} & {k for m in r["scene_objects"].values() for k in m}
    assert len(r["geometry_sha256"]) == 64 and "carbonate" in r["geometry_sources"]


def test_manifest_hashes_equal_the_committed_files():
    r = _record()
    names = {Path(k).name for k in r["outputs"]}
    assert {"fig1.png", "fig1.pdf", "fig1_deuteranopia.png", "fig1_protanopia.png", "fig1_tritanopia.png"} <= names
    for rel, sha in r["outputs"].items():
        assert hashlib.sha256((REPO / rel).read_bytes()).hexdigest() == sha, rel
    if r["render_hashes_identical"]:
        assert r["outputs"]["figures/out/fig1.png"] == r["render_hashes"][0]


def test_committed_png_passes_the_raster_rule():
    assert checker.check_raster(REPO / "figures/out/fig1.png", DPI, WIDTHS, MAXH) == []
