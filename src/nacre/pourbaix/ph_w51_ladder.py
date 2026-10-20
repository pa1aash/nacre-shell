"""PH-W5.1 steps 3 to 7: the K1 ladder v2 with framings, stages, conversion steps, baselines and matrix rungs.

Tier 1 only (thermodynamic onset vs Li+/Li at a_w = 1, a_OH = 1, 298.15 K). E_ub is the onset with the
solid-salt LiClO4 sink (an upper bound: a falsification stands, a pass is inconclusive). E_lb needs the
hydration free energies of Ca2+, Al3+ and ClO4- (fix F2); `bracket_status` says whether they were on the
W1 branch at the one check of this session. The margin is the provisional per-reaction budget of PH-K1.

Framings (route ruling C4): the amorphous row governs the in-situ routes R1 to R3; the crystalline row is the
optimistic upper reference. Where the glass-to-crystal correction is missing the crystalline value is shown
with the gap flagged and the amorphous row reads `amorphous: undetermined`. "requires crystallisation" marks
a class where the crystalline row is above (upper bound) and the amorphous row is below.

Staged products (fix F3). (a) Ca(PO3)2: DfG = DfH - T DfS from the glass DfH (TR-032), the crystal S0
(TR-031) and the JANAF elemental entropies (white P, alpha Ca, O2), with a glass-to-crystal enthalpy bounded
by the alkali metaphosphate analogues (TR-041/TR-042, TT-045/TT-047) and inflated by a stated factor. (b)
Al(PO3)3: no calorimetric or phase-equilibrium value was found (search logged), so it stays undetermined; a
DFT comparator never makes it determined.
"""
import math

from nacre.pourbaix import cache
from nacre.pourbaix import gas as gasmod
from nacre.pourbaix import ph_k1 as k
from nacre.pourbaix import ph_k1_run as kr
from nacre.pourbaix import ph_w51_cache as wc
from nacre.pourbaix.entries import KJ_PER_MOL_PER_EV

R_J = k.constants.R
VIT_INFLATION = 2.0  # stated inflation of the analogue-bounded glass-to-crystal enthalpy (fix F3a)
S_RESID_MAX_PER_PO3 = R_J * math.log(2.0)  # assumed bound on the residual (configurational) entropy of a glass, J/K
NK_U_S = 10.0  # J/K/mol: stated uncertainty of a Neumann-Kopp entropy estimate (assumption, no source)
CLASSES = k.CUTOFF_CLASSES
BRACKET_KEYS = ("hydration_free_energy_ca", "hydration_free_energy_al", "hydration_free_energy_clo4")
W1_REF = "origin/preprint/p0-w1"

# new species: the amorphous Ca metaphosphate (the Ca-polyphosphate glass) and the Li metaphosphate baseline
EXTRA_SPECIES = {
    "Ca(PO3)2-glass": {"formula": "Ca(PO3)2", "expt": {"kind": "w51"}, "glass": True},
    "LiPO3": {"formula": "LiPO3", "expt": {"kind": "w51"}},
    "LiPO3-glass": {"formula": "LiPO3", "expt": {"kind": "w51"}, "glass": True},
    "boehmite": {"formula": "AlHO2", "expt": {"kind": "row", "dfg": "TI-026"}},
}
EXTRA_NAMES = {"Ca(PO3)2-glass": "Ca-polyphosphate glass Ca(PO3)2 (amorphous)", "LiPO3": "lithium metaphosphate LiPO3",
               "LiPO3-glass": "lithium polyphosphate glass (LiPO3)n", "boehmite": "boehmite AlO(OH)"}
EXTRA_REACTIONS = {
    "Ca(PO3)2-glass": [("r1", "r1 lattice O2 release (to P2O5)", ["LiClO4"], ["Ca(ClO4)2", "P2O5", "O2", "Li"])],
    "LiPO3": [("r1", "r1 lattice O2 release (to P2O5, Li-open)", [], ["P2O5", "O2", "Li"])],
    "LiPO3-glass": [("r1", "r1 lattice O2 release (to P2O5, Li-open)", [], ["P2O5", "O2", "Li"])],
}


def install():
    """Register the PH-W5.1 species with the PH-K1 reaction code (adds keys only; overrides nothing)."""
    for sid, spec in EXTRA_SPECIES.items():
        k.SPECIES.setdefault(sid, spec)
        k.NAMES.setdefault(sid, EXTRA_NAMES[sid])


