"""R-slurry: the aqueous Al-Ca-C-O-H Pourbaix screen (claim C5, items 19 and 21).

Thermodynamic questions answered, at the regime's ion concentrations and fixed total
carbonate:

1. Which combination of Al-, Ca- and C-bearing species has the lowest free energy at each
   (pH, E vs SHE)? (stability domains)
2. How far above that equilibrium does calcite, ACC, corundum, boehmite or diaspore sit, in
   eV/atom, across the regime's pH and potential range? (decomposition energies; 0 means stable)
3. With the crystalline CaCO3 polymorphs excluded, where would ACC be the stable Ca phase, and
   how does that region move with the ACC free-energy offset? (constrained equilibrium)

These are equilibrium proxies. A positive decomposition energy says a phase is not the
equilibrium state; it says nothing about how fast it dissolves.

Carbonate system: closed. Total dissolved carbonate is fixed (the C concentration of the
configuration) and the C(IV) speciation follows from pH through acid constants derived from
the same cached ion energies the diagram uses. The diagram itself uses the Pourbaix
predominance convention: each aqueous ion is placed at the element's total concentration,
which matches the closed-system speciation except within about one pH unit of a pKa.
"""
import warnings

import numpy as np

from nacre.pourbaix import entries as pe

T_POURBAIX_K = 298.15  # the temperature of the ion reference data and of PREFAC
CARBONATE_IONS = ("CO2(aq)", "HCO3[-]", "CO3[2-]")


def _pbx():
    from pymatgen.analysis import pourbaix_diagram as m

    return m


def acc_entry(calcite, offset_kj_per_mol):
    """ACC as calcite plus a free-energy offset per CaCO3 formula unit (kJ mol^-1)."""
    from pymatgen.entries.computed_entries import ComputedEntry

    m = _pbx()
    comp = calcite.entry.composition
    fu = comp.get_reduced_composition_and_factor()[1]
    energy = calcite.entry.energy + fu * offset_kj_per_mol / pe.KJ_PER_MOL_PER_EV
    return m.PourbaixEntry(ComputedEntry(comp, energy, entry_id="ACC(calcite+offset)"),
                           entry_id="ACC(calcite+offset)")


def label(entry):
    """Readable, deterministic label of a (multi-)entry: components sorted by name."""
    names = [e.name for e in getattr(entry, "entry_list", [entry])]
    return " + ".join(sorted(names))


def component_names(entry):
    return sorted(e.name for e in getattr(entry, "entry_list", [entry]))


def phase_kind(entry):
    kinds = {e.phase_type for e in getattr(entry, "entry_list", [entry])}
    if kinds == {"Solid"}:
        return "solid"
    if kinds == {"Ion"}:
        return "aqueous"
    return "mixed"


def _contains(entry, entry_id):
    return any(str(e.entry_id) == entry_id for e in getattr(entry, "entry_list", [entry]))


def water_lines(ph):
    """H2/H2O and H2O/O2 lines vs SHE from the library's water free energy (eV)."""
    m = _pbx()
    from pymatgen.entries.compatibility import MU_H2O

    ph = np.asarray(ph, dtype=float)
    return {"lower": -m.PREFAC * ph, "upper": -MU_H2O / 2.0 - m.PREFAC * ph}


def diagram(entries, conc, comp=None):
    m = _pbx()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return m.PourbaixDiagram(entries, comp_dict=comp, conc_dict=conc, filter_solids=True)


def assign_domains(pd, ph, E):
    """Stable (multi-)entry index on the grid, deterministic.

    Stable entries are ordered by label; ties go to the first in that order (np.argmin).
    Returns (labels, index[nE, npH]).
    """
    stable = sorted(pd.stable_entries, key=label)
    PH, EE = np.meshgrid(ph, E)
    g = np.array([s.normalized_energy_at_conditions(PH, EE) for s in stable])
    return stable, np.argmin(g, axis=0)


