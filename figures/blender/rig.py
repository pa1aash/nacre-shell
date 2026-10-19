"""The single lighting rig used by every scene: key, fill and rim lights, soft shadows,
ambient occlusion and a uniform ambient world.

Every scene gets its light from here and nowhere else; scene.py never creates a light,
a world or a shading network of its own.

Lights. Three disk area lights placed in the camera frame. Positions are (azimuth,
elevation) in degrees relative to the viewing direction (azimuth 0, elevation 0 is the
camera side, positive azimuth towards the camera's right), so the rig turns with the
camera and framing never changes it. Each light sits at ``distance_factor`` x the
subject extent from the subject centre and aims at it.

- key: the main light, upper left of the camera; it sets the shading and casts the
  visible shadows.
- fill: low on the right, weaker, opens up the shadow side so no atom goes black.
- rim: behind the subject, upper left; it separates the subject from the transparent
  background with a bright edge.

Irradiance. Light power is ``irradiance`` x distance^2, so the irradiance at the subject
is the same for any scene size; the key:fill:rim ratio is 4.0 : 1.4 : 2.5.

Soft shadows. Shadow edges are soft because the lights are large: a disk of diameter
``size_frac`` x extent seen from distance_factor x extent subtends ``penumbra_deg``
(listed by ``describe``), which gives a penumbra of that angle behind every atom.
``spread`` keeps the full emission cone (180 degrees), so the penumbra is not cut.

Ambient occlusion. Every material darkens its base colour where nearby geometry blocks
the hemisphere, through Blender's Ambient Occlusion shader node: the base colour is
multiplied by ``1 - strength x (1 - ao)``, with ao measured within ``distance``
(angstrom, scene units) over ``samples`` rays. Contacts between atoms, the template
surface under the nucleus and pockets between chains read as darker, while exposed
surfaces keep their palette colour exactly (ao = 1). The effect is local by design: the
distance is shorter than a molecule, so it never darkens a whole region.

World. A uniform white world at ``strength`` adds the ambient term that the occlusion
modulates. It lights the scene but is not seen: renders use a transparent film.

Nucleus rim. When a scene marks a component as its focus (the nucleus), a small disk
light behind it (``nucleus_rim``: azimuth and elevation in the camera frame as above,
centred on the nucleus, distance ``distance_factor`` x the nucleus extent) gives it a
subtle bright edge. Light linking restricts that light to the focus collection, so it
lights the nucleus and nothing else.

Ground shadow. A large plane ``gap`` below the lowest atom is a Cycles shadow catcher:
it is not drawn, but the shadow the scene casts on it is written into the transparent
film as a soft, partly transparent dark area, which grounds the slab on the page.

Depth cue. Atmospheric fading: beyond ``start`` of the subject's depth range (camera
space, nearest atom 0, farthest 1) the shaded colour is mixed towards ``haze`` (linear
RGB, a pale cool grey close to the white page) up to ``strength`` at the far end, so
distant atoms recede. Atoms in the nearer part keep their palette colour exactly. The
haze colour and the mix strength are drawing choices, not palette colours.
"""
from __future__ import annotations

import math

RIG = {
    "key": {"azimuth": -35.0, "elevation": 40.0, "irradiance": 4.0, "size_frac": 0.6},
    "fill": {"azimuth": 50.0, "elevation": 10.0, "irradiance": 1.4, "size_frac": 1.0},
    "rim": {"azimuth": 170.0, "elevation": 35.0, "irradiance": 2.5, "size_frac": 0.5},
    "distance_factor": 3.0,
    "shadows": {"cast": True, "spread_deg": 180.0},
    "ambient_occlusion": {"distance": 2.5, "strength": 0.55, "samples": 16},
    "world": {"colour": [1.0, 1.0, 1.0], "strength": 0.35},
    "nucleus_rim": {"azimuth": 165.0, "elevation": 30.0, "irradiance": 3.0, "size_frac": 0.4,
                    "distance_factor": 3.0, "linked": True},
    "ground": {"shadow_catcher": True, "gap": 0.6, "size_factor": 4.0},
    "depth_cue": {"start": 0.35, "strength": 0.45, "haze": [0.80, 0.84, 0.90]},
}

LIGHTS = ("key", "fill", "rim")


def light_position(centre, d, right, up, azimuth, elevation, distance):
    """Point at `distance` from centre; azimuth 0, elevation 0 is the camera side."""
    az, el = math.radians(azimuth), math.radians(elevation)
    back = [-x for x in d]  # towards the camera
    v = [math.cos(el) * (math.cos(az) * back[k] + math.sin(az) * right[k]) + math.sin(el) * up[k]
         for k in range(3)]
    return [centre[k] + distance * v[k] for k in range(3)]


def penumbra_deg(name):
    """Angle subtended by a light at the subject centre: the width of its shadow penumbra."""
    return math.degrees(2.0 * math.atan(RIG[name]["size_frac"] / (2.0 * RIG["distance_factor"])))


def ao_factor(ao, strength=None):
    """Multiplier applied to the base colour for an occlusion value ao in [0, 1]."""
    s = RIG["ambient_occlusion"]["strength"] if strength is None else strength
    return 1.0 - s * (1.0 - ao)


def depth_cue_factor(t):
    """Haze mix for a normalised camera depth t (0 nearest atom, 1 farthest)."""
    dc = RIG["depth_cue"]
    if t <= dc["start"]:
        return 0.0
    return dc["strength"] * min(1.0, (t - dc["start"]) / (1.0 - dc["start"]))


