"""Pourbaix entries rebuilt offline from the cache.

`slurry_entries` reproduces the Materials Project client's `get_pourbaix_entries` (mp-api
0.46.5) from the cached raw entries and ion reference data, so the diagram can be rebuilt
without the network. The steps are the client's own:

1. Process the solid entries with MaterialsProjectAqueousCompatibility on top of MP2020.
2. Build the solid phase diagram of the ions' reference-solid element system plus O and H.
3. Place each ion at its experimental free energy of formation, shifted by the DFT-minus-
   experiment difference of its reference solid (the scheme of Persson et al. 2012).
4. Turn every solid outside the O-H system, and without the reference-only elements, into a
   PourbaixEntry carrying its formation energy.

Phase identification (calcite, corundum, boehmite, diaspore) uses the cached structures.
"""
import warnings
from functools import lru_cache

from scipy import constants

from nacre.pourbaix import cache

# kJ mol^-1 per eV per formula unit (Faraday constant / 1000).
KJ_PER_MOL_PER_EV = constants.e * constants.N_A / 1000.0

ROLE_SPACEGROUPS = {
    # role: (reduced formula, international space-group symbol)
    "calcite": ("CaCO3", "R-3c"),
    "aragonite": ("CaCO3", "Pnma"),
    "corundum": ("Al2O3", "R-3c"),
    # H-ordered boehmite cell; the ideal Cmcm cell needs H disorder.
    "boehmite": ("AlHO2", "Cmc2_1"),
    "diaspore": ("AlHO2", "Pnma"),
}


def entry_key(entry_or_id):
    """Plain string id of an entry: '<identifier>-<suffix>' for emmet EntryID dictionaries."""
    eid = getattr(entry_or_id, "entry_id", entry_or_id)
    if isinstance(eid, dict) and "identifier" in eid:
        return eid["identifier"] + (eid.get("separator") or "-") + eid["suffix"] if eid.get("suffix") else eid["identifier"]
    return str(eid)


def material_id(entry):
    """Legacy Materials Project material id (e.g. mp-3953) from the entry data, if present."""
    return str((getattr(entry, "data", None) or {}).get("material_id") or "")


def _slurry_file(cache_dir=cache.CACHE_DIR):
    names = [n for n in cache.files_of_kind("mp_entries", cache_dir) if n.startswith("mp_entries_slurry_")]
    if len(names) != 1:
        raise RuntimeError("expected one slurry entries file in the cache, found %s" % names)
    return names[0]


def ion_records(elements, cache_dir=cache.CACHE_DIR):
    """Ion reference records whose major element is in `elements`."""
    data = cache.load("mp_ion_reference_data.json", cache_dir)["response"]
    return [d for d in data if d["data"]["MajElements"] in set(elements)]


def _energy_ev(datum):
    if datum["unit"] == "kJ/mol":
        return datum["value"] / KJ_PER_MOL_PER_EV
    if datum["unit"] == "MJ/mol":
        return datum["value"] * 1000.0 / KJ_PER_MOL_PER_EV
    raise ValueError("unexpected energy unit %r" % datum["unit"])


def ion_entries(ion_ref_pd, records):
    """IonEntry objects positioned against the solid phase diagram (client algorithm)."""
    from pymatgen.analysis.pourbaix_diagram import IonEntry
    from pymatgen.core.ion import Ion

    out = []
    for rec in records:
        ion = Ion.from_formula(rec["formula"])
        refs = [e for e in ion_ref_pd.all_entries
                if e.composition.reduced_formula == rec["data"]["RefSolid"]]
        if not refs:
            raise ValueError("reference solid %s not in the entry list" % rec["data"]["RefSolid"])
        stable_ref = sorted(refs, key=lambda x: x.energy_per_atom)[0]
        rf = stable_ref.composition.get_reduced_composition_and_factor()[1]
        solid_diff = ion_ref_pd.get_form_energy(stable_ref) - _energy_ev(rec["data"]["ΔGᶠRefSolid"]) * rf
        elt = rec["data"]["MajElements"]
        factor = ion.composition[elt] / stable_ref.composition[elt]
        out.append(IonEntry(ion, _energy_ev(rec["data"]["ΔGᶠ"]) + solid_diff * factor, name=rec["identifier"]))
    return out


@lru_cache(maxsize=4)
def _processed(cache_dir_str):
    """Aqueous-compatible solid entries and their phase diagram (cached per process)."""
    from pymatgen.analysis.phase_diagram import PhaseDiagram
    from pymatgen.entries.compatibility import (MaterialsProject2020Compatibility,
                                                MaterialsProjectAqueousCompatibility)

    raw = cache.load_entries(_slurry_file(cache_dir_str), cache_dir_str)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        compat = MaterialsProjectAqueousCompatibility(solid_compat=MaterialsProject2020Compatibility())
        processed = compat.process_entries(raw)
    return processed, PhaseDiagram(processed)


def slurry_entries(elements=("Al", "C", "Ca"), cache_dir=cache.CACHE_DIR):
    """PourbaixEntry list for the given non-O/H elements, rebuilt from the cache.

    Returns (entries, solid_lookup) where solid_lookup maps entry_id -> PourbaixEntry for solids.
    """
    from pymatgen.analysis.pourbaix_diagram import PourbaixEntry
    from pymatgen.core import Element
    from pymatgen.core.ion import Ion
    from pymatgen.entries.computed_entries import ComputedEntry

    processed, pd = _processed(str(cache_dir))
    records = ion_records(elements, cache_dir)
    ref_elts = {el for d in records for el in Ion.from_formula(d["data"]["RefSolid"]).elements}
    wanted = {Element(e) for e in elements}
    extra = set(ref_elts) - wanted - {Element("H"), Element("O")}

    pbx = [PourbaixEntry(e, "ion-%d" % n) for n, e in enumerate(ion_entries(pd, records))]
    for entry in processed:
        elts = set(entry.composition.elements)
        if elts <= {Element("H"), Element("O")} or extra & elts:
            continue
        if not (elts - {Element("H"), Element("O")}) <= wanted:
            continue
        ce = ComputedEntry(entry.composition, pd.get_form_energy(entry), entry_id=entry_key(entry),
                           data={"material_id": material_id(entry)})
        pbx.append(PourbaixEntry(ce))
    return pbx


@lru_cache(maxsize=4)
def _roles(cache_dir_str):
    """entry_id of the lowest-energy MP entry for each named polymorph role."""
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    raw = cache.load_entries(_slurry_file(cache_dir_str), cache_dir_str)
    out = {}
    for role, (formula, sg) in ROLE_SPACEGROUPS.items():
        cands = []
        for e in raw:
            if e.composition.reduced_formula != formula:
                continue
            try:
                sym = SpacegroupAnalyzer(e.structure, symprec=0.1).get_space_group_symbol()
            except Exception:  # noqa: BLE001 - symmetry failure means "not this polymorph"
                continue
            if sym == sg:
                cands.append(e)
        if cands:
            best = min(cands, key=lambda e: e.energy_per_atom)
            out[role] = {"entry_id": entry_key(best), "material_id": material_id(best),
                         "formula": formula, "spacegroup": sg, "n_candidates": len(cands)}
    return out


def polymorph_roles(cache_dir=cache.CACHE_DIR):
    return dict(_roles(str(cache_dir)))


def solid_by_id(entries, entry_id):
    for e in entries:
        if e.phase_type == "Solid" and str(e.entry_id) == entry_key(entry_id):
            return e
    raise KeyError(entry_id)
