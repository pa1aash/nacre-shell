"""K1 tier 1: the oxidation-limit ladder of the phosphate candidates (PH-K1, lane p0-w5).

Thermodynamic question: at which potential vs Li+/Li does each candidate phase first oxidise, with its
cations taken up by the anion of the electrolyte salt (the solid-salt sink LiClO4, as for the carbonate
control) and its anion released as the next residue (P2O5, SiO2, CO2, a lower-basicity phosphate)
plus O2? A solid-salt sink bounds the onset from above: a falsification stands, a pass is inconclusive
(theory/claims_redirect.md 2a). Nothing here is a rate.

Routes. The experimental route (tabulated formation free energies with their row ids, the exchange
enthalpy for the perchlorate sinks, as for the carbonate) governs wherever every species of a reaction is
tabulated. Materials Project DFT (BY-C entries, database version recorded) is printed beside it as a
comparator under the two gas-reference schemes of gas_reference.md (`janaf`, `mp`) and is labelled
`dft-unbenchmarked` for phosphates until a phosphate benchmark passes (PH-W5.1).

The carbonate control runs through the same reaction code (`carbonate_control`); the gate compares it with
the frozen value.

    uv run python -m nacre.pourbaix.ph_k1 gate
    uv run python -m nacre.pourbaix.ph_k1 run
"""
import argparse
import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field

from scipy import constants

from nacre.pourbaix import cache, gasref, inputs, ph_cache, provenance, salts
from nacre.pourbaix import gas as gasmod
from nacre.pourbaix import supplement_cache as sc
from nacre.pourbaix import supplement_d3 as sd3
from nacre.pourbaix import window as w
from nacre.pourbaix.entries import KJ_PER_MOL_PER_EV, entry_key, material_id
from nacre.pourbaix.paths import POURBAIX_RESULTS, REPO, rel

SESSION = "PH-K1"
OUT = POURBAIX_RESULTS / "ph_k1"
T0 = 298.15
K_B_EV = constants.k / constants.e
F_KJ = constants.e * constants.N_A / 1000.0  # kJ per volt per mole of electrons
KCAL_KJ = constants.calorie  # 4.184
PARAMS_SHA = "8bc15c88f5f4a28e64d394186729836bac01cfec"  # lit/params.yaml at tag p0-cp3, as the frozen carbonate runs
EVIDENCE = REPO / "lit" / "evidence_table.csv"
FROZEN_SUMMARY = POURBAIX_RESULTS / "supplement_d3" / "cell_d3_summary.json"
FROZEN_INVENTORY_V = 3.938  # ops/reports/carbonate_control_inventory.md, row 4 (CaCO3, LiClO4, expt)
GATE_TOL_V = 1.0e-3

# Design axes. Neither a_w nor the OH-site activity is a params key at this sha (a_w_slurry is a gap), so each is
# reported over a stated grid; the reference state is a_w = 1 (liquid water) and a_OH = 1 (stoichiometric apatite).
A_W_GRID = [1.0, 1.0e-2, 1.0e-4, 1.0e-6]
A_OH_GRID = [1.0, 0.5, 0.1, 0.01]
CUTOFF_CLASSES = {  # V vs Li+/Li; inf and sup of each class (theory/claims_redirect.md 2e)
    "LFP-class": (3.65, 3.65),
    "4.2-4.3 V": (4.2, 4.3),
    "4.4-4.5 V": (4.4, 4.5),
}
SCHEMES = ("janaf", "mp")


