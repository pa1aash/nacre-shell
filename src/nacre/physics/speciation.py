"""Free-ion activities of Ca2+ and CO3^2- in the slurry from carbonate speciation (contract v3).

Theory contract v3 (P0-W3.2 cp2 fix-up, gap policy item (v)). The supersaturation of the
registered framing, Omega_bulk = a_Ca a_CO3 / K_sp, takes the FREE-ion activities, which follow
from the totals of a closed solution: pH, dissolved inorganic carbon C_T, total dissolved
calcium Ca_T and ionic strength I, with the ion pairs CaCO3(aq), CaHCO3+ and the hydrolysis
product CaOH+.

    g_1, g_2   Davies activity coefficients of singly and doubly charged ions,
               log10 g_z = -z^2 A_DH (sqrt(I/m0)/(1 + sqrt(I/m0)) - b_D I/m0), g_2 = g_1^4;
               neutral species take activity coefficient one. Valid for I <= I_val only.
    m_CT, m_CaT  totals in standard molalities, C_T/(rho_w m0) and Ca_T/(rho_w m0).
    A_carb     free carbon (CO2(aq), HCO3-, CO3^2-) per unit carbonate activity.
    P_pair     Ca-carbonate ion pairs (CaCO3(aq), CaHCO3+) per unit product a_Ca a_CO3.
    D_Ca       free Ca2+ and CaOH+ per unit Ca2+ activity.
    a_CO3      the positive root of A P y^2 + (A D + P (m_CaT - m_CT)) y - m_CT D = 0
               (carbon balance m_CT = A y + P y a_Ca, calcium balance m_CaT = a_Ca (D + P y)).
    a_Ca       m_CaT / (D + P a_CO3).
    c_Ca_free  free Ca2+ concentration a_Ca rho_w m0 / g_2, mol m^-3: the c_bulk of the C2
               Langmuir and Gibbs relations (contract convention `speciation`).

The equilibrium constants are thermodynamic (I = 0) values from lit/params.yaml; nothing is
typed here. The standard molality m0 is exact by definition of the molal scale.
"""
import numpy as np

from nacre.physics._domain import non_negative, positive, real, scalar_or_array
from nacre.physics.constants import STANDARD_MOLALITY

LN10 = np.log(10.0)


class ActivityModelRange(ValueError):
    """The ionic strength lies above the registered validity bound I_val of the Davies equation."""


#: Largest |ln g| that a double can represent; beyond it the coefficient is not a number.
LN_RANGE = np.log(np.finfo(float).max)


def _davies_exponent(A_DH, I_ionic, b_D):
    s = np.sqrt(I_ionic / STANDARD_MOLALITY)
    return A_DH * (s / (1.0 + s) - b_D * I_ionic / STANDARD_MOLALITY)


def davies_ln_coefficient(z2, A_DH, I_ionic, b_D):
    """ln g_z = -z^2 ln(10) (Davies bracket) without exponentiating (dimensionless)."""
    return -z2 * LN10 * _davies_exponent(A_DH, I_ionic, b_D)


def _davies(z2, A_DH, I_ionic, b_D):
    a = non_negative("A_DH (Debye-Hueckel constant)", A_DH)
    i = non_negative("I_ionic (ionic strength, mol kg^-1)", I_ionic)
    b = non_negative("b_D (Davies linear coefficient)", b_D)
    ln_g = davies_ln_coefficient(z2, a, i, b)
    if np.any(np.abs(ln_g) > LN_RANGE):
        raise ValueError("Davies activity coefficient outside the floating-point range: the ionic strength "
                         "lies far beyond the validity of the activity model")
    return scalar_or_array(np.exp(ln_g))


def activity_coefficient_charge_one(A_DH, I_ionic, b_D):
    """Davies activity coefficient g_1 of a singly charged ion (dimensionless)."""
    return _davies(1.0, A_DH, I_ionic, b_D)


def activity_coefficient_charge_two(A_DH, I_ionic, b_D):
    """Davies activity coefficient g_2 = g_1^4 of a doubly charged ion (dimensionless)."""
    return _davies(4.0, A_DH, I_ionic, b_D)


def total_carbon_molal(C_T, rho_water):
    """Dissolved inorganic carbon in standard molalities, m_CT = C_T / (rho_w m0) (dimensionless)."""
    c = positive("C_T (dissolved inorganic carbon, mol m^-3)", C_T)
    rho = positive("rho_water (water density, kg m^-3)", rho_water)
    return scalar_or_array(c / (rho * STANDARD_MOLALITY))


