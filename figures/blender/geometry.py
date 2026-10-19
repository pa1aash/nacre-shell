"""Mesh templates and instancing in plain numpy (no Blender imports).

Atoms of one element are merged into a single mesh, and each bond is two half
cylinders coloured by the atom at each end, merged per element as well.
"""
from __future__ import annotations

import numpy as np


def uv_sphere(segments=32, rings=16):
    """Unit sphere: (verts, faces) with quads and pole triangles."""
    verts = [(0.0, 0.0, 1.0)]
    for r in range(1, rings):
        th = np.pi * r / rings
        for s in range(segments):
            ph = 2 * np.pi * s / segments
            verts.append((np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)))
    verts.append((0.0, 0.0, -1.0))
    faces = []
    for s in range(segments):
        faces.append((0, 1 + s, 1 + (s + 1) % segments))
    for r in range(rings - 2):
        a, b = 1 + r * segments, 1 + (r + 1) * segments
        for s in range(segments):
            s2 = (s + 1) % segments
            faces.append((a + s, b + s, b + s2, a + s2))
    last = len(verts) - 1
    base = 1 + (rings - 2) * segments
    for s in range(segments):
        faces.append((base + s, last, base + (s + 1) % segments))
    return np.array(verts), faces


def cylinder(segments=16):
    """Open unit cylinder along +z from z=0 to z=1, radius 1."""
    ang = 2 * np.pi * np.arange(segments) / segments
    ring = np.stack([np.cos(ang), np.sin(ang), np.zeros(segments)], axis=1)
    verts = np.vstack([ring, ring + [0.0, 0.0, 1.0]])
    faces = [(s, (s + 1) % segments, segments + (s + 1) % segments, segments + s) for s in range(segments)]
    return verts, faces


def frame_from_z(v):
    """Rotation matrix whose third column is the unit vector v."""
    z = v / np.linalg.norm(v)
    t = np.array([1.0, 0.0, 0.0]) if abs(z[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    x = np.cross(t, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.stack([x, y, z], axis=1)


def merge_instances(template, transforms):
    """template: (verts, faces); transforms: list of (R 3x3, scale (3,), t (3,)).

    Returns merged (verts, faces).
    """
    tv, tf = template
    tf = list(tf)
    verts, faces = [], []
    for k, (rot, scale, t) in enumerate(transforms):
        verts.append((tv * scale) @ rot.T + t)
        off = k * len(tv)
        faces.extend(tuple(i + off for i in f) for f in tf)
    if not verts:
        return np.zeros((0, 3)), []
    return np.vstack(verts), faces


def atom_transforms(positions, radii):
    eye = np.eye(3)
    return [(eye, np.full(3, r), p) for p, r in zip(positions, radii)]


def half_bond_transforms(p_start, p_end, radius):
    """Half bonds from each start point to the bond midpoint (radius: one value or one per bond)."""
    out = []
    radii = np.broadcast_to(np.asarray(radius, dtype=float), (len(p_start),))
    for a, b, radius in zip(p_start, p_end, radii):
        mid = 0.5 * (np.asarray(a) + np.asarray(b))
        v = mid - a
        length = np.linalg.norm(v)
        out.append((frame_from_z(v), np.array([radius, radius, length]), np.asarray(a)))
    return out


def projected_extent(points, radii, right, up):
    """Bounding box of spheres projected on the camera plane: (centre_r, centre_u, width, height)."""
    pr = points @ right
    pu = points @ up
    r = np.asarray(radii)
    lo_r, hi_r = (pr - r).min(), (pr + r).max()
    lo_u, hi_u = (pu - r).min(), (pu + r).max()
    return 0.5 * (lo_r + hi_r), 0.5 * (lo_u + hi_u), hi_r - lo_r, hi_u - lo_u


def camera_axes(direction, up):
    d = np.asarray(direction, dtype=float)
    d /= np.linalg.norm(d)
    right = np.cross(d, up)
    right /= np.linalg.norm(right)
    true_up = np.cross(right, d)
    return d, right, true_up


def ortho_scale(width, height, res, margin):
    """Blender's ortho_scale spans the larger image dimension (sensor fit AUTO)."""
    aspect = res[0] / res[1]
    if aspect >= 1:
        return margin * max(width, height * aspect)
    return margin * max(width / aspect, height)
