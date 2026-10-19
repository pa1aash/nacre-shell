"""Render one scene headlessly.

    blender -b --threads 4 -P figures/blender/scene.py -- --scene <name> --out <path.png>

Loads the extxyz files named in figures/blender/scenes/<name>.yaml, draws them
ball-and-stick or space-filling, lights them with the rig in rig.py, frames them with an
orthographic camera (with depth of field if the scene asks for it) and writes a
transparent PNG plus a settings log (<out>.json). Faded components (the water shell)
carry a per-vertex ``alpha`` attribute that drives the material's opacity; every other
mesh has alpha 1.
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


def make_material(name, rgb_linear, mcfg, depth_range):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb_linear, 1.0)
    bsdf.inputs["Roughness"].default_value = mcfg["roughness"]
    bsdf.inputs["Specular IOR Level"].default_value = mcfg["specular_ior_level"]
    # Opacity from the per-vertex alpha attribute (1 everywhere except the faded water shell).
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "alpha"
    nt.links.new(attr.outputs["Fac"], bsdf.inputs["Alpha"])
    return rig.shade(mat, depth_range)


def add_mesh(collection, name, verts, faces, mat, alpha_per_vertex):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    att = mesh.attributes.new("alpha", "FLOAT", "POINT")
    att.data.foreach_set("value", [float(a) for a in alpha_per_vertex])
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def collect(scene_cfg, rcfg, radii):
    """Atoms to draw as (symbol, position, radius, alpha, focus) and half bonds as
    (symbol, start, end, radius, alpha, focus); see config.select_component."""
    atoms, bonds, inputs, comp_of = [], [], [], []
    for k, comp in enumerate(scene_cfg["components"]):
        path = config.repo_path(comp["file"])
        st = config.read_extxyz(path)
        inputs.append({"file": comp["file"], "sha256": config.sha256(path),
                       "evidence_row_ids": config.evidence_row_ids(st),
                       "params_keys": config.params_keys(st),
                       "drawing_choices": config.structure_drawing_choices(st)})
        if st["info"].get("illustrative") != "T":
            raise SystemExit(f"{comp['file']}: not marked illustrative")
        a, b = config.select_component(st, comp, rcfg, radii)
        comp_of += [k] * len(a)
        atoms += a
        bonds += b
    # Bonds across components: catechol O-Al anchors, Ca2+ to its sites and to the nucleus.
    br = rcfg["styles"]["ball_and_stick"]["bond_radius"]
    cross = config.cross_component_bonds(atoms, comp_of, radii, rcfg["bonds"]["factor"])
    for i, j in cross:
        for a, b in ((i, j), (j, i)):
            bonds.append((atoms[a][0], atoms[a][1], atoms[b][1], br, 1.0, atoms[a][4]))
    return atoms, bonds, inputs, len(cross)


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
    atoms, bonds, inputs, n_cross = collect(scfg, rcfg, radii)
    if not atoms:
        raise SystemExit("scene has no atoms")
    elements = sorted({a[0] for a in atoms})
    missing = [e for e in elements if e not in colours]
    if missing:
        raise SystemExit(f"palette has no colour for {missing}")

    # Orthographic camera framed on the projected extent of all spheres.
    cam_cfg = scfg["camera"]
    d, right, up = geometry.camera_axes(cam_cfg["direction"], cam_cfg["up"])
    pts = np.array([a[1] for a in atoms])
    rad = np.array([a[2] for a in atoms])
    cr, cu, w, h = geometry.projected_extent(pts, rad, right, up)
    depth = pts @ d
    centre = cr * right + cu * up + 0.5 * (depth.min() + depth.max()) * d
    extent = float(max(w, h, depth.max() - depth.min()))
    cam_back = 2.0 * extent + 10.0
    cam_loc = centre - cam_back * d
    # Camera-space depth range of the subject, for the rig's depth cue.
    cam_depth = (pts - cam_loc) @ d
    depth_range = (float(cam_depth.min()), float(cam_depth.max()))
    mats = {e: make_material(f"el_{e}", colours[e], rcfg["material"], depth_range) for e in elements}

    m = rcfg["mesh"]
    sphere = geometry.uv_sphere(m["sphere_segments"], m["sphere_rings"])
    cyl = geometry.cylinder(m["bond_segments"])
    focus_coll = bpy.data.collections.new("focus")
    scene.collection.children.link(focus_coll)
    for e in elements:
        for focus in (False, True):
            coll = focus_coll if focus else scene.collection
            tag = "focus_" if focus else ""
            sel = [a for a in atoms if a[0] == e and a[4] == focus]
            if sel:
                v, f = geometry.merge_instances(sphere, geometry.atom_transforms([a[1] for a in sel],
                                                                                 [a[2] for a in sel]))
                add_mesh(coll, f"{tag}atoms_{e}", v, f, mats[e], np.repeat([a[3] for a in sel], len(sphere[0])))
            bsel = [b for b in bonds if b[0] == e and b[5] == focus]
            if bsel:
                tr = geometry.half_bond_transforms([b[1] for b in bsel], [b[2] for b in bsel],
                                                   [b[3] for b in bsel])
                v, f = geometry.merge_instances(cyl, tr)
                add_mesh(coll, f"{tag}bonds_{e}", v, f, mats[e], np.repeat([b[4] for b in bsel], len(cyl[0])))
    res = scfg["resolution"]
    cam_data = bpy.data.cameras.new("camera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = geometry.ortho_scale(w, h, res, cam_cfg["margin"])
    cam_data.clip_start = 0.01
    cam_data.clip_end = 10.0 * extent + 100.0
    dof = cam_cfg["dof"]
    dof_log = None
    if dof is not None:
        sel = np.array([a[1] for a in atoms if a[5].startswith(dof["focus"])])
        if not len(sel):
            raise SystemExit(f"dof focus {dof['focus']!r} names no drawn atoms")
        cam_data.dof.use_dof = True
        cam_data.dof.focus_distance = float((sel.mean(axis=0) - cam_loc) @ d)
        cam_data.dof.aperture_fstop = dof["fstop"]
        dof_log = {"focus": dof["focus"], "fstop": dof["fstop"],
                   "focus_distance": round(cam_data.dof.focus_distance, 4)}
    cam = bpy.data.objects.new("camera", cam_data)
    cam.location = tuple(cam_loc)
    cam.rotation_euler = Matrix(np.stack([right, up, -d], axis=1).tolist()).to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam

    focus_atoms = [a for a in atoms if a[4]]
    focus = None
    if focus_atoms:
        fp = np.array([a[1] for a in focus_atoms])
        focus = {"collection": focus_coll, "centre": fp.mean(axis=0).tolist(),
                 "extent": float(np.ptp(fp, axis=0).max())}
    rig.build(scene, centre.tolist(), extent, d.tolist(), right.tolist(), up.tolist(),
              ground_z=float((pts[:, 2] - rad).min()), focus=focus)

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
    scene.cycles.transparent_max_bounces = eng["transparent_max_bounces"]
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
    # Anything that is not a mesh, the camera or a light could carry text; the guard above refuses
    # it, and the log records the count (always 0).
    n_text = sum(1 for o in scene.objects if o.type not in {"MESH", "CAMERA", "LIGHT"})

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
        "scene_config": (str(Path(scfg["path"]).resolve().relative_to(REPO))
                         if Path(scfg["path"]).resolve().is_relative_to(REPO) else Path(scfg["path"]).name),
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
            "transparent_max_bounces": eng["transparent_max_bounces"],
            "resolution": res, "film_transparent": rcfg["film_transparent"],
            "colour_management": cm, "output": out,
        },
        "camera": {"type": "ORTHO", "direction": cam_cfg["direction"], "up": cam_cfg["up"],
                   "margin": cam_cfg["margin"], "ortho_scale": round(cam_data.ortho_scale, 4),
                   "dof": dof_log},
        "drawing_choices": scfg["drawing_choices"],
        "styles_used": sorted({c["style"] for c in scfg["components"]}),
        "atom_scale": {k: rcfg["styles"][k]["atom_scale"] for k in sorted({c["style"] for c in scfg["components"]})},
        "rig": rig.describe(),
        "counts": {"atoms": len(atoms), "half_bonds": len(bonds), "elements": elements,
                   "translucent_atoms": sum(1 for a in atoms if a[3] < 1.0),
                   "cross_component_bonds": n_cross,
                   "focus_atoms": len(focus_atoms)},
        "text_objects": n_text,
    }
    out_path.with_suffix(".json").write_text(json.dumps(log, indent=1, sort_keys=True) + "\n")
    # Timings depend on the machine and its load: they go to the run record, not the settings log.
    print(f"RENDERED {out_path.name} scene build {t_build:.1f} s, render {t_render:.1f} s")


if __name__ == "__main__":
    main()
