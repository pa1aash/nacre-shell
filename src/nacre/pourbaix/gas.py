"""Gas-phase thermochemistry from the cached NIST-JANAF tables.

The tables give, per temperature row, S (J K^-1 mol^-1), H - H(298.15) and the standard enthalpy
and Gibbs energy of formation (kJ mol^-1). Values between rows are interpolated linearly in T.
Nothing here is typed: every number comes from the cached table text, with the table URL as
its locator.
"""
import numpy as np

from nacre.pourbaix import cache
from nacre.pourbaix.entries import KJ_PER_MOL_PER_EV

COLUMNS = ["T", "Cp", "S", "minus_G_minus_Href_over_T", "H_minus_Href", "dfH", "dfG", "logKf"]


def parse_janaf(text):
    """Numeric rows of a JANAF table as a dict of numpy arrays keyed by COLUMNS."""
    rows = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < len(COLUMNS):
            continue
        try:
            vals = [float(p) if p.strip().upper() != "INFINITE" else np.nan for p in parts[:len(COLUMNS)]]
        except ValueError:
            continue
        rows.append(vals)
    if not rows:
        raise ValueError("no numeric rows in JANAF table")
    arr = np.array(rows)
    return {c: arr[:, i] for i, c in enumerate(COLUMNS)}


def table(species, cache_dir=cache.CACHE_DIR):
    rec = cache.load("janaf_%s.json" % species, cache_dir)
    t = parse_janaf(rec["text"])
    t["url"] = rec["request"]["url"]
    return t


def _interp(t, col, T):
    T = float(T)
    if not t["T"][0] <= T <= t["T"][-1]:
        raise ValueError("T = %s K outside the JANAF table range" % T)
    return float(np.interp(T, t["T"], t[col]))


def entropy_ev_per_K(species, T, cache_dir=cache.CACHE_DIR):
    """Standard molar entropy S(T) of a gas, eV K^-1 per molecule."""
    return _interp(table(species, cache_dir), "S", T) / 1000.0 / KJ_PER_MOL_PER_EV


def formation_enthalpy_ev(species, T, cache_dir=cache.CACHE_DIR):
    """Standard enthalpy of formation dfH(T) of a gas, eV per molecule."""
    return _interp(table(species, cache_dir), "dfH", T) / KJ_PER_MOL_PER_EV


def formation_free_energy_ev(species, T, cache_dir=cache.CACHE_DIR):
    """Standard Gibbs energy of formation dfG(T), eV per formula unit (gas or condensed table)."""
    return _interp(table(species, cache_dir), "dfG", T) / KJ_PER_MOL_PER_EV


def row_kj(species, T, cache_dir=cache.CACHE_DIR):
    """The table's dfH, dfG (kJ mol^-1) and S (J K^-1 mol^-1) at T, as printed (interpolated)."""
    t = table(species, cache_dir)
    return {"dfH_kJ_per_mol": _interp(t, "dfH", T), "dfG_kJ_per_mol": _interp(t, "dfG", T),
            "S_J_per_K_mol": _interp(t, "S", T), "table": t["url"]}


def locator(species, T, cache_dir=cache.CACHE_DIR):
    t = table(species, cache_dir)
    return "%s, row(s) bracketing T = %s K" % (t["url"], T)
