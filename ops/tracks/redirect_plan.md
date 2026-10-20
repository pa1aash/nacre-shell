# Redirect plan (decided 2026-10-20, D34 to D40)

The preprint is redirected from a CaCO3 barrier (negative above about 4 V vs Li) to a thermodynamic screen of bone-inspired calcium-phosphate barriers on aluminium collectors in fluorine-free lithium-ion cells. Carbonate stays as the control. The nucleation half failed its retrodiction (7 of 12 against 10), so template and nucleation results are hypotheses plus the required-precision map.

## DECISION

Title (frozen): "Thermodynamic screening of bone-inspired calcium phosphate barriers for aluminium current collectors in fluorine-free lithium-ion cells".

Carbonate is the control and motivation: one paragraph, one table row, one figure panel, one honest sentence in the Introduction. A screen does not promise a pass; the abstract and the predictions are conditional on the cutoff class. The general rule is stated in all three outcome frames:

- (A) A phosphate clears 4.3 to 4.5 V: positive headline.
- (B) A phosphate clears only to about 4.2 V or LFP-class: positive for those classes.
- (C) None clears above LFP-class: the headline is the design rule that oxoanion minerals have an oxidation ceiling within a few tenths of a volt of aluminium's own onset, plus the LFP-class and processing-stage result.

## FOUR CONDITIONS (gating claims)

- **K1.** Oxidation window above the charge cutoff, reported per cutoff class (LFP-class about 3.65 V; 4.2 to 4.3 V; 4.4 to 4.5 V), never a single verdict.
- **K2.** Insoluble at the processing pH (Ω_bulk ≥ 1, from sourced Ksp and speciation).
- **K3.** An accessible nucleation window along the dose axis: the heterogeneous barrier meets the criterion at an Ω where the homogeneous barrier does not. Bulk precipitation competes and is stated.
- **K4.** Thin continuous film: feasible if S_spread ≥ m_S OR closure is credible (nucleation-density closure plus the insulating-thickness bound); falsified only if both fail.

Adhesion and Ca-binding stay descriptors, not gates. The deletion test stays on K3 and K4. K3 and K4 run for any phase that passes K1 at ANY registered cutoff class. A mineral is falsified only if falsified under every registered phase framing (ACP and apatite are both registered as nucleus framings; report which passes).

## K1 TWO-TIER RULE

**Tier 1: thermodynamic onset.** The experimental route governs wherever formation data exist. DFT (Materials Project) is only a comparator, with its measured benchmark error. Report a per-reaction table (lattice O2 release, structural OH oxidation, water oxidation in hydrates, with a_w and a_OH as design axes) and the benchmark status of every number. A pass needs a solvated sink. "Undetermined never passes." Dehydration thresholds are reported as thresholds. DFT phosphate numbers are unbenchmarked until a phosphate benchmark on tabulated formation data passes.

**Tier 2: measured service limit from the literature,** with evidence class A (potential hold or LSV on a coated Al collector), B (coating on a cathode particle cycled to a stated charge cutoff in carbonate electrolyte; indirect) or C (LSV of the bulk phase). Log electrolyte, temperature, cutoff and duration.

**Verdict.** A phase is falsified at a cutoff only if tier 1 and the available tier 2 both fall below it. If tier 1 is below and tier 2 of class A or B reaches above, report "not excluded, kinetically stabilised", labelled with the class. With no tier 2, report tier 1 only and say so. Carbonate runs through the same rule and stays falsified (its measured onset is near its thermodynamic value).

Seed sources, to be fetched and verified, not copied:

- AlPO4-coated LiCoO2 at 4.8 V (Lee, Kim, Cho, Kim, Park, J. Electrochem. Soc. 2004, DOI 10.1149/1.1723495).
- Li3PO4-coated LiCoO2 (Nanoscale 2023, d3nr01251d).
- ALD Li3PO4 on Ni-rich NMC at a 4.5 V cutoff (US 10,734,641; related US 10,243,206).
- ALD AlPO4 on LNMO (Univ. Western Ontario, 2017).

## CANDIDATES

Panel: hydroxyapatite, amorphous calcium phosphate, octacalcium phosphate, beta-TCP, Ca pyrophosphate, Ca metaphosphate. Brushite is a precursor, not a candidate.

Al-salt film ladder (core): AlPO4, Al(PO3)3, Al-borate, Al-oxalate, Al2O3, and the bare-Al onset, ranked on (a) oxidation limit (tier 1 and tier 2), (b) insolubility in carbonate electrolyte (literature; undetermined where no source), (c) ionic blocking.

