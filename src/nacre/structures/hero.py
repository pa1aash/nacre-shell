"""Hero scene of Figure 1 (and the Fig 2 panels): an illustrative construction of the
template-nucleus contact.

Composition (every placement is a parameter in build.yaml; nothing is simulated):

1. ``slab``: the hydroxylated alpha-Al2O3(0001) slab in a rectangular periodic cell.
2. ``chains``: generic catechol-bearing oligomers (nacre.structures.oligomer) anchored
   on the slab. The end catechol (unit 0) binds bidentate: its two O take the places of
   two neighbouring surface hydroxyl O, whose OH groups and the two phenolic H are
   removed (surface +2, catecholate -2, so each anchor is neutral). The chain is a rigid
   body turned about the O-O axis; of the orientations that keep every other atom at
   least ``clearance`` from the slab and earlier parts and point within ``azimuth_tol``
   of the requested azimuth, the lowest-lying one is taken. A chain entry may name a
   ``template`` other than the default chain (for example the carboxyl-ended chain).
3. ``bound``: a few Ca2+ at sites of the chains. A ``catecholate`` site is a catechol
   monoanion (one H removed; ``unit: auto`` takes the outermost unit where the site is
   clash-free); a ``carboxylate`` site is the deprotonated carboxyl end group. Ca sits on
   the bisector of the O pair at the evidence Ca-O distance, and the rest of its evidence
   coordination number is filled with water from the hydrated-ion shell. Each site is +1.
   Binding does not add driving force (derivation, section 7), so a scene shows a few
   bound ions, not a cloud.
4. ``nucleus``: an amorphous CaCO3 nucleus drawn as a lens: one spherical cap (or, for a
   coalesced film, the union of several ``caps``) with a flat base on the template, base
   plane ``base_height`` above the top hydroxyl H, at contact angle
   ``contact_angle_deg``. Ca2+ and CO3^2- are inserted alternately inside it under the
   minimum-distance rules of nacre.structures.acc and stay clear of the template atoms.
   The number of formula units is the lens volume times the sourced packing (N_A / V_m,
   key v_m_acc) and the carbonate C-O length is the sourced key c_o_bond_length_acc
   (nacre.structures.params_source); neither may be typed. The structural water of ACC
   is not drawn. The contact is the focus of the figure.
5. ``bridge`` (optional): one Ca2+ at a catecholate site under the rim of the cap,
   bridging the template and the nucleus: it is built like a bound site, its waters
   inside the cap are removed, and one nucleus carbonate is placed first so that its O
   completes the Ca shell. This site is also +1.
6. ``carbonate``: dissolved CO3^2- ions that balance the charge of the Ca sites
   (decision D5); their number follows from the bookkeeping and must equal the number
   of positions given. Each must lie at least ``carbonate_far`` from the nucleus.
7. ``water``: water packed above the slab, in the whole cell or behind a cut-away plane
   (``y_cut``, fraction of the cell); see nacre.structures.water. The renderer draws
   only the shell near the interface, fading with distance.

Per-atom ``component`` labels: slab, chain<i>, bound<j>, bound<j>_water, bridge,
bridge_water, nucleus, carbonate<k>, water. The total charge is the explicit sum of the
bookkeeping above and must be zero. ``drawing_choices`` (from build.yaml) names every
unsourced drawing parameter and is written into the file's metadata.
"""
from __future__ import annotations

import json

import numpy as np

from nacre.structures import acc, ion, water
from nacre.structures.meta import stamp
from nacre.structures.water import random_rotation

DEFAULTS = {
    "clearance": 2.0,
    "ca_clearance": 2.6,
    "azimuth_tol": 35.0,
    "phi_step_deg": 2.0,
    "site_pair_range": [2.3, 3.1],
    "site_tie_tol": 0.01,
    "nucleus": {"centre": [0.5, 0.45], "base_radius": 11.0, "contact_angle_deg": 50.0,
                "base_height": 2.5, "caps": None, "attempts": 60000, "env_min": 2.3,
                "env_min_h": 1.9, "grid": 0.25},
    "bridge": None,
    "carbonate_min": 2.6,
    "carbonate_far": 8.0,
    "water": {"y_cut": 0.62, "gap": 1.6, "thickness": 18.0, "density_g_cm3": 1.0},
}


