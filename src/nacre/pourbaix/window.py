"""R-cell: the Li-referenced thermodynamic stability window (claim C5, item 20).

Thermodynamic question: between which electrode potentials, on the Li+/Li scale, is a phase
(CaCO3, Al2O3) at equilibrium against lithiation and against oxidation? The window is a
thermodynamic statement. Outside it a decomposition is favoured, but the window says nothing
about whether or how fast that decomposition happens (no kinetic statement).

Convention (W3 contract, function E_window): a reaction releases Delta_n_Li Li atoms to the
Li+/Li reservoir (negative when Li is taken up) and has free energy Delta_G_r with Li metal as
the reference. Its grand-potential change is Delta_G_r - Delta_n_Li F E, which vanishes at
E_window = Delta_G_r / (Delta_n_Li F). E_red is the maximum over reactions with
Delta_n_Li < 0 and E_ox the minimum over reactions with Delta_n_Li > 0. With energies in eV per
formula unit, E_window in volts is Delta_G_r / Delta_n_Li.

Reduction (lithiation) limits come from the Li-open grand potential (0 K DFT energies, MP2020
corrections). The Li-open construction gives no delithiation reaction for a phase without Li,
so its oxidation limit would be unbounded (W3 open question Q9). The oxidation limit is
therefore computed from explicit oxidation reactions:

    phase + x Li-salt -> cation sink + O2(g) [+ CO2(g)] + n Li

The electrons released by oxidising the oxide or carbonate anion are referenced to Li/Li+
through the Li formed at the reference. Charge balance needs the cation to go somewhere: the
`sink`, a named phase pairing the cation with the electrolyte anion that the Li salt supplies.
Solids enter at their MP formation energies (entropy neglected). Gases enter as
dfH - T S + k T ln(p / 1 bar): O2 with dfH = 0, because the MP2020 oxide correction is fitted
against the computed O2 reference, and S(T) from NIST-JANAF; CO2 with dfH from NIST-JANAF
(scheme `janaf`) or from the MP CO2 molecular solid (scheme `mp`, sublimation not included).
Every candidate reaction is reported. The lowest onset within the active sink is the
conditional oxidation limit, stated beside its sink assumption.

Guard: no phase is ever reported with an unbounded window. A limit that cannot be determined
carries status `undetermined` and a reason, and `screen_pass` treats it as a fail.
"""
import math
from dataclasses import asdict, dataclass, field

import numpy as np
from scipy import constants

K_B_EV = constants.k / constants.e  # Boltzmann constant, eV K^-1


class UnboundedWindowError(RuntimeError):
    """A window limit is infinite without an explicit `undetermined` flag."""


class MissingPhase(KeyError):
    """A phase needed by a reaction is absent from the cached data."""


def e_window(delta_g_ev, delta_n_li):
    """W3 contract E_window with energies in eV per formula unit: Delta_G_r / Delta_n_Li (V)."""
    if delta_n_li == 0:
        raise ValueError("Delta_n_Li = 0: a reaction that exchanges no Li sets no potential limit")
    return delta_g_ev / delta_n_li


def e_window_si(delta_g_j_per_mol, delta_n_li):
    """W3 contract E_window in SI form: Delta_G_r / (Delta_n_Li F), V."""
    if delta_n_li == 0:
        raise ValueError("Delta_n_Li = 0: a reaction that exchanges no Li sets no potential limit")
    return delta_g_j_per_mol / (delta_n_li * constants.e * constants.N_A)


@dataclass
class Limit:
    value: float | None
    status: str  # "finite" | "undetermined"
    reason: str = ""
    reaction: str = ""
    method: str = ""
    delta_g_ev: float | None = None
    delta_n_li: float | None = None


@dataclass
class Candidate:
    phase: str
    sink: str
    product: str
    reaction: str
    status: str  # "finite" | "undetermined" | "rejected"
    onset_V: float | None = None
    delta_g_ev: float | None = None
    delta_n_li: float | None = None
    reason: str = ""
    species: dict = field(default_factory=dict)


