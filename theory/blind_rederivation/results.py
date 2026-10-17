"""Blind re-derivation results (sympy). Symbols as requested.
Extra symbols added (not in the requested list): N_req (required areal nucleus density, m^-2;
named in the task), Delta_mu (driving force per formula unit, used as the argument of r_star,
DG_hom, DG_het), and z (generic charge number, used only in gamma_davies_z).
"""
import sympy as sp

theta = sp.Symbol('theta', real=True)
Delta_gamma_w = sp.Symbol('Delta_gamma_w', real=True)
Delta_G_seq = sp.Symbol('Delta_G_seq', real=True)
(gamma_sl, gamma_sn, gamma_sn0, gamma_nl, R, T, k_B, N_A, Gamma_s, delta_s, c_bulk, V_m,
 Omega, J0, t_p, A_patch, p, q0, gamma_max, a_Ca, a_CO3, K_sp, m_CT, m_CaT, A_c, P_c, D_c,
 I, A_DH, b_D) = sp.symbols(
    'gamma_sl gamma_sn gamma_sn0 gamma_nl R T k_B N_A Gamma_s delta_s c_bulk V_m '
    'Omega J0 t_p A_patch p q0 gamma_max a_Ca a_CO3 K_sp m_CT m_CaT A_c P_c D_c '
    'I A_DH b_D', positive=True)
N_req = sp.Symbol('N_req', positive=True)      # added: required areal density of nuclei
Delta_mu = sp.Symbol('Delta_mu', positive=True)  # added: k_B T ln(Omega) per formula unit
z = sp.Symbol('z', integer=True)                 # added: charge number for Davies

# (a) shape factor
c = sp.cos(theta)
f_theta = (2 + c) * (1 - c)**2 / 4

# (b) Young with water-displacement correction inside gamma_sn = gamma_sn0 + Delta_gamma_w
cos_theta = (gamma_sl - (gamma_sn0 + Delta_gamma_w)) / gamma_nl
dcos_dDgw = sp.diff(cos_theta, Delta_gamma_w)                   # = -1/gamma_nl
_cs = sp.Symbol('cs')
_f_of_c = (2 + _cs) * (1 - _cs)**2 / 4
df_dDgw = sp.simplify(sp.diff(_f_of_c, _cs).subs(_cs, cos_theta) * dcos_dDgw)
#  = (3/4)(1 - cos^2 theta)/gamma_nl = 3 sin^2(theta) / (4 gamma_nl)  >= 0
cos_theta_deck = (gamma_sl - gamma_sn0) / (gamma_nl - Delta_gamma_w)

# (c) driving force per formula unit
Delta_mu_expr = k_B * T * sp.log(a_Ca * a_CO3 / K_sp)

# (d) Gibbs-Langmuir adsorption change of gamma_sl
x_bind = sp.exp(-Delta_G_seq / (R * T)) * c_bulk * delta_s / Gamma_s
Delta_gamma_ads = -R * T * (Gamma_s * sp.log(1 + x_bind) - delta_s * c_bulk)

# (e) CNT, v_m = V_m/N_A
v_m = V_m / N_A
r_star = 2 * gamma_nl * v_m / Delta_mu
DG_hom = 16 * sp.pi * gamma_nl**3 * v_m**2 / (3 * Delta_mu**2)
DG_het = f_theta * DG_hom

# (f) accessibility
B_acc = k_B * T * sp.log(J0 * t_p / N_req)
N_req_expr = sp.log(1 / q0) / A_patch
q0_expr = 1 - p

# (g) spreading
S_spread = gamma_sl - gamma_sn - gamma_nl
S_spread_from_cos = gamma_nl * (sp.Symbol('cos_theta_') - 1)  # placeholder replaced below
S_spread_from_cos = gamma_nl * (sp.cos(theta) - 1)

# (h) branch masses, gamma_sn ~ U[0, gamma_max]; interior case
#     0 <= gamma_sl - gamma_nl  and  gamma_sl + gamma_nl <= gamma_max
P_complete = (gamma_sl - gamma_nl) / gamma_max
P_partial = 2 * gamma_nl / gamma_max
P_non = (gamma_max - gamma_sl - gamma_nl) / gamma_max

def _clip01(e):
    return sp.Min(1, sp.Max(0, e))
P_complete_clipped = _clip01((gamma_sl - gamma_nl) / gamma_max)
P_non_clipped = _clip01((gamma_max - gamma_sl - gamma_nl) / gamma_max)
P_partial_clipped = 1 - P_complete_clipped - P_non_clipped

# (i) speciation: A_c P_c y^2 + [A_c D_c + P_c (m_CaT - m_CT)] y - m_CT D_c = 0
B_q = A_c * D_c + P_c * (m_CaT - m_CT)
a_CO3_root = 2 * m_CT * D_c / (B_q + sp.sqrt(B_q**2 + 4 * A_c * P_c * m_CT * D_c))

def gamma_davies_z(zz):
    s = sp.sqrt(I)   # I in units of the standard molality
    return 10**(-A_DH * zz**2 * (s / (1 + s) - b_D * I))
gamma_davies_z1 = gamma_davies_z(1)
gamma_davies_z2 = gamma_davies_z(2)

RESULTS = {
    'f_theta': f_theta,
    'cos_theta': cos_theta,
    'dcos_dDgw': dcos_dDgw,
    'df_dDgw': df_dDgw,
    'cos_theta_deck': cos_theta_deck,
    'Delta_mu': Delta_mu_expr,
    'Delta_gamma_ads': Delta_gamma_ads,
    'r_star': r_star,
    'DG_hom': DG_hom,
    'DG_het': DG_het,
    'B_acc': B_acc,
    'N_req': N_req_expr,
    'q0': q0_expr,
    'S_spread': S_spread,
    'S_spread_from_cos': S_spread_from_cos,
    'P_complete': P_complete,
    'P_partial': P_partial,
    'P_non': P_non,
    'a_CO3_root': a_CO3_root,
    'gamma_davies_z1': gamma_davies_z1,
    'gamma_davies_z2': gamma_davies_z2,
}

EXTRA = {
    'P_complete_clipped': P_complete_clipped,
    'P_partial_clipped': P_partial_clipped,
    'P_non_clipped': P_non_clipped,
    'dcos_dDgw_deck': sp.diff(cos_theta_deck, Delta_gamma_w),
    'x_bind': x_bind,
}

if __name__ == '__main__':
    for k, v in RESULTS.items():
        print(f'{k}: {v}')