# ------------------------------------------------------------------------- staged-product thermochemistry
def _s_row(row_id):
    r = k.evidence_rows()[row_id]
    f = k.KCAL_KJ if r["unit"].startswith("cal") else 1.0
    return float(r["value"]) * f


def element_entropies(T=k.T0):
    """S0 (J/K/mol) of the reference elements of the NBS and USGS tables, from the JANAF tables."""
    s = {"Ca": gasmod.row_kj("Ca_alpha", T, wc.W51_CACHE)["S_J_per_K_mol"],
         "P": gasmod.row_kj("P_white", T, wc.W51_CACHE)["S_J_per_K_mol"],
         "Li": gasmod.row_kj("Li_cr", T, wc.W51_CACHE)["S_J_per_K_mol"],
         "O2": gasmod.row_kj("O2", T, cache.CACHE_DIR)["S_J_per_K_mol"]}
    return s, {"Ca": wc.JANAF_W51["Ca_alpha"], "P": wc.JANAF_W51["P_white"], "Li": wc.JANAF_W51["Li_cr"],
               "O2": "https://janaf.nist.gov/tables/O-029.txt"}


def vitrification_bound():
    """Glass-minus-crystal DfH per PO3 unit from the alkali metaphosphates (kJ/mol), and the bound used."""
    pairs = [("LiPO3", "TR-041", "TR-042"), ("NaPO3", "TT-045", "TT-047"), ("LiPO3", "TT-044", "TR-042")]
    vals = []
    for name, g, c in pairs:
        vals.append({"analogue": name, "glass_row": g, "crystal_row": c,
                     "h_vit_kJ_per_PO3": k.row_kj(g)[0] - k.row_kj(c)[0]})
    pos = [v["h_vit_kJ_per_PO3"] for v in vals if v["h_vit_kJ_per_PO3"] > 0]
    h_max = max(pos)
    return {"analogues": vals, "excluded": [v for v in vals if v["h_vit_kJ_per_PO3"] <= 0],
            "excluded_why": "a glass below its crystal in enthalpy is unphysical at 298 K; TT-044 and TR-042 come from "
                            "different sources (the crystal reference differs)",
            "h_max_kJ_per_PO3": h_max, "inflation": VIT_INFLATION,
            "rule": "h_vit = n_PO3 x h_max / 2 (midpoint of [0, n_PO3 h_max]); u = inflation x n_PO3 x h_max / 2"}


