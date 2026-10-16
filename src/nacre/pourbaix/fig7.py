"""Figure 7 input: the R-slurry (pH, E) panel in the shape of W6's Fig 7 schema, and the list of
differences that remain between that schema and schema v2 (decision D4).

The export holds one design point, the central one (a_Ca at the middle of the provisional
grid, C_T at the dic_slurry value); every other point is in its own schema v2 document.
"""
import json

import numpy as np

from nacre.pourbaix import final as F
from nacre.pourbaix import provenance, slurry
from nacre.pourbaix.paths import rel

# Differences between W6's assumed Fig 7 schema (6bcb801) and schema v2, after this session.
DIFFERENCES = [
    "regimes must hold exactly two (pH, E) panels; R-cell is a one-dimensional window vs Li+/Li "
    "(schema v2 stability.R-cell). W6 needs a window panel that reads stability.R-cell.windows, as W4.2 states.",
    "domains[].phase allows solid and aqueous only; equilibrium domains are mixtures (schema v2 domain_identity "
    "kind: solid | aqueous | gas | mixed). The export writes the v2 kind, so mixed domains fail W6's enum.",
    "domains[].species is one joined label; schema v2 carries a component list (domain_identity.components). "
    "The export keeps the joined label and adds nothing W6 rejects.",
    "potential_range has no reference electrode; schema v2 fixes SHE for R-slurry and Li+/Li for R-cell.",
    "no field for decomposition energies, design axes (a_Ca, C_T), the ACC dissolution margin or the "
    "falsifiability control; schema v2 holds the first in decomposition_energy and W5's summary the rest.",
    "W6 has no place for the design axes: one figure panel is one design point. Schema v2 also has one state per "
    "document, so W5 writes one document per design point (results/preprint/pourbaix/final/slurry/).",
]


def export_slurry(summary, out_dir):
    """Write fig7_pourbaix_input.json for the central design point and its schema check."""
    pts = summary["points"]
    a_grid = summary["design_axes"]["a_Ca"]["grid"]
    a_mid = a_grid[len(a_grid) // 2]
    centre = next(p for p in pts if p["a_Ca"] == a_mid and p["C_T"]["from"] == "value")
    S = F.setup()
    ph = np.linspace(summary["axes"]["pH"]["min"], summary["axes"]["pH"]["max"], summary["axes"]["pH"]["n"])
    E = np.linspace(summary["axes"]["E_V_SHE"]["min"], summary["axes"]["E_V_SHE"]["max"], summary["axes"]["E_V_SHE"]["n"])
    doc = json.loads(open(centre["document"] if centre["document"].startswith("/") else
                          str(provenance.REPO / centre["document"]), encoding="utf-8").read())
    off = doc["stability"]["R-slurry"]["states"]["bulk"]["conditions"]["acc_offset"]["eV_per_formula_unit"]
    _, _, _, pd = F.domain_map(S, centre["a_Ca"], centre["C_T"]["mol_kg"],
                               doc["stability"]["R-slurry"]["states"]["bulk"]["conditions"]["a_Al_total_map"],
                               ph, E, off)
    limits = [[float(ph[0]), float(ph[-1])], [float(E[0]), float(E[-1])]]
    water = slurry.water_lines(ph)
    fig = {
        "mock": False, "schema": "fig7-pourbaix/assumed-v0",
        "note": "Exported by lane p0-w5 (P0-W5.2) from %s, the central design point. Potentials in V vs SHE. "
                "R-cell is not a (pH, E) panel; see final/cell/. Thermodynamic proxy, no rates." % centre["document"],
        "provenance": summary["provenance"],
        "regimes": [{"id": "R-slurry", "conditions": {"a_Ca": centre["a_Ca"], "C_T_mol_kg": centre["C_T"]["mol_kg"],
                                                      "reference_electrode": "SHE"},
                     "ph_range": limits[0], "potential_range": limits[1],
                     "domains": [{"species": d["label"], "phase": d["kind"], "polygon": d["polygon"]}
                                 for d in slurry.polygons(pd, limits)],
                     "water_lines": [{"kind": k, "points": [[float(ph[0]), float(water[k][0])],
                                                            [float(ph[-1]), float(water[k][-1])]]}
                                     for k in ("upper", "lower")]}],
    }
    path = out_dir / "fig7_pourbaix_input.json"
    path.write_text(json.dumps(fig, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    check = provenance.validate_against(provenance.W6_SCHEMA_PIN, fig)
    check["differences_remaining"] = DIFFERENCES
    cpath = out_dir / "fig7_schema_check.json"
    cpath.write_text(json.dumps(check, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return [path, cpath]


__all__ = ["export_slurry", "DIFFERENCES", "rel"]