def _deep(defaults, given):
    """Defaults merged one level deep; a part given as null (for example nucleus) stays null."""
    out = {}
    for k, v in defaults.items():
        g = (given or {}).get(k, v if not isinstance(v, dict) else {})
        out[k] = {**v, **g} if isinstance(v, dict) and g is not None else g
    for k, v in (given or {}).items():
        out.setdefault(k, v)
    return out


def _rot(axis, angle):
    axis = axis / np.linalg.norm(axis)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k


def _align_pair(a1, a2, b1, b2):
    """Rotation R and translation t taking the a1->a2 axis onto b1->b2 at their midpoints."""
    u = (a2 - a1) / np.linalg.norm(a2 - a1)
    v = (b2 - b1) / np.linalg.norm(b2 - b1)
    c = float(np.dot(u, v))
    w = np.cross(u, v)
    if np.linalg.norm(w) < 1e-12:
        r = np.eye(3) if c > 0 else _rot(np.cross(u, [1.0, 0.0, 0.0]) + np.cross(u, [0.0, 1.0, 0.0]), np.pi)
    else:
        r = _rot(w, np.arctan2(np.linalg.norm(w), c))
    t = (b1 + b2) / 2 - r @ ((a1 + a2) / 2)
    return r, t


class Scene:
    """Atoms under construction with per-atom component labels and a charge ledger."""

    def __init__(self, slab):
        self.cell = np.asarray(slab.cell)
        self.pbc = tuple(bool(x) for x in slab.pbc)
        self.sym = list(slab.get_chemical_symbols())
        self.pos = slab.get_positions().copy()
        self.comp = ["slab"] * len(slab)
        self.alive = np.ones(len(slab), dtype=bool)
        self.ledger = [("slab", int(slab.info["total_charge"]))]
        self.anchors = []

    def add(self, sym, pos, comp):
        self.sym += list(sym)
        self.pos = np.vstack([self.pos, np.asarray(pos)])
        self.comp += [comp] * len(sym)
        self.alive = np.r_[self.alive, np.ones(len(sym), dtype=bool)]

    def remove(self, idx):
        self.alive[list(idx)] = False

    def distances(self, pts, mask=None):
        """Minimum-image distances from pts (m, 3) to the live atoms (selected by mask)."""
        sel = self.alive if mask is None else self.alive & mask
        d = np.asarray(pts)[:, None, :] - self.pos[sel][None, :, :]
        frac = d @ np.linalg.inv(self.cell)
        for k in range(3):
            if self.pbc[k]:
                frac[..., k] -= np.round(frac[..., k])
        return np.linalg.norm(frac @ self.cell, axis=-1), np.where(sel)[0]

    def xy(self, f):
        return f[0] * self.cell[0][:2] + f[1] * self.cell[1][:2]


def _nearest_h(sc, i):
    sym = np.array(sc.sym)
    mask = (sym == "H") & (np.array(sc.comp) == sc.comp[i])
    r, idx = sc.distances(sc.pos[i][None, :], mask)
    return int(idx[np.argmin(r[0])])