# ------------------------------------------------------------------------------------ species
# sid -> formula (for balancing), expt source, MP pin. `expt` kinds: row (dfG evidence row), params (W1 key + row for u),
# janaf (table in a cache), exchange (sink salt through its tabulated enthalpy), special (Li, O2, H2O).
SPECIES = {
    "Li": {"formula": "Li", "expt": {"kind": "special"}},
    "O2": {"formula": "O2", "expt": {"kind": "special"}},
    "H2O": {"formula": "H2O", "expt": {"kind": "special"}, "mp": {"pin": None}},
    "LiClO4": {"formula": "LiClO4", "expt": {"kind": "janaf", "table": "LiClO4"}, "mp": {"pin": "mp-30301"}},
    "Ca(ClO4)2": {"formula": "Ca(ClO4)2", "expt": {"kind": "exchange", "z": 2, "ds_key": "exchange_entropy_bound"}},
    "Al(ClO4)3": {"formula": "Al(ClO4)3", "expt": {"kind": "exchange", "z": 3, "ds_key": None}},
    "CO2": {"formula": "CO2", "expt": {"kind": "params", "key": "dfg_co2_g", "row": "TI-008"}},
    "CaCO3": {"formula": "CaCO3", "expt": {"kind": "params", "key": "dfg_caco3_calcite", "row": "TI-002"},
              "mp": {"pin": "mp-3953", "frozen": True}},
    "P2O5": {"formula": "P2O5", "expt": {"kind": "row", "dfg": "TR-012", "dfh": "TR-011", "s": "TR-010"},
             "mp": {"pin": "mp-562613"}},
    "H3PO4": {"formula": "H3PO4", "expt": {"kind": "row", "dfg": "TR-119"}, "mp": {"pin": "mp-23902"}},
    "SiO2": {"formula": "SiO2", "expt": {"kind": "janaf", "table": "SiO2", "cache": "ph", "u_missing": True},
             "mp": {"pin": None, "sg": [152, 154]}},
    "HAp": {"formula": "Ca5(PO4)3OH", "expt": {"kind": "row", "dfg": "TR-009", "dfh": "TR-008", "s": "TR-007"},
            "mp": {"pin": "mp-41472"}, "oh_site": True},
    "b-TCP": {"formula": "Ca3(PO4)2", "expt": {"kind": "row", "dfg": "TR-006", "dfh": "TR-005", "s": "TR-004",
                                               "check": "TR-023"},
              "mp": {"pin": "mp-531132"}},
    "a-TCP": {"formula": "Ca3(PO4)2", "expt": {"kind": "row", "dfg": "TR-026", "dfh": "TR-025", "s": "TR-027"},
              "mp": {"pin": "mp-1197377"}},
    "OCP": {"formula": "Ca8P6H12O29", "expt": {"kind": "row", "dfg": "TR-039", "dfg_only": True},
            "mp": {"pin": "mp-1229154"}},
    "brushite": {"formula": "CaPH5O6", "expt": {"kind": "row", "dfg": "TR-037", "s": "TR-038", "dfh": "TR-036"},
                 "mp": {"pin": "mp-24389"}},
    "monetite": {"formula": "CaHPO4", "expt": {"kind": "row", "dfg": "TR-034", "s": "TR-035", "dfh": "TR-033"},
                 "mp": {"pin": "mp-24390"}},
    "Ca2P2O7": {"formula": "Ca2P2O7", "expt": {"kind": "row", "dfg": "TR-029", "dfh": "TR-028", "s": "TR-030"},
                "mp": {"pin": "mp-3531"}},
    "Ca(PO3)2": {"formula": "Ca(PO3)2", "expt": {"kind": "missing",
                                                  "reason": "Ca(PO3)2: no DfG and no crystalline DfH (TR-031 gives S only, "
                                                            "TR-032 the glass DfH); lit/corpus/T-R/gaps.md"},
                 "mp": {"pin": "mp-5680"}},
    "AlPO4": {"formula": "AlPO4", "expt": {"kind": "row", "dfg": "TR-003", "dfh": "TR-002", "s": "TR-001"},
              "mp": {"pin": "mp-5331"}},
    "Al(PO3)3": {"formula": "Al(PO3)3", "expt": {"kind": "missing",
                                                   "reason": "Al(PO3)3: no DfH, DfG, S or solubility found "
                                                             "(lit/corpus/T-R/gaps.md)"},
                 "mp": {"pin": "mp-1019377"}},
    "Li3PO4": {"formula": "Li3PO4", "expt": {"kind": "missing",
                                              "reason": "Li3PO4: only DfH (TR-040); DfG and S not found "
                                                        "(lit/corpus/T-R/gaps.md)"},
               "mp": {"pin": "mp-2878"}},
    "Li4P2O7": {"formula": "Li4P2O7", "expt": {"kind": "missing", "reason": "Li4P2O7: no tabulated formation data in "
                                                                           "the corpus"},
                "mp": {"pin": "mp-28450"}},
    "CaSiO3": {"formula": "CaSiO3", "expt": {"kind": "row", "dfg": "TR-018", "dfh": "TR-017", "s": "TR-016"},
               "mp": {"pin": "mp-4429"}},
    "Ca2SiO4": {"formula": "Ca2SiO4", "expt": {"kind": "row", "dfg": "TR-021", "dfh": "TR-020", "s": "TR-019"},
                "mp": {"pin": "mp-4481"}},
    "Li2SiO3": {"formula": "Li2SiO3", "expt": {"kind": "row", "dfg": "TR-044", "dfh": "TR-043", "s": "TR-045"},
                "mp": {"pin": "mp-5012"}},
}

