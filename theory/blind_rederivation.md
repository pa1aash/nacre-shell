# Blind re-derivation of the derivation (quality gate 1, session P0-W3.3)

## Protocol

- **Input.** Only `theory/build/derivation.pdf` at the cp3 build (commit `74ac69c`), copied alone
  into a fresh temporary directory outside the repository (`mktemp -d`).
- **Agent.** One isolated subagent. It was told:
  - to read nothing but that PDF: no repository file, equation sheet, contract or symbols file;
  - to take only the physics stated in the PDF's prose and assumptions, re-derive each result
    itself, and only afterwards compare with what the PDF displays;
  - to write its derivations to the temporary directory, with its final expressions in a
    sympy module.

  It reports that it read only the PDF, through a text extraction kept in that same directory,
  and wrote only there.
- **Outputs.** The agent's files are kept verbatim in `theory/blind_rederivation/`:
  - `results.py`: its sympy expressions;
  - `rederivation.txt`: its step-by-step derivations, kept as written. The `.txt` name keeps the
    theory number scan meaningful: the file cites section numbers and the agent's Monte Carlo
    settings.
  - `checks.py.txt`: its own sympy and Monte Carlo checks, verbatim.

  The temporary directory was deleted after the copy.
- **Comparison.** `theory/blind_rederivation/compare.py` reads the registered expressions from
  `theory/contract.yaml` (references expanded by the contract checker's parser), the `thresholds`
  block and the `ignorance` block, so nothing registered is retyped. Each agent expression is
  tested first for symbolic equality; if sympy cannot decide it, it is evaluated at random
  admissible points to a relative tolerance of 10^-10.
  - The only rewriting is of variables, never of an expression: Delta_mu = k_B T ln Omega,
    gamma_sn = gamma_sn0 + Delta_gamma_w, and cos(theta) from Young for df/dDelta_gamma_w.
  - Before use, the harness was run against a stub built from the registered forms (21 of 21
    agree) and with a planted wrong branch mass, which it flags.

Command: `uv run python theory/blind_rederivation/compare.py`. Result: **21 of 21 expressions
agree, every one by symbolic equality.**

## Results per target

| Target | Agent's expression (quoted from `results.py` / `rederivation.txt`) | Registered counterpart | Result |
|---|---|---|---|
| (a) f(theta) | `f_theta = (2 + c) * (1 - c)**2 / 4`, c = cos(theta); "f(0)=0, f(pi/2)=1/2, f(pi)=1. f' = (3/4) sin^3 theta >= 0"; "DeltaG_het(r) = f DeltaG_hom(r) at every r" | contract `f_theta` (limits, derivative identity); derivation Eqs. (19) to (24) | agree (symbolic) |
| (b) Young, Delta_gamma_w | `cos_theta = (gamma_sl - (gamma_sn0 + Delta_gamma_w)) / gamma_nl`; `dcos_dDgw = -1/gamma_nl`; `df_dDgw` = "3 sin^2(theta) / (4 gamma_nl) >= 0"; `cos_theta_deck = (gamma_sl - gamma_sn0) / (gamma_nl - Delta_gamma_w)`, derivative "(gamma_sl - gamma_sn0)/(gamma_nl - Delta_gamma_w)^2, positive when gamma_sl > gamma_sn0: the wrong sign" | contract `cos_theta_young`, `cos_theta_deck`, SF1; Eqs. (28) to (31) | agree (symbolic, four expressions); the placement (substrate side) and the sign (a cost raises the barrier) match |
| (c) uniform chemical potential | `Delta_mu_expr = k_B * T * log(a_Ca * a_CO3 / K_sp)`; "specific binding cancels (k_BT ln E + DeltaG_seq/N_A = 0), and a mean potential enters as (2-2)e psi = 0" | contract `Delta_mu` with `Omega_bulk`; Eqs. (13) to (16) | agree (symbolic); both cancellations re-derived |
| (d) Delta_gamma_ads and the headline | `Delta_gamma_ads = -R*T*(Gamma_s*log(1 + x_bind) - delta_s*c_bulk)`, `x_bind = exp(-Delta_G_seq/(R*T))*c_bulk*delta_s/Gamma_s`; "d(gamma_sl - gamma_sn)/d mu_Ca = -(Gamma_Ca,sl - Gamma_Ca,sn)"; "d Delta_gamma_ads / d Delta_G_seq = Gamma_s Theta > 0" | contract `Delta_gamma_ads` and its derivative identities; Eqs. (33) to (35) | agree (symbolic); headline relation identical. Remarks 1 and 3 below |
| (e) CNT barriers | `r_star = 2*gamma_nl*v_m/Delta_mu`, `DG_hom = 16*pi*gamma_nl**3*v_m**2/(3*Delta_mu**2)`, `DG_het = f_theta*DG_hom`, v_m = V_m/N_A | contract `r_star`, `DG_hom`, `DG_het`; Eqs. (17), (18), (24) | agree (symbolic, with Delta_mu = k_B T ln Omega) |
| (f) accessibility, N_req | `B_acc = k_B*T*log(J0*t_p/N_req)`; `N_req_expr = log(1/q0)/A_patch`; `q0_expr = 1 - p`; "q0 = 1/e recovers one nucleus per patch on average" | contract `B_acc`; thresholds `C3b` edge `log(1/(1 - p_cred))/A_patch`; Eqs. (25) to (27) | agree (symbolic, three expressions) |
| (g) spreading, complete wetting | `S_spread = gamma_sl - gamma_sn - gamma_nl`; `S_spread_from_cos = gamma_nl*(cos(theta) - 1)`; "S_spread >= 0 requires gamma_sl >= gamma_nl + gamma_sn >= gamma_nl" | contract `S_spread` and its Young identity; Eqs. (37), (41) | agree (symbolic); the complete-wetting condition is identical. Remark 2 below |
| (h) branch masses | `P_complete = (gamma_sl - gamma_nl)/gamma_max`, `P_partial = 2*gamma_nl/gamma_max`, `P_non = (gamma_max - gamma_sl - gamma_nl)/gamma_max`, each clipped to [0, 1] | `theory/ignorance_priors.md` block `branches.masses_interior` (span gamma_p + gamma_nv = gamma_max) | agree (symbolic, three expressions); the agent's Monte Carlo check also matches. The PDF does not display these; the agent derived them from Young and the branch definitions alone, as asked |
| (i) carbonate speciation | quadratic "A_c P_c y^2 + [A_c D_c + P_c (m_CaT - m_CT)] y - m_CT D_c = 0"; `a_CO3_root = 2*m_CT*D_c/(B_q + sqrt(B_q**2 + 4*A_c*P_c*m_CT*D_c))`; "m_CaT = 0: ... y = m_CT/A_c"; Davies `10**(-A_DH*z**2*(s/(1 + s) - b_D*I))`, "as I -> 0 every gamma -> 1" | contract `a_CO3_speciation`, `gamma_act_1`, `gamma_act_2` and their limits; Eqs. (11), (12) | agree (symbolic, three expressions); both limits re-derived |

**Summary: 9 of 9 targets agree.** No sign or algebra disagreement was found.

## The agent's remarks, diagnosed

None of the remarks is a disagreement with a result. Each was checked against the physics and
handled as follows.

1. **Strong-binding limit of Delta_gamma_ads (derivation wrong in wording; fixed).** The PDF said
   Delta_gamma_ads tends to Gamma_s Delta_G_seq + R T Gamma_s ln(c_max/c_bulk) "plus terms that
   vanish". The agent derived the limit as that plus R T delta_s c_bulk + O(1/x). **The agent is
   right.** The term -R T(-delta_s c_bulk) in Eq. (33) does not depend on x, so it survives as
   x -> infinity. It is small only when delta_s c_bulk << Gamma_s. The displayed equation and the
   contract are correct; only the prose of the limit bullet was wrong. It is fixed in commit
   `f23632d` and flagged for cp4.
2. **"Hydrophilic" excludes complete wetting only under the stated definition (clarified).** The
   result follows exactly from gamma_sn >= 0 together with the condition gamma_sl <= gamma_nl, and
   the derivation states that condition. The agent notes that the ordinary meaning of
   hydrophilic, a small water contact angle in air, does not imply it.
   - **Correct.** Young in air constrains gamma_p - gamma_sl and says nothing about gamma_sl
     against gamma_nl.
   - The cp3 ruling (R3) asked for the statement as a physical result. It holds as the exact
     consequence of the stated condition. Whether a given template meets the condition is a
     question for the inputs, which is why P(gamma_sl > gamma_nl) is reported.
   - Commit `f23632d` adds one sentence to derivation Section 8 saying so.
   - Flagged for cp4, because it qualifies the wording "for any hydrophilic template" in
     `theory/thresholds.md` C4 and `theory/ignorance_priors.md` Section 2, which are not changed
     here: thresholds are ready for W4 and frozen at p0-cp3.
3. **The contact's Ca2+ excess assumes exchange with the reservoir (clarified).** The relation
   d gamma_sn / d mu_Ca = -Gamma_Ca,sn holds only if the template-crystal contact is in exchange
   equilibrium with the slurry, so that the Ca2+ there carries the bulk chemical potential.
   **Correct, and implicit in the PDF.** Its grand-canonical definition at the regime chemical
   potentials presumes the exchange but did not say so. Commit `f23632d` states the assumption and
   its failure case: a contact sealed from the solution holds a fixed amount. Flagged for cp4.

The two agent comments under (i) (I taken as given; ion pairs counted in both totals) agree
with what the derivation states, and nothing changes.

## Effect on the registered artefacts

- **Contract.** No expression changed, so it stays at version 3.
- **Thresholds.** No rule changed; the machine block stays at version 2.
- **check_contract.** Re-run after the fix: PASS.
- **Derivation PDF.** Rebuilt: 18 pages, no undefined references, no overfull boxes. No new
  equation was added, so the equation numbers are unchanged.
