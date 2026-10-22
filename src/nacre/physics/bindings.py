"""W1-key to contract-symbol bindings (cp5a fix X3; PH-W4.2c, revised PH-W4.2d).

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
      DG_tr(M(ClO4)z) - z DG_tr(LiClO4)); both forms are in J mol^-1, one solvent, one scale and one source.
  E_lb uses only the aqueous standard Gibbs energies of formation (keys dfg_*_aq, one scale); E_PC = E_aq +
      Delta_G_tr_rel/(n F). Hydration free energies are kept for a labelled Born-model comparison, never for E_lb.
  K_P = K c0, c0 = 1 mol dm^-3 (molar, dimensionless), activity-based (k_p_from_k); a molal K is divided by the water
      density (kg dm^-3), a per-litre K is multiplied by c0 after unit scaling; nothing is copied.
  Single-ion transfer energies: every benchmark ion is declared on the TATB scale (Marcus 1983, mol dm^-3 scale); a value on
      another scale is converted by no rule and is excluded, so DG_tr_rel mixes no scales.
  window_margin* keys belong to the frozen carbonate control and never reach a phosphate row.
"""
import math
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from nacre.physics.constants import FARADAY, GAS_CONSTANT

ROOT = Path(__file__).resolve().parents[3]
BINDINGS_PATH = ROOT / "configs" / "preprint" / "symbol_bindings.yaml"

OK = "ok"
UNDETERMINED = "undetermined"
INDICATIVE = "indicative"
AQ_SCALE = "conventional_aq_standard"
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
    "G_phase": (-math.inf, math.inf, False, False),
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


C0_MOLAR = 1.0
"""c0 = 1 mol dm^-3, the standard concentration of K_P (molar, dimensionless, activity-based)."""
_K_PER_VOLUME_TO_DM3_MOL = {"dm^3 mol^-1": 1.0, "L mol^-1": 1.0, "M^-1": 1.0, "m^3 mol^-1": 1.0e3, "cm^3 mol^-1": 1.0e-3,
                            "mL mol^-1": 1.0e-3}
_K_MOLAL_UNITS = ("kg mol^-1",)
K_P_SCALES = ("molar_c0", "molal_m0")