def polygons(pd, limits):
    m = _pbx()
    stable = sorted(pd.stable_entries, key=label)
    doms = m.PourbaixDiagram.get_pourbaix_domains(stable, limits=limits)[0]
    out = []
    for entry in stable:
        edges = doms.get(entry)
        if not edges:
            continue
        # each domain is returned as boundary simplices (edges); collect their end points
        pts = np.array([c for s in edges for c in np.asarray(s.coords, dtype=float)])
        verts = np.unique(np.round(pts, 9), axis=0)
        if len(verts) < 3:
            continue
        c = verts.mean(axis=0)
        order = np.argsort(np.arctan2(verts[:, 1] - c[1], verts[:, 0] - c[0]))
        out.append({"label": label(entry), "components": component_names(entry),
                    "kind": phase_kind(entry),
                    "polygon": [[round(float(x), 6), round(float(y), 6)] for x, y in verts[order]]})
    return out


def carbonate_speciation(entries, ph, c_total):
    """Closed C(IV) system: pKa values and fractions from the cached ion energies.

    The acid constants come from the Pourbaix energies of CO2(aq), HCO3- and CO3^2- at unit
    activity (the same energies the diagram uses). Returns pKa1, pKa2 and, on the pH grid,
    the fractions alpha0..2 and the CO3^2- activity alpha2 * c_total (ideal solution).
    """
    m = _pbx()
    ions = {}
    for e in entries:
        if e.phase_type == "Ion" and e.name in CARBONATE_IONS:
            unit = m.PourbaixEntry(e.entry, entry_id=e.entry_id, concentration=1.0)
            ions[e.name] = unit
    missing = [n for n in CARBONATE_IONS if n not in ions]
    if missing:
        raise ValueError("carbonate ions missing from the cache: %s" % missing)

    def crossing(a, b):
        # normalized energies are linear in pH at fixed V (same C oxidation state: no V term)
        ga0 = ions[a].normalized_energy_at_conditions(0.0, 0.0)
        ga1 = ions[a].normalized_energy_at_conditions(1.0, 0.0)
        gb0 = ions[b].normalized_energy_at_conditions(0.0, 0.0)
        gb1 = ions[b].normalized_energy_at_conditions(1.0, 0.0)
        return float((gb0 - ga0) / ((ga1 - ga0) - (gb1 - gb0)))

    pka1 = crossing("CO2(aq)", "HCO3[-]")
    pka2 = crossing("HCO3[-]", "CO3[2-]")
    ph = np.asarray(ph, dtype=float)
    h = 10.0 ** (-ph)
    k1, k2 = 10.0 ** (-pka1), 10.0 ** (-pka2)
    den = h * h + k1 * h + k1 * k2
    a0, a1, a2 = h * h / den, k1 * h / den, k1 * k2 / den
    return {"pKa1": pka1, "pKa2": pka2, "alpha_CO2aq": a0, "alpha_HCO3": a1, "alpha_CO3": a2,
            "a_CO3": a2 * c_total}


