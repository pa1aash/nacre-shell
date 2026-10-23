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
    assert pal["carbonate"] == list(fills["suitable against dissolution"])
    assert pal["phosphate"] == list(fills["open"])
    problems, dmin = rendered.palette_problems(pal, REPO)
    assert problems == [] and dmin >= float(style.palette(REPO)["delta_e_min"])


def test_scene_script_builds_no_text_and_one_solid_phase_per_panel():
    src = (REPO / "figures/src/blender/hero.py").read_text()
    assert not re.search(r"text_add|font_curve|\.body\s*=", src)
    assert '"FONT" in types' in src  # the scene itself is checked, not only the source
    a, b = src.index('if panel == "a"'), src.index("else:", src.index('if panel == "a"'))
    assert "carbonate" in src[a:b] and "phosphate" not in src[a:b]
    assert "phosphate" in src[b:src.index("body = box")] and "carbonate" not in src[b:src.index("body = box")]


def test_hero_caption_states_the_rulings():
    text = (REPO / "figures/src/captions/fig1.md").read_text()
    draft = re.search(r"^## Draft\n(.*?)(?=^## )", text, re.S | re.M).group(1).lower()
    for must in ("illustrative construction", "not tested by the screen", "open candidate", "not a result",
                 "thermodynamically excluded at high voltage"):
        assert must in draft, must


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