def staged(T=k.T0):
    """Experimental-route DfG (kJ/mol) with u (kJ/mol) for the PH-W5.1 species, and how each was built."""
    s_el, s_src = element_entropies(T)
    vit = vitrification_bound()
    out = {}
    # Ca(PO3)2: glass DfH; crystal S0
    dh_g, u_dh_g, ub = k.row_kj("TR-032")
    s_c = _s_row("TR-031")
    n_po3 = 2
    s_sum = s_el["Ca"] + 2 * s_el["P"] + 3 * s_el["O2"]
    h_vit = n_po3 * vit["h_max_kJ_per_PO3"] / 2.0  # midpoint of [0, n h_max]
    u_vit = VIT_INFLATION * n_po3 * vit["h_max_kJ_per_PO3"] / 2.0  # half-width, inflated
    u_s_c = 20 * 0.01 * k.KCAL_KJ  # NBS convention on the printed 0.01 cal figure, J/K
    dg_c = (dh_g - h_vit) - T * (s_c - s_sum) / 1000.0
    out["Ca(PO3)2"] = {"dfG_kJ": dg_c, "u_kJ": u_dh_g + u_vit + T * u_s_c / 1000.0,
                       "route": "DfH(glass, TR-032) - h_vit - T (S0(crystal, TR-031) - S(Ca) - 2 S(P, white) - 3 S(O2))",
                       "dfH_glass_kJ": dh_g, "h_vit_kJ": h_vit, "u_vit_kJ": u_vit, "S0_J": s_c, "sum_S_el_J": s_sum,
                       "label": "experimental route with an analogue-bounded glass-to-crystal enthalpy (inflated x%g, "
                                "labelled)" % VIT_INFLATION, "sources": ["TR-032", "TR-031", "TR-041", "TR-042", "TT-045",
                                                                       "TT-047"] + list(s_src.values())}
    s_res = n_po3 * S_RESID_MAX_PER_PO3 / 2.0
    dg_g = dh_g - T * (s_c + s_res - s_sum) / 1000.0
    out["Ca(PO3)2-glass"] = {"dfG_kJ": dg_g, "u_kJ": u_dh_g + T * (u_s_c + s_res) / 1000.0,
                             "route": "DfH(glass, TR-032) - T (S0(crystal, TR-031) + S_resid - sum S(elements))",
                             "dfH_glass_kJ": dh_g, "S_resid_J": s_res,
                             "label": "experimental route; glass entropy = crystal S0 plus an assumed residual entropy in "
                                      "[0, R ln 2 per PO3] (no source; its effect is the budget term)",
                             "sources": ["TR-032", "TR-031"] + list(s_src.values())}
    # LiPO3: DfH only; S0 by Neumann-Kopp from Li2O (JANAF) and P2O5 (TR-010): an estimate, flagged
    s_li2o = gasmod.row_kj("Li2O", T, cache.CACHE_DIR)["S_J_per_K_mol"]
    s_nk = 0.5 * s_li2o + 0.5 * _s_row("TR-010")
    s_sum_li = s_el["Li"] + s_el["P"] + 1.5 * s_el["O2"]
    dh_c, u_dh_c, _ = k.row_kj("TR-042")
    out["LiPO3"] = {"dfG_kJ": dh_c - T * (s_nk - s_sum_li) / 1000.0, "u_kJ": u_dh_c + T * NK_U_S / 1000.0,
                    "route": "DfH(crystal, TR-042) - T (S_NK - S(Li) - S(P, white) - 1.5 S(O2)); S_NK = (S(Li2O) + "
                             "S(P2O5))/2", "S_NK_J": s_nk,
                    "label": "composition-based; S0 estimated (Neumann-Kopp, +-%g J/K assumed)" % NK_U_S,
                    "sources": ["TR-042", "TR-010", "https://janaf.nist.gov/tables/Li-014.txt"] + list(s_src.values())}
    g1, u1, _ = k.row_kj("TR-041")
    g2, u2, _ = k.row_kj("TT-044")
    dh_lg = 0.5 * (g1 + g2)
    s_res_li = S_RESID_MAX_PER_PO3 / 2.0
    out["LiPO3-glass"] = {"dfG_kJ": dh_lg - T * (s_nk + s_res_li - s_sum_li) / 1000.0,
                          "u_kJ": abs(g1 - g2) / 2.0 + max(u1, u2) + T * (NK_U_S + s_res_li) / 1000.0,
                          "route": "mean glass DfH (TR-041, TT-044) - T (S_NK + S_resid - sum S(elements))",
                          "dfH_glass_kJ": dh_lg, "dfH_glass_spread_kJ": abs(g1 - g2),
                          "label": "composition-based; two glass DfH values (half their spread in u); S0 estimated",
                          "sources": ["TR-041", "TT-044", "TR-010"] + list(s_src.values())}
    return out, {"element_entropies_J": s_el, "element_sources": s_src, "vitrification": vit}


class ExptBookW51(k.ExptBook):
    """The PH-K1 experimental book plus the staged-product species of PH-W5.1."""

    def __init__(self, ctx, provisional=False):
        super().__init__(ctx, provisional)
        self.extra, self.extra_meta = staged(ctx.T)

    def __call__(self, sid):
        if sid in self.extra:
            x = self.extra[sid]
            return k.Term(x["dfG_kJ"] / KJ_PER_MOL_PER_EV, x["u_kJ"],
                          meta={"basis": x["route"], "label": x["label"], "sources": x["sources"]})
        return super().__call__(sid)


class DftBookW51(k.DftBook):
    """MP 2026.09.28 under one gas scheme; no glass entries; the carbonate system from this database (fix F7)."""

    def __call__(self, sid):
        if k.SPECIES.get(sid, {}).get("glass"):
            raise k.Missing("%s: Materials Project holds no amorphous entry" % sid)
        if sid == "CaCO3":
            spec = k.SPECIES[sid]
            cands = self.by_id.get(spec["mp"]["pin"])
            if not cands:
                raise k.Missing("CaCO3: %s not in the PH-W5.1 cache" % spec["mp"]["pin"])
            best = min(cands, key=lambda e: e.energy_per_atom)
            from pymatgen.core import Composition
            scale = Composition(spec["formula"]).num_atoms / best.composition.num_atoms
            return k.Term(self.ew.formation_energy(best) * scale, meta={"material_id": spec["mp"]["pin"],
                                                                "basis": "MP 2026.09.28, PH-W5.1 Ca-C-O cache"})
        if sid == "CO2":
            g, meta = self.ew.gas("CO2")
            return k.Term(g, meta=meta)
        return super().__call__(sid)


