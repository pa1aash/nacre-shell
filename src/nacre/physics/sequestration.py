"""Ca2+ sequestration by the template and the local enrichment it produces (claim C2).

Theory contract (P0-W3.1):
    Delta_G_seq  = Delta_G_site + R T ln(1 + 10^(pKa - pH))   (single coordinating group
                   that must be deprotonated to bind)
    E_enr        = exp(-Delta_G_seq / (R T))                 (dilute, unsaturated limit)
    c_max        = Gamma_s / delta_s                         (saturation of the binding layer)
    c_local      = E_enr c_bulk / (1 + E_enr c_bulk / c_max) (Langmuir closure)

The saturation bound: c_local <= c_max and c_local <= E_enr c_bulk for every input.
"""
import numpy as np

from nacre.physics._domain import non_negative, positive, real, scalar_or_array
from nacre.physics.constants import GAS_CONSTANT


def sequestration_free_energy(Delta_G_site, pKa, pH, T):
    """Ca2+ transfer free energy, bulk to binding layer, with the protonation correction (J mol^-1).

    Delta_G_site + R T ln(1 + 10^(pKa - pH)); the correction is the free energy of finding
    the site deprotonated at the regime pH, never negative.
    """
    g = real("Delta_G_site (transfer free energy to the deprotonated site)", Delta_G_site)
    pka = real("pKa", pKa)
    ph = real("pH", pH)
    t = positive("T (temperature)", T)
    return scalar_or_array(g + GAS_CONSTANT * t * np.logaddexp(0.0, (pka - ph) * np.log(10.0)))


def enrichment_factor(Delta_G_seq, T):
    """Ca2+ enrichment factor c_local / c_bulk = exp(-Delta_G_seq / (R T)), dilute limit."""
    g = real("Delta_G_seq (Ca2+ transfer free energy)", Delta_G_seq)
    t = positive("T (temperature)", T)
    return scalar_or_array(np.exp(-g / (GAS_CONSTANT * t)))


def binding_layer_saturation_concentration(Gamma_s, delta_s):
    """Saturation concentration of the binding layer c_max = Gamma_s / delta_s, mol m^-3."""
    gs = positive("Gamma_s (areal binding-site density)", Gamma_s)
    ds = positive("delta_s (binding-layer thickness)", delta_s)
    return scalar_or_array(gs / ds)


def local_calcium_concentration(E_enr, c_bulk, c_max):
    """Mean Ca2+ concentration in the binding layer, mol m^-3 (Langmuir closure).

    E_enr c_bulk / (1 + E_enr c_bulk / c_max): equals E_enr c_bulk when dilute and tends to
    c_max as the layer saturates; never exceeds either.
    """
    e = non_negative("E_enr (enrichment factor)", E_enr)
    cb = positive("c_bulk (bulk Ca2+ concentration)", c_bulk)
    cm = positive("c_max (layer saturation concentration)", c_max)
    x = e * cb
    return scalar_or_array(x / (1.0 + x / cm))