def anchor_chain(sc, chain, site, azimuth, p, name):
    """Place one chain with its unit-0 catechol on two neighbouring surface hydroxyl O."""
    sym = np.array(sc.sym)
    comp = np.array(sc.comp)
    top = np.where((sym == "O") & (comp == "slab") & sc.alive)[0]
    z_top = sc.pos[top, 2].max()
    top = top[sc.pos[top, 2] > z_top - 0.3]
    target = sc.xy(site)
    d_t = np.linalg.norm(((sc.pos[top, :2] - target) @ np.linalg.inv(sc.cell[:2, :2])
                          - np.round((sc.pos[top, :2] - target) @ np.linalg.inv(sc.cell[:2, :2])))
                         @ sc.cell[:2, :2], axis=1)
    order = np.argsort(d_t, kind="stable")
    if d_t[order[1]] - d_t[order[0]] < p["site_tie_tol"]:
        # Two surface O equally near the requested site: which one wins would depend on the
        # last bits of the arithmetic, so on the platform. Refuse rather than guess.
        raise ValueError(f"{name}: site {site} is equidistant from two surface O "
                         f"({d_t[order[0]]:.4f} and {d_t[order[1]]:.4f} A); move it")
    s1 = int(top[order[0]])
    r_top = np.linalg.norm(sc.pos[top] - sc.pos[s1], axis=1)
    lo, hi = p["site_pair_range"]
    partners = [int(t) for t in top[(r_top > lo) & (r_top < hi)]]
    csym = np.array(chain.get_chemical_symbols())
    cpos = chain.get_positions()
    unit = chain.arrays["catechol"]
    o_a = np.where((unit == 0) & (csym == "O"))[0]
    h_a = np.where((unit == 0) & (csym == "H"))[0]
    keep_c = np.setdiff1d(np.arange(len(chain)), h_a)
    rest = np.setdiff1d(keep_c, o_a)
    az = np.radians(azimuth)
    want = np.array([np.cos(az), np.sin(az)])
    best = None
    for s2 in partners:
        h1, h2 = _nearest_h(sc, s1), _nearest_h(sc, s2)
        excl = np.zeros(len(sc.sym), dtype=bool)
        excl[[s1, s2, h1, h2]] = True
        for oa, ob in ((o_a[0], o_a[1]), (o_a[1], o_a[0])):
            r0, t0 = _align_pair(cpos[oa], cpos[ob], sc.pos[s1], sc.pos[s2])
            base = cpos @ r0.T + t0
            axis = sc.pos[s2] - sc.pos[s1]
            mid = (sc.pos[s1] + sc.pos[s2]) / 2
            for phi in np.radians(np.arange(0.0, 360.0, p["phi_step_deg"])):
                pos = (base - mid) @ _rot(axis, phi).T + mid
                heavy = rest[csym[rest] != "H"]
                cen = pos[heavy].mean(axis=0) - mid
                if np.linalg.norm(cen[:2]) < 1e-6:
                    continue
                ang = np.degrees(np.arccos(np.clip(cen[:2] @ want / np.linalg.norm(cen[:2]), -1, 1)))
                if ang > p["azimuth_tol"]:
                    continue
                r, _ = sc.distances(pos[rest], ~excl)
                if r.min() < p["clearance"]:
                    continue
                # Rounded so that symmetry-equivalent orientations tie exactly; the first in
                # enumeration order then wins on every platform.
                score = round(float(pos[heavy, 2].mean()), 6)
                if best is None or score < best[0]:
                    best = (score, pos, s2, h1, h2, float(np.degrees(phi)), int(oa != o_a[0]))
    if best is None:
        raise RuntimeError(f"{name}: no clash-free anchoring near {site} at azimuth {azimuth}")
    _, pos, s2, h1, h2, phi_deg, swapped = best
    sc.anchors.append({"chain": name, "s1": np.round(sc.pos[s1], 3).tolist(),
                       "s2": np.round(sc.pos[s2], 3).tolist(), "phi_deg": phi_deg, "swapped": swapped,
                       "partners": len(partners)})
    sc.remove([s1, s2, h1, h2])
    sc.add(csym[keep_c], pos[keep_c], name)
    sc.ledger.append((f"{name} anchor: two surface OH removed", +2))
    sc.ledger.append((f"{name} anchor: catecholate (two phenolic H removed)", -2 + int(chain.info["total_charge"])))
    first = len(sc.sym) - len(keep_c)
    # Map original chain indices to scene indices for later site lookups.
    return {int(c): first + k for k, c in enumerate(keep_c)}


SITE_KINDS = ("catecholate", "carboxylate")