# --------------------------------------------------------------------------------------- ladder rows
ACP_GAP = ("amorphous: undetermined; ACP has only single-paper grade-D solubility products (TR-097 to TR-102) that "
           "the authors call erroneous against alpha-TCP (TR-105); no DfH or S")
# phase rows: label, stage, role, crystalline sid (or None), amorphous sid (or None with the reason), governing
# framing, and the composition flag for baselines.
LADDER = [
    {"phase": "brushite", "stage": "slurry", "role": "precursor", "cryst": "brushite",
     "amorph": (None, ACP_GAP), "governs": "both (nucleus framings)"},
    {"phase": "ACP", "stage": "slurry", "role": "candidate", "cryst": "b-TCP",
     "amorph": (None, ACP_GAP), "governs": "amorphous",
     "note": "crystalline reference is beta-TCP (same Ca/P = 1.5)"},
    {"phase": "HAp", "stage": "slurry", "role": "candidate", "cryst": "HAp", "amorph": (None, ACP_GAP),
     "governs": "both (nucleus framings)"},
    {"phase": "OCP", "stage": "slurry", "role": "candidate", "cryst": "OCP", "amorph": (None, ACP_GAP),
     "governs": "both (nucleus framings)"},
    {"phase": "b-TCP", "stage": "slurry", "role": "candidate", "cryst": "b-TCP", "amorph": (None, ACP_GAP),
     "governs": "both (nucleus framings)"},
    {"phase": "a-TCP", "stage": "slurry", "role": "candidate", "cryst": "a-TCP", "amorph": (None, ACP_GAP),
     "governs": "both (nucleus framings)"},
    {"phase": "Li3PO4", "stage": "slurry", "role": "competing", "cryst": "Li3PO4",
     "amorph": (None, "amorphous: not registered"), "governs": "crystalline"},
    {"phase": "Ca2P2O7", "stage": "cell", "role": "candidate", "cryst": "Ca2P2O7",
     "amorph": (None, "amorphous: undetermined; no amorphous Ca pyrophosphate thermochemistry (gap)"),
     "governs": "amorphous (in-situ); crystalline is the upper reference"},
    {"phase": "Ca(PO3)2 / Ca-polyphosphate glass", "stage": "cell", "role": "candidate (routes R2, R3)",
     "cryst": "Ca(PO3)2", "amorph": ("Ca(PO3)2-glass", ""), "governs": "amorphous (C4)"},
    {"phase": "AlPO4", "stage": "cell", "role": "Al-salt rung", "cryst": "AlPO4",
     "amorph": (None, "amorphous: undetermined; no amorphous AlPO4 thermochemistry (gap)"),
     "governs": "amorphous (in-situ); crystalline is the upper reference"},
    {"phase": "Al(PO3)3", "stage": "cell", "role": "Al-salt rung", "cryst": "Al(PO3)3",
     "amorph": (None, "amorphous: undetermined; no Al(PO3)3 thermochemistry in either framing (F3b search logged)"),
     "governs": "amorphous (C4)"},
    {"phase": "Al-polyphosphate (R1 gel)", "stage": "cell", "role": "Al-salt rung (route R1)", "cryst": "Al(PO3)3",
     "amorph": (None, "amorphous: undetermined; no Al-polyphosphate gel thermochemistry; Al(PO3)3 is a gap"),
     "governs": "amorphous (C4)", "note": "crystalline reference is Al(PO3)3"},
    {"phase": "(LiPO3)n Hydro-Quebec film", "stage": "cell", "role": "baseline (US 6,485,866)", "cryst": "LiPO3",
     "amorph": ("LiPO3-glass", ""), "governs": "both (baked baseline, structure unspecified)", "composition": True,
     "note": "K2 expected fail: water-soluble (inference from chemistry, not a patent statement; no solubility row)"},
    {"phase": "baked aluminophosphate (Tsinghua)", "stage": "cell", "role": "baseline (US 8,252,463)",
     "cryst": "AlPO4", "amorph": (None, "amorphous: undetermined; no amorphous AlPO4 or Al(PO3)3 thermochemistry"),
     "governs": "both (baked baseline, structure unspecified)", "composition": True,
     "note": "composition Al(x)M(y)PO4 / Al(x)M(y)(PO3)3 read as AlPO4 (M-free); the (PO3)3 member is undetermined"},
    {"phase": "CaSiO3", "stage": "comparator", "role": "comparator", "cryst": "CaSiO3",
     "amorph": (None, "amorphous: not registered"), "governs": "crystalline"},
    {"phase": "Ca2SiO4", "stage": "comparator", "role": "comparator", "cryst": "Ca2SiO4",
     "amorph": (None, "amorphous: not registered"), "governs": "crystalline"},
    {"phase": "Li2SiO3", "stage": "comparator", "role": "comparator", "cryst": "Li2SiO3",
     "amorph": (None, "amorphous: not registered"), "governs": "crystalline"},
    {"phase": "CaCO3", "stage": "control", "role": "control", "cryst": "CaCO3",
     "amorph": (None, "ACC: not run here (frozen carbonate control)"), "governs": "crystalline (control gate)"},
]
NOT_RUN = [{"phase": "Ca-modified aluminophosphate", "stage": "cell", "role": "baseline (optional, F5)",
            "why": "not run: no thermochemistry of Ca-Al phosphates in the corpus (data do not permit)"}]

