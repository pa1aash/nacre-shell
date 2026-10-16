"""Figure system for the preprint: RSC style, palette, panel letters, the figure checker and the builder.

Layout of the repository it works on:
  figures/style/   rsc_spec.yaml, rsc.mplstyle (generated), palette.yaml (generated)
  figures/src/     figN.py templates, mock/*.json inputs, schemas/*.json
  figures/out/     figN.pdf and figN.png; mock output only under figures/out/mock/
"""
from pathlib import Path


def paths(root):
    root = Path(root)
    fig = root / "figures"
    return {
        "root": root,
        "style": fig / "style",
        "src": fig / "src",
        "mock": fig / "src" / "mock",
        "schemas": fig / "src" / "schemas",
        "out": fig / "out",
        "out_mock": fig / "out" / "mock",
    }
