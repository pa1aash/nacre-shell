"""R-slurry final run (P0-W5.2, task B): the aqueous Pourbaix screen over the design axes.

Thermodynamic questions, at each design point (free Ca2+ activity a_Ca, total dissolved
carbonate C_T) over the registered (pH, E vs SHE) region:

1. Which Al-, Ca- and C(IV)-bearing state is at equilibrium? (domain map)
2. How far above that equilibrium do calcite, ACC, corundum, boehmite, diaspore and the Al(OH)3
   ground state sit, in eV per atom? (decomposition energies; 0 means stable)
3. With every crystalline Ca carbonate excluded, is ACC stable against dissolution, and by how
   much? (the ACC-specific dissolution margin, cp2 ruling F6, a labelled sensitivity)
4. Without any Ca phase, is the native Al oxide the equilibrium state of Al? (bare-oxide
   baseline; it does not gate C5)

All are equilibrium proxies: a positive decomposition energy says a phase is not the
equilibrium state, never how fast it dissolves or corrodes.

Construction (see results/preprint/pourbaix/config/final.yaml for the reasons):

- Carbon is held in the C(IV) carbonate system: reduced-carbon ions and solids are excluded from
  the decision hull, because the regime fixes a_CO3 as an input. The unconstrained case (carbon
  redox allowed) is computed for calcite as a labelled sensitivity.
- Exact closed-system speciation per pH column for the Ca-C decision quantities. With the free
  Ca2+ activity and C_T fixed, the dissolved state is Ca2+ at a_Ca and CO3^2- at alpha2(pH) C_T;
  every other dissolved Ca or C(IV) species at equilibrium has the same chemical potential, so
  these two ions are exact (ideal solution). alpha2 uses the acid constants implied by the cached
  ion energies, so the speciation is consistent with the diagram; W1's pK values are reported
  beside them.
- The domain map uses the Pourbaix predominance convention (each C(IV) ion at C_T, Al ions at
  the total dissolved Al), stated in each output.
- Solids are filtered once, on the full solid set, exactly as the library does with
  filter_solids (stable on the solid phase diagram with H and O referenced to water); the C(IV)
  constraint is applied afterwards, so the diagrams never need an elemental C solid. The named
  phases are evaluated against the hull whether or not they are on it.
"""
import math
import warnings

import numpy as np
from scipy import constants

from nacre.pourbaix import entries as pe
from nacre.pourbaix import slurry

K_B_EV = constants.k / constants.e
EV_PER_J_PER_MOL = 1.0 / (constants.e * constants.N_A)  # eV per (J mol^-1), per formula unit
T_K = slurry.T_POURBAIX_K
C4_IONS = ("CO2(aq)", "HCO3[-]", "CO3[2-]")
AL_ROLES = ("corundum", "boehmite", "diaspore", "gibbsite")
CA_ROLES = ("calcite", "ACC")
OX = {"H": 1, "O": -2, "Ca": 2, "Al": 3, "Na": 1}


def _pbx():
    from pymatgen.analysis import pourbaix_diagram as m

    return m


# ------------------------------------------------------------------------- species selection
def carbon_oxidation_state(entry):
    """Oxidation state of C in an entry from fixed states of H, O, Ca, Al, Na (None if no C)."""
    comp = entry.composition
    n_c = comp["C"] if "C" in {str(e) for e in comp.elements} else 0
    if not n_c:
        return None
    charge = getattr(getattr(entry, "entry", entry), "ion", None)
    q = charge.charge if charge is not None else 0
    total = sum(OX[str(el)] * n for el, n in comp.items() if str(el) != "C")
    return (q - total) / n_c


def is_c4_or_c_free(entry):
    ox = carbon_oxidation_state(entry)
    return ox is None or abs(ox - 4.0) < 1e-9