MATRIX = [
    {"phase": "chitosan", "key": "matrix_oxidation_onset_chitosan"},
    {"phase": "polydopamine", "key": "matrix_oxidation_onset_pda", "risk": "stated K1 risk, contrary B4"},
    {"phase": "chitosan-polyphosphate complex", "key": "matrix_chitosan_polyp_complex"},
]


def reactions_of(sid):
    if sid in EXTRA_REACTIONS:
        return EXTRA_REACTIONS[sid]
    return k.PHASE_BY_ID[sid]["reactions"]


def evaluate_sid(sid, books):
    """PH-K1 reaction evaluation for one species; summary as in PH-K1 (E_ox = min over registered reactions)."""
    reactions = {}
    for rid, cls, extra, products in reactions_of(sid):
        by_sid = k.build_reaction(sid, extra, products)
        r = kr.evaluate_reaction(by_sid, books)
        r["class"] = cls
        reactions[rid] = r
    return reactions, kr.phase_summary(sid, reactions)


def class_status(summ, inf, sup):
    s, note = kr.class_status(summ, inf, sup)
    return ("above (ub)" if s == "above" else s), note


# ------------------------------------------------------------------------------------- bracket (F2)
def bracket_status(ref=W1_REF):
    """One look at the W1 branch (fetched once in the session header) for the hydration keys of F2."""
    import yaml

    from nacre.pourbaix import provenance
    rc, sha = provenance._git("rev-parse", ref)
    rc2, text = provenance._git("show", "%s:lit/params.yaml" % ref)
    if rc or rc2:
        return {"ref": ref, "computed": False, "status": "bracket pending PH-W1.3", "why": "W1 branch not readable"}
    params = yaml.safe_load(text)["params"]
    found = {key: (params.get(key) or {}).get("value") for key in BRACKET_KEYS}
    missing = [key for key, v in found.items() if v is None]
    return {"ref": ref, "commit": sha.strip(), "keys": found, "missing": missing, "computed": not missing,
            "status": "bracket pending PH-W1.3" if missing else "computed",
            "why": ("no %s on %s; Ca2+ and Al3+ hydration keys are present (grade D, TK-002, TK-003) but the anion term "
                    "is required" % (", ".join(missing), ref)) if missing else "",
            "convention": "E_lb would use the aqueous hydration of Ca2+, Al3+ and ClO4- (most favourable sink) against Li+ "
                          "hydrated in the same solvent, so the Li+/Li reference and the anion term are referred to "
                          "water consistently (F2); E_ub is the solid-salt LiClO4 sink"}


# ------------------------------------------------------------------------------------ conversion steps
def _aw_star(dg_kj, u_kj, n_w, T=k.T0):
    """a_w at which the condensed (water-releasing) side and the hydrated side have equal free energy."""
    rt = R_J * T / 1000.0
    f = lambda x: math.exp(-x / (n_w * rt))  # noqa: E731
    return f(dg_kj), [f(dg_kj + u_kj), f(dg_kj - u_kj)]