@dataclass
class Window:
    phase: str
    reduction: Limit
    oxidation: Limit
    sink: str
    notes: list = field(default_factory=list)

    def as_dict(self):
        return {"phase": self.phase, "sink": self.sink, "reduction": asdict(self.reduction),
                "oxidation": asdict(self.oxidation), "notes": list(self.notes)}


def guard(window):
    """Raise UnboundedWindowError unless each limit is finite or explicitly undetermined."""
    for side in (window.reduction, window.oxidation):
        if side.status == "undetermined":
            if side.value is not None:
                raise UnboundedWindowError("%s: undetermined limit carries a value" % window.phase)
            if not side.reason:
                raise UnboundedWindowError("%s: undetermined limit without a reason" % window.phase)
            continue
        if side.status != "finite" or side.value is None or not math.isfinite(side.value):
            raise UnboundedWindowError("%s: unbounded or missing limit (%s)" % (window.phase, side))
    return window


def screen_pass(window, e_low, e_high):
    """True only if both limits are finite and the window contains [e_low, e_high]."""
    guard(window)
    if window.reduction.status != "finite" or window.oxidation.status != "finite":
        return False
    return window.reduction.value <= e_low and window.oxidation.value >= e_high


# ------------------------------------------------------------------------- reduction (Li-open)
def li_open_limits(pd, phase_entry):
    """Li-open grand-potential limits of a phase from a phase diagram containing Li.

    Returns (reduction Limit, oxidation Limit). For a phase without Li the oxidation side is
    returned with value +inf and status "finite" on purpose: that is the raw Li-open answer,
    and `build_window` must replace it. `guard` refuses it if it ever reaches a result.
    """
    from pymatgen.core import Composition, Element

    li = Element("Li")
    comp = phase_entry.composition.reduced_composition
    fu = phase_entry.composition.get_reduced_composition_and_factor()[1]
    e_phase = phase_entry.energy / fu
    mu0 = pd.el_refs[li].energy_per_atom
    e_hull = pd.get_e_above_hull(phase_entry)
    profile = pd.get_element_profile(li, comp)

    def reaction_limit(n_li):
        # n_li Li taken up (>0) or released (<0) per formula unit, products on the hull
        total = Composition(comp.as_dict()) + Composition({"Li": n_li}) if n_li > 0 else comp
        dg = pd.get_hull_energy(total) - e_phase - n_li * mu0
        return dg, -n_li

    lithiation = sorted({round(float(s["evolution"]), 10) for s in profile if s["evolution"] > 1e-9})
    if lithiation:
        n = lithiation[0]
        dg, dn = reaction_limit(n)
        rxn = next(str(s["reaction"]) for s in profile if abs(s["evolution"] - n) < 1e-8)
        red = Limit(e_window(dg, dn), "finite", reaction=rxn, delta_g_ev=dg, delta_n_li=dn,
                    method="Li-open grand potential, first lithiation reaction on the hull")
    else:
        red = Limit(None, "undetermined", reason="no lithiation reaction on the Li-open hull",
                    method="Li-open grand potential")
    if comp[li] > 0:
        # Delithiation of a Li-bearing phase: not needed for CaCO3 or Al2O3; kept explicit.
        ox = Limit(None, "undetermined", reason="delithiation limits of Li-bearing phases are "
                   "not implemented in this session", method="Li-open grand potential")
    else:
        ox = Limit(math.inf, "finite", reason="Li-free phase: the Li-open grand potential has no "
                   "reaction with Delta_n_Li > 0 (open question Q9)",
                   method="Li-open grand potential")
    red_note = {"e_above_hull_eV_per_atom": float(e_hull)}
    return red, ox, red_note


# ------------------------------------------------------------------------ oxidation reactions
def balance(reactants, products, fixed):
    """Balance a reaction with pymatgen and return {formula: coefficient} (reactants < 0).

    `fixed` names the formula whose coefficient is normalised to -1 (the phase).
    """
    from pymatgen.analysis.reaction_calculator import Reaction
    from pymatgen.core import Composition

    rcomps = [Composition(f) for f in reactants]
    pcomps = [Composition(f) for f in products]
    rxn = Reaction(rcomps, pcomps)
    rxn.normalize_to(Composition(fixed), 1.0)
    coeffs = {}
    for f in list(reactants) + list(products):
        c = Composition(f)
        coeffs[f] = float(rxn.get_coeff(c)) if c in rxn.all_comp else 0.0
    return coeffs, str(rxn)


