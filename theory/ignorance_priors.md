# Ignorance priors for the unmeasured interfacial quantities (cp3 gap policy, theory part)

Session P0-W3.2 fix-up, lane p0-w3, written before any screen output existed. No literature
number appears here (rule R2). Every bound is an expression in registered symbol ids
(`theory/symbols.yaml`), and every input it needs is named by the `lit/params.yaml` key that will
supply it. W1 builds the priors from these expressions, and W4 samples them. The fenced
`ignorance` block at the end is the machine form, which `theory/tools/check_contract.py` checks.

Why this file exists: several C1 and C3/C4 inputs have no admitted literature row (status `gap`
in `lit/params.yaml`). For each one, the admissible range must come from physics, so that a gap
becomes a bounded ignorance prior and not a guess. The range is what thermodynamics allows; it
says nothing about where in that range the true value lies. That is why a probability computed
under such a prior is never a finding (Section 3).

## 1. Interfacial energies

Notation: s is the anchored template, n the nucleus (CaCO3 framing), l the liquid (water),
o the oxide, p the polymer. The template is the polymer, so its dry surface energy is gamma_p.

### 1a Template-nucleus contact, gamma_sn

**Two bounds, both from stability of a sharp interface.**

- **Upper bound from the dry work of adhesion.** Separating the contact into the two free
  surfaces against vacuum costs W_adh,dry = gamma_p + gamma_nv - gamma_sn. This work cannot be
  negative. If it were, the two solids would lower their free energy by separating, and no
  contact would exist whose energy could be quoted. Hence

  gamma_sn <= gamma_max = gamma_p + gamma_nv.

- **Lower bound from interface stability.** gamma_sn >= 0. A negative interfacial free energy
  between two immiscible solids would make the system create interface without limit, so the
  phases would interpenetrate and no sharp contact would exist.

**The prior.** gamma_sn ~ U[0, gamma_p + gamma_nv]. It sits on the total contact energy in water,
with Delta_gamma_w = 0 (Section 1b).

**Keys.**
- gamma_p (template, dry): `params.gamma_p_pda`, already sourced.
- gamma_nv (CaCO3, dry): new keys `params.gamma_nv_calcite` and `params.gamma_nv_acc`, one per
  framing. The framing must match K_sp, V_m and gamma_nl (Q12).

**Positivity does not apply to the wet work of adhesion.** The template-nucleus work of adhesion
in water is W_adh,wet,sn = gamma_sl + gamma_nl - gamma_sn. Young gives
cos(theta) = (gamma_sl - gamma_sn)/gamma_nl, so

- W_adh,wet,sn <= 0 is exactly cos(theta) <= -1, the non-wetting branch;
- W_adh,wet,sn >= 2 gamma_nl is exactly S_spread >= 0, complete wetting.

Imposing W_adh,wet,sn >= 0 would therefore remove the non-wetting branch by assumption. Water can
displace a nucleus from a template, so the wet work can have either sign. Only the dry work is
bounded below by zero.

### 1b Water-displacement correction, Delta_gamma_w

Under an ignorance prior, Delta_gamma_w cannot be identified apart from gamma_sn0. The bounds of
Section 1a hold for the contact energy actually present under the nucleus, gamma_sn =
gamma_sn0 + Delta_gamma_w, whatever the split. The prior is therefore placed on the total
gamma_sn, and Delta_gamma_w = 0 by the registered rule: a full in-water contact energy already
contains the displacement, and adding it again is the double count of C3 item 13.

If W1 finds a measured gamma_sn0 from a reference without the template's bound water, the
correction is bounded as follows.
- **Lower bound, 0.** Displacing a bound layer is a cost. A layer that held water less well than
  bulk water would not be bound.
- **Upper bound, gamma_p - gamma_sl.** This is the free energy released when the dry template is
  wetted (its immersion free energy). Stripping the layer cannot cost more than that.

So 0 <= Delta_gamma_w <= max(0, gamma_p - gamma_sl), with the keys `params.gamma_p_pda` and
`params.gamma_sl0_template`. In that case the total must still respect
0 <= gamma_sn0 + Delta_gamma_w <= gamma_p + gamma_nv. Draws outside it are refused, not clipped.

### 1c Oxide-water, gamma_ow, and oxide-polymer, gamma_op (C1 comparator route)