def total_calcium_molal(Ca_T, rho_water):
    """Total dissolved calcium in standard molalities, m_CaT = Ca_T / (rho_w m0) (dimensionless)."""
    c = positive("Ca_T (total dissolved calcium, mol m^-3)", Ca_T)
    rho = positive("rho_water (water density, kg m^-3)", rho_water)
    return scalar_or_array(c / (rho * STANDARD_MOLALITY))


def carbonate_speciation_factor(pK1_carbonic, pK2_carbonic, pH, g_1, g_2):
    """Free carbon per unit carbonate activity, A_carb (dimensionless).

    10^(pK1 + pK2 - 2 pH) (CO2(aq)) + 10^(pK2 - pH)/g_1 (HCO3-) + 1/g_2 (CO3^2-).
    """
    k1 = real("pK1_carbonic", pK1_carbonic)
    k2 = real("pK2_carbonic", pK2_carbonic)
    ph = real("pH", pH)
    a = positive("g_1 (activity coefficient, charge one)", g_1)
    b = positive("g_2 (activity coefficient, charge two)", g_2)
    return scalar_or_array(np.exp(LN10 * (k1 + k2 - 2.0 * ph)) + np.exp(LN10 * (k2 - ph)) / a + 1.0 / b)


def ion_pair_factor(K_CaCO3_aq, K_CaHCO3, pK2_carbonic, pH, g_1):
    """Ca-carbonate ion pairs per unit product a_Ca a_CO3, P_pair (dimensionless).

    K_CaCO3(aq) (neutral pair) + K_CaHCO3 10^(pK2 - pH) / g_1 (CaHCO3+).
    """
    k0 = non_negative("K_CaCO3_aq (formation constant of CaCO3(aq))", K_CaCO3_aq)
    kh = non_negative("K_CaHCO3 (formation constant of CaHCO3+)", K_CaHCO3)
    k2 = real("pK2_carbonic", pK2_carbonic)
    ph = real("pH", pH)
    a = positive("g_1 (activity coefficient, charge one)", g_1)
    return scalar_or_array(k0 + kh * np.exp(LN10 * (k2 - ph)) / a)


def free_calcium_factor(g_1, g_2, K_CaOH, a_w, pH):
    """Ca2+ and CaOH+ per unit Ca2+ activity, D_Ca = 1/g_2 + K_CaOH a_w 10^pH / g_1 (dimensionless)."""
    a = positive("g_1 (activity coefficient, charge one)", g_1)
    b = positive("g_2 (activity coefficient, charge two)", g_2)
    k = non_negative("K_CaOH (hydrolysis constant of CaOH+)", K_CaOH)
    w = positive("a_w (water activity)", a_w)
    ph = real("pH", pH)
    return scalar_or_array(1.0 / b + k * w * np.exp(LN10 * ph) / a)


def carbonate_activity(m_CT, D_Ca, A_carb, P_pair, m_CaT):
    """Free carbonate activity a_CO3 (dimensionless), the positive root of the mass balances.

    A P y^2 + B y - m_CT D = 0 with B = A D + P (m_CaT - m_CT). The root is taken as
    2 m_CT D / (B + sqrt(B^2 + 4 A P m_CT D)) where B >= 0 and as (sqrt(...) - B) / (2 A P)
    where B < 0, so neither branch subtracts nearly equal numbers.
    """
    mc = non_negative("m_CT (dissolved inorganic carbon, molal)", m_CT)
    d = positive("D_Ca (free-calcium factor)", D_Ca)
    a = positive("A_carb (carbonate speciation factor)", A_carb)
    p = non_negative("P_pair (ion-pair factor)", P_pair)
    mca = non_negative("m_CaT (total calcium, molal)", m_CaT)
    b = a * d + p * (mca - mc)
    disc = np.sqrt(b * b + 4.0 * a * p * mc * d)
    with np.errstate(divide="ignore", invalid="ignore"):
        upper = 2.0 * mc * d / (b + disc)
        lower = (disc - b) / (2.0 * a * p)
    return scalar_or_array(np.where(b >= 0, upper, lower))


