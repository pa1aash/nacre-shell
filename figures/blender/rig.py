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


def shade(mat):
    """Insert the rig's ambient-occlusion term in front of a Principled material's base colour.

    Nodes: Ambient Occlusion (distance, samples) -> Map Range [0, 1] -> [1 - strength, 1]
    -> Multiply with the palette colour -> Principled Base Color.
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
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


def build(scene, centre, extent, d, right, up):
    """Add the rig's lights and world to a bpy scene. `extent` is the subject size in scene units."""
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
    world = bpy.data.worlds.new("rig_world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*RIG["world"]["colour"], 1.0)
    bg.inputs["Strength"].default_value = RIG["world"]["strength"]
    scene.world = world
    return made


def describe():
    out = {k: v for k, v in RIG.items()}
    out["penumbra_deg"] = {name: round(penumbra_deg(name), 2) for name in LIGHTS}
    return out