NAMES = {
    "HAp": "hydroxyapatite Ca5(PO4)3OH", "b-TCP": "beta-TCP Ca3(PO4)2", "a-TCP": "alpha-TCP Ca3(PO4)2",
    "OCP": "octacalcium phosphate Ca8H2(PO4)6.5H2O", "brushite": "brushite CaHPO4.2H2O",
    "monetite": "monetite CaHPO4", "Ca2P2O7": "calcium pyrophosphate Ca2P2O7", "Ca(PO3)2": "calcium metaphosphate Ca(PO3)2",
    "AlPO4": "aluminium phosphate AlPO4 (berlinite)", "Al(PO3)3": "aluminium metaphosphate Al(PO3)3",
    "Li3PO4": "lithium phosphate Li3PO4", "CaSiO3": "wollastonite CaSiO3", "Ca2SiO4": "calcium orthosilicate Ca2SiO4",
    "Li2SiO3": "lithium metasilicate Li2SiO3", "CaCO3": "calcite CaCO3 (control)",
    "P2O5": "P2O5", "H3PO4": "H3PO4", "SiO2": "SiO2 (quartz)", "Li4P2O7": "Li4P2O7", "H2O": "H2O", "O2": "O2",
    "Li": "Li", "CO2": "CO2", "LiClO4": "LiClO4", "Ca(ClO4)2": "Ca(ClO4)2", "Al(ClO4)3": "Al(ClO4)3",
}