The same two bounds give the following.
- **gamma_ow ~ U[0, gamma_o + gamma_w].** The oxide-water contact cannot have a negative work of
  adhesion against vapour, and it is a stable interface. Keys: `params.gamma_o_alumina` and
  `params.gamma_w`.
- **gamma_op ~ U[0, gamma_o + gamma_p].** The dry work of adhesion of the oxide-polymer contact
  is not negative. Keys: `params.gamma_o_alumina` and `params.gamma_p_pda`.

**Tighter bound, only with evidence.** A complete-wetting upper bound, gamma_ow <= gamma_o -
gamma_w (water spreads on the hydroxylated oxide), applies only if W1 admits evidence of complete
wetting. `lit/params.yaml` records a conflict between simulated and measured water contact angles
on the oxide, so the ignorance range keeps the weaker bound.

**What these feed.** C1 is decided from the PMF route, `W_adh_wet_from_pmf`. gamma_ow and
gamma_op enter only the interfacial-energy comparator, `W_adh_wet`. Their ignorance therefore
moves the comparator, not the C1 verdict. The flip value of the comparator is
gamma_op* = gamma_ow + gamma_pw - m_W.

### 1d Polymer-water, gamma_pw

gamma_pw is not needed as an ignorance prior. It is the same quantity as gamma_sl0, sourced under
`params.gamma_sl0_template`. The bounds above give 0 <= gamma_pw <= gamma_p + gamma_w, and they
serve as a consistency check.

The sourced range extends below zero (the van Oss route). A negative template-water energy would
mean the template disperses or swells in water without limit. The conflict is reported to W1 as a
flag. It does not override the sourced prior.

## 2. Branch masses of the gamma_sn prior (properties of the prior)

Write G = gamma_p + gamma_nv, and condition on the other energies (gamma_sl at the regime
activities, gamma_nl). Young's relation splits the gamma_sn axis at two cut points.

| Branch | Condition on gamma_sn | Cut point |
|---|---|---|
| complete wetting (S_spread >= 0, f = 0) | gamma_sn <= a | a = gamma_sl - gamma_nl |
| partial wetting (abs(cos(theta)) < 1) | a < gamma_sn < b | |
| non-wetting (cos(theta) <= -1, f = 1) | gamma_sn >= b | b = gamma_sl + gamma_nl |

With gamma_sn ~ U[0, G] the conditional masses are

- P_complete = clip(a/G, 0, 1) = clip((gamma_sl - gamma_nl)/G, 0, 1);
- P_non = clip(1 - b/G, 0, 1) = clip(1 - (gamma_sl + gamma_nl)/G, 0, 1);
- P_partial = 1 - P_complete - P_non. When both cut points lie in [0, G] this is
  2 gamma_nl / G.

The marginal masses are the expectations of these over the priors of gamma_sl and gamma_nl, and
W4 reports them.

**When all three masses are non-zero.**
- **Partial wetting** always has positive mass when the cut interval overlaps [0, G]. The
  interval (a, b) has width 2 gamma_nl > 0.
- **Non-wetting** has positive mass iff b < G, that is, gamma_sl + gamma_nl < gamma_p + gamma_nv.
  Write each in-water energy through its works with water, gamma_sl = gamma_p + gamma_w - W_pw and
  gamma_nl = gamma_nv + gamma_w - W_nw. The condition becomes W_pw + W_nw > 2 gamma_w: together,
  the two solids bind water more strongly than water binds itself. This holds for a hydrophilic
  template and mineral.
- **Complete wetting** has positive mass iff a > 0, that is, gamma_sl > gamma_nl.

**What the prior does and does not guarantee.** The prior on gamma_sn excludes no branch that
the other energies admit: gamma_sn = 0 is the most wetting contact thermodynamics allows, and
gamma_sn = G is the least. Whether the marginal complete-wetting mass is non-zero is decided by
the priors of gamma_sl and gamma_nl, not by the ignorance on gamma_sn.

If gamma_sl <= gamma_nl over their whole support, then S_spread < 0 for every admissible gamma_sn.
The C4 criterion then fails whatever gamma_sn is. That is a physical result that does not depend
on the ignorance prior (Section 3).