def ca_site(sc, chain_index_map, chain, unit_k, geom, rng, name, p, kind="catecholate"):
    """Ca2+ bound bidentate to a site of a placed chain; returns the Ca index.

    ``kind`` catecholate: the O pair of catechol unit ``unit_k``, made a monoanion (one H
    removed, the other turned away from Ca). ``kind`` carboxylate: the carboxyl O pair of
    the end group, deprotonated. Either site carries +1 with its Ca2+.

    The Ca must stay ``ca_clearance`` from every atom other than its two O and their C,
    and the shell waters ``clearance`` - 0.4 from everything; otherwise the site is
    refused (a drawing never shows overlapping atoms).
    """
    if kind not in SITE_KINDS:
        raise ValueError(f"{name}: site must be one of {SITE_KINDS}")
    csym = np.array(chain.get_chemical_symbols())
    if kind == "carboxylate":
        if "carboxyl" not in chain.arrays:
            raise ValueError(f"{name}: the chain has no carboxyl end group")
        unit, unit_k = chain.arrays["carboxyl"], 0
    else:
        unit = chain.arrays["catechol"]
    o = [chain_index_map[i] for i in np.where((unit == unit_k) & (csym == "O"))[0]]
    h = [chain_index_map[i] for i in np.where((unit == unit_k) & (csym == "H"))[0]]
    pos = sc.pos
    c_of = []
    sym = np.array(sc.sym)
    for oi in o:
        r, idx = sc.distances(pos[oi][None, :], (sym == "C") & (np.array(sc.comp) == sc.comp[oi]))
        c_of.append(int(idx[np.argmin(r[0])]))
    m = pos[o].mean(axis=0)
    w = m - pos[c_of].mean(axis=0)
    axis_oo = (pos[o[1]] - pos[o[0]]) / np.linalg.norm(pos[o[1]] - pos[o[0]])
    w -= np.dot(w, axis_oo) * axis_oo  # perpendicular to O-O, so both Ca-O equal r_ca_o
    w /= np.linalg.norm(w)
    r_cao = geom["r_ca_o"]
    half = np.linalg.norm(pos[o[0]] - pos[o[1]]) / 2
    ca = m + w * np.sqrt(max(r_cao ** 2 - half ** 2, 0.0))
    own = np.zeros(len(sc.sym), dtype=bool)
    own[o + c_of + h] = True
    r_ca, _ = sc.distances(ca[None, :], ~own)
    if r_ca.min() < p["ca_clearance"]:
        raise RuntimeError(f"{name}: Ca at unit {unit_k} would sit {r_ca.min():.2f} A from another atom")
    # Catechol monoanion: remove the H of the first O, turn the H of the second O away from
    # Ca. Carboxylate: remove the acid H.
    h_first = min(h, key=lambda hh: np.linalg.norm(pos[hh] - pos[o[0]]))
    h_second = None
    if kind == "catecholate":
        h_second = [hh for hh in h if hh != h_first][0]
        u1 = (pos[o[1]] - ca) / np.linalg.norm(pos[o[1]] - ca)
        u2 = (pos[o[1]] - pos[c_of[1]]) / np.linalg.norm(pos[o[1]] - pos[c_of[1]])
        dh = (u1 + u2) / np.linalg.norm(u1 + u2)
        h_new = pos[o[1]] + 0.97 * dh
    # Hydration shell: evidence CN, two places taken by the catecholate O.
    shell = ion.build({"cn": geom["cn"], "r_ca_o": r_cao}, seed=int(rng.integers(1 << 31)))
    ssym = np.array(shell.get_chemical_symbols())
    spos = shell.get_positions() - shell.positions[0]
    so = np.where(ssym == "O")[0]
    dirs = spos[so] / r_cao
    ua = (pos[o[0]] - ca) / np.linalg.norm(pos[o[0]] - ca)
    ub = (pos[o[1]] - ca) / np.linalg.norm(pos[o[1]] - ca)
    best = None
    for i in range(len(so)):
        for j in range(len(so)):
            if i == j:
                continue
            a = np.stack([dirs[i], dirs[j], np.cross(dirs[i], dirs[j])])
            b = np.stack([ua, ub, np.cross(ua, ub)])
            u, _, vt = np.linalg.svd(b.T @ a)
            rmat = u @ np.diag([1, 1, np.sign(np.linalg.det(u @ vt))]) @ vt
            keep = [k for k in range(len(so)) if k not in (i, j)]
            wat = []
            for k in keep:
                wat.append(spos[[so[k], so[k] + 1, so[k] + 2]] @ rmat.T + ca)
            wat = np.array(wat)
            if len(wat):
                r, _ = sc.distances(wat.reshape(-1, 3))
                clear = r.min()
            else:
                clear = np.inf
            # Rounded: symmetric shell directions fit equally well, and the first pair in
            # enumeration order must win on every platform.
            fit = round(float(np.linalg.norm(rmat @ dirs[i] - ua) + np.linalg.norm(rmat @ dirs[j] - ub)), 6)
            key = (clear < p["clearance"] - 0.4, fit)
            if best is None or key < best[0]:
                best = (key, wat)
    if best[0][0]:
        raise RuntimeError(f"{name}: no clash-free hydration shell at unit {unit_k}")
    # All checks passed: only now change the scene.
    sc.remove([h_first])
    if h_second is not None:
        sc.pos[h_second] = h_new
    sc.add(["Ca"], ca[None, :], name)
    ca_idx = len(sc.sym) - 1
    wat = best[1]
    if len(wat):
        sc.add(["O", "H", "H"] * len(wat), wat.reshape(-1, 3), f"{name}_water")
    what = "a catechol monoanion (one H removed)" if kind == "catecholate" else "a carboxylate (acid H removed)"
    sc.ledger.append((f"{name}: Ca2+ on {what}", +2 - 1))
    return ca_idx, len(wat)