# role: candidate | precursor | competing | comparator | control. Each reaction: (id, class, extra reactants, products).
SINK_CA = ["LiClO4"]
PHASES = [
    {"id": "HAp", "role": "candidate", "reactions": [
        ("r1", "r1 lattice O2 release (to P2O5)", SINK_CA, ["Ca(ClO4)2", "P2O5", "H2O", "O2", "Li"]),
        ("r1s", "r1 lattice O2 release (staged, to Ca2P2O7)", SINK_CA, ["Ca2P2O7", "Ca(ClO4)2", "H2O", "O2", "Li"]),
        ("r2", "r2 structural OH oxidation (to beta-TCP)", SINK_CA, ["b-TCP", "Ca(ClO4)2", "H2O", "O2", "Li"])]},
    {"id": "b-TCP", "role": "candidate", "reactions": [
        ("r1", "r1 lattice O2 release (to P2O5)", SINK_CA, ["Ca(ClO4)2", "P2O5", "O2", "Li"]),
        ("r1s", "r1 lattice O2 release (staged, to Ca2P2O7)", SINK_CA, ["Ca2P2O7", "Ca(ClO4)2", "O2", "Li"])]},
    {"id": "a-TCP", "role": "candidate", "reactions": [
        ("r1", "r1 lattice O2 release (to P2O5)", SINK_CA, ["Ca(ClO4)2", "P2O5", "O2", "Li"]),
        ("r1s", "r1 lattice O2 release (staged, to Ca2P2O7)", SINK_CA, ["Ca2P2O7", "Ca(ClO4)2", "O2", "Li"])]},
    {"id": "OCP", "role": "candidate", "reactions": [
        ("r1", "r1 lattice O2 release (to P2O5, lattice water released)", SINK_CA,
         ["Ca(ClO4)2", "P2O5", "H2O", "O2", "Li"])]},
    {"id": "brushite", "role": "precursor", "reactions": [
        ("r1", "r1 lattice O2 release (to P2O5, lattice water released)", SINK_CA,
         ["Ca(ClO4)2", "P2O5", "H2O", "O2", "Li"]),
        ("r3", "r3 water oxidation in the hydrate (to H3PO4, protons taken up by the phosphate)", SINK_CA,
         ["Ca(ClO4)2", "H3PO4", "H2O", "O2", "Li"])]},
    {"id": "monetite", "role": "precursor", "reactions": [
        ("r1", "r1 lattice O2 release (to P2O5)", SINK_CA, ["Ca(ClO4)2", "P2O5", "H2O", "O2", "Li"])]},
    {"id": "Ca2P2O7", "role": "candidate", "reactions": [
        ("r1", "r1 lattice O2 release (to P2O5)", SINK_CA, ["Ca(ClO4)2", "P2O5", "O2", "Li"]),
        ("r1s", "r1 lattice O2 release (staged, to Ca(PO3)2)", SINK_CA, ["Ca(PO3)2", "Ca(ClO4)2", "O2", "Li"])]},
    {"id": "Ca(PO3)2", "role": "candidate", "reactions": [
        ("r1", "r1 lattice O2 release (to P2O5)", SINK_CA, ["Ca(ClO4)2", "P2O5", "O2", "Li"])]},
    {"id": "AlPO4", "role": "candidate", "reactions": [
        ("r4", "r4 Al-phase oxidation (Al3+ to the sink, anion to P2O5)", ["LiClO4"], ["Al(ClO4)3", "P2O5", "O2", "Li"]),
        ("r4s", "r4 Al-phase oxidation (staged, to Al(PO3)3)", ["LiClO4"], ["Al(PO3)3", "Al(ClO4)3", "O2", "Li"])]},
    {"id": "Al(PO3)3", "role": "candidate", "reactions": [
        ("r4", "r4 Al-phase oxidation (Al3+ to the sink, anion to P2O5)", ["LiClO4"], ["Al(ClO4)3", "P2O5", "O2", "Li"])]},
    {"id": "Li3PO4", "role": "competing", "reactions": [
        ("r1", "r1 lattice O2 release (to P2O5, Li-open)", [], ["P2O5", "O2", "Li"]),
        ("r1s", "r1 lattice O2 release (staged, to Li4P2O7, Li-open)", [], ["Li4P2O7", "O2", "Li"])]},
    {"id": "CaSiO3", "role": "comparator", "reactions": [
        ("r1", "r1 lattice O2 release (to SiO2)", SINK_CA, ["Ca(ClO4)2", "SiO2", "O2", "Li"])]},
    {"id": "Ca2SiO4", "role": "comparator", "reactions": [
        ("r1", "r1 lattice O2 release (to SiO2)", SINK_CA, ["Ca(ClO4)2", "SiO2", "O2", "Li"]),
        ("r1s", "r1 lattice O2 release (staged, to CaSiO3)", SINK_CA, ["CaSiO3", "Ca(ClO4)2", "O2", "Li"])]},
    {"id": "Li2SiO3", "role": "comparator", "reactions": [
        ("r1", "r1 lattice O2 release (to SiO2, Li-open)", [], ["SiO2", "O2", "Li"])]},
    {"id": "CaCO3", "role": "control", "reactions": [
        ("r1", "r1 lattice O2 release (to CO2); the registered carbonate reaction", SINK_CA,
         ["Ca(ClO4)2", "CO2", "O2", "Li"])]},
]
PHASE_BY_ID = {p["id"]: p for p in PHASES}
ORDER = [p["id"] for p in PHASES]


class Missing(Exception):
    """A species of a reaction has no usable value on this route."""


@dataclass
class Term:
    g_eV: float
    u_kJ: float = 0.0
    complete: bool = True  # False when an uncertainty or an entropy bound is missing
    ds_J_per_K: float = 0.0  # entropy bound of an exchange (J K^-1 mol^-1), carried into the budget
    meta: dict = field(default_factory=dict)
    note: str = ""


# ---------------------------------------------------------------------------------- evidence rows
_ROWS = None


def evidence_rows():
    global _ROWS
    if _ROWS is None:
        with open(EVIDENCE, newline="", encoding="utf-8") as fh:
            _ROWS = {r["row_id"]: r for r in csv.DictReader(fh)}
    return _ROWS


def evidence_sha256():
    return hashlib.sha256(EVIDENCE.read_bytes()).hexdigest()


_UNIT_KJ = {"kJ/mol": 1.0, "kJ mol^-1": 1.0, "J/mol": 1.0e-3, "J mol^-1": 1.0e-3, "kcal/mol": KCAL_KJ}


