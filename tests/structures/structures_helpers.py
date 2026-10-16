"""Helpers shared by the lane p0-w7 tests (structure builders and the render scene system)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BLENDER_DIR = REPO / "figures" / "blender"
STRUCT_DIR = REPO / "structures" / "preprint"
RENDER_DIR = REPO / "figures" / "renders"


def load_blender_module(name):
    """Import figures/blender/<name>.py under a unique module name (no Blender needed)."""
    path = BLENDER_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"p0w7_blender_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def committed_structures():
    manifest = json.loads((STRUCT_DIR / "manifest.json").read_text())
    return {name: STRUCT_DIR / entry["file"] for name, entry in manifest.items()}
