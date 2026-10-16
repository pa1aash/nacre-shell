"""Ca2+ sequestration by the template, its occupancy and its effect on gamma_sl (claim C2).

Theory contract (v2, P0-W3.2):
    Delta_G_seq      = Delta_G_site + R T ln(1 + 10^(pKa - pH))   (single coordinating group
                       that must be deprotonated to bind)
    E_enr            = exp(-Delta_G_seq / (R T))         (a concentration ratio, dilute limit)
    c_max            = Gamma_s / delta_s                 (saturation of the binding layer)
    c_local          = E_enr c_bulk / (1 + E_enr c_bulk / c_max)   (Langmuir closure)
    x_bind           = E_enr c_bulk / c_max              (occupancy odds of a site)
    Theta_occ        = x / (1 + x)                       (fraction of sites occupied)
    Gamma_Ca         = Gamma_s Theta - delta_s c_bulk    (Gibbs relative surface excess)
    Delta_gamma_ads  = -R T (Gamma_s ln(1 + x) - delta_s c_bulk)
                       (Gibbs adsorption integral with the Langmuir isotherm)

At equilibrium the Ca2+ chemical potential is uniform, so E_enr and c_local are reporting
quantities of C2 and never enter the driving force; the binding reaches the nucleation
barrier only through Delta_gamma_ads in gamma_sl (contract no_double_counting).
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


def _log_binding_odds(Delta_G_seq, T, c_bulk, Gamma_s, delta_s):
    g = real("Delta_G_seq (Ca2+ transfer free energy)", Delta_G_seq)
    t = positive("T (temperature)", T)
    cb = positive("c_bulk (bulk Ca2+ concentration)", c_bulk)
    gs = positive("Gamma_s (areal binding-site density)", Gamma_s)
    ds = positive("delta_s (binding-layer thickness)", delta_s)
    return -g / (GAS_CONSTANT * t) + np.log(cb * ds / gs)


def binding_odds(Delta_G_seq, T, c_bulk, Gamma_s, delta_s):
    """Langmuir binding variable x = E_enr c_bulk delta_s / Gamma_s (dimensionless).

    The odds that a binding site is occupied by Ca2+ at the regime activity: x / (1 + x)
    is the occupied fraction.
    """
    with np.errstate(over="ignore"):
        return scalar_or_array(np.exp(_log_binding_odds(Delta_G_seq, T, c_bulk, Gamma_s, delta_s)))


def site_occupancy(Delta_G_seq, T, c_bulk, Gamma_s, delta_s):
    """Fraction of template binding sites occupied by Ca2+, Theta = x / (1 + x) (Langmuir).

    Evaluated as 1 / (1 + 1/x) from ln x, so it tends to 1 for strong binding and to 0 for
    a repulsive site without overflow.
    """
    lx = _log_binding_odds(Delta_G_seq, T, c_bulk, Gamma_s, delta_s)
    with np.errstate(over="ignore"):
        return scalar_or_array(1.0 / (1.0 + np.exp(-lx)))


def calcium_surface_excess(Delta_G_seq, T, c_bulk, Gamma_s, delta_s):
    """Gibbs relative surface excess of Ca2+ at the template-liquid interface, mol m^-2.

    Gamma_s Theta - delta_s c_bulk: the bound amount per area minus the amount the layer
    volume would hold at the bulk concentration without the template. Negative for a
    template that depletes Ca2+.
    """
    th = np.asarray(site_occupancy(Delta_G_seq, T, c_bulk, Gamma_s, delta_s))
    gs = positive("Gamma_s (areal binding-site density)", Gamma_s)
    ds = positive("delta_s (binding-layer thickness)", delta_s)
    cb = positive("c_bulk (bulk Ca2+ concentration)", c_bulk)
    return scalar_or_array(gs * th - ds * cb)


def adsorption_interfacial_energy_change(Delta_G_seq, T, c_bulk, Gamma_s, delta_s):
    """Change of the template-liquid interfacial energy by Ca2+ adsorption, J m^-2.

    Delta_gamma_ads = -R T (Gamma_s ln(1 + x) - delta_s c_bulk): the Gibbs adsorption
    integral -int Gamma_Ca d mu_Ca from zero Ca2+ to the regime activity with the Langmuir
    isotherm (ideal dilute bulk). Negative for net binding (it lowers gamma_sl), positive
    for a depleting template. It is the only route by which Delta_G_seq, Gamma_s and
    delta_s reach the nucleation barrier, and it is zero by definition when gamma_sl is
    already evaluated at the regime activities (it must then not be added).
    """
    lx = _log_binding_odds(Delta_G_seq, T, c_bulk, Gamma_s, delta_s)
    t = positive("T (temperature)", T)
    gs = positive("Gamma_s (areal binding-site density)", Gamma_s)
    ds = positive("delta_s (binding-layer thickness)", delta_s)
    cb = positive("c_bulk (bulk Ca2+ concentration)", c_bulk)
    log1px = np.logaddexp(0.0, lx)             # ln(1 + x), exact for small x and without overflow
    return scalar_or_array(-GAS_CONSTANT * t * (gs * log1px - ds * cb))