def rim_unit(sc, index_map, chain, centre, base_radius, z_base):
    """The catechol unit (not the anchor) whose O pair lies closest to the rim of the cap base."""
    csym = np.array(chain.get_chemical_symbols())
    unit = chain.arrays["catechol"]
    best = None
    for k in sorted(set(unit[unit > 0])):
        o = [index_map[i] for i in np.where((unit == k) & (csym == "O"))[0]]
        m = sc.pos[o].mean(axis=0)
        miss = abs(np.linalg.norm(m[:2] - centre[:2]) - base_radius) + max(0.0, m[2] - z_base - 2.0)
        if best is None or miss < best[0]:
            best = (miss, int(k))
    return best[1]


def _carbonate(centre, rot, r_co):
    sym, pos = acc.carbonate(r_co)
    return sym, pos @ rot.T + centre


def lens(sc, n):
    """The nucleus shape: caps as (centre, sphere radius) and the base plane height.

    One cap from ``centre`` and ``base_radius``, or the union of ``caps`` ([fx, fy,
    base_radius] each); all share the contact angle and the flat base plane.
    """
    slab_top = sc.pos[(np.array(sc.comp) == "slab") & sc.alive, 2].max()
    z_b = slab_top + n["base_height"]
    th = np.radians(n["contact_angle_deg"])
    spec = n["caps"] or [[n["centre"][0], n["centre"][1], n["base_radius"]]]
    caps = []
    for fx, fy, a in spec:
        radius = a / np.sin(th)
        height = radius * (1 - np.cos(th))
        caps.append((np.r_[sc.xy([fx, fy]), z_b + height - radius], float(radius)))
    return caps, float(z_b)


def lens_inside(caps, z_b, pts):
    pts = np.atleast_2d(pts)
    hit = np.zeros(len(pts), dtype=bool)
    for c, r in caps:
        hit |= np.linalg.norm(pts - c, axis=1) <= r
    return hit & (pts[:, 2] >= z_b)


def lens_box(caps, z_b):
    lo = np.min([c - r for c, r in caps], axis=0)
    hi = np.max([c + r for c, r in caps], axis=0)
    lo[2] = z_b
    return lo, hi


def lens_volume(caps, z_b, step):
    """Volume of the lens by counting the points of a regular grid inside it (A^3)."""
    lo, hi = lens_box(caps, z_b)
    axes = [np.arange(lo[k] + step / 2, hi[k], step) for k in range(3)]
    g = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    return float(lens_inside(caps, z_b, g).sum() * step ** 3)


