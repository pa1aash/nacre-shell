"""Axis titles from the theory symbol register (theory/symbols.yaml, lane p0-w3).

The register gives each symbol id its LaTeX form and SI unit; the titles set it as mathtext in
the figure font. Quantities the screen reports in units of k_B T, and axes that need a unit
other than SI (degrees, V on a named scale), are composed here from register ids only.
"""
from nacre.figs import upstream

# Units written the way the register writes them -> axis-title form. A unit not listed here is
# printed as the register gives it.
_UNIT_TEXT = {"1": None, "rad": "rad", "V": "V", "J m^-2": r"J m$^{-2}$", "J mol^-1": r"J mol$^{-1}$"}


def entry(sym_id, root):
    table = upstream.symbols(root)
    if sym_id not in table:
        raise KeyError("symbol %r not in theory/symbols.yaml (%s)" % (sym_id, upstream.cite("symbols", root)))
    return table[sym_id]


def symbol(sym_id, root):
    """The register's LaTeX form as mathtext."""
    return "$%s$" % entry(sym_id, root)["latex"]


def unit_text(sym_id, root):
    u = entry(sym_id, root)["unit"]
    return _UNIT_TEXT.get(u, u)


def axis_title(sym_id, root, unit=None):
    """'symbol (unit)'; unit overrides the register's SI unit (for example '°' for an angle)."""
    u = unit if unit is not None else unit_text(sym_id, root)
    return symbol(sym_id, root) if not u else "%s (%s)" % (symbol(sym_id, root), u)


def per_kT(sym_id, root):
    """'X / k_B T' for an energy the screen reports in units of the thermal energy."""
    return "$%s/%s%s$" % (entry(sym_id, root)["latex"], entry("k_B", root)["latex"], entry("T", root)["latex"])


def potential_title(sym_id, root, scale):
    """Potential axis on a named reference scale, e.g. 'E_SHE (V vs SHE)'."""
    return "%s (V vs %s)" % (symbol(sym_id, root), scale)
