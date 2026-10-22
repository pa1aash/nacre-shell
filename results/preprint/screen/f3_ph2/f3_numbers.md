# Nucleation wording numbers (PH-W4.5, cp5b F3 and F5)

Design point Ca_T=0.001 mol dm^-3; C_T=dic_slurry@min; a_w=wet_film, 16384 draws of the production seed (C3a band mass reproduced: True).

gamma_sl (J m^-2), admitted draws: min 1.06e-06, q05 0.000184, q50 0.00122, q95 0.00288, max 0.00336
gamma_sl (J m^-2), all finite draws: min -0.168, q05 -0.0875, q50 -0.0132, q95 0.00164, max 0.00336

Mass with gamma_sn <= gamma_sl under the registered gamma_nv prior of calcite: 0.0029 (stored C3a P_good 0.0029).

| gamma_nv (J m^-2) | median gamma_p + gamma_nv | mass gamma_sn <= gamma_sl |
|---|---|---|
| 0 | 0.05246 | 0.0230 |
| 0.001 | 0.05346 | 0.0230 |
| 0.0025 | 0.05496 | 0.0221 |
| 0.005 | 0.05746 | 0.0211 |
| 0.01 | 0.06246 | 0.0201 |
| 0.025 | 0.07746 | 0.0173 |
| 0.05 | 0.1025 | 0.0144 |
| 0.1 | 0.1525 | 0.0101 |
| 0.25 | 0.3025 | 0.0067 |
| 0.5 | 0.5525 | 0.0034 |
| 1 | 1.052 | 0.0024 |
| 1.84 | 1.892 | 0.0014 |

Over the 36 design points: mass at gamma_nv = 0 at most 0.0541 (0.0338 where M_adm >= 0.02, i.e. at least 0.02 of the draws admitted); under the sourced gamma_nv prior at most 0.0270.

C3 link falsified at 24 of 36 design points ({'falsified': 24, 'inconclusive': 12}).

Nucleate Sobol total-order (and first-order) confidence-interval half-width: 0.0977 against the target 0.02; capped True at 2^17 base rows (3407872 evaluations).
