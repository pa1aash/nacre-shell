# cp3 spot-check: charter edits for decisions 10 and 11

For the planning chat. Both edits are in `charter/claim_register.yaml`, one commit each (`dfb0093`, `4df93cd`). Text is applied as given in the P0-I2.5 prompt.

## Decision 10 (4a): C5 physics, sentence restored

Commit `dfb0093`.

```diff
@@ -486,4 +486,5 @@ claims:
       are different chemistries (design flag 7) and need different observables. Both are
       screening quantities: necessary, not sufficient, and blind to morphology.
+      Stability against dissolution is the same question as S > 1.
       If the bulk S is below 1, CaCO3 is unstable against dissolution at the template as
       well, because at equilibrium enrichment does not raise the driving force. C5 is
```

**Omission for the auditor.** The original G0 F2 sentence continued "...: if the bulk S is below 1, CaCO3 is unstable in the bulk and survives only where the C2 enrichment holds the local S above 1. C5 therefore reports both the bulk state and the C2-enriched state." That continuation is deliberately not restored, because cp2 established that enrichment does not raise S. The existing text after the restored sentence ("If the bulk S is below 1, CaCO3 is unstable against dissolution at the template as well, because at equilibrium enrichment does not raise the driving force") is unchanged.

## Decision 11 (4b): C2 residual fields

Commit `4df93cd`. Replaced `computation.method` and `open_items`; appended one entry to `controls`.

```diff
@@ -164,7 +164,12 @@ claims:
       method: >-
-        Enhanced-sampling free energy of Ca2+ approach to each site (free and
-        surface-bound template), closed into a cycle against hydrated Ca2+; protonation
-        correction from Phase 1 pKa values at the regime pH; ionic-strength correction;
-        charge-neutral cells or explicit finite-size correction; conversion to the
-        enrichment factor and to local S for C3.
+        Binding free energy of Ca2+ at each template site type, closed into a thermodynamic
+        cycle against hydrated Ca2+ at the regime activity, with the protonation correction
+        at the regime pH and an ionic-strength correction. From ΔG_seq, a Langmuir isotherm
+        at the regime Ca2+ activity gives the site occupancy Θ_occ and the surface excess
+        Γ_Ca, and the Gibbs–Langmuir term (neutral-solute approximation) gives Δγ_ads, the
+        change in the template–liquid interfacial energy passed to C3. In P0, ΔG_seq comes
+        from literature binding free energies (single-source values flagged, with inflated
+        uncertainty); in the main study it comes from enhanced-sampling free energies with
+        charge-neutral cells. C2 reports these descriptors; it computes no local
+        supersaturation and is not a kill criterion.
       phase: 7
@@ -212,13 +217,8 @@ claims:
       - "competitor ions Li+ and Al3+ at the same sites (selectivity, Phase 7 item 7)"
+      - "Each control is reported through the same descriptors (ΔG_seq, Θ_occ, Γ_Ca, Δγ_ads); its effect on nucleation is judged in C3, and only C3 and C4 carry the deletion test (cp2 F3)."
     open_items:
-      - >-
-        Activity versus concentration in the enrichment factor, the site-volume definition
-        that converts a site free energy into a local concentration, and how enrichment of
-        Ca2+ alone enters S (carbonate is not assumed enriched): Phase 2 derivation freeze.
-      - >-
-        Proof that the template's action through enrichment (C2 -> S) and through wetting
-        (C3 -> f(theta)) is not double counted: Phase 2 derivation freeze (S20/S21).
-      - >-
-        Numeric margin, and whether the test is on the best site or on a site-population
-        average: registered at G2.
+      - "Site density Γ_s and interfacial layer thickness δ_s are bounded by geometry (theory/ignorance_priors.md); site types are reported per termination, with an ignorance mixture."
+      - "The double-layer (electrocapillary) contribution to γ_sl is neglected (neutral-solute approximation); ionic strength screens it; stated as a limitation."
+      - "Any Ca2+ excess at the template–crystal contact belongs inside γ_sn (cp2 F1); γ_sn is supplied from contact data at the regime state, never by adding ΔG_seq."
+      - "If ΔG_seq is not negative under the registered decision rule, the result is reported as 'the sequestration premise fails'."
     verdict_bands:
```