**Physical result (cp3 R3; derivation, Section 8, Eq. [th:eq:spread-bound]).** Because gamma_sn >= 0,
S_spread = gamma_sl - gamma_sn - gamma_nl <= gamma_sl - gamma_nl. For any hydrophilic template,
gamma_sl <= gamma_nl (water wets the template at least as favourably as it wets the mineral), so
S_spread <= -gamma_sn < 0 for every admissible gamma_sn > 0: complete wetting is excluded, and the
complete-wetting branch mass of this prior is zero, not by assumption but because the cut point
a = gamma_sl - gamma_nl lies at or below zero. Ca2+ binding lowers gamma_sl further. C4 then rests
on coalescence (the second route of `theory/thresholds.md`, C4), and the report prints
P(gamma_sl > gamma_nl), the largest mass the spreading route can carry. The ruling asked this file to show non-zero mass on all three
branches. That holds only under the two conditions above, and the session report records the
difference.

## 3. Reporting rule under an ignorance prior

1. **P(feasible) under an ignorance prior is never reported as a finding.** The prior encodes the
   admissible range, not knowledge, so a band mass computed with it measures the width of the
   range relative to the edge. It does not measure the evidence.
2. **Flip values instead.** For each unmeasured quantity q, W4 computes P_good(q), the band mass
   of the link at fixed q with every other input at its prior.
   - P_good is monotone in q for every quantity listed here. For example, f rises with gamma_sn,
     and S_spread falls with it.
   - The flip values are q_F, where P_good(q_F) = p_cred, and q_X, where P_good(q_X) = 1 - p_cred.
   - The verdict is feasible on one side of q_F, falsified beyond q_X, and inconclusive between.
   - If no flip value lies in the admissible range, the verdict is robust to the ignorance on q,
     and the report says which verdict holds over the whole range.
3. **Required precision.** A measurement q_hat with uncertainty half-width delta decides the link
   only if [q_hat - delta, q_hat + delta] does not meet the inconclusive interval (q_X, q_F)
   (ordered as they fall). The required precision at q_hat is therefore the distance from q_hat
   to that interval, and it is zero inside it. The report gives q_F, q_X and the width of
   (q_X, q_F) for each quantity.
   - Where two unmeasured quantities enter the same Young numerator (gamma_sn with gamma_sl), the
     report also gives the flip line in their plane, gamma_sl - gamma_sn = m_cos gamma_nl for C3
     (a) and gamma_sl - gamma_sn = gamma_nl + m_S for C4.
4. **Flagged analog priors.** Where W1 finds measured analogs, for example a contact energy of a
   different organic template against calcite, the analog prior is run side by side with the
   ignorance prior. It is flagged `analog`, and its verdict is reported as conditional on the
   analog. An analog never replaces the ignorance prior silently.

## 4. Bounds on Gamma_s and delta_s from geometry (gap policy item (iii))

**Site density, Gamma_s.** Each occupied site holds one Ca2+ with its coordinating group, which
covers at least the footprint a_site. Sites cannot outnumber the coordinating groups the layer
contains. Hence

0 < Gamma_s <= min(1/(N_A a_site), rho_L d_layer).

- a_site: footprint area of one site with its bound ion, new key `params.site_footprint_area`.
- rho_L: volume density of coordinating groups in the layer, new key
  `params.template_group_density`.
- d_layer: template layer thickness, new key `params.template_layer_thickness`.

The sourced prior `params.gamma_s_site_density` must lie inside this bound. W1 checks it and
flags a violation.

**Binding-layer thickness, delta_s.**
- **Lower bound.** One coordination shell sets the least thickness, delta_s >= 2 r_Ca. The layer
  also cannot hold Ca2+ more densely than a solid Ca phase does, c_max = Gamma_s/delta_s <= 1/V_m,
  so delta_s >= Gamma_s V_m.
- **Upper bound.** The sites lie inside the template layer, delta_s <= d_layer.

So max(2 r_Ca, Gamma_s V_m) <= delta_s <= d_layer, with r_Ca from the new key
`params.ca_ionic_radius` and V_m from the framing key (`params.v_m_calcite` or `params.v_m_acc`).

**Prior family.** W1's own rules apply: uniform over the bound (U1), or loguniform where the bound
spans more than a decade (L1).

**The site volume follows.** V_site = delta_s/(N_A Gamma_s), the binding-layer volume per site
(derivation, Section 3). It is derived, not an independent input. This closes the `gap` status of
`params.v_site` once delta_s and Gamma_s are set, and it fixes V_site once, as Q4 requires.

