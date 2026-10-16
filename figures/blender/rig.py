"""The single lighting rig used by every scene.

Three area lights placed in the camera frame (key, fill, rim) plus a uniform grey world
for soft ambient light. The world lights the scene but is not seen: renders use a
transparent film. Light positions are given as (azimuth, elevation) in degrees relative
to the viewing direction, so the rig turns with the camera and framing never changes it.
Light power scales with distance squared, so the irradiance at the subject is the same
for any scene size.
"""
from __future__ import annotations

import math

RIG = {
    "key": {"azimuth": -35.0, "elevation": 40.0, "irradiance": 4.0, "size_frac": 0.6},
    "fill": {"azimuth": 50.0, "elevation": 10.0, "irradiance": 1.4, "size_frac": 1.0},
    "rim": {"azimuth": 170.0, "elevation": 35.0, "irradiance": 2.5, "size_frac": 0.5},
    "distance_factor": 3.0,
    "world": {"colour": [1.0, 1.0, 1.0], "strength": 0.35},
}


def light_position(centre, d, right, up, azimuth, elevation, distance):
    """Point at `distance` from centre; azimuth 0, elevation 0 is the camera side."""
    az, el = math.radians(azimuth), math.radians(elevation)
    back = [-x for x in d]  # towards the camera
    v = [math.cos(el) * (math.cos(az) * back[k] + math.sin(az) * right[k]) + math.sin(el) * up[k]
         for k in range(3)]
    return [centre[k] + distance * v[k] for k in range(3)]


def build(scene, centre, extent, d, right, up):
    """Add the rig to a bpy scene. `extent` is the subject size in scene units."""
    import bpy
    from mathutils import Vector

    distance = RIG["distance_factor"] * extent
    made = []
    for name in ("key", "fill", "rim"):
        spec = RIG[name]
        data = bpy.data.lights.new(f"rig_{name}", type="AREA")
        data.shape = "DISK"
        data.size = spec["size_frac"] * extent
        data.energy = spec["irradiance"] * distance ** 2
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
    return {k: v for k, v in RIG.items()}