def row_kj(row_id):
    """(value kJ/mol, u kJ/mol, text of the uncertainty basis) of an energy evidence row.

    Uncertainty as printed (+- x, 2 sigma for the USGS tables, in the row's unit); where none is printed the
    upper end of the NBS convention, 20 units of the last printed figure (row TK-030, params u_tab_*)."""
    r = evidence_rows()[row_id]
    f = _UNIT_KJ[r["unit"].replace(" ", "") if r["unit"].replace(" ", "") in ("kcal/mol",) else r["unit"]]
    val = float(r["value"]) * f
    unc = (r["range_or_uncertainty"] or "").replace("±", "").strip()
    if unc:
        return val, float(unc) * f, "as printed, %s" % unc
    txt = r["value"].strip().lstrip("-")
    digit = 10.0 ** (-len(txt.split(".")[1])) if "." in txt else 1.0
    return val, 20.0 * digit * f, "NBS convention, 20 units of the last figure (%g %s)" % (digit, r["unit"])


def row_cite(row_id):
    r = evidence_rows()[row_id]
    return {"row_id": row_id, "doi": r["doi"], "locator": r["locator"], "grade": r["grade"], "value": r["value"],
            "unit": r["unit"], "uncertainty": r["range_or_uncertainty"]}


# ------------------------------------------------------------------------------------- context
class Ctx:
    """Frozen inputs: params at tag p0-cp3 (as the carbonate runs), the evidence file, the caches."""

    def __init__(self, params_sha=PARAMS_SHA, T=T0):
        self.T = T
        self.params_sha = params_sha
        self.params = sd3.load_params(params_sha, sd3.EXTRA_KEYS)
        self.p_o2 = 1.0
        self.p_co2 = 1.0
        self._exchange = {}

    # exchange enthalpy (eV) of M + z LiClO4 -> M(ClO4)z + z Li, from tabulated dfH (solid entropy neglected)
    def exchange(self, salt):
        if salt in self._exchange:
            return self._exchange[salt]
        spec = SPECIES[salt]["expt"]
        z = spec["z"]
        dh_li, loc_li = salts.dfh_kj("LiClO4", self.T)
        u_li = float(self.params.value("u_tab_dfh_liclo4")) / 1000.0
        if salt == "Ca(ClO4)2":
            dh_s, loc_s = salts.dfh_kj("Ca(ClO4)2", self.T)
            nbs = salts.nbs_row("Ca(ClO4)2")
            # the last printed figure of the NBS row is 0.01 kcal; 20 units, as params u_tab_dfh_ca_clo4_2
            u_s = 20.0 * 0.01 * KCAL_KJ
            _ = nbs
        elif salt == "Al(ClO4)3":
            dh_s, u_s, loc_s = sc.literature_dfh_kj("krivtsov1973_al_clo4_3")
        else:
            raise KeyError(salt)
        out = {"dH_ex_eV": (dh_s - z * dh_li) / KJ_PER_MOL_PER_EV, "u_kJ": u_s + z * u_li,
               "locator": {"salt": loc_s, "LiClO4": loc_li}, "dfH_salt_kJ": dh_s, "dfH_LiClO4_kJ": dh_li}
        self._exchange[salt] = out
        return out

    def ds_bound(self, salt):
        key = SPECIES[salt]["expt"]["ds_key"]
        return float(self.params.value(key)) if key else None


def _params_row_u(ctx, key, row):
    r = ctx.params.row(row)
    unc = (r["range_or_uncertainty"] or "").replace("±", "").strip()
    return float(unc) * _UNIT_KJ[r["unit"]] if unc else None