def k_p_from_k(value, unit, basis="activity", rho_water_kg_dm3=None, scale=None):
    """K_P = K c0 with c0 = 1 mol dm^-3: the dimensionless, activity-based Langmuir constant of the molar scale.

    A literature K is converted, never copied:
      per-litre forms (dm^3 mol^-1, L mol^-1, M^-1, m^3 mol^-1, cm^3 mol^-1, mL mol^-1): K_P = K[dm^3 mol^-1] c0;
      molal form (kg mol^-1) or a dimensionless constant declared on the molal scale (m° = 1 mol kg^-1): with
        c = rho_w m for a dilute aqueous solution, Theta = K_m m = K_m c / rho_w, so K_c = K_m / rho_w and
        K_P = K_m c0 / rho_w, rho_w in kg dm^-3 (required, e.g. water_density / 1000);
      a dimensionless constant needs its scale declared (molar_c0 or molal_m0): an unlabelled "1" is refused.
    basis must be "activity": a concentration quotient is not an activity constant, so it is refused. Raises ValueError.
    """
    if basis != "activity":
        raise ValueError("K_P is activity-based: basis %r (a concentration quotient) is refused, not copied" % (basis,))
    if not _finite(value):
        raise ValueError("K needs a finite number")
    if unit in _K_PER_VOLUME_TO_DM3_MOL:
        return value * _K_PER_VOLUME_TO_DM3_MOL[unit] * C0_MOLAR
    molal = unit in _K_MOLAL_UNITS or (unit == "1" and scale == "molal_m0")
    if molal:
        if not (_finite(rho_water_kg_dm3) and rho_water_kg_dm3 > 0):
            raise ValueError("a molal K needs the density of water (kg dm^-3) for the conversion to the molar scale")
        return value * C0_MOLAR / rho_water_kg_dm3
    if unit == "1" and scale == "molar_c0":
        return value
    raise ValueError("K unit %r (scale %r) is not convertible to the molar activity form K_P = K c0" % (unit, scale))


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
      ads_unit (Gamma_P, K_P, delta_P): unit, molar_mass_g_mol; K_P also scale, basis, rho_water_kg_dm3 (k_p_from_k).
    A single-ion transfer or a hydration key returns the value tagged with its scale; combine with
    delta_g_tr_rel and require_one_hydration_scale.
    """
    table = table or load_bindings()
    b, rec = _find(table, key)
    if b is None:
        return _undetermined("?", "no binding entry for key %r" % key)
    symbol = rec.get("symbol", b["contract_symbol"]) if b["conversion"]["name"] != "ads_unit" else b["contract_symbol"]
    if b.get("carbonate_control_only"):
        return _undetermined(symbol, "frozen carbonate control only; a phosphate margin is the derived m_K1 of block v6", b["contract_unit"])
    if b.get("proxy_forbidden") and rec.get("status") != "resolved":
        return _undetermined(symbol, "unresolved: %s (never a proxy for the linear chain-unit constant)" % rec.get("reason", ""), b["contract_unit"])
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
        return single_ion_bound(value, rec["scale"], rec.get("solvent"), rec.get("ion"),
                                inputs.get("source") or rec.get("source"))
    if conv == "aqueous_formation_energy" and rec.get("role") == "e_lb_input":
        notes = {"role": rec["role"], "uncertainty": rec.get("uncertainty")}
        return _checked(symbol, value, unit, scale=rec["scale"], notes=notes)
    if conv == "hydration_by_scale" or rec.get("role") == "born_comparison_only":
        scale = rec.get("scale")
        if scale not in HYDRATION_SCALES:
            return _undetermined(symbol, "hydration scale not named", unit)
        return _checked(symbol, value, unit, "absolute Delta_G_hyd is negative; a conventional-scale value needs the proton "
                        "value added on a named real scale", scale=scale, notes={"role": "born_comparison_only"})
    if conv == "ads_unit":
        symbol, unit = rec["symbol"], {"Gamma_P": "mol m^-2", "K_P": "1", "delta_P": "m"}[rec["symbol"]]
        try:
            u = inputs["unit"]
            if symbol == "Gamma_P":
                x = gamma_p_to_mol_m2(value, u, inputs.get("molar_mass_g_mol"))
            elif symbol == "K_P":
                x = k_p_from_k(value, u, inputs.get("basis", "activity"), inputs.get("rho_water_kg_dm3"),
                               inputs.get("scale"))
            else:
                x = delta_p_to_m(value, u)
        except (KeyError, ValueError) as e:
            return _undetermined(symbol, "unit of the adsorption key not established: %s" % e, unit)
        return _checked(symbol, x, unit)
    return _undetermined(symbol, "unknown conversion %r" % conv, unit)


def single_ion_bound(value, scale, solvent, ion=None, source=None, unit="J mol^-1"):
    """A single-ion transfer energy (form A) as a Bound; an unnamed scale or solvent is undetermined."""
    if not _finite(value):
        return _undetermined("DG_tr_single_ion", "non-finite value", unit, form="A")
    if not scale or not solvent:
        return _undetermined("DG_tr_single_ion", "single-ion scale or solvent not named", unit, form="A")
    return Bound(OK, "DG_tr_single_ion", float(value), unit, scale=scale, form="A", solvent=solvent,
                 notes={"ion": ion, "source": source})


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
        sa, sb = a.notes.get("source"), b.notes.get("source")
        if sa != sb:
            return _undetermined(sym, "source mismatch: %s versus %s (one method only)" % (sa, sb), unit, form="A")
        return Bound(OK, sym, a.value - z * b.value, unit, scale=a.scale, form="A", solvent=a.solvent)
    if form == "B":
        a, b = salt, li_salt
        if a is None or b is None or not (a.ok and b.ok):
            return _undetermined(sym, "salt-form input missing or undetermined", unit, form="B")
        if a.form != "B" or b.form != "B":
            return _undetermined(sym, "form B needs salt values (form B), not single-ion values", unit, form="B")
        if a.solvent != b.solvent:
            return _undetermined(sym, "solvent mismatch: %s versus %s" % (a.solvent, b.solvent), unit, form="B")
        if a.notes.get("source") != b.notes.get("source"):
            return _undetermined(sym, "source mismatch: %s versus %s (one method only)" % (a.notes.get("source"), b.notes.get("source")), unit, form="B")
        return Bound(OK, sym, a.value - z * b.value, unit, form="B", solvent=a.solvent)
    return _undetermined(sym, "form must be 'A' (single ion) or 'B' (salt)", unit)


def salt_bound(value, solvent, unit="J mol^-1", source=None):
    """A salt-form transfer energy (form B) as a Bound, for delta_g_tr_rel(form='B')."""
    if not _finite(value):
        return _undetermined("DG_tr_salt", "non-finite value", unit, form="B", solvent=solvent)
    return Bound(OK, "DG_tr_salt", float(value), unit, form="B", solvent=solvent, notes={"source": source})


def require_one_hydration_scale(*bounds):
    """True only when every Bound is ok and all share one named hydration scale; never converts between scales."""
    if not bounds or not all(b.ok and b.scale in HYDRATION_SCALES for b in bounds):
        return False
    return len({b.scale for b in bounds}) == 1


def delta_g_r_aq(terms, table=None):
    """Delta_G_r_aq (J mol^-1) = sum nu_i G_i over (key, nu, value) terms, nu signed (products positive).

    Only the dfg_*_aq keys of the table (role e_lb_input, one scale) are admitted: any other key, in particular a
    hydration free energy, a gap, or a second scale, gives "undetermined". The uncertainty is "tabulated" only when
    every term has one.
    """
    sym = "Delta_G_r_aq"
    unit = "J mol^-1"
    table = table or load_bindings()
    total, scales, tabulated = 0.0, set(), True
    for key, nu, value in terms:
        r = bind(key, value, table=table)
        if not (r.ok and r.notes.get("role") == "e_lb_input"):
            return _undetermined(sym, "%s is not an aqueous formation energy of E_lb (%s)" % (key, r.reason or r.notes.get("role")), unit)
        scales.add(r.scale)
        tabulated = tabulated and r.notes.get("uncertainty") == "tabulated"
        total += nu * r.value
    if len(scales) != 1:
        return _undetermined(sym, "terms are not on one scale", unit)
    return Bound(OK, sym, total, unit, scale=scales.pop(), notes={"uncertainty": "tabulated" if tabulated else "none"})


def e_lb(terms, delta_n_li, table=None):
    """E_lb = Delta_G_r_aq/(Delta_n_Li F) in V, from dfg_*_aq keys only."""
    g = delta_g_r_aq(terms, table)
    if not g.ok:
        return _undetermined("E_lb", g.reason, "V")
    if not (_finite(delta_n_li) and delta_n_li > 0):
        return _undetermined("E_lb", "Delta_n_Li must be positive", "V")
    return Bound(OK, "E_lb", g.value / (delta_n_li * FARADAY), "V", scale=g.scale, notes=g.notes)


def e_pc(e_aq, dg_tr_rel, n_li):
    """E_PC = E_aq + Delta_G_tr_rel/(n F) in V. Notes carry lower_bound: True iff Delta_G_tr_rel >= 0 (E_aq is then a
    lower bound of E_PC); a negative relative transfer energy violates the premise and E_aq is not a bound."""
    if not (e_aq.ok and dg_tr_rel.ok and e_aq.symbol == "E_lb" and dg_tr_rel.symbol == "Delta_G_tr_rel"):
        return _undetermined("E_PC", "E_lb or Delta_G_tr_rel undetermined", "V")
    if not (_finite(n_li) and n_li > 0):
        return _undetermined("E_PC", "n must be positive", "V")
    return Bound(OK, "E_PC", e_aq.value + dg_tr_rel.value / (n_li * FARADAY), "V", scale=e_aq.scale,
                 solvent=dg_tr_rel.solvent, notes={"lower_bound": dg_tr_rel.value >= 0.0})


def indicative_beta(value):
    """A beta_AlPP computed by the selectivity calculation, as an indicative input: never ok, never gates."""
    if not (_finite(value) and value >= 0):
        return _undetermined("beta_AlPP", "non-finite or negative indicative value", "1")
    return Bound(INDICATIVE, "beta_AlPP", float(value), "1", reason="indicative only; never gates",
                 notes={"gates": False})
