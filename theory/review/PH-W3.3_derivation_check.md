# Derivation check of the draft (PH-W3.3, 2026-10-23)

Read-only review of the merged draft (preprint/p0-w3 after the merge of origin/preprint/p0-w8 at aaed242).
Findings are numbered as in `ops/reports/P0-W3.PH-W3.3.md`. Nothing in `theory/` was changed besides this note.

## 1. The solid-salt sink is an upper bound only at LiClO4 saturation (report B3)

The registered solid-salt reaction (Section 2f of `claims_redirect.md`) takes Li+ from solid LiClO4:

    P(s) + z LiClO4(s) -> M(ClO4)z(s) + neutral products + z Li(s)          E_ub = Delta_G_ss / (z F)

In the cell the Li+ and ClO4- come from the electrolyte. The reaction that reaches the solid-salt product is

    P(s) + z Li+(S) + z ClO4-(S) -> M(ClO4)z(s) + neutral products + z Li(s)

and its free energy is Delta_G_ss + z [mu(LiClO4, s) - mu(Li+, S) - mu(ClO4-, S)]. The bracket is zero at saturation and
positive in an undersaturated electrolyte, so the onset of the solid-salt route in the cell is

    E_ss,cell = E_ub + Delta_E_sat,   Delta_E_sat = (2 R T / F) ln(a_pm,sat / a_pm) >= 0   (per Li, 1:1 salt).

The thermodynamic onset is min(E_S, E_ss,cell) <= E_ss,cell. The guaranteed upper bound is therefore E_ub + Delta_E_sat, not
E_ub. The term is one-sided (it only raises the bound), so it is not covered by a symmetric margin. SI line 190 says that
m_expt holds the tabulated uncertainties and the neglected Ca(ClO4)2 entropy, so the term is not in m_expt either.
Headroom of the exclusions at the class infimum: HAp 4.2 - 4.1918 = 8 mV; beta-TCP 4.2 - 4.1703 = 30 mV;
alpha-TCP 4.2 - 4.1464 = 54 mV; carbonate 4.2 - 4.0248 = 175 mV. 2RT/F = 51 mV per e-fold of the mean-activity ratio.
Action for W3: register Delta_E_sat in Section 2f, either with the registered electrolyte state at LiClO4 saturation or with a
sourced bound (LiClO4 solubility and mean activity coefficient in PC). W5 then reapplies it to the crossovers.

## 2. E_lb also needs a stated product activity (report M14)

E_lb takes every ion at its aqueous standard state (activity 1). In a fresh electrolyte a(Ca2+) and a(Al3+) are far below 1.
The onset falls by (R T / (z F)) ln a(M) per electron for z = 2 or 3, about -0.18 V for Ca2+ at a = 1e-6. E_lb is
a lower bound only at the registered product activity (the Pourbaix convention of 1e-6 is the usual choice). This matters
only for the pass side (v2), and the inequality E_lb <= E_solv in contract v6 holds at equal product activity. Section 2f
should name the activity. The paper's text "every ion hydrated at its standard state gives a lower bound" needs the same
qualifier.

## 3. I17 is not applied to ACP (report M1)

I17 (Section 9h) and Section 10c say the amorphous row is falsified (by the bound) wherever its crystalline reference is,
because DeltaG_g->c >= 0. The ladder (`ladder_v3.csv`, ACP amorphous: undetermined), the regime table (ACP K1:
undetermined) and the Results text ("the amorphous row of ACP reads undetermined") do not apply it. The rule "falsified only
if falsified under every framing" then leaves HAp's exclusion formally open, because the ACP framing reads undetermined.
Action: the generator labels the amorphous rows of HAp, beta-TCP, alpha-TCP and ACP "excluded (bound)" at C_mid and C_hi.

## 4. Vocabulary: Section 11d and D78 disagree (report M7)

11d registers "not excluded" as "feasible or kinetically stabilised (class A or B named)". D78 (planning chat, cp5b) rules
that prose "not excluded" means table "open". The table legend lists both as registered words. Section 11d needs a dated
amendment recording D78, or the prose should use "open". The regime table also uses "open" for K2 states (OCP control
failure; ACC in the acid state at pH 6.5 and 7.5), which is a third meaning. The Design section's class vocabulary
("feasible, falsified or partial") is that of Section 2e, not the table's.

## 5. Contract v6 and symbols against the Design rules

| Item in the draft | Contract or symbol | Status |
|---|---|---|
| E_ub, E_lb, onset E = Delta_G_r/(Delta_n_Li F) | `E_ub`, `E_lb`, `E_window` | match in name and meaning; E_lb needs item 2 above |
| f_cond = exp(-k_eff t_wet) | `f_cond` = 2^(-t_wet/t_half_hyd), identity exp(-tau_k k_hyd t_wet); `k_hyd_eff` | match; `k_eff` is not a registered symbol (use k_hyd,eff or tau_k k_hyd) |
| S_coac = gsl - gsn - gnl with s, n, l redefined | `S_coac` = gamma_al_l - gamma_al_n - gamma_nl_c, latex S_c | same meaning, but the symbols overload the template quantities gamma_sl, gamma_sn, gamma_nl |
| Gel criterion, oxide-pinned a(Al3+) | `Omega_AlPP`, `a_Al_oxide_eq` | match |
| Glass framing | `E_window_glass`, `E_ub_glass`, `E_lb_glass` | match; I17 not applied (item 3) |
| N_req = ln(1/q_0)/A_patch, B_acc = k_B T ln(J_0 t_p / N_req) | `N_req`, `q_0`, `B_acc`, `t_proc` (latex t_p) | match; symbols.yaml `A_patch` meaning still says N_req = 1/A_patch (stale, cp2) |
| cos theta = (gamma_sl0 + Delta_gamma_ads - gamma_sn)/gamma_nl; theta through the nucleus | `cos_theta_young`, `theta`, `Delta_gamma_ads` (negative for binding) | match |
| Delta_G_diss = -R T ln Omega_bulk (Eq. stability) | not a contract function | sign error: Delta_G_diss = +R T ln Omega_bulk per mole of formula units (>= 0 when Omega_bulk >= 1) |
| gamma_nl | symbols.yaml meaning "CaCO3 framing" | stale since contract v5 (mineral-neutral) |

## 6. Further checks that hold

- The transfer-premise direction in the Design text ("loses at least as much solvation per unit charge as Li+") matches
  Delta_G_tr_rel >= 0 of Section 2f.
- Crossovers are E_ub + m_1 for every row checked (CaCO3, HAp, brushite r3, alpha-TCP, beta-TCP).
- Class verdicts follow Section 2e (falsified at inf C) for HAp, the TCPs and carbonate at C_mid; brushite is partial at C_hi.
- Ca2P2O7 cannot pass C_mid or C_hi whatever the transfer data: E_ub = 4.4497 V < sup C + m_1 (4.5308 and 4.7308 V).
  Ca(PO3)2 glass and crystal and the (LiPO3)n rows could pass every class (precision map headroom 0.26 to 0.60 V).
- The precision map counts (32 = 14 closed + 8 MC + 10 gap) match `precision_map.json`.