# ------------------------------------------------------------------------------------ expt book
class ExptBook:
    """Free energy of each species (eV per formula unit, 298.15 K) from tabulated values, with u (kJ/mol)."""

    route = "expt"

    def __init__(self, ctx):
        self.ctx = ctx
        self.T = ctx.T
        self.kT = K_B_EV * ctx.T

    def __call__(self, sid):
        c = self.ctx
        spec = SPECIES[sid]["expt"]
        kind = spec["kind"]
        if sid == "Li":
            return Term(0.0, meta={"basis": "Li metal, the Li+/Li reference"})
        if sid == "O2":
            return Term(self.kT * math.log(c.p_o2), meta={"basis": "element in its reference state, p = %g bar" % c.p_o2})
        if sid == "H2O":
            key = "dfg_h2o_l"
            u = (float(c.params.range(key)["max"]) - float(c.params.range(key)["min"])) / 2.0 / 1000.0
            return Term(float(c.params.value(key)) / 1000.0 / KJ_PER_MOL_PER_EV, u,
                        meta={"source": c.params.cite(key), "state": "H2O(l), unit activity"})
        if kind == "missing":
            raise Missing(spec["reason"])
        if kind == "params":
            key = spec["key"]
            if c.params.unit(key) != "J mol^-1":
                raise ValueError(key)
            g = float(c.params.value(key)) / 1000.0 / KJ_PER_MOL_PER_EV
            u = _params_row_u(c, key, spec["row"])
            if sid == "CO2":
                g += self.kT * math.log(c.p_co2)
            return Term(g, u or 0.0, complete=u is not None, meta={"source": c.params.cite(key), "row": spec["row"]})
        if kind == "janaf":
            cdir = ph_cache.PH_CACHE if spec.get("cache") == "ph" else cache.CACHE_DIR
            r = gasmod.row_kj(spec["table"], self.T, cdir)
            if spec.get("u_missing"):
                return Term(r["dfG_kJ_per_mol"] / KJ_PER_MOL_PER_EV, 0.0, complete=False,
                            meta={"source": r["table"], "note": "JANAF prints no uncertainty; budget term missing"})
            # LiClO4: its free energy cancels in every reaction (Cl is conserved), so it carries no budget term
            return Term(r["dfG_kJ_per_mol"] / KJ_PER_MOL_PER_EV, 0.0, meta={"source": r["table"], "cancels": True})
        if kind == "exchange":
            ex = c.exchange(sid)
            g_li = self("LiClO4").g_eV
            ds = c.ds_bound(sid)
            return Term(spec["z"] * g_li + ex["dH_ex_eV"], ex["u_kJ"], complete=ds is not None,
                        ds_J_per_K=ds or 0.0,
                        meta={"basis": "exchange M + %d LiClO4 -> %s + %d Li: %d x G(LiClO4) plus the tabulated "
                                       "exchange enthalpy; solid entropy of the exchange neglected" %
                                       (spec["z"], sid, spec["z"], spec["z"]), "locator": ex["locator"]},
                        note="" if ds is not None else "no entropy bound key for this exchange")
        if kind == "row":
            val, u, ubasis = row_kj(spec["dfg"])
            return Term(val / KJ_PER_MOL_PER_EV, u, meta={"row": row_cite(spec["dfg"]), "u_basis": ubasis})
        raise ValueError(sid)


