"""Work of adhesion of the template on the hydroxylated oxide (claim C1).

The decisive observable is the Dupre work of adhesion in water,

    W_adh,wet = gamma_ow + gamma_pw - gamma_op,

the reversible work per unit contact area to separate the oxide-polymer contact into an
oxide-water and a polymer-water interface. Positive means the template stays anchored
against interfacial water. The vacuum (dry) work of adhesion is a comparator only.
"""
from nacre.physics._domain import positive, real, scalar_or_array


def work_of_adhesion_wet(gamma_ow, gamma_pw, gamma_op):
    """Dupre work of adhesion in water, gamma_ow + gamma_pw - gamma_op, in J m^-2."""
    ow = real("gamma_ow (oxide-water energy)", gamma_ow)
    pw = real("gamma_pw (polymer-water energy)", gamma_pw)
    op = real("gamma_op (oxide-polymer energy)", gamma_op)
    return scalar_or_array(ow + pw - op)


def work_of_adhesion_dry(gamma_o, gamma_p, gamma_op):
    """Dupre work of adhesion against vacuum, gamma_o + gamma_p - gamma_op, J m^-2 (comparator only)."""
    o = positive("gamma_o (oxide surface energy)", gamma_o)
    p = positive("gamma_p (polymer surface energy)", gamma_p)
    op = real("gamma_op (oxide-polymer energy)", gamma_op)
    return scalar_or_array(o + p - op)


def work_of_adhesion_from_pmf(Delta_F_pmf, A_c):
    """Wet work of adhesion from a PMF: Delta_F_pmf / A_c, in J m^-2.

    Delta_F_pmf is the free energy of the separated minus the bound state (J, positive
    when bound is lower); A_c the fragment contact area (m^2).
    """
    df = real("Delta_F_pmf (PMF free energy, separated minus bound)", Delta_F_pmf)
    a = positive("A_c (contact area)", A_c)
    return scalar_or_array(df / a)