def place_bridge_carbonate(sc, p, rng, bridge_ca, cap_centre, geom, r_co):
    n = p["nucleus"]
    ca = sc.pos[bridge_ca]
    comp = np.array(sc.comp)
    wat_o = [i for i in np.where((comp == "bridge_water") & sc.alive)[0] if sc.sym[i] == "O"]
    towards = (cap_centre - ca) / np.linalg.norm(cap_centre - ca)
    wat_o.sort(key=lambda i: -float(np.dot((sc.pos[i] - ca) / np.linalg.norm(sc.pos[i] - ca), towards)))
    for o in wat_o:
        u = (sc.pos[o] - ca) / np.linalg.norm(sc.pos[o] - ca)
        env = sc.alive.copy()
        env[[bridge_ca, o, o + 1, o + 2]] = False
        perp0 = np.cross(u, [0.0, 0.0, 1.0])
        if np.linalg.norm(perp0) < 1e-6:
            perp0 = np.cross(u, [1.0, 0.0, 0.0])
        perp0 /= np.linalg.norm(perp0)
        for spin in np.radians(np.arange(0.0, 120.0, 10.0)):
            perp = _rot(u, spin) @ perp0
            # acc.carbonate puts O1 along +y of its frame; map +y to -u so O1 faces the Ca.
            rot = np.stack([perp, -u, np.cross(perp, -u)], axis=1)
            sym, pos = _carbonate(ca + u * (geom["r_ca_o"] + r_co), rot, r_co)
            r, idx = sc.distances(pos, env)
            lim = np.where(np.array(sc.sym)[idx] == "H", n["env_min_h"], n["env_min"])
            if (r >= lim[None, :]).all():
                sc.remove([o, o + 1, o + 2])
                return list(sym), pos
    raise RuntimeError("bridge: no clash-free carbonate on the Ca shell towards the nucleus")


def build_nucleus(sc, p, rng, bridge_ca, geom, accg):
    """Fill the lens with Ca2+ and CO3^2- at the sourced packing; returns placement counts."""
    n = p["nucleus"]
    r_co = accg["r_co"]
    caps, z_b = lens(sc, n)
    vol = lens_volume(caps, z_b, n["grid"])
    target = int(round(vol * accg["fu_per_a3"]))
    lo, hi = lens_box(caps, z_b)
    cap_sym, cap_pos = [], np.zeros((0, 3))
    if bridge_ca is not None:
        # The first carbonate completes the bridging Ca shell: it takes the place of the shell
        # water that points most towards the nearest cap, one O at the evidence Ca-O distance.
        near = min(caps, key=lambda cr: np.linalg.norm(cr[0][:2] - sc.pos[bridge_ca][:2]))[0]
        cap_sym, cap_pos = place_bridge_carbonate(sc, p, rng, bridge_ca, near, geom, r_co)
    env = sc.alive.copy()
    if bridge_ca is not None:
        env[bridge_ca] = False
    attempts = 0
    # Ca and CO3 alternate (after the bridging carbonate, if any), ending neutral.
    units = (["Ca"] + ["CO3", "Ca"] * max(target - 1, 0)) if bridge_ca is not None \
        else ["Ca", "CO3"] * target
    rejected = {"outside": 0, "nucleus": 0, "template": 0}
    for unit in units:
        while attempts < n["attempts"]:
            attempts += 1
            pt = rng.uniform(lo, hi)
            if not lens_inside(caps, z_b, pt)[0]:
                rejected["outside"] += 1
                continue
            if unit == "Ca":
                ns, npos = ["Ca"], pt[None, :]
            else:
                ns, npos = _carbonate(pt, random_rotation(rng), r_co)
            if len(cap_pos) and not acc._ok(ns, npos, cap_sym, cap_pos, acc.DEFAULTS):
                rejected["nucleus"] += 1
                continue
            r, idx = sc.distances(npos, env)
            esym = np.array(sc.sym)[idx]
            lim = np.where(esym == "H", n["env_min_h"], n["env_min"])
            if (r < lim[None, :]).any():
                rejected["template"] += 1
                continue
            cap_sym += ns
            cap_pos = np.vstack([cap_pos, npos])
            break
        else:
            break
    # Keep the nucleus neutral: drop the last-placed unit of the species in excess
    # (never the bridging carbonate, which is placed first).
    first_free = 4 if bridge_ca is not None else 0
    while cap_sym.count("Ca") != cap_sym.count("C"):
        if cap_sym.count("Ca") > cap_sym.count("C"):
            i = len(cap_sym) - 1 - cap_sym[::-1].index("Ca")
            drop = [i]
        else:
            i = len(cap_sym) - 1 - cap_sym[::-1].index("C")
            if i < first_free:
                raise RuntimeError(f"nucleus: no Ca placed (rejections {rejected})")
            drop = list(range(i, i + 4))
        keep = [k for k in range(len(cap_sym)) if k not in drop]
        cap_sym, cap_pos = [cap_sym[k] for k in keep], cap_pos[keep]
    n_ca = cap_sym.count("Ca")
    sc.add(cap_sym, cap_pos, "nucleus")
    sc.ledger.append(("nucleus: CaCO3 formula units", 0))
    return {"target_fu": target, "placed_fu": n_ca, "attempts": attempts, "rejected": rejected,
            "volume_a3": round(vol, 3), "z_base": z_b,
            "caps": [[*np.round(c, 6).tolist(), round(r, 6)] for c, r in caps]}