def oxidation_candidate(phase, cation, sink_id, sink, product, energy, gases):
    """One explicit oxidation reaction of `phase` with the cation going to `product`.

    energy(formula) -> (G_eV per formula unit, metadata) or raises MissingPhase.
    `gases` lists the gas products (O2, and CO2 for a carbonate).
    """
    li_src = sink["li_source"]
    reactants = [phase, li_src]
    products = [product] + list(gases) + ["Li"]
    try:
        coeffs, text = balance(reactants, products, phase)
    except Exception as exc:  # noqa: BLE001 - pymatgen raises ReactionError and others
        return Candidate(phase, sink_id, product, "%s + %s -> %s" % (phase, li_src, " + ".join(products)),
                         "rejected", reason="cannot balance: %s" % exc)
    expected = {phase: -1, li_src: -1, product: 1, "Li": 1, **{g: 1 for g in gases}}
    wrong = [f for f, s in expected.items() if coeffs.get(f, 0.0) * s <= 0]
    if wrong:
        return Candidate(phase, sink_id, product, text, "rejected",
                         reason="not an oxidation as written; coefficient sign or zero for %s" % wrong)
    species = {}
    dg = 0.0
    for f, c in coeffs.items():
        try:
            g, meta = energy(f)
        except MissingPhase as exc:
            return Candidate(phase, sink_id, product, text, "undetermined",
                             reason="phase %s absent from the cached data" % exc.args[0])
        species[f] = {"coefficient": c, "G_eV": g, **meta}
        dg += c * g
    dn = coeffs["Li"]
    return Candidate(phase, sink_id, product, text, "finite", onset_V=e_window(dg, dn),
                     delta_g_ev=dg, delta_n_li=dn, species=species)


def oxidation_candidates(phase, cation, sinks, energy, gases):
    """Every candidate reaction across every sink definition."""
    out = []
    for sink_id, sink in sinks.items():
        if sink.get("kind") == "solvated":
            out.append(Candidate(phase, sink_id, "%s(solv)" % cation, "", "undetermined",
                                 reason=sink.get("reason") or "requires the free energy of the "
                                 "dissolved cation relative to Li+ in the electrolyte; not in "
                                 "the cached data"))
            continue
        for product in sink["products"].get(cation, []):
            out.append(oxidation_candidate(phase, cation, sink_id, sink, product, energy, gases))
        if not sink["products"].get(cation):
            out.append(Candidate(phase, sink_id, "", "", "undetermined",
                                 reason="sink %s defines no product for %s" % (sink_id, cation)))
    return out


def conditional_oxidation_limit(candidates, active_sink):
    """Lowest finite onset among the active sink's candidates, or undetermined."""
    mine = [c for c in candidates if c.sink == active_sink]
    finite = [c for c in mine if c.status == "finite"]
    if not mine:
        return Limit(None, "undetermined", reason="no oxidation reaction supplied for sink %s"
                     % active_sink, method="explicit oxidation reactions")
    if not finite:
        reasons = "; ".join(c.reason for c in mine if c.reason)
        return Limit(None, "undetermined", reason="no computable oxidation reaction for sink %s: %s"
                     % (active_sink, reasons), method="explicit oxidation reactions")
    best = min(finite, key=lambda c: (c.onset_V, c.reaction))
    return Limit(best.onset_V, "finite", reaction=best.reaction, delta_g_ev=best.delta_g_ev,
                 delta_n_li=best.delta_n_li,
                 method="explicit oxidation reactions, lowest onset within sink %s" % active_sink)


def build_window(phase, reduction, li_open_ox, candidates, active_sink):
    """Combine the Li-open reduction limit with the explicit oxidation limit, then guard."""
    notes = []
    if li_open_ox.status == "finite" and li_open_ox.value is not None and math.isinf(li_open_ox.value):
        notes.append("Li-open oxidation limit unbounded (%s); replaced by explicit oxidation "
                     "reactions" % li_open_ox.reason)
        ox = conditional_oxidation_limit(candidates, active_sink)
    else:
        ox = li_open_ox
    return guard(Window(phase, reduction, ox, active_sink, notes))