def conversions(book):
    """Precursor-to-cell-stage steps with the thermodynamic a_w* where every species is tabulated."""
    def g(sid):
        t = book(sid)
        return t.g_eV * KJ_PER_MOL_PER_EV, t.u_kJ
    lit_t = ("pending PH-W1.3: no conversion-temperature row on %s at this session's check" % W1_REF)
    cure = "100 to 350 C cure (US 8,252,463, lit/novelty.md BL3; patent, no DOI, so no row id)"
    steps = [
        {"step": "brushite -> monetite + 2 H2O", "pair": "brushite to monetite (to Ca2P2O7)",
         "species": [("brushite", -1), ("monetite", 1), ("H2O", 2)], "n_w": 2, "lit_T": lit_t},
        {"step": "2 monetite -> Ca2P2O7 + H2O", "pair": "monetite to Ca2P2O7 (condensation)",
         "species": [("monetite", -2), ("Ca2P2O7", 1), ("H2O", 1)], "n_w": 1, "lit_T": lit_t},
        {"step": "Ca2P2O7 + 2 H3PO4 -> 2 Ca(PO3)2 + 3 H2O", "pair": "Ca2P2O7 to Ca(PO3)2 (acid-fed condensation)",
         "species": [("Ca2P2O7", -1), ("H3PO4", -2), ("Ca(PO3)2", 2), ("H2O", 3)], "n_w": 3, "lit_T": lit_t},
        {"step": "Ca-polyphosphate coacervate -> Ca(PO3)2 glass (drying)", "pair": "coacervate to glass (R2, R3)",
         "undetermined": "no coacervate binodal or activity data (coacervate_pH_window, coacervate_gamma_nl gaps)",
         "lit_T": "drying; no temperature row"},
        {"step": "AlO(OH) + H3PO4 -> AlPO4 + 2 H2O", "pair": "Al oxide film + phosphoric acid to AlPO4 (baked baseline)",
         "species": [("boehmite", -1), ("H3PO4", -1), ("AlPO4", 1), ("H2O", 2)], "n_w": 2, "lit_T": cure},
        {"step": "AlPO4 + P2O5 -> Al(PO3)3", "pair": "AlPO4 to Al(PO3)3", "undetermined": "Al(PO3)3 has no tabulated "
         "thermochemistry (F3b search logged)", "lit_T": cure},
        {"step": "polyphosphate + Al3+ -> Al-polyphosphate gel", "pair": "R1 gelation (slurry to cell stage)",
         "undetermined": "Ksp of the Al polyphosphate is a gap (polyp_log10_ksp_al)", "lit_T": "room temperature"},
        {"step": "(HPO3)n + Li2O/LiOH -> (LiPO3)n glass, dried", "pair": "Hydro-Quebec film (baseline)",
         "undetermined": "not a dehydration threshold; dried at 150 C (lit/novelty.md BL1)", "lit_T": "150 C dry (BL1)"},
    ]
    out = []
    for st in steps:
        row = {"row_type": "conversion", "phase": st["pair"], "step": st["step"], "lit_conversion_T": st["lit_T"],
               "cure_range_reference": cure}
        if "undetermined" in st:
            row.update(a_w_star=None, status="undetermined", note=st["undetermined"])
        else:
            dg = u = 0.0
            for sid, c in st["species"]:
                v, uu = g(sid)
                dg += c * v
                u += abs(c) * uu
            star, rng = _aw_star(dg, u, st["n_w"])
            row.update(dG_kJ_at_aw1=dg, u_kJ=u, a_w_star=star, a_w_star_range=rng,
                       status=("water release favoured at a_w = 1 (a_w* > 1)" if star > 1 else
                               "hydrated side stable above a_w*"),
                       note="thermodynamic threshold only; a_w* within its range of 1 is undecided; the conversion is "
                            "kinetically gated (temperatures beside)")
        out.append(row)
    return out


