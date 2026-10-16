"""R-cell window runs from the cache: CaCO3 and Al2O3 against Li (see window.py)."""
import warnings
from dataclasses import asdict
from functools import lru_cache

from nacre.pourbaix import cache
from nacre.pourbaix import window as w
from nacre.pourbaix.entries import entry_key, material_id

# phase formula -> (cation, gas products of its oxidation, element system for the Li-open hull)
PHASES = {
    "CaCO3": ("Ca", ("O2", "CO2"), "Li-Ca-C-O"),
    "Al2O3": ("Al", ("O2",), "Li-Al-O"),
}


@lru_cache(maxsize=2)
def pooled_entries(cache_dir_str):
    """All R-cell entries, one per entry id."""
    seen, out = set(), []
    for name in sorted(cache.files_of_kind("mp_entries", cache_dir_str)):
        if not name.startswith("mp_entries_cell_"):
            continue
        for e in cache.load_entries(name, cache_dir_str):
            k = entry_key(e)
            if k not in seen:
                seen.add(k)
                out.append(e)
    return out


def chemsys_entries(chemsys, cache_dir=cache.CACHE_DIR):
    return cache.load_entries("mp_entries_cell_%s.json" % chemsys, cache_dir)


def build(cfg_regime, cache_dir=cache.CACHE_DIR):
    """Windows, every oxidation candidate and the chemical-decomposition check (offline)."""
    from pymatgen.analysis.phase_diagram import PhaseDiagram

    T = float(cfg_regime["temperature_K"])
    sinks = cfg_regime["sinks"]
    active = cfg_regime["active_sink"]
    if active not in sinks:
        raise ValueError("active sink %r is not defined" % active)
    gas_settings = cfg_regime["gas"]
    pinned = {f: p["material_id"] for f, p in cfg_regime["phases"].items()}

    pool = pooled_entries(str(cache_dir))
    book = w.EnergyBook(pool, T, gas_settings, cache_dir, pinned=pinned)
    alt_settings = {k: dict(v) for k, v in gas_settings.items()}
    if "CO2" in alt_settings:
        alt_settings["CO2"]["enthalpy_scheme"] = {"janaf": "mp", "mp": "janaf"}[
            gas_settings["CO2"].get("enthalpy_scheme", "janaf")]
    alt_book = w.EnergyBook(pool, T, alt_settings, cache_dir, pinned=pinned)

    out = {"phases": {}, "candidates": [], "sensitivity_CO2_scheme": [], "chemical": {}}
    for phase, spec in cfg_regime["phases"].items():
        cation, gases, chemsys = PHASES[phase]
        ents = chemsys_entries(chemsys, cache_dir)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pd = PhaseDiagram(ents)
        pe_ = [e for e in ents if material_id(e) == spec["material_id"]]
        if not pe_:
            raise w.MissingPhase(spec["material_id"])
        red, li_open_ox, note = w.li_open_limits(pd, pe_[0])
        cands = w.oxidation_candidates(phase, cation, sinks, book, gases)
        win = w.build_window(phase, red, li_open_ox, cands, active)
        alt = w.oxidation_candidates(phase, cation, sinks, alt_book, gases) if "CO2" in gases else []
        out["phases"][phase] = {"window": win.as_dict(), "material_id": spec["material_id"],
                                "entry_id": entry_key(pe_[0]), "li_open_hull": note,
                                "li_open_oxidation": asdict(li_open_ox),
                                "lithiation_hull": chemsys}
        out["candidates"] += [asdict(c) for c in cands]
        out["sensitivity_CO2_scheme"] += [asdict(c) for c in alt]
        if phase == "CaCO3":
            dg, text = w.chemical_decomposition(book, "CaCO3", ["CaO", "CO2"])
            dg_alt, _ = w.chemical_decomposition(alt_book, "CaCO3", ["CaO", "CO2"])
            out["chemical"]["CaCO3"] = {"reaction": text, "delta_g_ev": dg,
                                        "delta_g_ev_alternative_CO2_scheme": dg_alt,
                                        "question": "is CaCO3 stable against CO2 loss without "
                                        "electrochemistry at this T and p(CO2)?"}
    out["active_sink"] = active
    out["temperature_K"] = T
    return out