def shade(mat, depth_range=None):
    """Insert the rig's ambient-occlusion term (and depth cue) in front of a Principled
    material's base colour.

    Nodes: Ambient Occlusion (distance, samples) -> Map Range [0, 1] -> [1 - strength, 1]
    -> Multiply with the palette colour; then, with ``depth_range`` (camera-space depth of
    the nearest and farthest atom), Camera Data view depth -> Map Range [near + start x
    span, far] -> [0, strength] -> Mix towards the haze colour -> Principled Base Color.
    """
    ao_cfg = RIG["ambient_occlusion"]
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    base = tuple(bsdf.inputs["Base Color"].default_value)
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = ao_cfg["samples"]
    ao.inputs["Distance"].default_value = ao_cfg["distance"]
    ao.only_local = False
    remap = nt.nodes.new("ShaderNodeMapRange")
    remap.inputs["From Min"].default_value = 0.0
    remap.inputs["From Max"].default_value = 1.0
    remap.inputs["To Min"].default_value = ao_factor(0.0)
    remap.inputs["To Max"].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs["A"].default_value = base
    nt.links.new(ao.outputs["AO"], remap.inputs["Value"])
    nt.links.new(remap.outputs["Result"], mix.inputs["B"])
    out = mix.outputs["Result"]
    if depth_range is not None:
        dc = RIG["depth_cue"]
        near, far = depth_range
        cam = nt.nodes.new("ShaderNodeCameraData")
        dmap = nt.nodes.new("ShaderNodeMapRange")
        dmap.clamp = True
        dmap.inputs["From Min"].default_value = near + dc["start"] * (far - near)
        dmap.inputs["From Max"].default_value = max(far, near + 1e-3)
        dmap.inputs["To Min"].default_value = 0.0
        dmap.inputs["To Max"].default_value = dc["strength"]
        haze = nt.nodes.new("ShaderNodeMix")
        haze.data_type = "RGBA"
        haze.blend_type = "MIX"
        haze.inputs["B"].default_value = (*dc["haze"], 1.0)
        nt.links.new(cam.outputs["View Z Depth"], dmap.inputs["Value"])
        nt.links.new(dmap.outputs["Result"], haze.inputs["Factor"])
        nt.links.new(out, haze.inputs["A"])
        out = haze.outputs["Result"]
    nt.links.new(out, bsdf.inputs["Base Color"])
    return mat


def build(scene, centre, extent, d, right, up, ground_z=None, focus=None):
    """Add the rig's lights, world and ground shadow catcher to a bpy scene.

    `extent` is the subject size in scene units; `ground_z` the lowest atom surface;
    `focus` (optional) {collection, centre, extent} of the nucleus for its linked rim light.
    """
    import bpy
    from mathutils import Vector

    distance = RIG["distance_factor"] * extent
    made = []
    for name in LIGHTS:
        spec = RIG[name]
        data = bpy.data.lights.new(f"rig_{name}", type="AREA")
        data.shape = "DISK"
        data.size = spec["size_frac"] * extent
        data.energy = spec["irradiance"] * distance ** 2
        data.use_shadow = RIG["shadows"]["cast"]
        data.spread = math.radians(RIG["shadows"]["spread_deg"])
        obj = bpy.data.objects.new(f"rig_{name}", data)
        obj.location = light_position(centre, d, right, up, spec["azimuth"], spec["elevation"], distance)
        look = Vector(centre) - Vector(obj.location)
        obj.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(obj)
        made.append(obj)
    if focus is not None:
        spec = RIG["nucleus_rim"]
        dist = spec["distance_factor"] * focus["extent"]
        data = bpy.data.lights.new("rig_nucleus_rim", type="AREA")
        data.shape = "DISK"
        data.size = spec["size_frac"] * focus["extent"]
        data.energy = spec["irradiance"] * dist ** 2
        data.use_shadow = RIG["shadows"]["cast"]
        obj = bpy.data.objects.new("rig_nucleus_rim", data)
        obj.location = light_position(focus["centre"], d, right, up, spec["azimuth"], spec["elevation"], dist)
        look = Vector(focus["centre"]) - Vector(obj.location)
        obj.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(obj)
        if spec["linked"]:
            obj.light_linking.receiver_collection = focus["collection"]
        made.append(obj)
    if ground_z is not None and RIG["ground"]["shadow_catcher"]:
        g = RIG["ground"]
        half = 0.5 * g["size_factor"] * extent
        z = ground_z - g["gap"]
        cx, cy = centre[0], centre[1]
        mesh = bpy.data.meshes.new("rig_ground")
        mesh.from_pydata([(cx - half, cy - half, z), (cx + half, cy - half, z), (cx + half, cy + half, z),
                          (cx - half, cy + half, z)], [], [(0, 1, 2, 3)])
        att = mesh.attributes.new("alpha", "FLOAT", "POINT")
        att.data.foreach_set("value", [1.0] * 4)
        ground = bpy.data.objects.new("rig_ground", mesh)
        ground.is_shadow_catcher = True
        scene.collection.objects.link(ground)
    world = bpy.data.worlds.new("rig_world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*RIG["world"]["colour"], 1.0)
    bg.inputs["Strength"].default_value = RIG["world"]["strength"]
    scene.world = world
    return made


def describe():
    out = {k: v for k, v in RIG.items() if k not in ("shadows",)}
    out["shadows"] = RIG["shadows"]
    out["penumbra_deg"] = {name: round(penumbra_deg(name), 2) for name in LIGHTS}
    return out
