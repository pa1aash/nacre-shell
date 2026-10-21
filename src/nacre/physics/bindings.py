"""W1-key to contract-symbol bindings (cp5a fix X3; PH-W4.2c).

The binding table is configs/preprint/symbol_bindings.yaml. This module holds the conversions and applies the
table: a key whose binding is unresolved, whose value is a gap, whose scale or form is unnamed or mismatched, or
whose converted value leaves the contract interval of its symbol yields status "undetermined", never a silently
converted number. No prior, threshold or verdict rule is touched here.

Conventions
  log10 K -> beta: beta = 10^x, base 10, activities on the molal scale, standard state m° = 1 mol kg^-1
      (symbols.yaml: m_std), dimensionless.
  Delta_G_gc = H_phase - T S_resid, with the residual entropy of the glass over the crystal, S_resid in
      [0, R ln 2] per PO3 (claims_redirect.md 10b point 3, a labelled assumption with no source).
  Delta_G_tr_rel = DG_tr(M) - z DG_tr(Li+), form A (single ions on one named scale) or form B (the salt form
      DG_tr(M(ClO4)z) - z DG_tr(LiClO4)); both forms are in J mol^-1 and the solvent must be the same.
"""
import math
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from nacre.physics.constants import GAS_CONSTANT

ROOT = Path(__file__).resolve().parents[3]
BINDINGS_PATH = ROOT / "configs" / "preprint" / "symbol_bindings.yaml"

OK = "ok"
UNDETERMINED = "undetermined"
HYDRATION_SCALES = ("marcus1991", "tissandier", "conventional")
DEFAULT_T = 298.15

#: Open and closed ends of the contract intervals (theory/symbols.yaml) of the bound symbols.
INTERVALS = {
    "beta_AlPP": (0.0, math.inf, True, False),
    "K_sp_AlPP": (0.0, math.inf, False, False),
    "gamma_nl_c": (0.0, math.inf, False, False),
    "Delta_G_gc": (0.0, math.inf, True, False),
    "k_hyd": (0.0, math.inf, False, False),
    "Delta_G_tr_rel": (-math.inf, math.inf, False, False),
    "Delta_G_hyd": (-math.inf, 0.0, False, False),
    "Gamma_P": (0.0, math.inf, False, False),
    "K_P": (0.0, math.inf, False, False),
    "delta_P": (0.0, math.inf, False, False),
}


@dataclass(frozen=True)
class Bound:
    """Result of a binding: a contract-side value or "undetermined" with the reason."""

    status: str
    symbol: str
    value: float = None
    unit: str = None
    reason: str = ""
    scale: str = None
    form: str = None
    solvent: str = None
    notes: dict = field(default_factory=dict)

    @property
    def ok(self):
        return self.status == OK


def _undetermined(symbol, reason, unit=None, **kw):
    return Bound(UNDETERMINED, symbol, None, unit, reason, **kw)


def _in_interval(symbol, x):
    lo, hi, lo_closed, hi_closed = INTERVALS[symbol]
    above = x >= lo if lo_closed else x > lo
    below = x <= hi if hi_closed else x < hi
    return above and below


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _checked(symbol, x, unit, reason_if_out="outside the contract interval of the symbol", **kw):
    if not _in_interval(symbol, x):
        return _undetermined(symbol, "%s: %s = %r" % (reason_if_out, symbol, x), unit, **kw)
    return Bound(OK, symbol, float(x), unit, **kw)


# ---------------------------------------------------------------- conversions (pure functions)

def log10_to_beta(x):
    """beta = 10^x: base 10, molal activity scale, standard state m° = 1 mol kg^-1; dimensionless."""
    return 10.0 ** x


def beta_to_log10(beta):
    """Inverse of log10_to_beta; beta must be positive."""
    if not beta > 0:
        raise ValueError("beta must be positive for a log10")
    return math.log10(beta)


def residual_entropy_ceiling(n_po3):
    """R ln 2 per PO3 times n_PO3, J K^-1 mol^-1 per formula unit: the registered upper bound of S_resid."""
    return n_po3 * GAS_CONSTANT * math.log(2.0)


def delta_g_gc(h_phase, s_resid, n_po3, temperature=DEFAULT_T):
    """Delta_G_gc = H_phase - T S_resid (J mol^-1 per formula unit), glass minus crystal.

    h_phase is the enthalpy difference (J mol^-1), never a free energy. s_resid is the named second input, the
    residual entropy of the glass over the crystal per formula unit in J K^-1 mol^-1, bounded by 0 <= s_resid <=
    n_po3 R ln 2 (PO3 groups in the formula unit). Raises ValueError outside the bound.
    """
    if not (_finite(h_phase) and _finite(s_resid) and _finite(n_po3) and _finite(temperature)):
        raise ValueError("delta_g_gc needs finite numbers")
    if n_po3 <= 0 or temperature <= 0:
        raise ValueError("n_po3 and temperature must be positive")
    ceiling = residual_entropy_ceiling(n_po3)
    if not 0.0 <= s_resid <= ceiling * (1.0 + 1e-12):
        raise ValueError("s_resid %r outside the registered bound [0, %r] J K^-1 mol^-1" % (s_resid, ceiling))
    return h_phase - temperature * s_resid


