"""Hero figure scene: two separate single-phase panels, rendered headless.

  blender -b -P figures/src/blender/hero.py -- --palette p.json --out-dir DIR [--seed 7]
          [--samples 128] [--width-px 1973] [--height-px 1480] [--scale 1.0] [--panel a|b]

Panel a: carbonate crystallites on aluminium foil in water (processing stage).
Panel b: a condensed phosphate film on foil in electrolyte (cell stage).
Illustrative construction: no text objects, no scale, no data. The two solids are never in one
scene. Colours come from the palette file written by nacre.figs.rendered (the figure palette of
the stability map). Deterministic: Cycles on the CPU with one thread, a fixed seed, a fixed
sample count, no denoiser, no adaptive sampling, and a private random generator.
Writes hero_a.png and hero_b.png (or one, with --panel) and hero_scene_<panels>.json (engine settings and object counts).
"""
import argparse
import json
import math
import random
import sys

import bpy
import bmesh
from mathutils import Euler, Vector

HALF_X, HALF_Y, LIQ_H, FOIL_T = 5.0, 3.2, 3.3, 0.16


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--palette", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--samples", type=int, default=128)
    p.add_argument("--width-px", type=int, default=1973)
    p.add_argument("--height-px", type=int, default=1480)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--panel", choices=("a", "b"), help="render one panel only (default both)")
    return p.parse_args(argv)


def lin(c):
    f = lambda x: x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return [f(x) for x in c]