**Single-source binding energies (rule for W1).** A binding free energy or binding constant with
status `single-source` (for example `params.log10_k_ca_catecholate`,
`params.dg_bind_ca_acetate`, `params.dg_bind_calcite_template`) carries an inflated uncertainty
and a flag.
- Its prior is the sourced span widened symmetrically about its centre to a half-width of at
  least the method error of its class. For a Ca2+ transfer or binding free energy that is
  m_seq (`thresholds.C2.margin_DG_seq`), and m_seq/(R T ln 10) for a log10 binding constant.
- It carries `single_source: true`.
- Every verdict or finding whose band would change if the unwidened span were used is marked as
  resting on a single source.

W1 applies the rule. This file only states it.

## 5. Machine-readable form

```ignorance
version: 1
authority: theory/ignorance_priors.md
written_before_screen_output: true
quantities:
  gamma_sn:
    prior: uniform
    low: '0'
    high: gamma_p + gamma_nv
    bound_from: [dry work of adhesion gamma_p + gamma_nv - gamma_sn >= 0, interface stability gamma_sn >= 0]
    Delta_gamma_w: '0'
    params: {gamma_p: params.gamma_p_pda, gamma_nv: [params.gamma_nv_calcite, params.gamma_nv_acc]}
    not_bounded: wet work of adhesion (its sign separates the non-wetting branch)
  Delta_gamma_w:
    when: a measured gamma_sn0 from a reference without the bound water exists
    prior: uniform
    low: '0'
    high: gamma_p - gamma_sl
    params: {gamma_p: params.gamma_p_pda, gamma_sl: params.gamma_sl0_template}
    otherwise: '0 (prior on the total gamma_sn)'
  gamma_ow:
    prior: uniform
    low: '0'
    high: gamma_o + gamma_w
    params: {gamma_o: params.gamma_o_alumina, gamma_w: params.gamma_w}
    feeds: W_adh_wet (comparator only)
  gamma_op:
    prior: uniform
    low: '0'
    high: gamma_o + gamma_p
    params: {gamma_o: params.gamma_o_alumina, gamma_p: params.gamma_p_pda}
    feeds: W_adh_wet (comparator only)
  gamma_pw:
    status: sourced as params.gamma_sl0_template
    low: '0'
    high: gamma_p + gamma_w
    use: consistency check only
branches:
  variable: gamma_sn
  span: gamma_p + gamma_nv
  cuts: {complete: gamma_sl - gamma_nl, non: gamma_sl + gamma_nl}
  masses_interior:
    complete: (gamma_sl - gamma_nl)/(gamma_p + gamma_nv)
    partial: 2*gamma_nl/(gamma_p + gamma_nv)
    non: 1 - (gamma_sl + gamma_nl)/(gamma_p + gamma_nv)
  interior_when: ['gamma_sl - gamma_nl > 0', 'gamma_sl + gamma_nl < gamma_p + gamma_nv']
  complete_wetting_excluded_when: 'gamma_sl <= gamma_nl (hydrophilic template; S_spread <= gamma_sl - gamma_nl - gamma_sn)'
  clipping: masses are clipped to [0, 1] when a cut leaves [0, span]
geometry:
  Gamma_s:
    low: '0'
    high_min_of: [1/(N_A*a_site), rho_L*d_layer]
    params: {a_site: params.site_footprint_area, rho_L: params.template_group_density,
             d_layer: params.template_layer_thickness}
  delta_s:
    low_max_of: [2*r_Ca, Gamma_s*V_m]
    high: d_layer
    params: {r_Ca: params.ca_ionic_radius, d_layer: params.template_layer_thickness,
             V_m: [params.v_m_calcite, params.v_m_acc]}
  V_site:
    equals: delta_s/(N_A*Gamma_s)
single_source_binding:
  widen_half_width_to_at_least: {free_energy: m_seq, log10_constant: m_seq/(R_gas*T*log(10))}
  params: {m_seq: thresholds.C2.margin_DG_seq}
  flag: single_source
reporting:
  probability_under_ignorance_is_finding: false
  report: [flip_values, inconclusive_interval_width, required_precision, branch_masses]
  analog_priors: side_by_side, flagged analog
```