def delta_g_gc_ends(h_phase, n_po3, temperature=DEFAULT_T):
    """(Delta_G_gc at S_resid = 0, at S_resid = n_PO3 R ln 2): the ends used for E_lb and E_ub respectively."""
    return (delta_g_gc(h_phase, 0.0, n_po3, temperature),
            delta_g_gc(h_phase, residual_entropy_ceiling(n_po3), n_po3, temperature))


_GAMMA_P_TO_MOL_M2 = {"mol m^-2": 1.0, "mmol m^-2": 1e-3, "umol m^-2": 1e-6, "nmol m^-2": 1e-9}
_GAMMA_P_MASS_TO_G_M2 = {"g m^-2": 1.0, "mg m^-2": 1e-3, "ug m^-2": 1e-6}
_LENGTH_TO_M = {"m": 1.0, "mm": 1e-3, "um": 1e-6, "nm": 1e-9, "angstrom": 1e-10}


def gamma_p_to_mol_m2(value, unit, molar_mass_g_mol=None):
    """Gamma_P in mol m^-2 from an amount (mol, mmol, umol, nmol m^-2) or, with the molar mass of the PO3 chain
    unit supplied by the caller, a mass per area (g, mg, ug m^-2). Anything else raises ValueError."""
    if unit in _GAMMA_P_TO_MOL_M2:
        return value * _GAMMA_P_TO_MOL_M2[unit]
    if unit in _GAMMA_P_MASS_TO_G_M2:
        if not (_finite(molar_mass_g_mol) and molar_mass_g_mol > 0):
            raise ValueError("a mass density needs the molar mass (g mol^-1) of the chain unit")
        return value * _GAMMA_P_MASS_TO_G_M2[unit] / molar_mass_g_mol
    raise ValueError("unit %r of Gamma_P is not convertible to mol m^-2" % (unit,))


def k_p_activity_form(value, unit):
    """K_P, dimensionless in the activity form (Theta = K_P a_P / (1 + K_P a_P)). A concentration-form constant
    (L mol^-1 and the like) would need an activity coefficient and a standard state: raises ValueError."""
    if unit == "1":
        return value
    raise ValueError("K_P unit %r is not the activity form ('1'); no silent conversion" % (unit,))


def delta_p_to_m(value, unit):
    """delta_P in m from m, mm, um, nm or angstrom."""
    if unit in _LENGTH_TO_M:
        return value * _LENGTH_TO_M[unit]
    raise ValueError("unit %r of delta_P is not a length" % (unit,))


# ---------------------------------------------------------------- the table

def load_bindings(path=BINDINGS_PATH):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _find(table, key):
    """(binding, key record) for a W1 key: an exact entry of a binding's `keys`, else None."""
    for b in table["bindings"]:
        rec = (b.get("keys") or {}).get(key)
        if rec is not None:
            return b, rec
    return None, None


def binding_for(table, key):
    return _find(table, key)[0]


