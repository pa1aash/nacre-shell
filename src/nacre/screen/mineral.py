"""The mineral object of the screen chain (contract v5, theory/claims_redirect.md).

A mineral is the nucleus phase whose saturation state, molar volume and interfacial energies the chain
evaluates. It names the table keys that supply K_sp, V_m and the gamma set of one framing, the
stoichiometry of its formula unit and, for the phosphate routes, two fields that do not exist for calcite:

    phase_state    crystalline (default) | amorphous | liquid_precursor
    chain_length_n integer chain length of a condensed phosphate, or None (default)

Stoichiometry. The formula unit has nu_ca Ca2+ ions, nu_x ions of the anion type X and nu_y ions of the
anion type Y, so nu = nu_ca + nu_x + nu_y (calcite 1 + 1 + 0, hydroxyapatite 5 + 3 + 1), and n_hyd structural
water molecules that enter the ion activity product only through a_w^n. K_sp is written for the same
formula unit. ``x_symbol`` and ``y_symbol`` are the chain symbols of the two anion activities.

Calcite in its carbonate form (nu = 2, no water, X = CO3) takes the legacy code path of the chain unchanged,
so the carbonate results are reproduced exactly; every other mineral takes the contract v5 functions.
"""
from dataclasses import dataclass, field
from typing import Mapping, Optional

PHASE_STATES = ("crystalline", "amorphous", "liquid_precursor")
SPECIATIONS = (None, "carbonate", "phosphate")


class MineralError(ValueError):
    """The mineral object is inconsistent."""


@dataclass(frozen=True, eq=False)
class Mineral:
    name: str
    formula_unit: str
    nu_ca: float
    nu_x: float
    ksp_key: str
    vm_key: str
    framing: str
    nu_y: float = 0.0
    n_hyd: float = 0.0
    gamma_keys: Mapping = field(default_factory=dict)       # {"gamma_nl": table key, "gamma_nv": table key, ...}
    x_symbol: str = "a_X"
    y_symbol: str = "a_Y"
    speciation: Optional[str] = None                       # which free-ion speciation supplies a_Ca and the anions
    n_hyd_key: Optional[str] = None                        # table key of the structural water (registered with the framing)
    phase_state: str = "crystalline"
    chain_length_n: Optional[int] = None
    k1_phase: Optional[str] = None                         # phase name of the K1 ladder (several framings share one)
    input_keys: Mapping = field(default_factory=dict)      # {symbol: table key} of inputs this mineral alone reads
                                                           # (the activities of a mineral with no speciation)

    def __post_init__(self):
        if self.phase_state not in PHASE_STATES:
            raise MineralError("%s: phase_state %r is not one of %s" % (self.name, self.phase_state, PHASE_STATES))
        n = self.chain_length_n
        if n is not None and (isinstance(n, bool) or not isinstance(n, int) or n < 1):
            raise MineralError("%s: chain_length_n must be a positive integer or None, got %r" % (self.name, n))
        if self.speciation not in SPECIATIONS:
            raise MineralError("%s: speciation must be one of %s" % (self.name, SPECIATIONS))
        if not (self.nu_ca > 0 and self.nu_x > 0 and self.nu_y >= 0 and self.n_hyd >= 0):
            raise MineralError("%s: stoichiometry needs nu_ca > 0, nu_x > 0, nu_y >= 0 and n_hyd >= 0" % self.name)
        if self.nu_y > 0 and self.y_symbol == self.x_symbol:
            raise MineralError("%s: the two anion types need distinct activity symbols" % self.name)
        if self.chain_length_n is not None and self.speciation == "carbonate":
            raise MineralError("%s: a chain length belongs to a condensed phosphate" % self.name)

    @property
    def nu(self):
        """Ions per formula unit, nu = nu_ca + nu_x + nu_y (contract v5)."""
        return self.nu_ca + self.nu_x + self.nu_y

    @property
    def is_carbonate_form(self):
        """True for the stoichiometry of calcite with the carbonate anion: the legacy chain path."""
        return (self.nu_ca == 1 and self.nu_x == 1 and self.nu_y == 0 and not self.hydrated
                and self.x_symbol == "a_CO3")

    @property
    def hydrated(self):
        """True when structural water enters the IAP: a stoichiometric n_hyd, or an n_hyd read from the table."""
        return self.n_hyd > 0 or self.n_hyd_key is not None

    @property
    def activity_symbols(self):
        """Chain symbols of the IAP inputs (water activity, and n from the table where it is registered there)."""
        out = ["a_Ca", self.x_symbol]
        if self.nu_y > 0:
            out.append(self.y_symbol)
        if self.hydrated:
            out.append("a_w")
        if self.n_hyd_key is not None:
            out.append("n_hyd")
        return tuple(out)

    @property
    def omega_symbols(self):
        return self.activity_symbols + ("K_sp",)

    def describe(self):
        """The record printed beside every result of this mineral."""
        return {"name": self.name, "formula_unit": self.formula_unit, "nu": self.nu,
                "stoichiometry": {"nu_ca": self.nu_ca, "nu_x": self.nu_x, "nu_y": self.nu_y, "n_hyd": self.n_hyd},
                "k1_phase": self.k1_phase or self.name, "framing": self.framing, "phase_state": self.phase_state, "chain_length_n": self.chain_length_n,
                "ksp_key": self.ksp_key, "vm_key": self.vm_key, "gamma_keys": dict(self.gamma_keys),
                "n_hyd_key": self.n_hyd_key, "input_keys": dict(self.input_keys)}


#: The control of the screen, unchanged: calcite in the carbonate form.
CALCITE = Mineral("calcite", "CaCO3", 1, 1, "log10_ksp_calcite", "v_m_calcite", "calcite",
                  x_symbol="a_CO3", speciation="carbonate",
                  gamma_keys={"gamma_nl": "gamma_nl_calcite", "gamma_nv": "gamma_nv_calcite"})


def from_config(name, spec):
    """A mineral from one entry of screen.yaml ``minerals`` (stoichiometry, table keys, fields)."""
    st = spec.get("stoichiometry") or {}
    keys = spec.get("keys") or {}
    for k in ("ksp", "v_m"):
        if k not in keys:
            raise MineralError("%s: keys.%s is required" % (name, k))
    return Mineral(
        name=name, formula_unit=str(spec["formula_unit"]), nu_ca=st.get("nu_ca"), nu_x=st.get("nu_x"),
        nu_y=st.get("nu_y", 0), n_hyd=st.get("n_hyd", 0), ksp_key=keys["ksp"], vm_key=keys["v_m"],
        framing=str(spec.get("framing", name)), gamma_keys=dict(spec.get("gamma_keys") or {}),
        x_symbol=spec.get("x_symbol", "a_X"), y_symbol=spec.get("y_symbol", "a_Y"),
        speciation=spec.get("speciation"), n_hyd_key=keys.get("n_hyd"),
        phase_state=spec.get("phase_state", "crystalline"), chain_length_n=spec.get("chain_length_n"),
        k1_phase=spec.get("k1_phase"), input_keys=dict(spec.get("inputs") or {}))


def registry(cfg):
    """{name: Mineral} of screen.yaml ``minerals`` plus the calcite control."""
    out = {"calcite": CALCITE}
    for name, spec in ((cfg or {}).get("minerals") or {}).items():
        out[name] = from_config(name, spec)
    return out