Design rule: a barrier need not be thermodynamically stable if the corrosion product forms an insoluble, oxidation-stable film (fluoride protection works this way through AlF3; the fluorine-free analogue is Al-phosphate or borate). Two labelled parts: film properties are screened; supply of phosphate at a pit is a hypothesis. A survey of fluorine-free phosphate sources (phosphate esters as additives or co-solvents; a phosphate-bearing binder or film as a reservoir), with their own oxidation limits, is owned by W2.

Comparators: silicate (first to cut) and calcite/ACC (the control). No fluorides anywhere (no AlF3, no fluorapatite, not even as comparators). "Self-healing" appears only as a design hypothesis or criterion, never as a claim.

## REGIMES

- Alkaline aqueous slurry (pH 10 to 13 primary).
- The acid-adjusted state in the Al passivation window is a comparator to the incumbent (phosphoric-acid pH control), not a regime of the barrier. Derive the window from our own Al-O-H Pourbaix on benchmarked experimental ion data and cross-check against the published 4.5 to 8.5 (RSC Sustainability 2023; the KIT slides say 4 to 8.5): report both.
- Fluorine-free high-voltage Li-ion cell with the charge cutoff as a design axis; LFP-class low-voltage reference.
- Na-ion and Si-anode binders are dropped.

## VALIDATED VERSUS NOT

The thermochemistry and window pipeline (benchmarked against measured data) is reliable. The nucleation and template half failed its retrodiction (7 of 12; 10 required): report 7 of 12 in an SI table and one main-text sentence that the nucleation half is not validated. No nucleation or wetting numbers as findings; no added cases. An optional qualitative consistency check against PDA-promoted apatite (Ryu, Ku, Lee, Park, Adv. Funct. Mater. 2010) is labelled consistency, not validation. Template and nucleation results are hypotheses plus the required-precision map.

## CONTROL LOGIC

Carbonate runs through the same pipeline and thresholds as one table row and one figure panel (negative control for K1, positive control for K2). Reuse the carbonate control from tag `p0-carbonate-control` and `ops/reports/carbonate_control_inventory.md` only.

## INCUMBENTS

Verify assignees and claims. The patent route is a gap (no Lens token): use open full-text patent pages and the listed documents.

- US 6,844,114 (continuation of US 6,485,866; Canadian priority CA 2,268,355, 1999): collector coated with a vitreous or partly vitreous alkali borate or polyborate binder plus an electronic conduction additive. The description names phosphate and polyphosphate, especially (LiPO3)n at pH 4 to 9, carbon black 2 to 20 vol %, a 3 to 4 um coating, polymer-electrolyte cells at a 3.1 V limit. Check the parent for the phosphate claims. Background cites US 5,580,686 and US 5,262,254.
- US 9,350,017, 9,263,731, 8,221,915 ("High performance lithium or lithium ion cell"): conductive-coated Al foil, 60 C potential hold where bare Al corrodes at 4.2 V and onset is delayed at 3.65 V.
- Phosphoric-acid pH control in aqueous electrodes: RSC Sustainability 2023 (d3su00031a), J. Mater. Chem. A 2024 (d4ta03592e), the Bresser group's water-processed LTO with H3PO4 and Li3PO4, HAL-CEA water-processed NMC532.
- Template precedent: Ryu et al. 2010.
- W2 also searches phosphate conversion coatings on Al.

Novelty must come from the templated biomimetic film with a quantitative design rule in the fluorine-free plus aqueous-processing regime.

## RISKS TO TEST, NOT ASSUME

- Phosphate may fail K1 too (Li3PO4 computed near 4.2 V; no source shows phosphate more anodically stable than carbonate).
- Structural OH and hydrate water may oxidise near the carbonate limit.
- K3 may have no accessible window (bulk precipitation competes).
- Insulating film thickness.
- Slurry competing phases (Li3PO4, AlPO4).
- Novelty against incumbents.

## PREDICTIONS

The Predictions section is conditional on the cutoff class. The first experiment is templated Ca-phosphate on Al foil, with and without a fluorine-free phosphate source, in an anodic potential hold at 4.3 to 4.5 V against bare and carbon-coated foil. The notice to Prof. Braun asks whether his lab could run it.

## SCOPE GUARD ADDITIONS

To `charter/scope_guard.md`, by the planning-chat-approved list. Recorded here only; the integrator applies them at PH-I5.