def snapshot(sc):
    """Positions of every live part of the scene, keyed by component, and the anchors so far."""
    comp = np.array(sc.comp)
    out = {c: sc.pos[(comp == c) & sc.alive].copy() for c in dict.fromkeys(sc.comp)}
    out["_anchors"] = [dict(a) for a in sc.anchors]
    return out


def build(slab, chains, geom, accg, params=None, seed=0, source_ids=None, drawing_choices=None,
          trace=None):
    """Build the scene. ``chains`` maps template names to oligomers ("default" is required, or
    pass one oligomer); ``geom`` is the evidence Ca2+ shell, ``accg`` the sourced ACC geometry
    (nacre.structures.params_source.acc_geometry). ``trace``, if a list, receives
    (step, snapshot) after each step, so a failing build shows which part departed first."""
    from ase import Atoms

    if not isinstance(chains, dict):
        chains = {"default": chains}
    p = _deep(DEFAULTS, params)
    for typed in ("density_g_cm3", "co_bond"):
        if typed in (params or {}) or typed in ((params or {}).get("nucleus") or {}):
            raise ValueError(f"{typed} comes from the params record (v_m_acc, c_o_bond_length_acc), never typed")
    r_co = accg["r_co"]
    rng = np.random.default_rng(seed)
    sc = Scene(slab)
    record = trace.append if trace is not None else (lambda item: None)
    maps, used = [], []
    for i, ch in enumerate(p["chains"]):
        tmpl = chains[ch.get("template", "default")]
        maps.append(anchor_chain(sc, tmpl, ch["site"], ch["azimuth"], p, f"chain{i}"))
        used.append(tmpl)
        record((f"chain{i}", snapshot(sc)))
    n_bound_water = []
    bound = []
    for j, b in enumerate(p["bound"]):
        kind = b.get("site", "catecholate")
        chain = used[b["chain"]]
        if kind == "carboxylate":
            units = [0]
        elif b.get("unit", "auto") != "auto":
            units = [b["unit"]]
        else:
            units = sorted(set(chain.arrays["catechol"]) - {-1, 0}, reverse=True)
        for k in units:
            try:
                _, nw = ca_site(sc, maps[b["chain"]], chain, k, geom, rng, f"bound{j}", p, kind)
            except RuntimeError:
                if k == units[-1]:
                    raise
                continue
            bound.append({"chain": b["chain"], "unit": int(k), "site": kind})
            n_bound_water.append(nw)
            record((f"bound{j}", snapshot(sc)))
            break
    p["bound"] = bound
    bridge_ca = None
    n = p["nucleus"]
    if n is not None and p["bridge"] is not None:
        # The bridging site is built before the nucleus; the nucleus carbonate then takes the
        # place of the shell water that points most towards the cap.
        caps, z_b = lens(sc, n)
        br = dict(p["bridge"])
        if br["unit"] == "auto":
            centre, radius = caps[0]
            base = float(np.sqrt(radius ** 2 - (z_b - centre[2]) ** 2))
            br["unit"] = rim_unit(sc, maps[br["chain"]], used[br["chain"]], centre, base, z_b)
        p["bridge"] = br
        bridge_ca, _ = ca_site(sc, maps[br["chain"]], used[br["chain"]], br["unit"], geom, rng, "bridge", p)
        record(("bridge", snapshot(sc)))
    nuc = None
    if n is not None:
        nuc = build_nucleus(sc, p, rng, bridge_ca, geom, accg)
        record(("nucleus", snapshot(sc)))
    charge_sites = sum(q for _, q in sc.ledger)
    n_co3 = charge_sites // 2
    if charge_sites % 2 or n_co3 != len(p["carbonate"]):
        raise ValueError(f"Ca sites carry {charge_sites:+d}; give {charge_sites / 2:g} carbonate positions, "
                         f"not {len(p['carbonate'])}")
    slab_top = sc.pos[(np.array(sc.comp) == "slab") & sc.alive, 2].max()
    for k, (fx, fy, dz) in enumerate(p["carbonate"]):
        c = np.r_[sc.xy([fx, fy]), slab_top + dz]
        for _ in range(500):
            s, x = _carbonate(c, random_rotation(rng), r_co)
            r, _ = sc.distances(x)
            if r.min() >= p["carbonate_min"]:
                break
            c = c + rng.normal(scale=0.5, size=3)
        else:
            raise RuntimeError(f"carbonate{k}: no clash-free position near {(fx, fy, dz)}")
        nuc_mask = np.array(sc.comp) == "nucleus"
        if nuc_mask.any():
            far = sc.distances(x, nuc_mask)[0].min()
            if far < p["carbonate_far"]:
                raise ValueError(f"carbonate{k} lies {far:.1f} A from the nucleus; dissolved carbonate "
                                 f"must stay {p['carbonate_far']} A away")
        sc.add(s, x, f"carbonate{k}")
        sc.ledger.append((f"carbonate{k}: dissolved CO3^2-", -2))
    total = sum(q for _, q in sc.ledger)
    if total != 0:
        raise ValueError(f"hero scene charge {total:+d}, expected 0")

    alive = np.where(sc.alive)[0]
    solid = Atoms(symbols=[sc.sym[i] for i in alive], positions=sc.pos[alive], cell=sc.cell, pbc=sc.pbc)
    solid.new_array("component", np.array([sc.comp[i] for i in alive]))
    w = p["water"]
    box = None if w.get("y_cut") is None else [[0.0, 1.0], [w["y_cut"], 1.0]]
    wet = water.build(solid, {"xy_box": box, "z_base_component": "slab",
                              "gap": w["gap"], "thickness": w["thickness"],
                              "density_g_cm3": w["density_g_cm3"],
                              **({"max_attempts": w["max_attempts"]} if "max_attempts" in w else {})},
                      seed=int(rng.integers(1 << 31)))
    out = Atoms(symbols=wet.get_chemical_symbols(), positions=wet.positions, cell=sc.cell, pbc=sc.pbc)
    out.new_array("component", np.asarray(wet.arrays["component"]))
    src = dict(source_ids or {})
    stamp(
        out,
        builder="nacre.structures.hero.build",
        params={k: v for k, v in p.items()},
        seed=seed,
        source_ids=src,
        total_charge=total,
        notes="illustrative construction: hydroxylated alumina, anchored catechol oligomers, a few "
        "Ca2+ at template sites" + (", an amorphous CaCO3 nucleus as a lens of flat base on the template"
                                     if nuc else "") +
        (", a bridging Ca2+ under its rim" if bridge_ca is not None else "") +
        ", dissolved carbonate for charge balance, water above the template",
    )
    out.info["drawing_choices"] = json.dumps(drawing_choices or {}, sort_keys=True)
    out.info["charge_ledger"] = json.dumps(sc.ledger)
    out.info["anchors"] = json.dumps(sc.anchors)
    if nuc:
        out.info["nucleus_fu_target"] = nuc["target_fu"]
        out.info["nucleus_fu_placed"] = nuc["placed_fu"]
        out.info["nucleus_attempts"] = nuc["attempts"]
        out.info["nucleus_lens"] = json.dumps({"caps": nuc["caps"], "z_base": round(nuc["z_base"], 6),
                                               "volume_a3": nuc["volume_a3"]})
    out.info["bound_waters"] = json.dumps(n_bound_water)
    out.info["bridge_waters"] = int((np.asarray(out.arrays["component"]) == "bridge_water").sum() // 3)
    out.info["n_water_placed"] = int(wet.info["n_water_placed"])
    out.info["n_water_target"] = int(wet.info["n_water_target"])
    return out
