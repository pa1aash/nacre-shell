"""Hero figure scene: two separate single-phase molecular panels, rendered headless.

  blender -b -P figures/src/blender/hero.py -- --palette p.json --geometry g.json --out-dir DIR
          [--seed 7] [--samples 128] [--width-px 1973] [--height-px 1480] [--scale 1.0] [--panel a|b]

Panel a (processing stage): an Al(111) slab under water, with dissolved Ca2+ and CO3(2-) ions.
Panel b (cell stage): the same slab with a condensed phosphate chain lying on it, under propylene
carbonate with Li+ and ClO4- ions. Atom positions come from nacre.figs.hero_geometry (generated
lattice, package molecule geometries, a committed C-O length, schematic tetrahedra); this script
only draws them ball-and-stick. Illustrative construction: no text objects, no scale, no data.
Colours come from the palette file written by nacre.figs.rendered: one colour per element, the
stability-map fills for the carbonate ion and the phosphate chain. Deterministic: Cycles on the
CPU with one thread, a fixed seed, a fixed sample count, no denoiser, no adaptive sampling.
Writes hero_<panel>.png and hero_scene_<panel>.json (engine settings and object counts).
"""
import argparse
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Vector

FORBIDDEN = {"FONT", "GPENCIL", "GREASEPENCIL"}


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--palette", required=True)
    p.add_argument("--geometry", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--samples", type=int, default=128)
    p.add_argument("--width-px", type=int, default=1973)
    p.add_argument("--height-px", type=int, default=1480)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--panel", choices=("a", "b"), required=True)
    return p.parse_args(argv)


def lin(c):
    f = lambda x: x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return [f(x) for x in c]


def material(name, srgb, rough=0.35, metallic=0.0, spec=0.5, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(srgb) + [1.0]
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Specular IOR Level"].default_value = spec
    b.inputs["Coat Weight"].default_value = coat
    return m


def _template_cylinder(segments=16):
    """Open unit cylinder along z from -0.5 to 0.5, radius 1, as triangles."""
    ang = np.arange(segments) * 2 * np.pi / segments
    ring = np.stack([np.cos(ang), np.sin(ang)], axis=1)
    verts = np.vstack([np.c_[ring, np.full(segments, -0.5)], np.c_[ring, np.full(segments, 0.5)]])
    k = np.arange(segments)
    n = (k + 1) % segments
    faces = np.vstack([np.stack([k, n, n + segments], 1), np.stack([k, n + segments, k + segments], 1)])
    return verts, faces


def _rotations_z_to(d):
    """Rotation matrices taking +z onto each unit vector in d (Rodrigues)."""
    z = np.array([0.0, 0.0, 1.0])
    out = np.empty((len(d), 3, 3))
    for i, v in enumerate(d):
        c = float(np.dot(z, v))
        if c < -1.0 + 1e-9:
            out[i] = np.diag([1.0, -1.0, -1.0])
            continue
        w = np.cross(z, v)
        k = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
        out[i] = np.eye(3) + k + k @ k / (1.0 + c)
    return out


def mesh_object(name, verts, faces, mat):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    me.loops.add(faces.size)
    me.loops.foreach_set("vertex_index", faces.astype(np.int32).ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set("loop_start", (np.arange(len(faces)) * 3).astype(np.int32))
    me.update(calc_edges=True)
    me.shade_smooth()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def points_object(name, pos, rad, mat):
    """Atoms as a point cloud: Cycles renders each point as an exact sphere."""
    pc = bpy.data.pointclouds.new(name)
    pc.resize(len(pos))
    pc.attributes["position"].data.foreach_set("vector", pos.astype(np.float32).ravel())
    if "radius" not in pc.attributes:
        pc.attributes.new("radius", "FLOAT", "POINT")
    pc.attributes["radius"].data.foreach_set("value", rad.astype(np.float32))
    pc.materials.append(mat)
    o = bpy.data.objects.new(name, pc)
    bpy.context.scene.collection.objects.link(o)
    return o


def _tile(tv, tf, transform):
    """Copies of a template mesh, one per transform (n, 3, 3 linear part; n, 3 offset)."""
    lin, off = transform
    verts = np.einsum("nij,vj->nvi", lin, tv) + off[:, None, :]
    faces = tf[None, :, :] + (np.arange(len(lin)) * len(tv))[:, None, None]
    return verts.reshape(-1, 3), faces.reshape(-1, 3)


def draw(geo, style, mats):
    """One point cloud of atoms and one merged mesh of half-bonds per colour class."""
    atoms, bonds = geo["atoms"], geo["bonds"]
    cls = np.array([a[0] for a in atoms])
    el = [a[1] for a in atoms]
    pos = np.array([a[2:] for a in atoms], dtype=float)
    rf = style["radius_factor"]
    rad = np.array([rf.get(c, rf["default"]) * style["covalent"][e] for c, e in zip(cls, el)])
    cyl = _template_cylinder()
    br = style["bond_radius"]
    b = np.array(bonds, dtype=int).reshape(-1, 2)
    starts = np.vstack([pos[b[:, 0]], pos[b[:, 1]]])
    mids = np.vstack([(pos[b[:, 0]] + pos[b[:, 1]]) / 2] * 2)
    bcls = np.concatenate([cls[b[:, 0]], cls[b[:, 1]]])
    vec = mids - starts
    length = np.linalg.norm(vec, axis=1)
    keep = length > 1e-6
    for c in sorted(set(cls)):
        points_object("atoms_" + c, pos[cls == c], rad[cls == c], mats[c])
        sel = (bcls == c) & keep
        if sel.any():
            d = vec[sel] / length[sel][:, None]
            lin = _rotations_z_to(d) @ np.einsum("n,ij->nij", np.ones(sel.sum()), np.diag([br, br, 1.0]))
            lin[:, :, 2] *= length[sel][:, None]
            v, f = _tile(cyl[0], cyl[1], (lin, (starts[sel] + mids[sel]) / 2))
            mesh_object("bonds_" + c, v, f, mats[c])


def lights(style):
    for name, loc, energy, size in style["lights"]:
        d = bpy.data.lights.new(name, "AREA")
        d.energy, d.size = energy, size
        o = bpy.data.objects.new(name, d)
        o.location = loc
        bpy.context.scene.collection.objects.link(o)
        o.rotation_euler = (Vector(style["target"]) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def camera(style):
    c = style["camera"]
    d = bpy.data.cameras.new("cam")
    d.lens, d.sensor_width = c["lens_mm"], 36.0
    d.clip_end = 1000.0
    o = bpy.data.objects.new("cam", d)
    bpy.context.scene.collection.objects.link(o)
    o.location = c["location"]
    target = Vector(style["target"])
    o.rotation_euler = (target - o.location).to_track_quat("-Z", "Y").to_euler()
    d.dof.use_dof = True
    d.dof.focus_distance = (Vector(c["focus"]) - o.location).length
    d.dof.aperture_fstop = c["fstop"]
    bpy.context.scene.camera = o


def setup(a, w, h, style):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    c = sc.cycles
    c.device, c.samples, c.seed = "CPU", a.samples, a.seed
    c.use_animated_seed, c.use_adaptive_sampling, c.use_denoising = False, False, False
    c.max_bounces, c.glossy_bounces, c.diffuse_bounces = 8, 4, 4
    c.sample_clamp_indirect = 10.0
    sc.render.threads_mode, sc.render.threads = "FIXED", 1
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.view_settings.view_transform, sc.view_settings.look = "Standard", "None"
    sc.view_settings.exposure, sc.view_settings.gamma = 0.0, 1.0
    sc.display_settings.display_device = "sRGB"
    im = sc.render.image_settings
    im.file_format, im.color_mode, im.color_depth, im.compression = "PNG", "RGB", "8", 15
    sc.render.use_stamp = False
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = lin(style["background"]) + [1.0]
    bg.inputs["Strength"].default_value = 1.0


def materials(pal):
    mats = {}
    for cls, srgb in pal.items():
        if cls == "Al":
            mats[cls] = material(cls, srgb, rough=0.38, metallic=0.55, spec=0.6)
        else:
            mats[cls] = material(cls, srgb, rough=0.3, spec=0.5, coat=0.25)
    return mats


def main():
    a = args()
    pal = json.load(open(a.palette))
    geo_all = json.load(open(a.geometry))
    style = geo_all["style"]
    geo = geo_all["panels"][a.panel]
    w, h = max(8, int(round(a.width_px * a.scale))), max(8, int(round(a.height_px * a.scale)))
    setup(a, w, h, style)
    draw(geo, style, materials(pal))
    lights(style)
    camera(style)
    types = {}
    for o in bpy.context.scene.objects:
        types[o.type] = types.get(o.type, 0) + 1
    if FORBIDDEN & set(types):
        raise SystemExit("hero: text or annotation objects in the scene: %s" % types)
    meta = {"blender": bpy.app.version_string, "seed": a.seed, "samples": a.samples, "engine": "CYCLES",
            "device": "CPU", "threads": 1, "denoise": False, "size_px": [w, h],
            "panels": {a.panel: types}, "atoms": len(geo["atoms"]), "bonds": len(geo["bonds"])}
    bpy.context.scene.render.filepath = "%s/hero_%s.png" % (a.out_dir, a.panel)
    bpy.ops.render.render(write_still=True)
    json.dump(meta, open("%s/hero_scene_%s.json" % (a.out_dir, a.panel), "w"), indent=1, sort_keys=True)


main()