- `(phosphate|apatite) (barrier|layer|film|coating) (works|protects|is effective)`
- `nacre-inspired` outside the carbonate paragraph
- `we show .* (holds|survives) above`
- `outperforms (phosphoric acid|carbon-coated)`
- `(novel|first)` without audit support
- `self-heal` outside hypothesis or criterion wording

## FIGURES AND TABLES

Figures: hero render (phosphate, alone, late); four-panel bone-like pathway schematic; four-conditions diagram; window ladder (oxidation limits versus cutoffs and bare-Al onset); pH versus supersaturation map with the Al passivation window; nucleation-barrier map; required-precision map; candidate-by-condition heatmap; Al-salt film ladder.

Tables: candidates versus conditions; sourced parameters; thermochemistry benchmark; retrodiction (SI).

## CHECKPOINTS

Three audits. The planning chat spot-checks diffs and returns PASS or a numbered fix list. Lanes proceed on assumed PASS for mechanical fixes only. Anything touching verdict rules, thresholds, priors or K1 numbers waits for PASS before the production run. Packets contain the actual numbers and a fix-by-fix table; a zip is fine.

- **cp4:** design rulings frozen (claim register K1 to K4, candidate panel, regimes, K1 two-tier rule, thresholds structure, scope guard). Tag `p0-cp4`.
- **cp5:** two uploads. (a) FREEZE before the production screen (parameter table, benchmark, thresholds with numeric margins, hashes); the planning chat returns PASS or fixes in the same turn; dry runs are allowed before it; any change after the freeze is a dated deviation with its effect on verdicts. Tag `p0-cp5`. (b) RESULTS after the screen. Tag `p0-cp5r`.
- **cp6:** manuscript. Tag `p0-cp6`.

## DAYS and SESSIONS

Four working days, tool days 4 to 7. The ledger in `ops/tracks/p0.yaml` is authoritative. Within-day order is as listed; it is not enforced by polling.

- **Day 4 (working day 1).** PH-W1.1 (Sonnet): phosphate and Al-salt evidence rows. PH-W2.1 (Sonnet): incumbents and novelty scan, tier-2 hunt, phosphate-source survey, contrary dossier. PH-W3.1 (Opus): generalised derivation and contract, K1 to K4 structure, K1 two-tier rule, symbolic thresholds and priors, Al-salt ladder criterion; committed before any screen output. PH-K1 (Opus, lane w5): window pipeline on every candidate, started after W1.1's END BLOCK. PH-I4 (Sonnet): cp4 packet.
- **Day 5 (working day 2).** PH-W5.1 (Opus, cp4): phosphate benchmark, Al-O-H passivation-window Pourbaix, Al-salt ladder, final window ladder (heavy). PH-W4.1 (Opus, cp4): generic mineral screen code. PH-W1.2 (Sonnet, cp4): parameter table and priors. PH-W3.2 (Opus, cp4): numeric margins, blind re-derivation. PH-W8.1 (Sonnet, cp4): outline, briefs, claims ledger, macros. PH-I5 (Sonnet): FREEZE packet (cp5a), scope-guard additions applied, freeze block set to `p0-cp5` with the phosphate paths.
- **Day 6 (working day 3).** PH-W4.2 (Opus, cp5): production screens (heavy). PH-W4.3 (Sonnet, cp5): required-precision map and flip values. PH-W8.2 (Opus, cp4): Introduction, Design rules, Methods. PH-W6.1 (Sonnet, cp4): figure templates. PH-W2.2 (Sonnet, cp4): ChemRxiv package retitled, co-author pack. PH-I6 (Sonnet): RESULTS packet (cp5b).
- **Day 7 (working day 4).** PH-W8.3 (Opus, cp5r): Results, Predictions, Discussion and limits. PH-W6.2 (Sonnet, cp5r): real-data figures. PH-W7.1 (Sonnet, cp5r): phosphate hero, runs alone. PH-W1.3 (Sonnet, cp5r): reference audit. PH-W3.3 (Opus, cp5r): referee-style review and fixes. PH-I7 (Sonnet): cp6 packet.

## CUT ORDER

First to go: silicate comparator; extra Al-salt comparators beyond AlPO4, Al(PO3)3 and Al2O3; beta-TCP and OCP; the acid-adjusted comparator state; hero polish (use the schematic); the second framing.

Never cut: the carbonate control, the K1 ladder, K2, the required-precision map, the predictions, the Al-salt ladder for AlPO4.

## OPEN FOR THE PLANNING CHAT

Nothing. Items marked "to be fetched" are for the lanes.

