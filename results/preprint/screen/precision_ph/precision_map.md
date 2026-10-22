# Required-precision map (PH-W4.3)

code sha d0226135cd39c29213201ccb0ea093761a9358b8, params sha 5b955b06f4c36ab6e660711b1bbe8f67ff338976, thresholds block sha sha256:d92b42e9106e574fd330635fdc0d54e56d4a1dec4a7f38ece93d8bdfe922b04b, pre-run sha 8073c8e

| id | verdict link | prior | flip | required precision | settles | evidence grade | measurable by |
|---|---|---|---|---|---|---|---|
| gamma_sn | C3a / K3a | [0.01749945865377309, 0.7731085701804293] | gamma_sn* = gamma_sl - m_cos*gamma_nl (m_cos = 0) = 0.000184, 0.00122, 0.00288 | already_clears s*=1.000 | C3a / K3a (cos theta >= 0): feasible only if gamma | ignorance prior (bounds gamma_p B, gamma | within reach; not within reach |
| gamma_nv | K3a / K4 | gap | 0.0013547817947210047 | no_flip | K3a and K4 (through gamma_sn <= u*(gamma_p + gamma | gap (HAp, ACP); calcite B |  |
| gamma_nl | K4 (spreading) / C4 | [0.072, 0.487] | gamma_nl* = gamma_sl - gamma_sn - m_S <= gamma_sl | ok_by_inspection | K4 spreading route S_spread = gamma_sl - gamma_sn  | calcite B; HAp, ACP gap | within reach; not within reach |
| A_patch | C3b / K3b | gap | A* = ln(1/(1-p)) / q_p(N_nuc) for the falsified side; the feasible side needs N_nuc q_(1-p | no_flip_in_physical_range | C3b falsified | gap |  |
| c1_dupre_gamma_ow | C1 | [0.0, 0.11597756491870283] | gamma_ow* = gamma_op - gamma_pw + m_W = 0.00662, 0.0497, 0.0955 | unreachable | C1 (Dupre comparator) feasible or falsified | ignorance prior (bounds: gamma_o B, gamm | not assessed |
| c1_dupre_gamma_op | C1 | [0.0, 0.09630292313503346] | gamma_op* = gamma_ow + gamma_pw - m_W = 0.00383, 0.0556, 0.108 | unreachable | C1 (Dupre comparator) feasible or falsified | ignorance prior (bounds: gamma_o B, gamm | not assessed |
| c1_dupre_joint | C1 | None | gamma_op* = gamma_ow + gamma_pw - m_W | ok s*=0.119 | C1 (Dupre comparator) | ignorance prior | within reach |
| c1_analog_w_adh_wet | C1 | [0.0001, 0.015] | 0.00376938758553 | ok s*=0.560 | C1 (analog) feasible or falsified | B | within reach |
| c1_pmf | C1 | gap | 0.00376938758553 | gap | C1 (decisive route) | gap | within reach |
| k2_ksp_hap | K2 | -57.55 |  |  | K2 (dissolution stability) in the inconclusive cel | A | within reach |
| k2_ksp_btcp | K2 | -28.95 |  |  | K2 (dissolution stability) in the inconclusive cel | A | not assessed |
| k2_ksp_acp | K2 | -28.3 |  |  | K2 (dissolution stability) in the inconclusive cel | D | not within reach |
| k2_ksp_ocp | K2 | None |  | no_inconclusive_cell_before_control | K2 | None |  |
| k2_ksp_brushite | K2 | gap | log10 K_sp* = log10 IAP (per cell, slurry state, a_w = 1) | gap | K2 in every cell of the registered slurry grid | evidence-table row exists, no params key | within reach |
| k2_ksp_atcp | K2 | gap | log10 K_sp* = log10 IAP (per cell, slurry state, a_w = 1) | gap | K2 in every cell of the registered slurry grid | evidence-table row exists, no params key | undetermined |
| k2_ksp_li3po4 | K2 | gap | log10 K_sp* = log10 IAP | not_computable | K2 of the competing phase | evidence-table rows grade B (solubility) |  |
| n_hyd_acp | K2 (ACP, drying) | gap | n* = ln(Omega_anhydrous) / ln(1/a_w); K2 passes for n <= n* | gap | K2 of ACP at drying cells | gap (acp_water_content: one compilation  |  |
| k1_brushite_crystalline | K1 | gap | E_lb* = sup(E_c) + m_expt | gap | K1 pass (E_lb >= E_c + m_expt) at the listed class | E_ub sourced (tabulated thermochemistry) | within reach |
| k1_acp_crystalline | K1 | gap | E_lb* = sup(E_c) + m_expt | gap | K1 pass (E_lb >= E_c + m_expt) at the listed class | E_ub sourced (tabulated thermochemistry) | within reach |
| k1_hap_crystalline | K1 | gap | E_lb* = sup(E_c) + m_expt | gap | K1 pass (E_lb >= E_c + m_expt) at the listed class | E_ub sourced (tabulated thermochemistry) | within reach |
| k1_b_tcp_crystalline | K1 | gap | E_lb* = sup(E_c) + m_expt | gap | K1 pass (E_lb >= E_c + m_expt) at the listed class | E_ub sourced (tabulated thermochemistry) | within reach |
| k1_a_tcp_crystalline | K1 | gap | E_lb* = sup(E_c) + m_expt | gap | K1 pass (E_lb >= E_c + m_expt) at the listed class | E_ub sourced (tabulated thermochemistry) | within reach |
| k1_ca2p2o7_crystalline | K1 | gap | E_lb* = sup(E_c) + m_expt | gap | K1 pass (E_lb >= E_c + m_expt) at the listed class | E_ub sourced (tabulated thermochemistry) | within reach |
| k1_ca_po3_2_ca_polyphosphat_crystalline | K1 | gap | E_lb* = sup(E_c) + m_expt | gap | K1 pass (E_lb >= E_c + m_expt) at the listed class | E_ub sourced (tabulated thermochemistry) | within reach |
| k1_ca_po3_2_ca_polyphosphat_amorphous | K1 | gap | E_lb* = sup(E_c) + m_expt | gap | K1 pass (E_lb >= E_c + m_expt) at the listed class | E_ub sourced (tabulated thermochemistry) | within reach |
| k1_lipo3_n_hydro_quebec_fil_crystalline | K1 | gap | E_lb* = sup(E_c) + m_expt | gap | K1 pass (E_lb >= E_c + m_expt) at the listed class | E_ub sourced (tabulated thermochemistry) | within reach |
| k1_lipo3_n_hydro_quebec_fil_amorphous | K1 | gap | E_lb* = sup(E_c) + m_expt | gap | K1 pass (E_lb >= E_c + m_expt) at the listed class | E_ub sourced (tabulated thermochemistry) | within reach |
| t_wet | K2h | gap | t_wet* = ln(1/f_min) / k, f_cond = exp(-k t) | gap | K2h_falsify (f_cond < f_min at the slowest rate) o | rates: C single-source (4 keys); t_wet,  |  |
| f_min | K2h | [0.40725394191, 0.68839195] | f_min* = exp(-k t_wet) | closed | K2h at the interval ends | p_c keys B (computation: transfer-matrix |  |
| ksp_alpp | route layer | gap |  | not_computable | route verdict (report-only, never gating) | gap |  |
| binodal_map | route layer | gap |  | not_computable | route verdict (report-only, never gating) | gap |  |
| gamma_nl_coacervate | route layer | gap |  | not_computable | route verdict (report-only, never gating) | gap |  |