# --------------------------------------------------------------------------- energy book
class EnergyBook:
    """Free energies per formula unit (eV) for the oxidation reactions at temperature T.

    Solids: MP formation energy (0 K, MP2020 corrections) of the lowest-energy entry with that
    reduced formula, or of a pinned material id. Gases: dfH - T S + k T ln(p / 1 bar).
    """

    def __init__(self, entries, T, gas_settings, gas_tables, pinned=None):
        from pymatgen.core import Composition

        self.T = float(T)
        self.gas_settings = gas_settings
        self.gas_tables = gas_tables
        self.pinned = dict(pinned or {})
        self._by_formula = {}
        self._mu = {}
        for e in entries:
            comp = e.composition
            if len(comp.elements) == 1:
                el = str(comp.elements[0])
                self._mu[el] = min(self._mu.get(el, math.inf), e.energy_per_atom)
        for e in entries:
            self._by_formula.setdefault(e.composition.reduced_formula, []).append(e)
        self._Composition = Composition

    def formation_energy(self, entry):
        comp = entry.composition
        return entry.energy - sum(n * self._mu[str(el)] for el, n in comp.items())

    def solid(self, formula):
        from nacre.pourbaix.entries import entry_key, material_id

        comp = self._Composition(formula)
        cands = self._by_formula.get(comp.reduced_formula, [])
        if formula in self.pinned:
            cands = [e for e in cands if material_id(e) == self.pinned[formula]]
        if not cands:
            raise MissingPhase(formula)
        best = min(cands, key=lambda e: e.energy_per_atom)
        fu_ratio = comp.num_atoms / best.composition.num_atoms
        g = self.formation_energy(best) * fu_ratio
        return g, {"kind": "solid", "entry_id": entry_key(best), "material_id": material_id(best),
                   "basis": "MP formation energy, 0 K, MP2020; entropy neglected"}

    def gas(self, species):
        from nacre.pourbaix import gas as gasmod

        s = self.gas_settings[species]
        p = float(s["pressure_bar"])
        entropy = gasmod.entropy_ev_per_K(species, self.T, self.gas_tables)
        scheme = s.get("enthalpy_scheme", "mp_fitted_reference" if species == "O2" else "janaf")
        if species == "O2":
            if scheme != "mp_fitted_reference":
                raise ValueError("O2 enthalpy scheme must be mp_fitted_reference")
            dfh = 0.0
            basis = "dfH = 0 (MP2020 oxide correction fitted against the computed O2 reference)"
        elif scheme == "janaf":
            dfh = gasmod.formation_enthalpy_ev(species, self.T, self.gas_tables)
            basis = "dfH from NIST-JANAF"
        elif scheme == "mp":
            dfh, _ = self.solid(species)
            basis = "dfH from the MP %s molecular solid (sublimation not included)" % species
        else:
            raise ValueError("unknown enthalpy scheme %r" % scheme)
        g = dfh - self.T * entropy + K_B_EV * self.T * math.log(p)
        return g, {"kind": "gas", "scheme": scheme, "dfH_eV": dfh, "S_eV_per_K": entropy,
                   "pressure_bar": p, "basis": basis + "; S(T) from NIST-JANAF",
                   "locator": gasmod.locator(species, self.T, self.gas_tables)}

    def __call__(self, formula):
        if formula == "Li":
            return 0.0, {"kind": "reference", "basis": "Li metal, the Li+/Li reference"}
        if formula in self.gas_settings:
            return self.gas(formula)
        return self.solid(formula)


def chemical_decomposition(book, phase, products):
    """Free energy (eV per formula unit) of a non-redox decomposition, e.g. CaCO3 -> CaO + CO2.

    Negative would mean the phase is unstable without any electrochemistry at this T and p.
    """
    coeffs, text = balance([phase], products, phase)
    return sum(c * book(f)[0] for f, c in coeffs.items()), text


def finite_or_none(x):
    return None if x is None or not np.isfinite(x) else float(x)
