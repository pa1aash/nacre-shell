"""Rendered (raster) figures: a headless Blender scene composed into one RSC-width PNG and a PDF wrapper.

figures/src/blender/renders.yaml registers each figure: a Blender script that renders one PNG per
panel, the composite layout and the render settings. Colours are the stability-map palette
(nacre.figs.regimes fills and the palette gray), exported to a JSON file the script reads.

A render is not built by a plain `nacre figs`; it is built on request (`--only fig1`) because it
takes about an hour on one CPU thread. The build renders the whole figure twice, compares the
composite sha256 and records the result: byte-identical, or "render not byte-reproducible; asset
hash pinned" (the committed PNG is then the asset and the manifest pins its hash).

The checks are the narrowest rule for a raster figure (checker.check_raster, check_pdf_schematic
for the wrapper): an 8-bit RGB PNG without alpha or text chunks at exactly the RSC column width at
the raster resolution, a one-page wrapper without text or fonts, and a scene that holds no text
or annotation object (recorded by the Blender script). Colour-vision simulations are written as
for every other raster figure.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import yaml

from nacre.figs import checker, colours, paths, regimes, style


class RenderError(Exception):
    pass


def table(root):
    f = paths(root)["src"] / "blender" / "renders.yaml"
    return yaml.safe_load(f.read_text())["renders"] if f.exists() else {}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def blender_exe():
    for c in (os.environ.get("BLENDER"), shutil.which("blender"), "/Applications/Blender.app/Contents/MacOS/Blender"):
        if c and Path(c).exists():
            return c
    raise RenderError("Blender not found (set BLENDER or install it: brew install --cask blender)")


def blender_version(exe):
    out = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.splitlines()
    return out[0].strip() if out else "unknown"


def palette(entry, root=None):
    """Scene colours (sRGB) from the stability-map palette: the regime fills for the carbonate
    ('suitable against dissolution') and the phosphate ('open'), the palette gray for the foil, and a
    tint of the 'undetermined' fill for the liquid. The element colour of Al is not used: it sits
    9.6 CAM02-UCS units from the phosphate fill, below delta_e_min."""
    fills = regimes.fills(root)
    pal = style.palette(root)
    return {
        "foil": [float(x) for x in pal["categorical"]["okabe_ito"]["gray"]["srgb"]],
        "carbonate": [float(x) for x in fills["suitable against dissolution"]],
        "phosphate": [float(x) for x in fills["open"]],
        "liquid": [float(x) for x in colours.lighten(fills["undetermined"], entry["liquid_lighten"])],
    }


def palette_problems(pal, root=None):
    """The three solids must clear palette delta_e_min against each other under every vision
    condition (the liquid is a tint over the scene and is not a separate class)."""
    need = float(style.palette(root)["delta_e_min"])
    got = colours.min_delta_e([pal["foil"], pal["carbonate"], pal["phosphate"]])
    return [] if got >= need else ["scene solids: smallest CAM02-UCS distance %.1f < %.1f" % (got, need)], got


def _wait_for_memory(log, limit_min=60):
    def free():
        out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout.strip().splitlines()
        m = re.search(r"(\d+)%", out[-1]) if out else None
        return int(m.group(1)) if m else 100
    waited = 0
    while free() < 25:
        if waited >= limit_min:
            raise RenderError("memory free below 25% after %d min" % waited)
        log("memory free %d%% < 25%%; waiting 5 min" % free())
        time.sleep(300)
        waited += 5


def render_panels(root, entry, pal_file, out_dir, exe, scale=1.0, samples=None, log=print):
    """Run the Blender script, one process per panel, concurrently, one CPU thread each."""
    dpi = int(style.applied(root)["raster_dpi"]["value"])
    width_px = int(round(style.width_in(entry["width"], root) * dpi))
    n = len(entry["panels"])
    panel_w = (width_px - entry["gutter_px"] * (n - 1)) // n
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    procs = []
    for panel in entry["panels"]:
        cmd = [exe, "-b", "-P", str(Path(root) / entry["script"]), "--", "--palette", str(pal_file),
               "--out-dir", str(out_dir), "--seed", str(entry["seed"]), "--samples", str(samples or entry["samples"]),
               "--width-px", str(panel_w), "--height-px", str(entry["height_px"]), "--scale", str(scale), "--panel", panel]
        logf = open(out_dir / ("blender_%s.log" % panel), "w")
        procs.append((panel, subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT), logf))
    for panel, p, logf in procs:
        rc = p.wait()
        logf.close()
        if rc != 0 or not (out_dir / ("hero_%s.png" % panel)).exists():
            raise RenderError("%s: Blender failed for panel %s (exit %s), see %s" % (entry["script"], panel, rc, out_dir))
    scene = {}
    for panel in entry["panels"]:
        scene[panel] = json.loads((out_dir / ("hero_scene_%s.json" % panel)).read_text())
    return scene, panel_w


def compose(panel_files, gutter_px, dpi, out_png):
    """Panels side by side on white, with a white gutter, as 8-bit RGB without metadata but the dpi."""
    from PIL import Image
    ims = [Image.open(f).convert("RGB") for f in panel_files]
    h = max(i.height for i in ims)
    w = sum(i.width for i in ims) + gutter_px * (len(ims) - 1)
    sheet = Image.new("RGB", (w, h), (255, 255, 255))
    x = 0
    for im in ims:
        sheet.paste(im, (x, 0))
        x += im.width + gutter_px
    sheet.save(out_png, dpi=(dpi, dpi), optimize=False, compress_level=9)
    return sheet.size


def wrap_pdf(png, pdf):
    """A one-page PDF holding the PNG, page size exactly the image size at its dpi; no text, no dates."""
    import pymupdf
    from PIL import Image
    im = Image.open(png)
    dpi = im.info["dpi"][0]
    w_pt, h_pt = im.width / dpi * 72.0, im.height / dpi * 72.0
    doc = pymupdf.open()
    page = doc.new_page(width=w_pt, height=h_pt)
    page.insert_image(page.rect, filename=str(png))
    doc.set_metadata({})
    doc.save(str(pdf), garbage=4, deflate=True, no_new_id=True)
    doc.close()


def check(root, png, pdf, scene):
    dpi = int(style.applied(root)["raster_dpi"]["value"])
    problems = checker.check_raster(png, dpi, (style.width_in("single", root), style.width_in("double", root)),
                                    style.max_height_in(root))
    pt = 72.0
    problems += checker.check_pdf_schematic(
        pdf, min_line_pt=style.min_line_pt(root),
        widths_pt=(style.width_in("single", root) * pt, style.width_in("double", root) * pt),
        max_height_pt=style.max_height_in(root) * pt, text_free=True)
    for panel, meta in sorted(scene.items()):
        bad = sorted(set(meta["panels"][panel]) & {"FONT", "GPENCIL", "GREASEPENCIL"})
        if bad:
            problems.append("panel %s: scene holds %s objects" % (panel, ", ".join(bad)))
    return problems


def build(root, only=None, cvd=True, log=print, scale=1.0, samples=None, repeat=2):
    """Build the registered renders named in `only`. Returns (records, failures); never runs unless named."""
    root = Path(root)
    records, failures = {}, []
    wanted = [k for k in table(root) if only and k in only]
    if not wanted:
        return records, failures
    out = paths(root)["out"]
    dpi = int(style.applied(root)["raster_dpi"]["value"])
    exe = blender_exe()
    for fid in wanted:
        entry = table(root)[fid]
        scratch = None
        try:
            pal = palette(entry, root)
            problems, dmin = palette_problems(pal, root)
            if problems:
                raise RenderError("%s: %s" % (fid, "; ".join(problems)))
            scratch = Path(tempfile.mkdtemp(prefix="nacre-render-"))
            pal_file = scratch / "palette.json"
            pal_file.write_text(json.dumps(pal, sort_keys=True))
            composites = []
            for run in range(repeat):
                _wait_for_memory(log)
                rdir = scratch / ("run%d" % run)
                log("%s: render %d of %d (Blender, one thread per panel)" % (fid, run + 1, repeat))
                scene, _pw = render_panels(root, entry, pal_file, rdir, exe, scale=scale, samples=samples, log=log)
                png = rdir / (fid + ".png")
                compose([rdir / ("hero_%s.png" % p) for p in entry["panels"]], entry["gutter_px"], dpi, png)
                composites.append(png)
            hashes = [_sha(p) for p in composites]
            identical = len(set(hashes)) == 1
            png, pdf = out / (fid + ".png"), out / (fid + ".pdf")
            out.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(composites[0], png)
            wrap_pdf(png, pdf)
            problems = check(root, png, pdf, scene)
            if problems:
                raise checker.FigureCheckError(["%s: %s" % (fid, x) for x in problems])
            outs = [png, pdf]
            if cvd:
                from nacre.figs import cvd as cvdmod
                cdir = out / "cvd"
                cdir.mkdir(exist_ok=True)
                outs += cvdmod.simulate_png(png, cdir, fid, dpi)
            from PIL import Image
            w_px, h_px = Image.open(png).size
            any_scene = next(iter(scene.values()))
            records[fid] = {
                "id": fid, "kind": "render",
                "claim": entry["claim"], "caption_key": entry["caption_key"], "mock": False, "width": entry["width"],
                "size_cm": [round(w_px / dpi * style.CM_PER_IN, 2), round(h_px / dpi * style.CM_PER_IN, 2)],
                "blender": {"version": blender_version(exe), "scene": any_scene["blender"]},
                "script": entry["script"], "script_sha256": _sha(root / entry["script"]),
                "seed": entry["seed"], "samples": samples or entry["samples"], "engine": any_scene["engine"],
                "device": any_scene["device"], "threads": any_scene["threads"], "denoise": any_scene["denoise"],
                "palette": {k: [round(x, 4) for x in v] for k, v in sorted(pal.items())},
                "palette_sha256": hashlib.sha256(json.dumps(pal, sort_keys=True).encode()).hexdigest(),
                "palette_min_delta_e_solids": round(dmin, 1),
                "scene_objects": {p: m["panels"][p] for p, m in sorted(scene.items())},
                "renders": repeat, "render_hashes": hashes, "render_hashes_identical": identical,
                "reproducibility": ("byte-identical across %d renders" % repeat) if identical
                else "render not byte-reproducible; asset hash pinned",
                "font": "none (no text)",
                "outputs": {str(o.resolve().relative_to(root.resolve())): _sha(o) for o in outs},
                "checker": "pass (raster: size, mode, no text chunks; PDF wrapper: no text; scene: no text objects)",
            }
            log("%s: ok -> %s (%s)" % (fid, png.relative_to(root), records[fid]["reproducibility"]))
        except (RenderError, checker.FigureCheckError) as exc:
            failures.append(str(exc))
            log("%s: FAIL %s" % (fid, exc))
        finally:
            if scratch is not None:
                shutil.rmtree(scratch, ignore_errors=True)
    return records, failures
