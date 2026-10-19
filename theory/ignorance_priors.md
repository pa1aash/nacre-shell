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
mean the template disperses or swells in water without limit. At cp3 (R8) the prior of
gamma_sl0 is truncated at zero, and the untruncated prior is a labelled sensitivity with the
removed mass reported (`theory/thresholds.md`, Section 1). Since D27 that truncation is the Ca-free
case of the admissibility rule of Section 2a: the same stability argument applies to the
template-liquid energy at the regime Ca2+ activity, gamma_sl = gamma_sl0 + Delta_gamma_ads >= 0.

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

## 2a. Admissibility of the template-liquid energy and the branch masses (D27)

Session P0-W3.4b, decision D27 (2026-10-18). Derived from the physics (derivation, Section 7 (Admissibility)) and from
the one fact D27 states; no other screen output was read.

**Why the bound applies at the regime state.** The argument of 1a and 1d is about the interface that
is actually present. In the slurry that interface is the template against Ca2+-bearing water, with
energy gamma_sl = gamma_sl0 + Delta_gamma_ads. If gamma_sl < 0, the film lowers its free energy by
making more interface. It swells or disperses, and no bounded template-water interface exists whose
energy Young could use.

**The rule.** The joint prior of (gamma_sl0, Delta_G_seq, Gamma_s, delta_s) is restricted to
gamma_sl >= 0 at every registered state and design point. Draws outside the set are refused and
counted, never clipped or floored. The retained mass M_adm is reported as a property of the prior
(`theory/thresholds.md`, Section 1). The gamma_sn prior of 1a is not changed: it is independent of
the template-liquid inputs, and its own bounds already come from the same stability argument.

**How far the geometric bounds of Section 4 cap the term.** Along the Ca2+ axis, the lowering
Pi_ads = -Delta_gamma_ads grows while the Gibbs excess is positive. It is largest where the excess
vanishes, at c_0 = c_max (1 - 1/E_enr), and there it equals

Pi_ads_max = R T Gamma_s (ln E_enr - 1 + 1/E_enr) <= -Gamma_s Delta_G_seq   (Delta_G_seq < 0).

delta_s drops out of the maximum, so its bounds do not cap the term. The Gamma_s cap of Section 4
caps it only at Gamma_s,max |Delta_G_seq|, the binding free energy of a full layer of sites. Nothing
ties that to gamma_sl0, so the geometric bounds cannot prevent an overshoot. Written per site footprint,
Gamma_s = 1/(N_A a_site), the lowering exceeds gamma_sl0 once
ln E_enr - 1 + 1/E_enr > gamma_sl0 a_site/(k_B T). The right-hand side is the bare interfacial work of
one site footprint in thermal units. For a hydrophilic film it is small, so modest binding already
overshoots. The comparison over the registered priors is a property of the priors and is evaluated in
the session report, not here.

**Branch masses under the restriction.** The masses of Section 2 are conditional on gamma_sl and
gamma_nl. The formulas are unchanged; the restriction changes which values of gamma_sl occur.
- **Non-wetting.** gamma_sl >= 0 gives b = gamma_sl + gamma_nl >= gamma_nl, so
  P_non <= clip(1 - gamma_nl/G) < 1. The case P_non = 1, which needed gamma_sl <= -gamma_nl, no longer
  occurs. On an admitted draw the clipped boundary theta = pi needs gamma_sn >= gamma_sl + gamma_nl.
- **Partial wetting.** P_partial >= min(1, gamma_nl/G) whenever gamma_sl <= gamma_nl.
- **Complete wetting.** For a binding template, gamma_sl <= gamma_sl0 + R T delta_s c_bulk, so
  P_complete <= clip((gamma_sl0 + R T delta_s c_bulk - gamma_nl)/G). It is zero for any template that
  is hydrophilic in the sense of Section 2.
