"""Scene configuration, palette and extxyz input for the renderer. No Blender imports.

This module runs both inside the Blender interpreter (via scene.py) and in the
repository environment (tests). It needs PyYAML and numpy only.

Rule R7 is enforced here: a scene config may not carry any text, label, arrow or
annotation key, so nothing but atoms and bonds can reach a render.

Scene options (all optional):

- component ``clip``: ``box`` [[x0, x1], [y0, y1]] (angstrom, structure coordinates) with
  ``seed_elements`` and ``attach`` (bond-aware crop, for the slab) or ``molecules: true``
  (whole molecules: a bonded group is kept, entire, when its centroid lies in the box;
  half a molecule is never drawn).
- component ``fade``: opacity falloff for a water shell. Each molecule's opacity is
  ``alpha`` within ``near`` of the ``reference`` components (the interface and the
  nucleus), falling linearly to zero at ``far``; molecules beyond ``far`` are not drawn.
- component ``focus: true``: the nucleus. Its meshes form the collection that the rig's
  nucleus rim light is linked to, and the depth of field can be centred on it.
- component ``bond_radius``: stick radius for that component (the template's sticks are
  slightly thicker); atom radii stay the style's, the same for every species.
- camera ``dof``: ``{focus: <component prefix>, fstop: <f>}`` focuses on the depth of the
  centroid of those atoms (Cycles depth of field).
- ``drawing_choices``: a mapping that names every unsourced drawing choice of the scene;
  it is copied into the settings log.
"""
from __future__ import annotations

import hashlib
import re
import shlex
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
RENDER_CONFIG = HERE / "render.yaml"
SCENES_DIR = HERE / "scenes"

STYLES = ("ball_and_stick", "space_filling")
SCENE_KEYS = {"name", "description", "resolution", "samples", "camera", "components", "drawing_choices"}
CAMERA_KEYS = {"direction", "up", "margin", "dof"}
DOF_KEYS = {"focus", "fstop"}
COMPONENT_KEYS = {"file", "style", "include", "exclude_elements", "translate", "clip", "fade", "focus",
                  "bond_radius"}
CLIP_KEYS = {"box", "seed_elements", "attach"}
CLIP_MOLECULE_KEYS = {"box", "molecules"}
FADE_KEYS = {"reference", "near", "far", "alpha"}
MIN_ALPHA = 0.04  # molecules fainter than this are not drawn
# R7: none of these may appear anywhere in a scene config.
FORBIDDEN_KEYS = re.compile(r"text|label|arrow|annotat|caption|legend|font", re.IGNORECASE)
# Day 1 renders stay small.
MAX_PIXELS = 1920 * 1080


class ConfigError(ValueError):
    pass


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text())


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repo_path(p) -> Path:
    p = Path(p)
    return p if p.is_absolute() else REPO_ROOT / p


# ---------------------------------------------------------------- render settings
def load_render_config(path=RENDER_CONFIG):
    cfg = load_yaml(path)
    for key in ("palette", "elements", "engine", "styles", "bonds"):
        if key not in cfg:
            raise ConfigError(f"render config missing {key}")
    eng = cfg["engine"]
    if eng.get("name") != "CYCLES" or eng.get("device") != "CPU":
        raise ConfigError("engine must be CYCLES on CPU for reproducible renders")
    for key in ("samples", "seed", "threads"):
        if not isinstance(eng.get(key), int):
            raise ConfigError(f"engine.{key} must be an integer")
    if cfg.get("film_transparent") is not True:
        raise ConfigError("film_transparent must be true (transparent background)")
    if set(cfg["styles"]) != set(STYLES):
        raise ConfigError(f"styles must define exactly {STYLES}")
    return cfg


def load_palette(path):
    """Element colours as {symbol: (r, g, b)} in linear RGB, plus the raw document."""
    doc = load_yaml(path)
    cols = {}
    for el, entry in doc["elements"].items():
        lin = entry.get("linear_rgb")
        if lin is None or len(lin) != 3:
            raise ConfigError(f"palette element {el} has no linear_rgb triple")
        cols[el] = tuple(float(x) for x in lin)
    return cols, doc


def load_radii(path):
    doc = load_yaml(path)
    return {el: e for el, e in doc["elements"].items()}


