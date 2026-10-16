"""Scene configuration, palette and extxyz input for the renderer. No Blender imports.

This module runs both inside the Blender interpreter (via scene.py) and in the
repository environment (tests). It needs PyYAML and numpy only.

Rule R7 is enforced here: a scene config may not carry any text, label, arrow or
annotation key, so nothing but atoms and bonds can reach a render.
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
SCENE_KEYS = {"name", "description", "resolution", "samples", "camera", "components"}
CAMERA_KEYS = {"direction", "up", "margin"}
COMPONENT_KEYS = {"file", "style", "include", "exclude_elements", "translate"}
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
    }
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
        out.append({
            "file": c["file"],
            "style": c["style"],
            "include": list(c.get("include", [])),
            "exclude_elements": list(c.get("exclude_elements", [])),
            "translate": _vec3(c.get("translate", [0, 0, 0]), f"component {i}.translate"),
        })
    return {"name": doc["name"], "path": str(path), "resolution": res, "samples": samples,
            "camera": camera, "components": out}


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


def find_bonds(symbols, positions, radii, factor, pairs):
    """Bonded pairs (i, j): allowed element pair and distance below factor x sum of covalent radii."""
    allowed = {frozenset(p) for p in pairs}
    pos = np.asarray(positions)
    rc = np.array([radii[s]["covalent"] for s in symbols])
    d = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=-1)
    cut = factor * (rc[:, None] + rc[None, :])
    ii, jj = np.where(np.triu(d < cut, k=1))
    return [(int(i), int(j)) for i, j in zip(ii, jj)
            if frozenset((symbols[i], symbols[j])) in allowed]
