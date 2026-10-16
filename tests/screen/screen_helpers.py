"""Shared helpers of the screen tests (synthetic numbers only, never literature values)."""
from nacre.screen import decision as dc

P = 0.9                                  # synthetic credible level


def synthetic_resolver(**over):
    """Resolver with synthetic values for every parameter-table key the thresholds block names."""
    vals = {
        "thresholds.decision.credible_level": P,
        "thresholds.decision.degrade_mass_min": 0.1,
        "thresholds.C1.margin_W_adh_wet": 0.1,
        "regimes.R-slurry.parameters.termination_weights": {"t1": 3.0, "t2": 1.0},
        "thresholds.C2.margin_DG_seq": 1000.0,
        "thresholds.C3.margin_cos_theta": 0.0,
        "thresholds.C3.N_req": 10.0,
        "regimes.R-slurry.parameters.J0_het": 1.0,
        "regimes.R-slurry.parameters.t_proc": 1.0,
        "thresholds.C4.margin_S_spread": 0.0,
        "regimes.R-cell.parameters.R_A_max": 1.0, "regimes.R-cell.parameters.rho_e": 1.0e9,
        "regimes.R-cell.parameters.j_req": 1.0, "regimes.R-cell.parameters.j_0": 1.0e3,
        "regimes.R-cell.parameters.phi_B": 1.0e-19, "regimes.R-cell.parameters.m_eff": 1.0e-30,
        "regimes.R-slurry.parameters.framing": "calcite",
        "thresholds.C5.formation_energy_error": (0.05, "eV/atom"),
        "regimes.R-slurry.parameters.ACC_offset": (10000.0, "J mol^-1"),
        "regimes.R-slurry.parameters.pH_range": {"min": 2.0, "max": 3.0},
        "regimes.R-slurry.parameters.E_SHE_range": {"min": -1.0, "max": 0.0},
        "thresholds.C5.window_margin": (0.1, "V"),
        "regimes.R-cell.parameters.E_min": (2.0, "V"),
        "regimes.R-cell.parameters.E_max": (4.0, "V"),
        "regimes.R-cell.parameters.al_phases": ["Al2O3"],
    }
    vals.update(over)
    return dc.Resolver(vals)