# ---------------------------------------------------------------------------------------- the ladder
def _row_for(entry, framing, sid, reason, books, bracket, bench_by):
    base = {"row_type": "baseline" if entry["role"].startswith("baseline") else (
            "control" if entry["role"] == "control" else "phase"),
            "phase": entry["phase"], "stage": entry["stage"], "role": entry["role"], "framing": framing,
            "governs": entry["governs"], "species": sid or "", "composition_based": bool(entry.get("composition")),
            "E_lb_V": None, "bracket": bracket["status"], "note": entry.get("note", "")}
    if sid is None:
        base.update(E_ub_V=None, label=reason, gap_flag=True, statuses={c: "undetermined" for c in CLASSES})
        return base, None
    reactions, summ = evaluate_sid(sid, books)
    e = summ["expt"]
    statuses = {c: class_status(summ, inf, sup)[0] for c, (inf, sup) in CLASSES.items()}
    dft = {s: summ[s]["onset_V"] for s in k.SCHEMES}
    bmk = bench_by.get(sid) or bench_by.get(sid.replace("-glass", " glass"))
    base.update(E_ub_V=e["onset_V"] if e else None, margin_V=e["budget_V"] if e else None,
                margin_complete=e["budget_complete"] if e else None, limiting_reaction=e["limiting"] if e else "",
                undetermined_reactions=",".join(summ["expt_undetermined"]), statuses=statuses,
                dft_janaf_V=dft["janaf"], dft_mp_V=dft["mp"],
                dft_label="comparator; %s" % (bmk["display"] if bmk else "dft-unbenchmarked (no tabulated value)"),
                gap_flag=bool(summ["expt_undetermined"]), label="")
    return base, {"reactions": reactions, "summary": summ}


def build(ctx, books, bench_rows):
    install()
    bracket = bracket_status()
    bench_by = {r["phase"]: r for r in bench_rows}
    rows, detail = [], {}
    for entry in LADDER:
        sid_c = entry["cryst"]
        sid_a, reason_a = entry["amorph"]
        rc, dc = _row_for(entry, "crystalline", sid_c, "", books, bracket, bench_by)
        ra, da = _row_for(entry, "amorphous", sid_a, reason_a, books, bracket, bench_by)
        if sid_a is None:
            if rc["E_ub_V"] is None:
                rc["label"] = "undetermined in both framings; " + reason_a
            elif "undetermined" in reason_a:
                rc["label"] = "crystalline shown, glass-to-crystal correction missing (gap flagged); " + reason_a
            else:
                rc["label"] = reason_a
            ra["label"] = reason_a
        else:
            req = [c for c in CLASSES if rc["statuses"][c] == "above (ub)" and ra["statuses"][c] == "below"]
            if req:
                lab = "requires crystallisation at %s" % ", ".join(req)
            elif entry["governs"].startswith("both"):
                lab = "both framings reported (structure unspecified)"
            else:
                lab = "amorphous row governs (C4); crystalline is the upper reference"
            rc["label"] = ra["label"] = lab
        if entry["phase"] == "CaCO3":
            rc["label"] = "control: frozen value governs the gate; DFT columns are the 2026.09.28 comparator (F7)"
        rows += [rc, ra]
        detail[entry["phase"]] = {"crystalline": dc, "amorphous": da}
    for nr in NOT_RUN:
        rows.append({"row_type": "baseline", "phase": nr["phase"], "stage": nr["stage"], "role": nr["role"],
                     "framing": "both", "label": nr["why"], "gap_flag": True, "bracket": bracket["status"],
                     "statuses": {c: "not run" for c in CLASSES}})
    for m in MATRIX:
        st = (ctx_params_status(m["key"]))
        rows.append({"row_type": "matrix", "phase": m["phase"], "stage": "cell", "role": "organic matrix rung (C6)",
                     "framing": "n/a (tier 2 only)", "governs": "tier 2 only", "E_ub_V": None,
                     "label": "gap, matrix-risk flag" + ("; %s" % m["risk"] if m.get("risk") else ""),
                     "note": "no tier-1 number for polymers; tier 2: key %s is %s at W1.2, no class A/B/C record" % (
                         m["key"], st), "gap_flag": True, "statuses": {c: "tier 2 gap" for c in CLASSES}})
    conv = conversions(books["expt"])
    return rows, conv, detail, bracket


def ctx_params_status(key):
    import yaml

    from nacre.pourbaix.paths import REPO
    cov = yaml.safe_load((REPO / "lit" / "corpus" / "phosphate_coverage.yaml").read_text(encoding="utf-8"))
    return (cov.get("route_layer", {}).get(key) or {}).get("status", "absent")