- **Favourable mass (C3 (a)).** The good side of the gamma_sn axis is gamma_sn <= gamma_sl - m_cos gamma_nl,
  so P_fav = clip((gamma_sl - m_cos gamma_nl)/G). It is non-negative on every admitted draw and at most
  clip((gamma_sl0 + R T delta_s c_bulk - m_cos gamma_nl)/G) for a binding template. Binding can only shrink
  it.
- **Marginal masses.** These are expectations over the restricted joint prior and the gamma_nl prior.
  They are properties of the prior and never a finding (Section 3). Their values over the registered
  priors are in the P0-W3.4b report.

**Single-source binding constants measured in solution.** The widening rule of Section 4 covers the
method error of a transfer free energy. It does not cover the transfer of a solution complexation
constant to a surface site, which is a different quantity (derivation, Section 7 (Admissibility), A3). Such a constant
reaches Delta_G_site only through the analog route of `theory/thresholds.md` (C2), flagged as an
analog, and with the cycle that charges every proton its ligand form has lost.

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

## 4a. Geometric bounds for the remaining geometric gaps (cp3b A3)

Session P0-W3.4, written without consulting any screen output. Four inputs of the screen still have
no admitted row: the contact patch area, the site footprint, the group density and the Ca2+ radius
(`lit/params.yaml`: `patch_area`, `site_footprint_area`, `template_group_density` and
`ca_ionic_radius`, status `gap`). Each bound below comes from geometry or stoichiometry alone, and
each names the params keys it needs. Whether W4 can evaluate a bound now is stated in 4a.5.

### 4a.1 The contact patch area, A_patch (C3 (b))

**Physics.** A cathode particle reaches the collector only where it touches it, and C3 (b) asks
for a nucleus under each such patch (`theory/thresholds.md`, C3 (b)). The patch is bounded by two
pieces of geometry.