## C2 kill_criterion, verdict_bands and threshold.status (ruling after 4b)

Commit `5e4df37`. Ruling: apply section C of `theory/cp2_brief.md` verbatim where it satisfies the constraint (no field says enrichment raises S or that C2 gates); otherwise apply the ruling's text. Source per field:

| Field | Source | Reason |
|---|---|---|
| `kill_criterion.statement` | cp2_brief section C, verbatim | Meets the constraint: "None", binds to C3 only through Delta_gamma_ads, not a kill criterion. |
| `kill_criterion.numeric_form` | ruling text ("not applicable") | Section C does not cover it. |
| `verdict_bands` (keys feasible, inconclusive, falsified) | ruling text | Section C renames the key to `finding_bands` with different keys. `tests/charter` and `charter/packet.py` require `verdict_bands` with exactly those three keys, so the key name is kept as the ruling allows. |
| `threshold.status` | ruling text | Section C reads "descriptor in P0 ...; no threshold", which contradicts the registered margin the bands refer to. |

Test assertions changed only where they asserted replaced text: C2 `threshold.status` and C2 `numeric_form` in `tests/charter/test_charter.py::test_thresholds_null_and_pending_g2`.

```diff
@@ -183,3 +183,3 @@ claims:
       value: null
-      status: "set in P0 (theory/thresholds.md, cp2); the main study adopts or amends with a dated note"
+      status: "set in P0 (theory/thresholds.md); C2 is reported, not gated (cp2 F3)"
       proposed: null
@@ -202,7 +202,7 @@ claims:
       statement: >-
-        Killed if Ca2+ binding at the template is unfavourable against the solvated
-        reference: Delta_G_seq not negative beyond its registered uncertainty at the
-        regime pH and ionic strength, so the template depletes rather than enriches
-        Ca2+ at the interface.
-      numeric_form: pending-G2
+        None. C2 is a binding descriptor. It enters C3 only through Delta_gamma_ads and is
+        not an independent kill criterion. If Delta_G_seq is not negative under the
+        registered decision rule, the report states the finding that the sequestration
+        premise fails.
+      numeric_form: "not applicable"
     depends_on: [C1]
@@ -225,10 +225,10 @@ claims:
       feasible: >-
-        Delta_G_seq is negative beyond the registered margin under the registered decision
-        rule, giving local enrichment above the aqueous reference.
+        Binding favourable: ΔG_seq is negative beyond the registered margin at the
+        registered credible level. Reported as a descriptor; it does not make the study
+        feasible.
       inconclusive: >-
-        The propagated Delta_G_seq straddles the registered margin, or the MLIP fallback
-        declares the free-energy route inconclusive.
+        Undetermined: the propagated ΔG_seq distribution straddles the registered margin.
       falsified: >-
-        Delta_G_seq is at or above the registered margin: no enrichment against solvated
-        Ca2+.
+        Binding unfavourable: ΔG_seq is not negative beyond the margin; reported as 'the
+        sequestration premise fails'. It does not falsify the study.
 
```

## Wording left for the auditor

No text in C2's definition or physics says that enrichment raises S; they say the opposite, so nothing was changed there. The C2 verdict_bands, kill_criterion and threshold.status wording flagged in the first version of this file is now resolved by the commit above. Still outside C2 and left alone:

- C5 `computation.method` reports an evaluation "for both the bulk state and the C2-enriched state", the latter as a labelled non-equilibrium sensitivity that never decides the verdict. It is consistent with the C5 physics text but is C5 text.
- C3 line "homogeneous reference ... at the bulk (unenriched) S" is consistent and untouched.
- C2 `verdict_bands` are retained under that key as reporting categories; a schema change to `finding_bands` would need a ruling on the schema.