def calcium_activity(m_CaT, D_Ca, P_pair, a_CO3):
    """Free Ca2+ activity a_Ca = m_CaT / (D_Ca + P_pair a_CO3) (dimensionless)."""
    mca = non_negative("m_CaT (total calcium, molal)", m_CaT)
    d = positive("D_Ca (free-calcium factor)", D_Ca)
    p = non_negative("P_pair (ion-pair factor)", P_pair)
    y = non_negative("a_CO3 (carbonate activity)", a_CO3)
    return scalar_or_array(mca / (d + p * y))


def free_calcium_concentration(a_Ca, rho_water, g_2):
    """Free Ca2+ concentration c_Ca_free = a_Ca rho_w m0 / g_2, mol m^-3 (the c_bulk of C2)."""
    a = non_negative("a_Ca (Ca2+ activity)", a_Ca)
    rho = positive("rho_water (water density, kg m^-3)", rho_water)
    b = positive("g_2 (activity coefficient, charge two)", g_2)
    return scalar_or_array(a * rho * STANDARD_MOLALITY / b)


def speciate(pH, C_T, Ca_T, I_ionic, rho_water, pK1_carbonic, pK2_carbonic, K_CaCO3_aq, K_CaHCO3,
             K_CaOH, a_w, A_DH, b_D, I_val):
    """Free-ion activities of a closed carbonate solution; the chain of the contract v3 functions.

    Returns {g_1, g_2, m_CT, m_CaT, A_carb, P_pair, D_Ca, a_CO3, a_Ca, c_Ca_free}. Raises
    ActivityModelRange where I_ionic > I_val: the Davies equation is registered as valid only
    up to I_val, and a draw beyond it is refused, never extrapolated (the screen counts it).
    """
    i = non_negative("I_ionic (ionic strength, mol kg^-1)", I_ionic)
    iv = positive("I_val (validity bound of the activity model)", I_val)
    if np.any(i > iv):
        raise ActivityModelRange("ionic strength above the registered Davies validity bound I_val")
    g1 = activity_coefficient_charge_one(A_DH, i, b_D)
    g2 = activity_coefficient_charge_two(A_DH, i, b_D)
    mct = total_carbon_molal(C_T, rho_water)
    mcat = total_calcium_molal(Ca_T, rho_water)
    a_c = carbonate_speciation_factor(pK1_carbonic, pK2_carbonic, pH, g1, g2)
    p = ion_pair_factor(K_CaCO3_aq, K_CaHCO3, pK2_carbonic, pH, g1)
    d = free_calcium_factor(g1, g2, K_CaOH, a_w, pH)
    y = carbonate_activity(mct, d, a_c, p, mcat)
    a_ca = calcium_activity(mcat, d, p, y)
    return {"g_1": g1, "g_2": g2, "m_CT": mct, "m_CaT": mcat, "A_carb": a_c, "P_pair": p, "D_Ca": d,
            "a_CO3": y, "a_Ca": a_ca, "c_Ca_free": free_calcium_concentration(a_ca, rho_water, g2)}


# ------------------------------------------------------------------ phosphate speciation (contract v5)
# Same structure as the carbonate system: a phosphate balance and a calcium balance close on the pair factor
# (each Ca-phosphate pair holds one Ca and one phosphate), so the carbonate quadratic holds with C_T -> P_T.
def activity_coefficient_charge_three(A_DH, I_ionic, b_D):
    """Davies activity coefficient g_3 = g_1^9 of a triply charged ion (dimensionless)."""
    return _davies(9.0, A_DH, I_ionic, b_D)


def total_phosphate_molal(P_T, rho_water):
    """Total dissolved phosphate in standard molalities, m_PT = P_T / (rho_w m0) (dimensionless)."""
    c = positive("P_T (total dissolved phosphate, mol m^-3)", P_T)
    rho = positive("rho_water (water density, kg m^-3)", rho_water)
    return scalar_or_array(c / (rho * STANDARD_MOLALITY))