def material(name, srgb, rough=0.5, metallic=0.0, spec=0.5, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(srgb) + [1.0]
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Specular IOR Level"].default_value = spec
    b.inputs["Alpha"].default_value = alpha
    return m


def put(obj, mat, smooth=True):
    obj.data.materials.append(mat)
    if smooth:
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def box(name, size, loc, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width, mod.segments = bevel, 3
        bpy.ops.object.modifier_apply(modifier="bevel")
    return put(o, mat, smooth=False)


def crystallite(rng, mat, size, loc):
    """A rhombohedron: a bevelled cube sheared along its body diagonal."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = "crystallite"
    me = o.data
    shear = rng.uniform(0.18, 0.34)
    for v in me.vertices:
        v.co.x += shear * v.co.z
        v.co.y += 0.5 * shear * v.co.z
    stretch = rng.uniform(0.8, 1.3)
    o.scale = (size, size, size * stretch)
    o.rotation_euler = Euler((rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), rng.uniform(0, math.tau)))
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    mod = o.modifiers.new("bevel", "BEVEL")
    mod.width, mod.segments = size * 0.06, 2
    bpy.ops.object.modifier_apply(modifier="bevel")
    o.location.z = FOIL_T / 2 * 0 + size * stretch * 0.5 * 0.92
    return put(o, mat, smooth=False)


def scatter(rng, n, rmin, rmax):
    pts = []
    tries = 0
    while len(pts) < n and tries < 40000:
        tries += 1
        s = rng.uniform(rmin, rmax)
        x, y = rng.uniform(-HALF_X + 0.5, HALF_X - 0.5), rng.uniform(-HALF_Y + 0.4, HALF_Y - 0.4)
        if all((x - px) ** 2 + (y - py) ** 2 > (0.82 * (s + ps)) ** 2 for px, py, ps in pts):
            pts.append((x, y, s))
    return pts


def film(rng, mat, thickness=0.2):
    """A continuous condensed layer: one displaced slab, rounded at the cut edges."""
    nx, ny = 220, 110
    me = bpy.data.meshes.new("film")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=1.0)
    waves = [(rng.uniform(0.35, 0.9), rng.uniform(0.35, 0.9), rng.uniform(0, math.tau), rng.uniform(0.012, 0.03))
             for _ in range(6)]
    for v in bm.verts:
        x, y = v.co.x * (HALF_X - 0.25), v.co.y * (HALF_Y - 0.25)
        z = sum(a * math.sin(fx * x + fy * y + ph) for fx, fy, ph, a in waves)
        v.co = Vector((x, y, thickness + z))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("film", me)
    bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    mod = o.modifiers.new("solid", "SOLIDIFY")
    mod.thickness, mod.offset = thickness + 0.05, -1.0
    bpy.ops.object.modifier_apply(modifier="solid")
    return put(o, mat)


def lights():
    for name, kind, loc, energy, size in (("key", "AREA", (-4.0, -6.0, 11.0), 1500.0, 9.0),
                                          ("fill", "AREA", (8.0, -9.0, 5.0), 350.0, 8.0)):
        d = bpy.data.lights.new(name, kind)
        d.energy, d.size = energy, size
        o = bpy.data.objects.new(name, d)
        o.location = loc
        bpy.context.scene.collection.objects.link(o)
        direction = Vector((0.0, 0.0, 0.6)) - Vector(loc)
        o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera(aspect):
    d = bpy.data.cameras.new("cam")
    d.lens, d.sensor_width = 42.0, 36.0
    o = bpy.data.objects.new("cam", d)
    bpy.context.scene.collection.objects.link(o)
    o.location = (1.2, -12.5, 8.2)
    o.rotation_euler = (Vector((0.0, 0.2, 1.0)) - o.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = o


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup(a, w, h):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    c = sc.cycles
    c.device, c.samples, c.seed = "CPU", a.samples, a.seed
    c.use_animated_seed, c.use_adaptive_sampling, c.use_denoising = False, False, False
    c.transmission_bounces, c.max_bounces, c.glossy_bounces = 10, 12, 6
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
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 1.0


def build(panel, pal, seed):
    rng = random.Random(seed * 1000 + (1 if panel == "a" else 2))
    foil = material("foil", pal["foil"], rough=0.45, metallic=0.6, spec=0.6)
    liquid = material("liquid", pal["liquid"], rough=0.0, spec=0.5, alpha=0.2)
    surface = material("surface", pal["liquid"], rough=0.0, spec=0.6, alpha=0.3)
    ground = material("ground", (1.0, 1.0, 1.0), rough=1.0, spec=0.0)
    box("ground", (60.0, 60.0, 0.1), (0.0, 0.0, -FOIL_T - 0.05 - 0.6), ground)
    box("foil", (2 * HALF_X, 2 * HALF_Y, FOIL_T), (0.0, 0.0, -FOIL_T / 2), foil, bevel=0.03)
    if panel == "a":
        mat = material("carbonate", pal["carbonate"], rough=0.32, spec=0.7)
        for x, y, s in scatter(rng, 150, 0.17, 0.46):
            crystallite(rng, mat, s, (x, y, 0.0))
    else:
        film(rng, material("phosphate", pal["phosphate"], rough=0.42, spec=0.55))
    body = box("liquid", (2 * HALF_X, 2 * HALF_Y, LIQ_H), (0.0, 0.0, LIQ_H / 2), liquid, bevel=0.05)
    top = box("surface", (2 * HALF_X, 2 * HALF_Y, 0.04), (0.0, 0.0, LIQ_H), surface)
    for o in (body, top):
        o.visible_shadow = False  # the liquid is a tint, not an obstacle
    lights()


def main():
    a = args()
    pal = json.load(open(a.palette))
    w, h = max(8, int(round(a.width_px * a.scale))), max(8, int(round(a.height_px * a.scale)))
    meta = {"blender": bpy.app.version_string, "seed": a.seed, "samples": a.samples, "engine": "CYCLES",
            "device": "CPU", "threads": 1, "denoise": False, "size_px": [w, h], "panels": {}}
    for panel in ((a.panel,) if a.panel else ("a", "b")):
        reset()
        setup(a, w, h)
        build(panel, pal, a.seed)
        camera(w / h)
        types = {}
        for o in bpy.context.scene.objects:
            types[o.type] = types.get(o.type, 0) + 1
        if "FONT" in types or "GPENCIL" in types:
            raise SystemExit("hero: text or annotation objects in the scene: %s" % types)
        meta["panels"][panel] = types
        bpy.context.scene.render.filepath = "%s/hero_%s.png" % (a.out_dir, panel)
        bpy.ops.render.render(write_still=True)
    json.dump(meta, open("%s/hero_scene_%s.json" % (a.out_dir, a.panel or "ab"), "w"), indent=1, sort_keys=True)


main()