# ------------------------------------------------------------------------------------- DFT book
class DftBook:
    """MP formation energies (0 K, entropy neglected) under one gas-reference scheme; perchlorate sinks enter
    through the same tabulated exchange enthalpy as under the experimental route."""

    def __init__(self, scheme, ctx, entries):
        self.route = scheme
        self.ctx = ctx
        self.T = ctx.T
        self.scheme = scheme
        self.ew = w.EnergyBook(entries, ctx.T, gasref.SCHEMES[scheme], cache.CACHE_DIR)
        self.by_id = {}
        for e in entries:
            self.by_id.setdefault(material_id(e), []).append(e)
        self.kT = K_B_EV * ctx.T
        g_l = gasmod.formation_free_energy_ev("H2O_l", ctx.T, sc.SUPP_CACHE)
        g_g = gasmod.formation_free_energy_ev("H2O", ctx.T, sc.SUPP_CACHE)
        self.p_sat = math.exp((g_l - g_g) / self.kT)  # bar; a_w = p / p_sat

    def entry(self, sid):
        spec = SPECIES[sid].get("mp") or {}
        pin = spec.get("pin")
        if pin is None:
            return None
        cands = self.by_id.get(pin)
        if not cands:
            raise Missing("%s: Materials Project entry %s is not in the PH-K1 cache" % (sid, pin))
        return min(cands, key=lambda e: e.energy_per_atom)

    def solid(self, sid):
        from pymatgen.core import Composition

        spec = SPECIES[sid]
        best = self.entry(sid)
        if best is None:
            comp = Composition(spec["formula"])
            cands = [e for e in self.ew._by_formula.get(comp.reduced_formula, [])]
            if not cands:
                raise Missing("%s: no Materials Project entry" % sid)
            sgs = (spec.get("mp") or {}).get("sg")
            if sgs:
                from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
                sel = [e for e in cands if SpacegroupAnalyzer(e.structure, symprec=0.1).get_space_group_number() in sgs]
                cands = sel or cands
            best = min(cands, key=lambda e: (e.energy_per_atom, material_id(e)))
        comp = Composition(spec["formula"])
        g = self.ew.formation_energy(best) * (comp.num_atoms / best.composition.num_atoms)
        return Term(g, meta={"kind": "solid", "entry_id": entry_key(best), "material_id": material_id(best),
                             "basis": "MP formation energy, 0 K, MP2020; entropy neglected"})

    def water(self):
        s = gasmod.entropy_ev_per_K("H2O", self.T, sc.SUPP_CACHE)
        if self.scheme == "janaf":
            dfh, basis = gasmod.formation_enthalpy_ev("H2O", self.T, sc.SUPP_CACHE), "dfH from NIST-JANAF H-064"
        else:
            dfh = self.solid("H2O").g_eV
            basis = "dfH from the MP H2O solid (sublimation not included)"
        g = dfh - self.T * s + self.kT * math.log(self.p_sat)
        return Term(g, meta={"kind": "gas", "basis": basis + "; S(T) from JANAF H-064; p = p_sat (a_w = 1)",
                             "p_sat_bar": self.p_sat})

    def __call__(self, sid):
        if sid == "Li":
            return Term(0.0)
        if sid == "O2":
            g, meta = self.ew.gas("O2")
            return Term(g, meta=meta)
        if sid == "H2O":
            return self.water()
        if sid in ("Ca(ClO4)2", "Al(ClO4)3"):
            ex = self.ctx.exchange(sid)
            z = SPECIES[sid]["expt"]["z"]
            return Term(z * self("LiClO4").g_eV + ex["dH_ex_eV"],
                        meta={"basis": "exchange route, as the experimental book", "dH_ex_eV": ex["dH_ex_eV"]})
        if SPECIES[sid].get("mp", {}).get("frozen"):
            raise Missing("%s: Materials Project energies of the carbonate system are the frozen production values" % sid)
        if sid == "CO2":
            raise Missing("CO2: carbonate system not in the PH-K1 cache")
        return self.solid(sid)


# ----------------------------------------------------------------------------------- reactions
def formula_map(sids):
    out = {}
    for s in sids:
        f = SPECIES[s]["formula"]
        if f in out:
            raise ValueError("two species with formula %s in one reaction" % f)
        out[f] = s
    return out


def build_reaction(phase_sid, extra, products):
    """Balanced reaction with the phase at -1: {sid: coefficient}, its text and n_e (= coefficient of Li)."""
    reactants = [phase_sid] + list(extra)
    fm = formula_map(reactants + products)
    try:
        coeffs, text = w.balance([SPECIES[s]["formula"] for s in reactants], [SPECIES[s]["formula"] for s in products],
                                 SPECIES[phase_sid]["formula"])
    except Exception as exc:  # noqa: BLE001 - pymatgen raises ReactionError and others
        raise ValueError("%s: cannot balance: %s" % (phase_sid, exc)) from exc
    by_sid = {fm[f]: c for f, c in coeffs.items()}
    bad = [s for s in reactants if by_sid.get(s, 0.0) >= 0] + [s for s in products if by_sid.get(s, 0.0) <= 0]
    if bad:
        raise ValueError("%s: not an oxidation as written; coefficient sign or zero for %s" % (phase_sid, bad))
    return by_sid


def reaction_text(by_sid):
    """Reaction as text, species by formula (phases that share a formula carry their id)."""
    def label(s):
        f = SPECIES[s]["formula"]
        return "%s [%s]" % (f, s) if s in ("b-TCP", "a-TCP", "HAp", "brushite", "monetite", "OCP") else f

    def side(sign):
        parts = []
        for s, c in by_sid.items():
            if c * sign > 0:
                n = abs(c)
                parts.append(("%g " % round(n, 4) if abs(n - 1) > 1e-9 else "") + label(s))
        return " + ".join(parts)
    return "%s -> %s" % (side(-1), side(1))