- **Upper bound: the particle's projection.** The part of a particle that touches a flat foil
  lies inside the particle's shadow on the foil. Its area therefore cannot exceed the particle's
  projected area. With d_p the projected-area-equivalent diameter (the diameter of the disc whose
  area equals the particle's largest projected area), A_patch <= pi d_p^2 / 4.
- **Lower bound: one asperity.** Real surfaces touch at asperities, so a particle that touches the
  foil does so through at least one asperity contact of finite area a_asp. Hence
  A_patch >= a_asp.

So a_asp <= A_patch <= pi d_p^2 / 4. The bound spans the whole range from one asperity to full
conformal contact, many decades, and only ln A_patch enters the C3 (b) edge. The prior is
therefore loguniform between the bounds (W1's rule L1). Through N_req = ln(1/q_0)/A_patch the
bound carries over to
4 ln(1/q_0)/(pi d_p^2) <= N_req <= ln(1/q_0)/a_asp.
A smaller patch demands more nuclei per area, so the asperity end is the strict one.

**Keys.**
- d_p: new key `params.cathode_particle_diameter`.
- a_asp: new key `params.asperity_contact_area`.

W1 holds neither key. The particle size W1 found (TL-086) is recorded as a comparator, because a
particle size is not a contact area. It is, however, the upper bound above, so W1 may admit it
under `params.cathode_particle_diameter`. No source for a_asp is known to this lane.

**While the bound is a gap.** A_patch is reported as a gap, and C3 (b) is reported as "gap" and
counted as inconclusive (C3 then cannot be feasible). N_nuc does not depend on A_patch, and
P(N_nuc A_patch >= ln(1/q_0)) rises with A_patch. The flip values of Section 3 are therefore
computed and printed:
- A_F, where P_good(A_F) = p_cred;
- A_X, where P_good(A_X) = 1 - p_cred.

They state which patch areas a measurement must exclude for C3 (b) to decide. Once both keys
exist, a flip value outside [a_asp, pi d_p^2 / 4] makes the C3 (b) verdict robust to the ignorance
on A_patch (Section 3, item 2).

### 4a.2 The site footprint, a_site

**Physics.** Each site holds one Ca2+, so two occupied sites are at least the contact distance
2 r_Ca apart. The ions' mutual repulsion can only push them further apart. The densest
arrangement of equal discs in a plane is the hexagonal one, in which each disc of radius r claims
the area 2 sqrt(3) r^2. Hence

a_site >= 2 sqrt(3) r_Ca^2,   so   1/(N_A a_site) <= 1/(2 sqrt(3) N_A r_Ca^2).

The bound counts only the ion. The coordinating group's own footprint can only enlarge a_site, so
this is the loosest bound geometry allows, and it holds for any template chemistry. Like the
footprint term of Section 4, it assumes one layer of sites at the template-liquid interface. Sites
stacked in depth are bounded instead by the volume terms: rho_L d_layer here, and
c_max = Gamma_s/delta_s <= 1/V_m in the delta_s bound.

**Keys.** r_Ca (`params.ca_ionic_radius`), with the treatment of 4a.4. No new key.

### 4a.3 The group density, rho_L

**Physics: stoichiometry.** A coordinating group belongs to a repeat unit of the template. A
volume of template of mass density rho_PDA therefore holds at most rho_PDA/M_u moles of groups per
volume. Here M_u is the least template mass per mole of coordinating groups: over the candidate
repeat units, the molar mass of a unit divided by the number of coordinating groups it carries.
Taking the least value covers every mixture of units. Hence

0 < rho_L <= rho_PDA / M_u,   and   rho_L d_layer <= rho_PDA d_layer / M_u.

The accessible-site content W1 uses for the analog (`params.pda_binding_site_content`) is not
registered as a lower bound on rho_L. It counts accessible amine-binding sites. Amines bind the
oxidised (quinone) form, so these sites are not established to be a subset of the coordinating
catechol groups (W1's note on the key calls the content a proxy).

**Keys.**
- rho_PDA: `params.pda_density` (sourced, single source).
- M_u: new key `params.template_mass_per_group_min`. W1 obtains it from the candidate repeat
  units of polydopamine and their compositions; no value is typed here.

**Consequence for Gamma_s.** With 4a.2 and 4a.3, the geometric cap of Section 4 becomes

Gamma_s <= min( 1/(2 sqrt(3) N_A r_Ca^2), rho_PDA d_layer / M_u ).

### 4a.4 The Ca2+ radius in the delta_s bound

**The lower bound needs the radius of the ion itself.** The binding layer must contain the bound
ion, so delta_s >= 2 r_Ca. The radius enters a lower bound, so it must not be overstated.
- r_Ca is the Ca2+ ionic radius at the **lowest coordination number** registered for the bound
  ion. Where none is registered, it is the lowest coordination number tabulated for Ca2+.
- Ionic radii grow with coordination number. The lowest therefore gives the smallest 2 r_Ca, and
  the bound stays valid at any higher coordination the site may have.
- W1 records the coordination number with the key.

**The analog overstates the radius.** The analog `params.ca_o_distance_aqueous_analog` is the
Ca-O distance of hydrated Ca2+. It exceeds r_Ca by the radius of the water oxygen (W1's note).
Using it in place of r_Ca:
- makes the lower bound of delta_s larger than the true bound, so it can exclude admissible
  thicknesses;
- makes the footprint bound of 4a.2 larger, so the cap on Gamma_s becomes smaller than the true
  cap.

Neither result is a valid bound.

**Registered treatment.**
- **While r_Ca is a gap, the 2 r_Ca term is dropped.** Dropping a term from a maximum lowers it,
  so the lower bound stays valid, only looser: Gamma_s V_m <= delta_s <= d_layer. V_m is that of
  the framing (`params.v_m_calcite` or `params.v_m_acc`).
- **The analog form runs as a labelled sensitivity:** max(2 r_Ca(analog), Gamma_s V_m), labelled
  "tighter than the geometric bound".
- **A draw with an empty interval (Gamma_s V_m > d_layer) is refused and counted,** never
  clipped.

**Rule for every analog-based bound.** A bound evaluated with an analog key is reported and
flagged. A draw outside it is flagged, never refused. Only a bound built from primary keys refuses
draws. This covers the Gamma_s cap evaluated with `params.ca_o_distance_aqueous_analog` or
`params.template_group_density_site_analog`. W1 describes the second as counting accessible sites
only, so it may understate rho_L and give too small a cap.

### 4a.5 What W4 can evaluate now

| Quantity | Bound | Inputs available in `lit/params.yaml` | Status for production |
|---|---|---|---|
| A_patch | a_asp <= A_patch <= pi d_p^2/4, loguniform | neither key | **gap**: C3 (b) reported as "gap", counted inconclusive; flip values A_F, A_X printed |
| a_site | a_site >= 2 sqrt(3) r_Ca^2 | r_Ca is a gap (analog only) | **gap**; the analog form is reported and flagged, never refuses |
| rho_L | 0 < rho_L <= rho_PDA/M_u | rho_PDA present; M_u absent | **gap**; the analog runs beside as before |
| Gamma_s cap | min(1/(2 sqrt(3) N_A r_Ca^2), rho_PDA d_layer/M_u) | each term needs a gap key | **gap**: no geometric cap on the sourced Gamma_s prior; the analog cap is reported, never refuses |
| delta_s | max(2 r_Ca, Gamma_s V_m) <= delta_s <= d_layer | Gamma_s, V_m, d_layer present; r_Ca a gap | **evaluable now** with the 2 r_Ca term dropped (valid, looser); analog sensitivity beside |
| V_site | V_site = delta_s/(N_A Gamma_s) | follows from delta_s and Gamma_s | **evaluable now** |

A gap is reported as "gap" and counted as inconclusive for the link that needs it, as lane note
N21 registers. The geometric gaps still open are therefore A_patch, a_site, rho_L and with them the
Gamma_s cap. delta_s and V_site can be drawn now.

## 5. Machine-readable form

```ignorance
version: 3
authority: theory/ignorance_priors.md
written_before_screen_output: true
revised_cp3b: {session: P0-W3.4, item: A3, base_commit: 227d997, screen_output_consulted: false,
               adds: [geometry.A_patch, geometry.a_site, geometry.rho_L, Gamma_s expanded cap, delta_s r_Ca treatment, analog_bounds, evaluable_now]}
revised_d27: {session: P0-W3.4b, decision: D27 (2026-10-18), screen_output_consulted: false,
              adds: [admissibility, branches.favourable, branches.under_admissibility, single_source_binding.solution_constants]}
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
  favourable:
    cut: gamma_sl - m_cos*gamma_nl
    mass_interior: (gamma_sl - m_cos*gamma_nl)/(gamma_p + gamma_nv)
    role: C3 (a) good side of the gamma_sn axis (D27, A5)
  under_admissibility:
    non_at_most: 'clip(1 - gamma_nl/(gamma_p + gamma_nv)); P_non = 1 no longer occurs'
    partial_at_least: 'min(1, gamma_nl/(gamma_p + gamma_nv)) when gamma_sl <= gamma_nl'
    complete_at_most_binding: 'clip((gamma_sl0 + R_gas*T*delta_s*c_bulk - gamma_nl)/(gamma_p + gamma_nv))'
    favourable_at_most_binding: 'clip((gamma_sl0 + R_gas*T*delta_s*c_bulk - m_cos*gamma_nl)/(gamma_p + gamma_nv))'
    marginals: expectations over the restricted joint prior; values in the session report, never a finding
admissibility:
  decision: D27 (2026-10-18)
  condition: {expr: gamma_sl0 + Delta_gamma_ads, relation: '>=', rhs: '0'}
  joint_over: [gamma_sl0, Delta_G_seq, Gamma_s, delta_s]
  at: every registered R-slurry state and design point
  draws_outside: refused and counted (never clipped, never floored)
  retained_mass: M_adm reported per design point and state; never silently renormalised
  gamma_sn_prior: unchanged
  cap_from_geometry: {Pi_ads_max: R_gas*T*Gamma_s*(log(E_enr) - 1 + 1/E_enr), at_most: -Gamma_s*Delta_G_seq,
                      delta_s: drops out of the maximum, relation_to_gamma_sl0: none (the bounds do not prevent overshoot)}
  special_case: 'c_bulk -> 0: gamma_sl0 >= 0 (cp3 R8)'
geometry:
  A_patch:
    low: a_asp
    high: pi*d_p**2/4
    prior: loguniform
    bound_from: [a contact holds at least one asperity contact, the contact lies inside the particle's projection]
    params: {a_asp: params.asperity_contact_area, d_p: params.cathode_particle_diameter}
    N_req_range: {low: 4*log(1/q_0)/(pi*d_p**2), high: log(1/q_0)/a_asp}
    status: gap
    on_gap: 'C3b reported as gap (counted inconclusive); flip values A_F (P_good = p_cred) and A_X (P_good = 1 - p_cred) reported'
  a_site:
    low: 2*sqrt(3)*r_Ca**2
    bound_from: hexagonal packing of the bound ions (contact distance 2 r_Ca); the group footprint can only enlarge it
    assumes: one layer of sites at the template-liquid interface
    params: {r_Ca: params.ca_ionic_radius}
    status: gap
    analog: {r_Ca: params.ca_o_distance_aqueous_analog, effect: overstates r_Ca, use: reported and flagged, never refuses}
  rho_L:
    low: '0'
    high: rho_PDA/M_u
    bound_from: stoichiometry (least template mass per mole of coordinating groups)
    params: {rho_PDA: params.pda_density, M_u: params.template_mass_per_group_min}
    status: gap
    analog: {rho_L: params.template_group_density_site_analog, use: reported and flagged, never refuses}
  Gamma_s:
    low: '0'
    high_min_of: [1/(N_A*a_site), rho_L*d_layer]
    high_min_of_expanded: [1/(2*sqrt(3)*N_A*r_Ca**2), rho_PDA*d_layer/M_u]
    params: {a_site: params.site_footprint_area, rho_L: params.template_group_density,
             d_layer: params.template_layer_thickness, r_Ca: params.ca_ionic_radius, rho_PDA: params.pda_density,
             M_u: params.template_mass_per_group_min}
    status: gap (no geometric cap on the sourced prior params.gamma_s_site_density until r_Ca or M_u exists)
  delta_s:
    low_max_of: [2*r_Ca, Gamma_s*V_m]
    high: d_layer
    params: {r_Ca: params.ca_ionic_radius, d_layer: params.template_layer_thickness,
             V_m: [params.v_m_calcite, params.v_m_acc]}
    r_Ca_treatment:
      primary: Ca2+ ionic radius at the lowest coordination number registered for the bound ion (else the lowest tabulated)
      while_gap: drop the 2*r_Ca term (low = Gamma_s*V_m); valid and looser
      analog: {r_Ca: params.ca_o_distance_aqueous_analog, effect: lower bound tighter than the geometric bound, use: labelled sensitivity}
    empty_interval: refused and counted, never clipped
    status: evaluable now (2*r_Ca term dropped)
  V_site:
    equals: delta_s/(N_A*Gamma_s)
    status: evaluable now (derived per draw)
analog_bounds:
  rule: a bound evaluated with an analog key is reported and flagged; draws outside it are flagged, never refused
  refuses_draws: only bounds built from primary keys
evaluable_now:
  evaluable: [delta_s (2*r_Ca term dropped), V_site]
  gap: [A_patch, a_site, rho_L, Gamma_s cap]
  gap_reporting: reported as gap and counted inconclusive for the link that needs it (lane note N21)
single_source_binding:
  widen_half_width_to_at_least: {free_energy: m_seq, log10_constant: m_seq/(R_gas*T*log(10))}
  solution_constants: 'not covered by the widening; reach Delta_G_site only through the analog route (thresholds C2.analog_route), flagged analog (D27)'
  params: {m_seq: thresholds.C2.margin_DG_seq}
  flag: single_source
reporting:
  probability_under_ignorance_is_finding: false
  report: [flip_values, inconclusive_interval_width, required_precision, branch_masses]
  analog_priors: side_by_side, flagged analog
```