def bind(key, value=None, table=None, **inputs):
    """Bind one W1 key and its value to the contract symbol; "undetermined" whenever the table says so.

    value is the W1 value in the key's W1 unit (None for a gap). Extra inputs by conversion:
      enthalpy_plus_entropy_bound (Delta_G_gc): s_resid (J K^-1 mol^-1 per formula unit), temperature (K).
      ads_unit (Gamma_P, K_P, delta_P): unit, molar_mass_g_mol.
    A single-ion transfer or a hydration key returns the value tagged with its scale; combine with
    delta_g_tr_rel and require_one_hydration_scale.
    """
    table = table or load_bindings()
    b, rec = _find(table, key)
    if b is None:
        return _undetermined("?", "no binding entry for key %r" % key)
    symbol = b["contract_symbol"]
    default = b["default"]
    if rec.get("status") != "resolved":
        return _undetermined(symbol, "unresolved: %s" % rec.get("reason", b.get("reason", "")), b["contract_unit"])
    if rec.get("role") == "slot":
        return _undetermined(symbol, "matrix or route slot only; not an input of any barrier or K1 formula", None)
    if value is None:
        return _undetermined(symbol, "gap: the key has no value", b["contract_unit"])
    if not _finite(value):
        return _undetermined(symbol, "non-finite value", b["contract_unit"])
    conv = b["conversion"]["name"]
    unit = b["contract_unit"]
    if conv == "log10_to_linear":
        return _checked(symbol, log10_to_beta(value), unit)
    if conv == "identity":
        out = _checked(symbol, value, unit)
        return replace(out, notes={"role": rec["role"]}) if out.ok and rec.get("role") else out
    if conv == "enthalpy_plus_entropy_bound":
        if "s_resid" not in inputs:
            return _undetermined(symbol, "H_phase is an enthalpy: the entropy bound s_resid is a required input", unit)
        try:
            g = delta_g_gc(value, inputs["s_resid"], rec["n_PO3"], inputs.get("temperature", DEFAULT_T))
        except ValueError as e:
            return _undetermined(symbol, str(e), unit)
        return _checked(symbol, g, unit, "Delta_G_gc must be >= 0 (the glass lies above the crystal)")
    if conv == "single_ion_transfer":
        if not rec.get("scale"):
            return _undetermined(symbol, "single-ion scale not named", unit)
        return Bound(OK, "DG_tr_single_ion", float(value), unit, scale=rec["scale"], form="A",
                     solvent=rec.get("solvent"), notes={"ion": rec.get("ion")})
    if conv == "hydration_by_scale":
        scale = rec.get("scale")
        if scale not in HYDRATION_SCALES:
            return _undetermined(symbol, "hydration scale not named", unit)
        return _checked(symbol, value, unit, "absolute Delta_G_hyd is negative; a conventional-scale value needs the proton "
                        "value added on a named real scale", scale=scale)
    if conv == "ads_unit":
        symbol, unit = rec["symbol"], rec["unit"]
        try:
            u = inputs["unit"]
            if symbol == "Gamma_P":
                x = gamma_p_to_mol_m2(value, u, inputs.get("molar_mass_g_mol"))
            elif symbol == "K_P":
                x = k_p_activity_form(value, u)
            else:
                x = delta_p_to_m(value, u)
        except (KeyError, ValueError) as e:
            return _undetermined(symbol, "unit of the adsorption key not established: %s" % e, unit)
        return _checked(symbol, x, unit)
    return _undetermined(symbol, "unknown conversion %r" % conv, unit)


def delta_g_tr_rel(cation, li, z, form="A", salt=None, li_salt=None):
    """Delta_G_tr_rel = DG_tr(M) - z DG_tr(Li+) in J mol^-1.

    Form A: cation and li are single-ion Bounds (from bind) on the same named scale and the same solvent.
    Form B: salt and li_salt are Bounds of DG_tr(M(ClO4)z) and DG_tr(LiClO4), taken from salt data with
    form="B" (the anion cancels); a Bound for a single ion is refused as a salt value. A scale mismatch, an unnamed
    scale or a different solvent gives "undetermined".
    """
    sym = "Delta_G_tr_rel"
    unit = "J mol^-1"
    if not (_finite(z) and z > 0):
        return _undetermined(sym, "ion charge z must be positive", unit)
    if form == "A":
        a, b = cation, li
        if not (a.ok and b.ok):
            return _undetermined(sym, "single-ion input undetermined: %s" % (a.reason or b.reason), unit, form="A")
        if not a.scale or not b.scale:
            return _undetermined(sym, "single-ion scale not named", unit, form="A")
        if a.scale != b.scale:
            return _undetermined(sym, "scale mismatch: %s versus %s (not converted)" % (a.scale, b.scale), unit, form="A")
        if a.solvent != b.solvent:
            return _undetermined(sym, "solvent mismatch: %s versus %s" % (a.solvent, b.solvent), unit, form="A")
        return Bound(OK, sym, a.value - z * b.value, unit, scale=a.scale, form="A", solvent=a.solvent)
    if form == "B":
        a, b = salt, li_salt
        if a is None or b is None or not (a.ok and b.ok):
            return _undetermined(sym, "salt-form input missing or undetermined", unit, form="B")
        if a.form != "B" or b.form != "B":
            return _undetermined(sym, "form B needs salt values (form B), not single-ion values", unit, form="B")
        if a.solvent != b.solvent:
            return _undetermined(sym, "solvent mismatch: %s versus %s" % (a.solvent, b.solvent), unit, form="B")
        return Bound(OK, sym, a.value - z * b.value, unit, form="B", solvent=a.solvent)
    return _undetermined(sym, "form must be 'A' (single ion) or 'B' (salt)", unit)


def salt_bound(value, solvent, unit="J mol^-1"):
    """A salt-form transfer energy (form B) as a Bound, for delta_g_tr_rel(form='B')."""
    if not _finite(value):
        return _undetermined("DG_tr_salt", "non-finite value", unit, form="B", solvent=solvent)
    return Bound(OK, "DG_tr_salt", float(value), unit, form="B", solvent=solvent)


def require_one_hydration_scale(*bounds):
    """True only when every Bound is ok and all share one named hydration scale; never converts between scales."""
    if not bounds or not all(b.ok and b.scale in HYDRATION_SCALES for b in bounds):
        return False
    return len({b.scale for b in bounds}) == 1