def evaluate(by_sid, book, act=None, budget=True):
    """Onset of one reaction under one book. act = {"a_w": x, "a_oh": y}: activities of H2O and of the OH site.

    Returns a dict: status finite|undetermined, onset_V, dg_eV, n_e, and for the experimental route the budget
    (V) as a linear sum of the row uncertainties plus the exchange entropy bound, with a completeness flag."""
    act = act or {}
    n_e = by_sid["Li"]
    kT = K_B_EV * book.T
    dg, terms, miss, u_kj, ds_j, complete = 0.0, {}, [], 0.0, 0.0, True
    for s, c in by_sid.items():
        try:
            t = book(s)
        except Missing as exc:
            miss.append({"species": s, "reason": str(exc)})
            continue
        g = t.g_eV
        if s == "H2O" and act.get("a_w") is not None:
            g += kT * math.log(act["a_w"])
        if SPECIES[s].get("oh_site") and act.get("a_oh") is not None:
            g += kT * math.log(act["a_oh"])
        dg += c * g
        u_kj += abs(c) * t.u_kJ
        ds_j += abs(c) * t.ds_J_per_K
        complete = complete and t.complete
        terms[s] = {"coefficient": c, "G_eV": g, **t.meta, "u_kJ": t.u_kJ, **({"note": t.note} if t.note else {})}
    if miss:
        return {"status": "undetermined", "onset_V": None, "n_e": n_e, "missing": miss, "terms": terms}
    out = {"status": "finite", "onset_V": dg / n_e, "dg_eV": dg, "n_e": n_e, "terms": terms, "missing": []}
    if budget and book.route == "expt":
        out["budget_V"] = (u_kj + T0 * ds_j / 1000.0) / (n_e * F_KJ)
        out["budget_complete"] = complete
        out["budget_terms_kJ"] = {"tabulated": u_kj, "entropy_bound": T0 * ds_j / 1000.0}
    return out


# ---------------------------------------------------------------------------------------- gate
def carbonate_control(ctx=None):
    """CaCO3 + 2 LiClO4 -> Ca(ClO4)2 + CO2 + 1/2 O2 + 2 Li, experimental route, through the generic code."""
    ctx = ctx or Ctx()
    ph = PHASE_BY_ID["CaCO3"]
    rid, _, extra, products = ph["reactions"][0]
    by_sid = build_reaction("CaCO3", extra, products)
    return {"reaction": by_sid, "result": evaluate(by_sid, ExptBook(ctx)), "text": reaction_text(by_sid)}


def gate(ctx=None):
    ctx = ctx or Ctx()
    ctl = carbonate_control(ctx)
    frozen = json.loads(FROZEN_SUMMARY.read_text(encoding="utf-8"))
    frozen_full = frozen["phases"]["CaCO3"]["by_sink"]["LiClO4"]["governing_V"]["expt"]
    margin_key = float(ctx.params.value("window_margin_expt"))
    v = ctl["result"]["onset_V"]
    out = {"value_V": v, "frozen_V_inventory": FROZEN_INVENTORY_V, "frozen_V_full_precision": frozen_full,
           "difference_to_inventory_mV": 1000.0 * (v - FROZEN_INVENTORY_V),
           "difference_to_full_precision_mV": 1000.0 * (v - frozen_full), "tolerance_mV": 1000.0 * GATE_TOL_V,
           "budget_V": ctl["result"]["budget_V"], "frozen_budget_V": margin_key,
           "budget_difference_V": ctl["result"]["budget_V"] - margin_key, "reaction": ctl["text"],
           "n_e": ctl["result"]["n_e"],
           "passed": abs(v - FROZEN_INVENTORY_V) <= GATE_TOL_V and abs(v - frozen_full) <= GATE_TOL_V}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.ph_k1")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gate")
    sub.add_parser("run")
    args = ap.parse_args(argv)
    if args.cmd == "gate":
        g = gate()
        print(json.dumps(g, indent=1))
        return 0 if g["passed"] else 1
    from nacre.pourbaix import ph_k1_run
    return ph_k1_run.run()


if __name__ == "__main__":
    sys.exit(main())
