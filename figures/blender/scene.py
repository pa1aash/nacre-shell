"""Render one scene headlessly.

    blender -b --threads 4 -P figures/blender/scene.py -- --scene <name> --out <path.png>

Loads the extxyz files named in figures/blender/scenes/<name>.yaml, draws them
ball-and-stick or space-filling, lights them with the rig in rig.py, frames them with an
orthographic camera and writes a transparent PNG plus a settings log (<out>.json).
No text, labels or arrows are ever created (R7); the colour key belongs in the caption.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _ensure_yaml():
    """The Blender interpreter ships without PyYAML; borrow the pure-Python package from .venv.

    Only `yaml` is imported from there, and the path is removed again afterwards. The
    compiled accelerator in .venv targets another Python version and is skipped by PyYAML.
    """
    try:
        import yaml  # noqa: F401
        return "bundled"
    except ImportError:
        pass
    sites = sorted((REPO / ".venv" / "lib").glob("python3*/site-packages"))
    if not sites:
        raise SystemExit("PyYAML not found: run uv sync in the repository first")
    sys.path.append(str(sites[0]))
    try:
        import yaml  # noqa: F401
    finally:
        sys.path.remove(str(sites[0]))
    return f"pure-python from {sites[0].relative_to(REPO)}"


YAML_SOURCE = _ensure_yaml()
sys.path.insert(0, str(HERE))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix  # noqa: E402

import config  # noqa: E402
import geometry  # noqa: E402
import rig  # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="scene.py")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--out", required=True)
    return ap.parse_args(argv)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def make_material(name, rgb_linear, mcfg):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb_linear, 1.0)
    bsdf.inputs["Roughness"].default_value = mcfg["roughness"]
    bsdf.inputs["Specular IOR Level"].default_value = mcfg["specular_ior_level"]
    return mat


def add_mesh(scene, name, verts, faces, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def collect(scene_cfg, rcfg, radii):
    """Atoms to draw: list of (symbol, position, draw radius) and bonds as (sym, start, end, radius)."""
    atoms, bonds, inputs = [], [], []
    for comp in scene_cfg["components"]:
        path = config.repo_path(comp["file"])
        inputs.append({"file": comp["file"], "sha256": config.sha256(path)})
        st = config.read_extxyz(path)
        if st["info"].get("illustrative") != "T":
            raise SystemExit(f"{comp['file']}: not marked illustrative")
        idx = config.select_atoms(st, comp["include"], comp["exclude_elements"])
        sym = [st["symbols"][i] for i in idx]
        pos = st["positions"][idx] + np.array(comp["translate"])
        style = rcfg["styles"][comp["style"]]
        for s, p in zip(sym, pos):
            atoms.append((s, p, style["atom_scale"] * radii[s][style["atom_radius"]]))
        if style.get("bonds"):
            for i, j in config.find_bonds(sym, pos, radii, rcfg["bonds"]["factor"], rcfg["bonds"]["pairs"]):
                bonds.append((sym[i], pos[i], pos[j], style["bond_radius"]))
                bonds.append((sym[j], pos[j], pos[i], style["bond_radius"]))
    return atoms, bonds, inputs


_DROP_CHUNKS = {b"tEXt", b"zTXt", b"iTXt", b"tIME", b"eXIf"}


def strip_png_metadata(path):
    """Drop text, time and EXIF chunks (render timings) so equal pixels give equal bytes.

    Image data chunks are copied unchanged; nothing is re-encoded.
    """
    import struct
    import zlib

    data = Path(path).read_bytes()
    sig, pos, out, dropped = data[:8], 8, [data[:8]], []
    if sig != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"{path}: not a PNG")
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        ctype = data[pos + 4 : pos + 8]
        end = pos + 12 + length
        chunk = data[pos:end]
        if zlib.crc32(chunk[4:-4]) != struct.unpack(">I", chunk[-4:])[0]:
            raise SystemExit(f"{path}: bad CRC in {ctype!r}")
        if ctype in _DROP_CHUNKS:
            dropped.append(ctype.decode())
        else:
            out.append(chunk)
        pos = end
    Path(path).write_bytes(b"".join(out))
    return dropped


def main():
    args = parse_args()
    t0 = time.time()
    rcfg = config.load_render_config()
    scfg = config.parse_scene(args.scene)
    palette_path = config.repo_path(rcfg["palette"])
    colours, _ = config.load_palette(palette_path)
    radii = config.load_radii(config.repo_path(rcfg["elements"]))

    scene = reset_scene()
    atoms, bonds, inputs = collect(scfg, rcfg, radii)
    if not atoms:
        raise SystemExit("scene has no atoms")
    elements = sorted({a[0] for a in atoms})
    missing = [e for e in elements if e not in colours]
    if missing:
        raise SystemExit(f"palette has no colour for {missing}")
    mats = {e: make_material(f"el_{e}", colours[e], rcfg["material"]) for e in elements}

    m = rcfg["mesh"]
    sphere = geometry.uv_sphere(m["sphere_segments"], m["sphere_rings"])
    cyl = geometry.cylinder(m["bond_segments"])
    for e in elements:
        sel = [a for a in atoms if a[0] == e]
        v, f = geometry.merge_instances(sphere, geometry.atom_transforms([a[1] for a in sel], [a[2] for a in sel]))
        add_mesh(scene, f"atoms_{e}", v, f, mats[e])
        bsel = [b for b in bonds if b[0] == e]
        if bsel:
            tr = geometry.half_bond_transforms([b[1] for b in bsel], [b[2] for b in bsel], bsel[0][3])
            v, f = geometry.merge_instances(cyl, tr)
            add_mesh(scene, f"bonds_{e}", v, f, mats[e])

    # Orthographic camera framed on the projected extent of all spheres.
    cam_cfg = scfg["camera"]
    d, right, up = geometry.camera_axes(cam_cfg["direction"], cam_cfg["up"])
    pts = np.array([a[1] for a in atoms])
    rad = np.array([a[2] for a in atoms])
    cr, cu, w, h = geometry.projected_extent(pts, rad, right, up)
    depth = pts @ d
    centre = cr * right + cu * up + 0.5 * (depth.min() + depth.max()) * d
    extent = float(max(w, h, depth.max() - depth.min()))
    res = scfg["resolution"]
    cam_data = bpy.data.cameras.new("camera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = geometry.ortho_scale(w, h, res, cam_cfg["margin"])
    cam_data.clip_start = 0.01
    cam_data.clip_end = 10.0 * extent + 100.0
    cam = bpy.data.objects.new("camera", cam_data)
    cam.location = tuple(centre - (2.0 * extent + 10.0) * d)
    cam.rotation_euler = Matrix(np.stack([right, up, -d], axis=1).tolist()).to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam

    rig.build(scene, centre.tolist(), extent, d.tolist(), right.tolist(), up.tolist())

    eng = rcfg["engine"]
    samples = scfg["samples"] or eng["samples"]
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.seed = eng["seed"]
    scene.cycles.use_animated_seed = False
    scene.cycles.use_adaptive_sampling = eng["adaptive_sampling"]
    scene.cycles.use_denoising = eng["denoise"]
    scene.cycles.denoiser = eng["denoiser"]
    scene.cycles.max_bounces = eng["max_bounces"]
    scene.render.threads_mode = "FIXED"
    scene.render.threads = eng["threads"]
    scene.render.film_transparent = rcfg["film_transparent"]
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    cm = rcfg["colour_management"]
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = cm["view_transform"]
    scene.view_settings.look = cm["look"]
    scene.view_settings.exposure = cm["exposure"]
    scene.view_settings.gamma = cm["gamma"]
    out = rcfg["output"]
    img = scene.render.image_settings
    img.file_format = out["format"]
    img.color_mode = out["color_mode"]
    img.color_depth = out["color_depth"]
    img.compression = out["compression"]
    # No burnt-in stamp and no metadata fields (date, file, render time) in the PNG.
    for attr in dir(scene.render):
        if attr.startswith("use_stamp"):
            try:
                setattr(scene.render, attr, False)
            except (AttributeError, TypeError):
                pass

    # R7 guard: nothing but meshes, the camera and the rig lights.
    kinds = {o.type for o in scene.objects}
    if kinds - {"MESH", "CAMERA", "LIGHT"}:
        raise SystemExit(f"unexpected object types {kinds}")

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out_path)
    t_build = time.time() - t0
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    t_render = time.time() - t1
    dropped = strip_png_metadata(out_path)

    pal_bytes = palette_path.read_bytes()
    log = {
        "scene": scfg["name"],
        "scene_config": str(Path(scfg["path"]).relative_to(REPO)),
        "scene_config_sha256": config.sha256(scfg["path"]),
        "output": str(out_path.relative_to(REPO)) if out_path.is_relative_to(REPO) else str(out_path),
        "output_bytes": out_path.stat().st_size,
        "output_sha256": config.sha256(out_path),
        "png_chunks_dropped": sorted(set(dropped)),
        "blender_version": bpy.app.version_string,
        "python": platform.python_version(),
        "yaml_source": YAML_SOURCE,
        "inputs": inputs,
        "palette": {
            "path": rcfg["palette"],
            "git_blob": config.git_blob_sha(pal_bytes),
            "sha256": config.sha256(palette_path),
            "colour_space": "linear RGB (palette elements.<El>.linear_rgb) as Principled base colour",
            "colours_used": {e: list(colours[e]) for e in elements},
        },
        "elements_table_sha256": config.sha256(config.repo_path(rcfg["elements"])),
        "render": {
            "engine": "CYCLES", "device": "CPU", "samples": samples, "seed": eng["seed"],
            "threads": eng["threads"], "adaptive_sampling": eng["adaptive_sampling"],
            "denoise": eng["denoise"], "denoiser": eng["denoiser"], "max_bounces": eng["max_bounces"],
            "resolution": res, "film_transparent": rcfg["film_transparent"],
            "colour_management": cm, "output": out,
        },
        "camera": {"type": "ORTHO", "direction": cam_cfg["direction"], "up": cam_cfg["up"],
                   "margin": cam_cfg["margin"], "ortho_scale": round(cam_data.ortho_scale, 4)},
        "rig": rig.describe(),
        "counts": {"atoms": len(atoms), "half_bonds": len(bonds), "elements": elements},
        "timing_s": {"build": round(t_build, 2), "render": round(t_render, 2)},
        "text_objects": 0,
    }
    out_path.with_suffix(".json").write_text(json.dumps(log, indent=1, sort_keys=True) + "\n")
    print(f"RENDERED {out_path} in {t_render:.1f} s")


if __name__ == "__main__":
    main()