def build(cfg_regime):
    """Build every R-slurry output from a resolved regime configuration (offline)."""
    T = float(cfg_regime["temperature_K"])
    if abs(T - T_POURBAIX_K) > 1e-9:
        raise NotImplementedError("the aqueous Pourbaix construction is fixed at %.2f K (ion "
                                  "reference data and Nernst prefactor); T = %s K requested"
                                  % (T_POURBAIX_K, T))
    if cfg_regime["carbonate_system"] != "closed":
        raise NotImplementedError("only the closed carbonate system is implemented")

    num = cfg_regime["numerics"]
    ph = np.linspace(cfg_regime["pH"]["min"], cfg_regime["pH"]["max"], int(num["n_pH"]))
    E = np.linspace(cfg_regime["potential_V_SHE"]["min"], cfg_regime["potential_V_SHE"]["max"],
                    int(num["n_E"]))
    conc = {k: float(v) for k, v in cfg_regime["concentrations_mol_kg"].items()}
    comp = {k: float(v) for k, v in cfg_regime["composition"].items()}
    if cfg_regime["acc_offset"].get("unit") != "kJ/mol":
        raise ValueError("acc_offset must be given in kJ/mol per CaCO3 formula unit")
    offset = float(cfg_regime["acc_offset"]["value"])
    limits = [[float(ph[0]), float(ph[-1])], [float(E[0]), float(E[-1])]]

    all_entries = pe.slurry_entries(("Al", "C", "Ca"))
    roles = pe.polymorph_roles()
    targets = {r: pe.solid_by_id(all_entries, roles[r]["entry_id"])
               for r in ("calcite", "corundum", "boehmite", "diaspore")}
    acc = acc_entry(targets["calcite"], offset)
    targets["ACC"] = acc

    # 1. Equilibrium domains, full Al-Ca-C system.
    pd_full = diagram(all_entries + [acc], conc, comp)
    stable, idx = assign_domains(pd_full, ph, E)
    # A cross compound holds Al together with Ca or C; its presence would make the subsystem
    # hulls below inexact.
    cross = sorted({c.name for s in stable for c in getattr(s, "entry_list", [s])
                    if "Al" in {str(el) for el in c.composition.elements}
                    and {str(el) for el in c.composition.elements} & {"Ca", "C"}})

    # 2. Decomposition energies against the hull of each target's own element subsystem.
    def sub(elts):
        return [e for e in all_entries
                if {str(el) for el in e.composition.elements} - {"O", "H"} <= set(elts)]

    PH, EE = np.meshgrid(ph, E)
    ca_c = sub(("Ca", "C"))
    pd_cac = diagram(ca_c + [acc], {k: conc[k] for k in ("Ca", "C")}, {"Ca": 1.0, "C": 1.0})
    pd_al = diagram(sub(("Al",)), {"Al": conc["Al"]}, {"Al": 1.0})
    dec = {}
    for role, entry in targets.items():
        pdx = pd_al if role in ("corundum", "boehmite", "diaspore") else pd_cac
        dec[role] = np.asarray(pdx.get_decomposition_energy(entry, PH, EE), dtype=float)

    # 3. ACC with the crystalline CaCO3 polymorphs excluded.
    acc_region = acc_constrained_region(ca_c, acc, conc, ph, E)

    return {"ph": ph, "E": E, "limits": limits, "pd": pd_full, "stable": stable, "index": idx,
            "cross_compounds": cross, "decomposition": dec, "roles": roles,
            "acc_region": acc_region, "entries": all_entries,
            "speciation": carbonate_speciation(all_entries, ph, conc["C"]),
            "water": water_lines(ph)}


def acc_constrained_region(ca_c_entries, acc, conc, ph, E):
    """Grid mask where ACC is part of the stable Ca-C state when crystalline CaCO3 is excluded,
    plus the lowest pH of that region at each potential (NaN where ACC is never stable)."""
    caco3 = "CaCO3"
    pool = [e for e in ca_c_entries
            if not (e.phase_type == "Solid" and e.composition.reduced_formula == caco3)]
    pd = diagram(pool + [acc], {k: conc[k] for k in ("Ca", "C")}, {"Ca": 1.0, "C": 1.0})
    stable, idx = assign_domains(pd, ph, E)
    has_acc = np.array([_contains(s, acc.entry_id) for s in stable])
    mask = has_acc[idx] if len(stable) else np.zeros((len(E), len(ph)), bool)
    ph_min = np.array([ph[row].min() if row.any() else np.nan for row in mask])
    return {"mask": mask, "ph_min": ph_min, "area_fraction": float(mask.mean())}


def acc_offset_scan(offsets_kj, conc, ph, E):
    """ACC constrained-region summary for several offsets (used by tests and reports)."""
    all_entries = pe.slurry_entries(("Al", "C", "Ca"))
    roles = pe.polymorph_roles()
    calcite = pe.solid_by_id(all_entries, roles["calcite"]["entry_id"])
    ca_c = [e for e in all_entries
            if {str(el) for el in e.composition.elements} - {"O", "H"} <= {"Ca", "C"}]
    out = []
    for off in offsets_kj:
        r = acc_constrained_region(ca_c, acc_entry(calcite, off), conc, ph, E)
        out.append({"offset_kj_per_mol": float(off), "area_fraction": r["area_fraction"],
                    "ph_min": r["ph_min"]})
    return out