def phosphate_speciation_factor(pK1_phosphoric, pK2_phosphoric, pK3_phosphoric, pH, g_1, g_2, g_3):
    """Free phosphate species per unit PO4 3- activity, A_phos (dimensionless).

    1/g_3 (PO4 3-) + 10^(pK3 - pH)/g_2 (HPO4 2-) + 10^(pK3 + pK2 - 2 pH)/g_1 (H2PO4-)
    + 10^(pK1 + pK2 + pK3 - 3 pH) (H3PO4, activity coefficient one).
    """
    k1 = real("pK1_phosphoric", pK1_phosphoric)
    k2 = real("pK2_phosphoric", pK2_phosphoric)
    k3 = real("pK3_phosphoric", pK3_phosphoric)
    ph = real("pH", pH)
    a = positive("g_1 (activity coefficient, charge one)", g_1)
    b = positive("g_2 (activity coefficient, charge two)", g_2)
    c = positive("g_3 (activity coefficient, charge three)", g_3)
    return scalar_or_array(1.0 / c + np.exp(LN10 * (k3 - ph)) / b + np.exp(LN10 * (k3 + k2 - 2.0 * ph)) / a
                           + np.exp(LN10 * (k1 + k2 + k3 - 3.0 * ph)))


def phosphate_ion_pair_factor(K_CaHPO4_aq, K_CaH2PO4, K_CaPO4, pK2_phosphoric, pK3_phosphoric, pH, g_1):
    """Ca-phosphate ion pairs per unit product a_Ca a_PO4, P_pair_phos (dimensionless).

    K_CaHPO4(aq) 10^(pK3 - pH) (neutral) + K_CaH2PO4 10^(pK3 + pK2 - 2 pH)/g_1 (CaH2PO4+) + K_CaPO4/g_1 (CaPO4-).
    """
    k0 = non_negative("K_CaHPO4_aq (formation constant of CaHPO4(aq))", K_CaHPO4_aq)
    k1 = non_negative("K_CaH2PO4 (formation constant of CaH2PO4+)", K_CaH2PO4)
    k2 = non_negative("K_CaPO4 (formation constant of CaPO4-)", K_CaPO4)
    p2 = real("pK2_phosphoric", pK2_phosphoric)
    p3 = real("pK3_phosphoric", pK3_phosphoric)
    ph = real("pH", pH)
    a = positive("g_1 (activity coefficient, charge one)", g_1)
    return scalar_or_array(k0 * np.exp(LN10 * (p3 - ph)) + k1 * np.exp(LN10 * (p3 + p2 - 2.0 * ph)) / a + k2 / a)


def phosphate_activity(m_PT, D_Ca, A_phos, P_pair_phos, m_CaT):
    """Free phosphate activity a_PO4 (dimensionless): the positive root of A P y^2 + B y - m_PT D = 0.

    B = A D + P (m_CaT - m_PT); the cancellation-free branch is chosen as for the carbonate system.
    """
    return carbonate_activity(m_PT, D_Ca, A_phos, P_pair_phos, m_CaT)


def calcium_activity_phosphate(m_CaT, D_Ca, P_pair_phos, a_PO4):
    """Free Ca2+ activity a_Ca = m_CaT / (D_Ca + P_pair_phos a_PO4) (dimensionless)."""
    return calcium_activity(m_CaT, D_Ca, P_pair_phos, a_PO4)


def hydrogen_phosphate_activity(a_PO4, pK3_phosphoric, pH):
    """Free HPO4 2- activity a_HPO4 = a_PO4 10^(pK3 - pH) (dimensionless)."""
    y = non_negative("a_PO4 (phosphate activity)", a_PO4)
    return scalar_or_array(y * np.exp(LN10 * (real("pK3_phosphoric", pK3_phosphoric) - real("pH", pH))))


def phosphate_fraction_acidbase(g_3, pK1_phosphoric, pK2_phosphoric, pK3_phosphoric, pH, g_1, g_2):
    """Fraction of total phosphate that is free PO4 3- with no calcium, 1 / (g_3 A_phos) (dimensionless)."""
    g3 = positive("g_3 (activity coefficient, charge three)", g_3)
    return scalar_or_array(1.0 / (g3 * phosphate_speciation_factor(pK1_phosphoric, pK2_phosphoric,
                                                                  pK3_phosphoric, pH, g_1, g_2, g3)))


def fraction_po4_free(a_PO4, g_3, m_PT):
    """Fraction of the total phosphate that is free PO4 3-, a_PO4 / (g_3 m_PT)."""
    return scalar_or_array(non_negative("a_PO4", a_PO4) / (positive("g_3", g_3) * positive("m_PT", m_PT)))


def fraction_hpo4_free(a_HPO4, g_2, m_PT):
    """Fraction of the total phosphate that is free HPO4 2-, a_HPO4 / (g_2 m_PT)."""
    return scalar_or_array(non_negative("a_HPO4", a_HPO4) / (positive("g_2", g_2) * positive("m_PT", m_PT)))