## NOTICE TO CO-AUTHORS

Palaash sends the scope-change notice and collects consent for the new scope now, in parallel. One line asks Prof. Braun whether his lab could run the first test.

## ROUTE LAYER (draft, pending ruling by the planning chat; amend this file when ruled)

Recorded 2026-10-20 (PH-I4b). Draft only; no session may treat it as ruled.

**Routes.**
- R1: interfacial gelation triggered by Al3+. Soluble Li or Na polyphosphate plus chitosan, pH 5 to 8.5. Al3+ released at the oxide crosslinks the polyphosphate into an insoluble Al-polyphosphate gel; self-limiting.
- R2: Ca-polyphosphate coacervate (liquid precursor) wets the foil and dries to an amorphous Ca-polyphosphate glass.
- R3: dry-trapped Ca-polyphosphate (Ca added last, fast drying).
- Constraint: Ca2+ and Al-oxide surfaces accelerate polyphosphate hydrolysis toward orthophosphate (the low-ceiling phase). Every route is a kinetic race against hydrolysis; this extends the two-stage logic of the cp4 candidate decision.

**Claims.**
- K1: the amorphous framing is registered beside the crystalline framing for Ca-polyphosphate glass and Al-polyphosphate. Glass thermochemistry (DfH, S0, glass-to-crystal correction) enters the tier-1 route.
- K2: solubility of crosslinked Ca- and Al-polyphosphate, plus a hydrolysis descriptor (half-life against t_proc from literature rates with Ca2+ and Al-oxide dependence). It gates only where rate data show a half-life shorter than t_proc; otherwise it is reported.
- K3 route form: R2 is the coacervate binodal region in (Ca:polyP, pH, ionic strength) from literature, undetermined if absent. R1 is a thermodynamic criterion only: the Al-polyphosphate IAP at the interface exceeds Ksp, with a(Al3+) at the foil from our own Al-O-H Pourbaix over pH 5 to 8.5. Kinetics of gelation versus hydrolysis is a labelled hypothesis.
- K4 route form: liquid-precursor wetting S_spread = gamma_sl - gamma_sn - gamma_nl, with gamma_nl the coacervate-water tension. The design rule is the condition on gamma_nl. Self-limiting thickness is a descriptor. The insulating bound stays.

**Al-salt ladder.** Promote Al(PO3)3 and Al-polyphosphate rungs (both framings). Organic-matrix rungs: chitosan, polydopamine and the chitosan-polyphosphate complex (oxidation limits from literature, tier 2 only). Polydopamine is a stated K1 risk, contrary B4.

**Baselines** (comparator rows through K1, K2 and K4 only; no performance claims).
- Tsinghua/Hon Hai baked aluminophosphate (US 8,252,463; 8,821,969).
- Hydro-Quebec Li polyphosphate film (US 6,485,866; 6,844,114; aqueous Li polyphosphate, soluble).

**Scope-guard additions** (record only; applied at the cp5 freeze).
- `self-heal(s)` outside hypothesis wording
- `(insoluble|crosslinked) .* film (forms|assembles) (on|at) (aluminium|the foil)`
- `coacervate (wets|forms) on aluminium`
- `(outperforms|better than) (baked|plain|conventional) (coating|aluminophosphate)`
- `polyphosphate (film|gel|glass) (protects|prevents|is stable)`

**First experiment** (replaces the earlier version). Route R1 or R2 film against baked aluminophosphate, hydroxyapatite, bare and carbon-coated foil: (a) water insolubility and aqueous-slurry immersion; (b) anodic potential hold at 4.3 to 4.5 V in a fluorine-free electrolyte. Conditional predictions: hydroxyapatite fails near 4.1 V; condensed phases survive; the gelled or coacervate film resists water where Li polyphosphate dissolves.

**Cut order for the route layer.** R3 first (one sentence); matrix rungs beyond chitosan; the R2 criterion (kept as "undetermined, literature gap" if no binodal data); hero render; beta-TCP and OCP. Never cut: the carbonate control, the K1 ladder in both framings, K2 solubility, the baselines through K1 K2 K4, the required-precision map, the R1 thermodynamic test, the predictions.

**Evidence status** (from the PH-W1.2 report). Hydrolysis rates exist only for gamma-Al2O3 at room temperature. Coacervate gamma_nl, binodal, matrix oxidation limits, Al(PO3)3 and the glass-to-crystal correction are gaps. All tier-2 records are in LiPF6 electrolyte. Undetermined verdicts are expected and are reported as such.
