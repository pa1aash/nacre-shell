"""The Ca_T by C_T design grid of the slurry screen, read from a K2 output and the parameter table.

Shared by the dose-window figures: design-axis values such as '0.0001 mol dm^-3' and
'dic_slurry@min' become mol m^-3 (the register's unit), cells become grids, and the cell edges
and the Omega_bulk = 1 contour are computed for plotting.
"""
import re

import numpy as np

CA_UNITS = {"mol dm^-3": 1e3, "mol m^-3": 1.0}  # to mol m^-3 (1 dm^3 = 1e-3 m^3)


def ca_t(text):
    m = re.fullmatch(r"\s*([0-9.eE+-]+)\s*(.+?)\s*", text)
    if not m or m.group(2) not in CA_UNITS:
        raise ValueError("dosegrid: cannot read the Ca_T design value %r" % text)
    return float(m.group(1)) * CA_UNITS[m.group(2)]


def param_value(params, key, at="value"):
    """A row of the parameter table: its value, or its range end 'min' or 'max'."""
    row = params["params"][key]
    return float(row["value"] if at == "value" else row["range"][at])


def c_t(text, params):
    """C_T in mol m^-3 from a design-axis value such as 'dic_slurry@min'."""
    key, at = text.split("@")
    if params["params"][key]["unit"] != "mol m^-3":
        raise ValueError("dosegrid: %s is not in mol m^-3" % key)
    return param_value(params, key, at)


def select(cells, **fixed):
    """The cells whose design axes match `fixed` (axis name -> value)."""
    return [c for c in cells.values() if all(c["axes"].get(k) == v for k, v in fixed.items())]


def grid(cells, params, **fixed):
    """(Ca_T values, C_T values, {(i_ct, j_ca): cell}) over the selected cells; refuses a gap or a duplicate."""
    chosen = select(cells, **fixed)
    pts = {}
    for c in chosen:
        key = (c_t(c["axes"]["C_T"], params), ca_t(c["axes"]["Ca_T"]))
        if key in pts:
            raise ValueError("dosegrid: two cells at C_T=%g, Ca_T=%g for %s" % (*key, fixed))
        pts[key] = c
    cts = sorted({k[0] for k in pts})
    cas = sorted({k[1] for k in pts})
    if len(pts) != len(cts) * len(cas):
        raise ValueError("dosegrid: the cells do not fill the Ca_T by C_T grid for %s" % fixed)
    return np.asarray(cas), np.asarray(cts), {(cts.index(k[0]), cas.index(k[1])): v for k, v in pts.items()}


def edges_log(c):
    lc = np.log10(c)
    mid = (lc[1:] + lc[:-1]) / 2.0
    return 10 ** np.concatenate([[lc[0] - (mid[0] - lc[0])], mid, [lc[-1] + (lc[-1] - mid[-1])]])


def edges_lin(c):
    mid = (c[1:] + c[:-1]) / 2.0
    return np.concatenate([[c[0] - (mid[0] - c[0])], mid, [c[-1] + (c[-1] - mid[-1])]])


def omega_one_line(cas, cts, cell_grid, log10_ksp):
    """Segments of Omega_bulk = 1 at the median activities, interpolated in (log10 Ca_T, C_T)."""
    import contourpy
    z = np.empty((len(cts), len(cas)))
    for (i, j), c in cell_grid.items():
        z[i, j] = np.log10(c["a_Ca_median"] * c["a_CO3_median"]) - log10_ksp
    gen = contourpy.contour_generator(x=np.log10(cas), y=cts, z=z, line_type="Separate")
    return [np.column_stack([10 ** seg[:, 0], seg[:, 1]]) for seg in gen.lines(0.0)]