# ---------------------------------------------------------------- scene configs
def _walk_keys(obj, where="scene"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if FORBIDDEN_KEYS.search(str(k)):
                raise ConfigError(f"{where}.{k}: text, labels and arrows are not allowed in renders (R7)")
            _walk_keys(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_keys(v, f"{where}[{i}]")


def _vec3(v, where):
    if not (isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v)):
        raise ConfigError(f"{where} must be a list of three numbers")
    return [float(x) for x in v]


def parse_scene(path_or_name):
    """Load and validate a scene config; return a normalised dict."""
    path = Path(path_or_name)
    if not path.suffix:
        path = SCENES_DIR / f"{path_or_name}.yaml"
    doc = load_yaml(path)
    if not isinstance(doc, dict):
        raise ConfigError(f"{path}: not a mapping")
    _walk_keys(doc)
    unknown = set(doc) - SCENE_KEYS
    if unknown:
        raise ConfigError(f"{path}: unknown keys {sorted(unknown)}")
    if doc.get("name") != path.stem:
        raise ConfigError(f"{path}: name must equal the file stem {path.stem!r}")
    res = doc.get("resolution")
    if not (isinstance(res, list) and len(res) == 2 and all(isinstance(x, int) and x > 0 for x in res)):
        raise ConfigError(f"{path}: resolution must be [width, height] in pixels")
    if res[0] * res[1] > MAX_PIXELS:
        raise ConfigError(f"{path}: resolution above the day-1 cap of {MAX_PIXELS} pixels")
    samples = doc.get("samples")
    if samples is not None and not (isinstance(samples, int) and samples > 0):
        raise ConfigError(f"{path}: samples must be a positive integer")
    cam = doc.get("camera") or {}
    if set(cam) - CAMERA_KEYS:
        raise ConfigError(f"{path}: unknown camera keys {sorted(set(cam) - CAMERA_KEYS)}")
    camera = {
        "direction": _vec3(cam.get("direction", [0.0, 1.0, 0.0]), "camera.direction"),
        "up": _vec3(cam.get("up", [0.0, 0.0, 1.0]), "camera.up"),
        "margin": float(cam.get("margin", 1.08)),
        "dof": None,
    }
    if cam.get("dof") is not None:
        dof = cam["dof"]
        if set(dof) != DOF_KEYS or not (isinstance(dof["fstop"], (int, float)) and dof["fstop"] > 0):
            raise ConfigError(f"{path}: camera.dof needs exactly {sorted(DOF_KEYS)} with fstop > 0")
        camera["dof"] = {"focus": str(dof["focus"]), "fstop": float(dof["fstop"])}
    choices = doc.get("drawing_choices") or {}
    if not isinstance(choices, dict):
        raise ConfigError(f"{path}: drawing_choices must be a mapping")
    if np.linalg.norm(np.cross(camera["direction"], camera["up"])) < 1e-6:
        raise ConfigError(f"{path}: camera.up is parallel to camera.direction")
    comps = doc.get("components")
    if not comps:
        raise ConfigError(f"{path}: no components")
    out = []
    for i, c in enumerate(comps):
        if set(c) - COMPONENT_KEYS:
            raise ConfigError(f"{path}: component {i} unknown keys {sorted(set(c) - COMPONENT_KEYS)}")
        if c.get("style") not in STYLES:
            raise ConfigError(f"{path}: component {i} style must be one of {STYLES}")
        if "file" not in c:
            raise ConfigError(f"{path}: component {i} has no file")
        clip = c.get("clip")
        if clip is not None:
            if set(clip) not in (CLIP_KEYS, CLIP_MOLECULE_KEYS) or clip.get("molecules", True) is not True:
                raise ConfigError(f"{path}: component {i} clip needs exactly {sorted(CLIP_KEYS)} "
                                  f"or {sorted(CLIP_MOLECULE_KEYS)} with molecules: true")
            box = clip["box"]
            if not (isinstance(box, list) and len(box) == 2
                    and all(isinstance(b, list) and len(b) == 2 and b[0] < b[1] for b in box)):
                raise ConfigError(f"{path}: component {i} clip.box must be [[x0, x1], [y0, y1]] with x0 < x1")
            box = [[float(v) for v in b] for b in box]
            clip = ({"box": box, "molecules": True} if "molecules" in clip else
                    {"box": box, "seed_elements": list(clip["seed_elements"]), "attach": list(clip["attach"])})
        fade = c.get("fade")
        if fade is not None:
            if set(fade) != FADE_KEYS:
                raise ConfigError(f"{path}: component {i} fade needs exactly {sorted(FADE_KEYS)}")
            if not (0 <= fade["near"] < fade["far"] and 0 < fade["alpha"] <= 1):
                raise ConfigError(f"{path}: component {i} fade needs 0 <= near < far and 0 < alpha <= 1")
            fade = {"reference": list(fade["reference"]), "near": float(fade["near"]),
                    "far": float(fade["far"]), "alpha": float(fade["alpha"])}
        br = c.get("bond_radius")
        if br is not None and not (isinstance(br, (int, float)) and 0 < br < 0.5):
            raise ConfigError(f"{path}: component {i} bond_radius must lie in (0, 0.5) angstrom")
        out.append({
            "bond_radius": None if br is None else float(br),
            "fade": fade,
            "focus": bool(c.get("focus", False)),
            "clip": clip,
            "file": c["file"],
            "style": c["style"],
            "include": list(c.get("include", [])),
            "exclude_elements": list(c.get("exclude_elements", [])),
            "translate": _vec3(c.get("translate", [0, 0, 0]), f"component {i}.translate"),
        })
    return {"name": doc["name"], "path": str(path), "resolution": res, "samples": samples,
            "camera": camera, "components": out, "drawing_choices": dict(choices)}


# ---------------------------------------------------------------- extxyz
_KV = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


def read_extxyz(path):
    """Minimal single-frame extended-XYZ reader (the subset ASE writes for these files)."""
    lines = Path(path).read_text().splitlines()
    n = int(lines[0].split()[0])
    header = {}
    for k, v in _KV.findall(lines[1]):
        header[k] = v[1:-1].replace('\\"', '"') if v.startswith('"') else v
    props = header.get("Properties", "species:S:1:pos:R:3").split(":")
    cols = []
    for i in range(0, len(props), 3):
        cols.append((props[i], props[i + 1], int(props[i + 2])))
    data = {name: [] for name, _, _ in cols}
    for line in lines[2 : 2 + n]:
        tok = shlex.split(line)
        j = 0
        for name, typ, width in cols:
            vals = tok[j : j + width]
            j += width
            if typ == "R":
                data[name].append([float(x) for x in vals])
            elif typ == "I":
                data[name].append([int(x) for x in vals])
            else:
                data[name].append(vals[0] if width == 1 else vals)
    lattice = None
    if "Lattice" in header:
        lattice = np.array([float(x) for x in header["Lattice"].split()]).reshape(3, 3)
    pbc = [x == "T" for x in header.get("pbc", "F F F").split()]
    return {
        "symbols": list(data["species"]),
        "positions": np.array(data["pos"], dtype=float),
        "component": list(data["component"]) if "component" in data else None,
        "lattice": lattice,
        "pbc": pbc,
        "info": header,
    }


def evidence_row_ids(struct):
    """Evidence row_ids named anywhere in a structure's source ids ({} when there are none)."""
    import json

    raw = struct["info"].get("source_ids")
    try:
        src = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except ValueError:
        return {}
    found = {}

    def walk(obj, path):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "row_ids" and isinstance(v, dict):
                    found[path or "structure"] = dict(v)
                else:
                    walk(v, f"{path}.{k}" if path else k)

    walk(src, "")
    return found


def _info_json(struct, key):
    import json

    raw = struct["info"].get(key)
    try:
        return json.loads(raw) if isinstance(raw, str) else (raw or {})
    except ValueError:
        return {}


def params_keys(struct):
    """Parameter-table keys named in a structure's source ids ({part: {keys, sources}})."""
    src = _info_json(struct, "source_ids")
    return {part: {"keys": v["keys"], "sources": v.get("sources", {})}
            for part, v in src.items() if isinstance(v, dict) and "keys" in v and "params" in v}


def structure_drawing_choices(struct):
    return _info_json(struct, "drawing_choices")


def select_component(st, comp, rcfg, radii):
    """Atoms and half bonds of one scene component, after include, clip and fade.

    Atoms are (symbol, position, radius, alpha, focus, component label); half bonds are
    (symbol, start, end, radius, alpha, focus). Every atom of every component uses the
    style's atom scale; only the stick radius may be set per component.
    """
    factor, pairs = rcfg["bonds"]["factor"], rcfg["bonds"]["pairs"]
    idx = select_atoms(st, comp["include"], comp["exclude_elements"])
    if comp["clip"]:
        idx = clip_selection(st["symbols"], st["positions"], idx, comp["clip"], radii, factor, pairs)
    alpha = [1.0] * len(idx)
    if comp["fade"]:
        ref = select_atoms(st, comp["fade"]["reference"], [])
        idx, alpha = fade_alpha(st["symbols"], st["positions"], idx, ref, comp["fade"], radii, factor, pairs)
    sym = [st["symbols"][i] for i in idx]
    pos = st["positions"][idx] + np.array(comp["translate"])
    labels = [st["component"][i] if st["component"] else "" for i in idx]
    style = rcfg["styles"][comp["style"]]
    focus = comp["focus"]
    atoms = [(s, p, style["atom_scale"] * radii[s][style["atom_radius"]], a, focus, lab)
             for s, p, a, lab in zip(sym, pos, alpha, labels)]
    bonds = []
    if style.get("bonds"):
        br = comp["bond_radius"] or style["bond_radius"]
        for i, j in find_bonds(sym, pos, radii, factor, pairs):
            a = min(alpha[i], alpha[j])
            bonds.append((sym[i], pos[i], pos[j], br, a, focus))
            bonds.append((sym[j], pos[j], pos[i], br, a, focus))
    return atoms, bonds


CROSS_PAIRS = (("Al", "O"), ("Ca", "O"))


def cross_component_bonds(atoms, comp_of, radii, factor, pairs=CROSS_PAIRS):
    """Half bonds between atoms of different scene components (the anchors and the Ca shells).

    Bonds are otherwise found within a component, so without this the catechol O-Al anchor,
    the bound Ca2+ to its catecholate and the bridging Ca2+ to the nucleus carbonate would not
    be drawn. Only fully opaque atoms take part (a faded water is never bonded to a solid).
    ``atoms`` as from select_component; ``comp_of`` the component index of each atom.
    """
    elements = {e for pr in pairs for e in pr}
    sel = [k for k, a in enumerate(atoms) if a[0] in elements and a[3] >= 1.0]
    sym = [atoms[k][0] for k in sel]
    pos = np.array([atoms[k][1] for k in sel]) if sel else np.zeros((0, 3))
    out = []
    for i, j in find_bonds(sym, pos, radii, factor, pairs):
        a, b = sel[i], sel[j]
        if comp_of[a] == comp_of[b]:
            continue
        out.append((a, b))
    return out


def select_atoms(struct, include, exclude_elements):
    """Indices kept by a component filter: component prefixes and excluded elements."""
    keep = []
    comp = struct["component"]
    for i, s in enumerate(struct["symbols"]):
        if s in exclude_elements:
            continue
        if include:
            if comp is None or not any(comp[i].startswith(p) for p in include):
                continue
        keep.append(i)
    return keep


def clip_selection(symbols, positions, idx, clip, radii, factor, pairs):
    """Bond-aware crop of a selection to an in-plane box (angstrom, structure coordinates).

    Atoms of ``seed_elements`` whose x, y lie in the box are kept; then, for each element
    of ``attach`` in order, every selected atom of that element bonded to a kept atom is
    added. With seeds Al, C, N, Ca and attach O, H, a periodic slab is cut inside its cell
    with every kept Al fully coordinated and every hydroxyl attached to its Al, so the
    crop shows no detached OH groups (the cell-edge problem of a periodic slab).
    """
    if clip.get("molecules"):
        return clip_molecules(symbols, positions, idx, clip["box"], radii, factor, pairs)
    (x0, x1), (y0, y1) = clip["box"]
    pos = np.asarray(positions)
    kept = [i for i in idx if symbols[i] in clip["seed_elements"]
            and x0 <= pos[i, 0] <= x1 and y0 <= pos[i, 1] <= y1]
    allowed = {frozenset(p) for p in pairs}
    rc = {s: radii[s]["covalent"] for s in set(symbols[i] for i in idx)}
    for el in clip["attach"]:
        cand = [i for i in idx if symbols[i] == el and i not in set(kept)]
        if not cand or not kept:
            continue
        k = np.array(kept)
        d = np.linalg.norm(pos[cand][:, None, :] - pos[k][None, :, :], axis=-1)
        cut = factor * (np.array([rc[el]] * len(cand))[:, None] + np.array([rc[symbols[j]] for j in k])[None, :])
        ok_pair = np.array([[frozenset((el, symbols[j])) in allowed for j in k]] * len(cand))
        hit = ((d < cut) & ok_pair).any(axis=1)
        kept += [c for c, h in zip(cand, hit) if h]
    return sorted(kept)


def molecules(symbols, positions, radii, factor, pairs):
    """Bonded groups (lists of indices into symbols) under the bond rule of find_bonds."""
    n = len(symbols)
    parent = list(range(n))

    def root(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in find_bonds(symbols, positions, radii, factor, pairs):
        ri, rj = root(i), root(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)
    groups = {}
    for i in range(n):
        groups.setdefault(root(i), []).append(i)
    return [groups[k] for k in sorted(groups)]


def clip_molecules(symbols, positions, idx, box, radii, factor, pairs):
    """Whole-molecule crop: keep a bonded group, entire, when its centroid lies in the box."""
    (x0, x1), (y0, y1) = box
    idx = list(idx)
    sub_sym = [symbols[i] for i in idx]
    sub_pos = np.asarray(positions)[idx]
    kept = []
    for g in molecules(sub_sym, sub_pos, radii, factor, pairs):
        c = sub_pos[g].mean(axis=0)
        if x0 <= c[0] <= x1 and y0 <= c[1] <= y1:
            kept += [idx[k] for k in g]
    return sorted(kept)


def min_distances(points, others, chunk=512):
    """Distance from each point to the nearest of ``others`` (chunked, bounded memory)."""
    points, others = np.asarray(points, dtype=float), np.asarray(others, dtype=float)
    out = np.full(len(points), np.inf)
    if not len(others):
        return out
    for a in range(0, len(points), chunk):
        d = np.linalg.norm(points[a : a + chunk, None, :] - others[None, :, :], axis=-1)
        out[a : a + chunk] = d.min(axis=1)
    return out


def fade_alpha(symbols, positions, idx, ref_idx, fade, radii, factor, pairs):
    """Opacity per kept atom of a faded component and the atoms that remain drawn.

    The distance of a molecule is that of its atom nearest to the reference atoms; its
    opacity is ``alpha`` up to ``near`` and falls linearly to zero at ``far``. Molecules
    below MIN_ALPHA are dropped whole. Returns (indices, alphas).
    """
    idx = list(idx)
    pos = np.asarray(positions)
    d = min_distances(pos[idx], pos[list(ref_idx)])
    sub_sym = [symbols[i] for i in idx]
    keep, alpha = [], []
    for g in molecules(sub_sym, pos[idx], radii, factor, pairs):
        dm = float(d[g].min())
        a = fade["alpha"] * float(np.clip((fade["far"] - dm) / (fade["far"] - fade["near"]), 0.0, 1.0))
        if a >= MIN_ALPHA:
            keep += [idx[k] for k in g]
            alpha += [a] * len(g)
    order = np.argsort(keep, kind="stable")
    return [keep[k] for k in order], [alpha[k] for k in order]


def find_bonds(symbols, positions, radii, factor, pairs, chunk=512):
    """Bonded pairs (i, j), i < j: allowed element pair and distance below factor x sum of covalent radii.

    Rows are processed in chunks so that memory stays bounded for scenes of many atoms;
    the pairs come out in the same (row-major) order as a full distance matrix gives.
    """
    allowed = {frozenset(p) for p in pairs}
    pos = np.asarray(positions, dtype=float)
    rc = np.array([radii[s]["covalent"] for s in symbols])
    out = []
    for a in range(0, len(pos), chunk):
        d = np.linalg.norm(pos[a : a + chunk, None, :] - pos[None, :, :], axis=-1)
        cut = factor * (rc[a : a + chunk, None] + rc[None, :])
        hit = d < cut
        rows = np.arange(a, a + len(d))
        hit &= np.arange(len(pos))[None, :] > rows[:, None]
        ii, jj = np.where(hit)
        out += [(int(a + i), int(j)) for i, j in zip(ii, jj)
                if frozenset((symbols[a + i], symbols[j])) in allowed]
    return out