def stable_solids(solids):
    """Solids on the solid phase diagram with H and O referenced to water: the library's own
    filter_solids step (pymatgen PourbaixDiagram), applied once to the full solid set."""
    from pymatgen.analysis.phase_diagram import PhaseDiagram
    from pymatgen.entries.computed_entries import ComputedEntry

    # O at 2.46 eV: the library's reference of O to water in Pourbaix entries
    ho = [ComputedEntry("H", 0), ComputedEntry("O", 2.46)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pd = PhaseDiagram(list(solids) + ho)
    stable = set(pd.stable_entries) - set(ho)
    return sorted([e for e in solids if e in stable], key=lambda e: str(e.entry_id))


def elements_of(entry):
    return {str(el) for el in entry.composition.elements} - {"O", "H"}


def subsystem(entries, elts, c4=True):
    return [e for e in entries if elements_of(e) <= set(elts) and elements_of(e)
            and (not c4 or is_c4_or_c_free(e))]


def diagram(entries, conc, comp):
    m = _pbx()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return m.PourbaixDiagram(entries, comp_dict=comp, conc_dict=conc, filter_solids=False)


# ------------------------------------------------------------------------------ carbonate
def ion_by_name(entries, name):
    for e in entries:
        if e.phase_type == "Ion" and e.name == name:
            return e
    raise KeyError(name)


def implied_constants(entries):
    """pKa1, pKa2 of C(IV) and log10 Ksp of calcite implied by the cached energies (298.15 K)."""
    spec = slurry.carbonate_speciation(entries, np.array([7.0]), 1.0)
    roles = pe.polymorph_roles()
    calcite = pe.solid_by_id(entries, roles["calcite"]["entry_id"])
    ca = ion_by_name(entries, "Ca[2+]").entry.energy
    co3 = ion_by_name(entries, "CO3[2-]").entry.energy
    fu = calcite.entry.composition.get_reduced_composition_and_factor()[1]
    dg = ca + co3 - calcite.entry.energy / fu  # CaCO3 -> Ca2+ + CO3^2-, eV per formula unit
    # the library's own (rounded) Nernst prefactor, so the constant matches the diagram's boundary
    prefac = _pbx().PREFAC
    return {"pKa1": spec["pKa1"], "pKa2": spec["pKa2"],
            "log10_ksp_calcite": -dg / prefac, "dissolution_dG_eV": dg,
            "nernst_prefactor_eV": prefac, "kT_ln10_eV": K_B_EV * T_K * math.log(10.0)}


def alpha2(ph, pka1, pka2):
    h = 10.0 ** (-np.asarray(ph, float))
    k1, k2 = 10.0 ** (-pka1), 10.0 ** (-pka2)
    return k1 * k2 / (h * h + k1 * h + k1 * k2)


# ------------------------------------------------------------------------------- entries
def acc_entry(calcite, offset_ev):
    """ACC as calcite plus an offset in eV per CaCO3 formula unit."""
    return slurry.acc_entry(calcite, offset_ev * pe.KJ_PER_MOL_PER_EV)


def setup(cache_dir=None):
    """Cached entries, named phases and the C(IV)-constrained species pools."""
    from nacre.pourbaix import cache

    kw = {} if cache_dir is None else {"cache_dir": cache_dir}
    all_entries = pe.slurry_entries(("Al", "C", "Ca"), **kw)
    roles = pe.polymorph_roles(**kw)
    named = {r: pe.solid_by_id(all_entries, roles[r]["entry_id"]) for r in ("calcite",) + AL_ROLES}
    solids = [e for e in all_entries if e.phase_type == "Solid"]
    ions = [e for e in all_entries if e.phase_type == "Ion"]
    pruned = stable_solids(solids)
    return {"all": all_entries, "roles": roles, "named": named, "solids": pruned, "ions": ions,
            "cache": cache}


# ----------------------------------------------------------------------- Ca-C decision grids
def _ca_c_pool(S, c4=True, exclude_carbonates=False):
    sol = subsystem(S["solids"], ("Ca", "C"), c4=c4)
    if exclude_carbonates:
        sol = [e for e in sol if not ("Ca" in elements_of(e) and "C" in elements_of(e))]
    return sol


def ca_c_exact(S, a_ca, c_t, ph, E, offset_ev, consts, exclude_carbonates=False, target="calcite"):
    """Decomposition energy grid [E, pH] (eV/atom) of calcite or ACC in the C(IV) Ca-C subsystem,
    exact speciation per pH column (Ca2+ at a_Ca, CO3^2- at alpha2 C_T)."""
    ca_ion = ion_by_name(S["all"], "Ca[2+]")
    co3 = ion_by_name(S["all"], "CO3[2-]")
    acc = acc_entry(S["named"]["calcite"], offset_ev)
    pool = _ca_c_pool(S, exclude_carbonates=exclude_carbonates) + [ca_ion, co3, acc]
    tgt = acc if target == "ACC" else S["named"]["calcite"]
    a2 = alpha2(ph, consts["pKa1"], consts["pKa2"])
    out = np.empty((len(E), len(ph)))
    for j, p in enumerate(ph):
        pd = diagram(pool, {"Ca": a_ca, "C": float(a2[j] * c_t)}, {"Ca": 0.5, "C": 0.5})
        out[:, j] = pd.get_decomposition_energy(tgt, np.full(len(E), p), np.asarray(E, float))
    return out


def ca_c_unconstrained(S, a_ca, c_t, ph, E):
    """Calcite decomposition energy with carbon redox allowed (all C ions at C_T, predominance;
    every C solid): the labelled sensitivity."""
    ions = [e for e in S["ions"] if elements_of(e) <= {"Ca", "C"} and e.name != "CaOH[+]"]
    pool = subsystem(S["solids"], ("Ca", "C"), c4=False) + ions
    pd = diagram(pool, {"Ca": a_ca, "C": c_t}, {"Ca": 0.5, "C": 0.5})
    PH, EE = np.meshgrid(ph, E)
    return np.asarray(pd.get_decomposition_energy(S["named"]["calcite"], PH, EE), float)


# --------------------------------------------------------------------------- Al baseline
def al_baseline(S, a_al, ph, E):
    """Decomposition energies (eV/atom) of the Al phases with no Ca present, and the Al domains."""
    pool = subsystem(S["solids"], ("Al",)) + [e for e in S["ions"] if elements_of(e) == {"Al"}]
    pd = diagram(pool, {"Al": a_al}, {"Al": 1.0})
    PH, EE = np.meshgrid(ph, E)
    dec = {r: np.asarray(pd.get_decomposition_energy(S["named"][r], PH, EE), float) for r in AL_ROLES}
    stable, idx = slurry.assign_domains(pd, ph, E)
    return dec, [slurry.label(s) for s in stable], idx


# ---------------------------------------------------------------------------- domain map
def domain_map(S, a_ca, c_t, a_al, ph, E, offset_ev):
    """Al-Ca-C(IV) equilibrium domains (predominance convention) and the cross compounds."""
    ions = [e for e in S["ions"] if (elements_of(e) == {"Al"}) or e.name == "Ca[2+]"
            or e.name in C4_IONS]
    acc = acc_entry(S["named"]["calcite"], offset_ev)
    pool = subsystem(S["solids"], ("Al", "Ca", "C")) + ions + [acc]
    pd = diagram(pool, {"Al": a_al, "Ca": a_ca, "C": c_t}, {"Al": 1 / 3, "Ca": 1 / 3, "C": 1 / 3})
    stable, idx = slurry.assign_domains(pd, ph, E)
    cross = sorted({c.name for s in stable for c in getattr(s, "entry_list", [s])
                    if "Al" in elements_of(c) and elements_of(c) & {"Ca", "C"}})
    phases = []
    for i, s in enumerate(stable):
        comps = getattr(s, "entry_list", [s])
        phases.append({"index": i, "label": slurry.label(s), "kind": slurry.phase_kind(s),
                       "components": [{"species": c.name,
                                       "kind": {"Solid": "solid", "Ion": "aqueous"}.get(c.phase_type, "solid"),
                                       "material_id": (c.entry.data or {}).get("material_id") or None
                                       if c.phase_type == "Solid" else None}
                                      for c in sorted(comps, key=lambda c: c.name)]})
    return phases, idx, cross, pd


# ------------------------------------------------------------------------------- controls
def experimental_omega(a_ca, c_t, ph, pk1, pk2, log10_ksp):
    """Omega = a_Ca a_CO3 / Ksp with the sourced constants (ideal solution)."""
    return a_ca * float(alpha2(ph, pk1, pk2)) * c_t / 10.0 ** log10_ksp