def fraction_h2po4_free(a_PO4, pK2_phosphoric, pK3_phosphoric, pH, g_1, m_PT):
    """Fraction of the total phosphate that is free H2PO4-."""
    y = non_negative("a_PO4", a_PO4)
    e = real("pK3_phosphoric", pK3_phosphoric) + real("pK2_phosphoric", pK2_phosphoric) - 2.0 * real("pH", pH)
    return scalar_or_array(y * np.exp(LN10 * e) / (positive("g_1", g_1) * positive("m_PT", m_PT)))


def fraction_h3po4(a_PO4, pK1_phosphoric, pK2_phosphoric, pK3_phosphoric, pH, m_PT):
    """Fraction of the total phosphate that is H3PO4(aq)."""
    y = non_negative("a_PO4", a_PO4)
    e = (real("pK1_phosphoric", pK1_phosphoric) + real("pK2_phosphoric", pK2_phosphoric)
         + real("pK3_phosphoric", pK3_phosphoric) - 3.0 * real("pH", pH))
    return scalar_or_array(y * np.exp(LN10 * e) / positive("m_PT", m_PT))


def fraction_pairs_phosphate(a_Ca, a_PO4, P_pair_phos, m_PT):
    """Fraction of the total phosphate held in Ca ion pairs, a_Ca a_PO4 P_pair_phos / m_PT."""
    return scalar_or_array(non_negative("a_Ca", a_Ca) * non_negative("a_PO4", a_PO4)
                           * non_negative("P_pair_phos", P_pair_phos) / positive("m_PT", m_PT))


def phosphate_closure_residual(A_phos, a_Ca, P_pair_phos, a_PO4, m_PT):
    """Closure residual (A_phos + a_Ca P_pair_phos) a_PO4 / m_PT - 1; zero at the speciation solution."""
    a = positive("A_phos", A_phos)
    return scalar_or_array((a + non_negative("a_Ca", a_Ca) * non_negative("P_pair_phos", P_pair_phos))
                           * non_negative("a_PO4", a_PO4) / positive("m_PT", m_PT) - 1.0)


def speciate_phosphate(pH, P_T, Ca_T, I_ionic, rho_water, pK1_phosphoric, pK2_phosphoric, pK3_phosphoric,
                       K_CaHPO4_aq, K_CaH2PO4, K_CaPO4, K_CaOH, a_w, A_DH, b_D, I_val):
    """Free-ion activities of a closed phosphate solution; the chain of the contract v5 functions.

    Returns {g_1, g_2, g_3, m_PT, m_CaT, A_phos, P_pair_phos, D_Ca, a_PO4, a_HPO4, a_Ca, c_Ca_free}. Raises
    ActivityModelRange where I_ionic > I_val, as for the carbonate system.
    """
    i = non_negative("I_ionic (ionic strength, mol kg^-1)", I_ionic)
    iv = positive("I_val (validity bound of the activity model)", I_val)
    if np.any(i > iv):
        raise ActivityModelRange("ionic strength above the registered Davies validity bound I_val")
    g1 = activity_coefficient_charge_one(A_DH, i, b_D)
    g2 = activity_coefficient_charge_two(A_DH, i, b_D)
    g3 = activity_coefficient_charge_three(A_DH, i, b_D)
    mpt = total_phosphate_molal(P_T, rho_water)
    mcat = total_calcium_molal(Ca_T, rho_water)
    a_p = phosphate_speciation_factor(pK1_phosphoric, pK2_phosphoric, pK3_phosphoric, pH, g1, g2, g3)
    p = phosphate_ion_pair_factor(K_CaHPO4_aq, K_CaH2PO4, K_CaPO4, pK2_phosphoric, pK3_phosphoric, pH, g1)
    d = free_calcium_factor(g1, g2, K_CaOH, a_w, pH)
    y = phosphate_activity(mpt, d, a_p, p, mcat)
    a_ca = calcium_activity_phosphate(mcat, d, p, y)
    return {"g_1": g1, "g_2": g2, "g_3": g3, "m_PT": mpt, "m_CaT": mcat, "A_phos": a_p, "P_pair_phos": p,
            "D_Ca": d, "a_PO4": y, "a_HPO4": hydrogen_phosphate_activity(y, pK3_phosphoric, pH), "a_Ca": a_ca,
            "c_Ca_free": free_calcium_concentration(a_ca, rho_water, g2)}
