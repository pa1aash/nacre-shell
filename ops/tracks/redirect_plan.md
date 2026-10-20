# Redirect plan (decided 2026-10-20, D34 to D40)

The preprint is redirected from a CaCO3 barrier (negative above about 4 V vs Li) to a thermodynamic screen of bone-inspired calcium-phosphate barriers on aluminium collectors in fluorine-free lithium-ion cells. Carbonate stays as the control. The nucleation half failed its retrodiction (7 of 12 against 10), so template and nucleation results are hypotheses plus the required-precision map.

## DECISION

Title (working wording, unfrozen; final at cp6): "Thermodynamic screening of bone-inspired calcium phosphate barriers for aluminium current collectors in fluorine-free lithium-ion cells".

Carbonate is the control and motivation: one paragraph, one table row, one figure panel, one honest sentence in the Introduction. A screen does not promise a pass; the abstract and the predictions are conditional on the cutoff class. The general rule is stated in all three outcome frames:

- (A) A phosphate clears 4.3 to 4.5 V: positive headline.
- (B) A phosphate clears only to about 4.2 V or LFP-class: positive for those classes.
- (C) None clears above LFP-class: the headline is the design rule that oxoanion minerals have an oxidation ceiling within a few tenths of a volt of aluminium's own onset, plus the LFP-class and processing-stage result.

## FOUR CONDITIONS (gating claims)

- **K1.** Oxidation window above the charge cutoff, reported per cutoff class (LFP-class about 3.65 V; 4.2 to 4.3 V; 4.4 to 4.5 V), never a single verdict.
- **K2.** Insoluble at the processing pH (Ω_bulk ≥ 1, from sourced Ksp and speciation).
- **K3.** An accessible nucleation window along the dose axis: the heterogeneous barrier meets the criterion at an Ω where the homogeneous barrier does not. Bulk precipitation competes and is stated.
- **K4.** Thin continuous film: feasible if S_spread ≥ m_S OR closure is credible (nucleation-density closure plus the insulating-thickness bound); falsified only if both fail.

Adhesion and Ca-binding stay descriptors, not gates. The deletion test stays on K3 and K4. K3 and K4 run for any phase that passes K1 at ANY registered cutoff class. A mineral is falsified only if falsified under every registered phase framing (ACP and apatite are both registered as nucleus framings; report which passes). For the in-situ routes R1 to R3 the amorphous framing governs (route layer C4).

## K1 TWO-TIER RULE

**Tier 1: thermodynamic onset.** The experimental route governs wherever formation data exist. DFT (Materials Project) is only a comparator, with its measured benchmark error. Report a per-reaction table (lattice O2 release, structural OH oxidation, water oxidation in hydrates, with a_w and a_OH as design axes) and the benchmark status of every number. A pass needs a solvated sink and a bracketed onset (hydration lower bound for the sink; route layer, evidence consequence 2). "Undetermined never passes." For the amorphous routes the amorphous row governs and the crystalline row is an optimistic upper reference (C4). Dehydration thresholds are reported as thresholds. DFT phosphate numbers are unbenchmarked until a phosphate benchmark on tabulated formation data passes.

**Tier 2: measured service limit from the literature,** with evidence class A (potential hold or LSV on a coated Al collector), B (coating on a cathode particle cycled to a stated charge cutoff in carbonate electrolyte; indirect) or C (LSV of the bulk phase). Log electrolyte, temperature, cutoff and duration.

**Verdict.** A phase is falsified at a cutoff only if tier 1 and the available tier 2 both fall below it. If tier 1 is below and tier 2 of class A or B reaches above, report "not excluded, kinetically stabilised", labelled with the class. With no tier 2, report tier 1 only and say so. Tier-2 rows in LiPF6 are context only for the fluorine-free regime and can counter-indicate but not support (route layer, evidence consequence 1). Organic-matrix rungs are tier 2 only (C6). Carbonate runs through the same rule and stays falsified (its measured onset is near its thermodynamic value).

Seed sources, to be fetched and verified, not copied:

- AlPO4-coated LiCoO2 at 4.8 V (Lee, Kim, Cho, Kim, Park, J. Electrochem. Soc. 2004, DOI 10.1149/1.1723495).
- Li3PO4-coated LiCoO2 (Nanoscale 2023, d3nr01251d).
- ALD Li3PO4 on Ni-rich NMC at a 4.5 V cutoff (US 10,734,641; related US 10,243,206).
- ALD AlPO4 on LNMO (Univ. Western Ontario, 2017).

## CANDIDATES

Panel: hydroxyapatite, amorphous calcium phosphate, octacalcium phosphate, beta-TCP, Ca pyrophosphate, Ca metaphosphate. Brushite is a precursor, not a candidate.

Al-salt film ladder (core): AlPO4, Al(PO3)3, Al-polyphosphate, Al-borate, Al-oxalate, Al2O3, and the bare-Al onset, ranked on (a) oxidation limit (tier 1 and tier 2), (b) insolubility in carbonate electrolyte (literature; undetermined where no source), (c) ionic blocking.

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
- **cp5:** two uploads. (a) FREEZE before the production screen (parameter table, benchmark, thresholds with numeric margins, hashes); GO/NO-GO rule applies here (route layer, evidence consequence 3); the planning chat returns PASS or fixes in the same turn; dry runs are allowed before it; any change after the freeze is a dated deviation with its effect on verdicts. Tag `p0-cp5`. (b) RESULTS after the screen. Tag `p0-cp5r`.
- **cp6:** manuscript. Tag `p0-cp6`.

## DAYS and SESSIONS

Four working days, tool days 4 to 7. The ledger in `ops/tracks/p0.yaml` is authoritative. Within-day order is as listed; it is not enforced by polling.

- **Day 4 (working day 1).** PH-W1.1 (Sonnet): phosphate and Al-salt evidence rows. PH-W2.1 (Sonnet): incumbents and novelty scan, tier-2 hunt, phosphate-source survey, contrary dossier. PH-W3.1 (Opus): generalised derivation and contract, K1 to K4 structure, K1 two-tier rule, symbolic thresholds and priors, Al-salt ladder criterion; committed before any screen output. PH-K1 (Opus, lane w5): window pipeline on every candidate, started after W1.1's END BLOCK. PH-I4 (Sonnet): cp4 packet.
- **Day 5 (working day 2).** Added at PH-I4c: PH-W1.3 (Sonnet, gap closing), PH-W3.2a (Opus, contract v6 and route derivations), PH-W4.2a (Opus, route evaluators, after PH-W3.2a's END BLOCK), PH-W6.1 (Sonnet, moved from day 6); the old reference audit is PH-W1.4 (day 7). PH-W5.1 (Opus, cp4): phosphate benchmark, Al-O-H passivation-window Pourbaix, Al-salt ladder, final window ladder (heavy). PH-W4.1 (Opus, cp4): generic mineral screen code. PH-W1.2 (Sonnet, cp4): parameter table and priors. PH-W3.2 (Opus, cp4): numeric margins, blind re-derivation. PH-W8.1 (Sonnet, cp4): outline, briefs, claims ledger, macros. PH-I5 (Sonnet): FREEZE packet (cp5a), scope-guard additions applied, freeze block set to `p0-cp5` with the phosphate paths.
- **Day 6 (working day 3).** PH-W4.2 (Opus, cp5): production screens (heavy). PH-W4.3 (Sonnet, cp5): required-precision map and flip values. PH-W8.2 (Opus, cp4): Introduction, Design rules, Methods. PH-W6.1 (Sonnet, cp4): figure templates. PH-W2.2 (Sonnet, cp4): ChemRxiv package retitled, co-author pack. PH-I6 (Sonnet): RESULTS packet (cp5b).
- **Day 7 (working day 4).** PH-W8.3 (Opus, cp5r): Results, Predictions, Discussion and limits. PH-W6.2 (Sonnet, cp5r): real-data figures. PH-W7.1 (Sonnet, cp5r): phosphate hero, runs alone. PH-W1.3 (Sonnet, cp5r): reference audit. PH-W3.3 (Opus, cp5r): referee-style review and fixes. PH-I7 (Sonnet): cp6 packet.

## CUT ORDER

First to go: silicate comparator; then the second framing and the Al-borate and Al-oxalate rungs; extra Al-salt comparators beyond AlPO4, Al(PO3)3 and Al2O3; beta-TCP and OCP; the acid-adjusted comparator state; hero polish (use the schematic).

Never cut: the carbonate control, the K1 ladder, the amorphous K1 row, K2, the required-precision map, the predictions, the Al-salt ladder for AlPO4.

## OPEN FOR THE PLANNING CHAT

Nothing. Items marked "to be fetched" are for the lanes.

## NOTICE TO CO-AUTHORS

Palaash sends the scope-change notice and collects consent for the new scope now, in parallel. One line asks Prof. Braun whether his lab could run the first test.

## ROUTE LAYER (ruled 2026-10-20, cp4 PASS)

Rulings C1 to C6 of the planning chat, recorded 2026-10-20 (PH-I4c). Supersedes the draft recorded at PH-I4b.

**Routes.**
- R1: interfacial gelation triggered by Al3+. Soluble Li or Na polyphosphate plus chitosan, pH 5 to 8.5. Al3+ released at the oxide crosslinks the polyphosphate into an insoluble Al-polyphosphate gel; self-limiting.
- R2: Ca-polyphosphate coacervate (liquid precursor) wets the foil and dries to an amorphous Ca-polyphosphate glass.
- R3: dry-trapped Ca-polyphosphate (Ca added last, fast drying).
- Constraint: Ca2+ and Al-oxide surfaces accelerate polyphosphate hydrolysis toward orthophosphate (the low-ceiling phase). Every route is a kinetic race against hydrolysis; this extends the two-stage logic of the cp4 candidate decision.

**C1. Hydrolysis descriptor (K2).** The observable is the condensed fraction at the end of the wet period, f_cond = 2^(-t_proc/t_half). t_proc is the wet residence time (mixing, coating and drying until a_w falls below the registered threshold). k_hyd carries a registered transfer factor: the data are gamma-Al2O3 particles at room temperature, pH 6 and 8, with and without 1 mM Ca2+; not foil, drying, or other pH or temperature. Falsified only if f_cond < f_min under the SLOWEST plausible rate at a state the data cover; not gating if the fastest plausible rate still gives f_cond >= f_min; otherwise inconclusive; outside the data: undetermined, never gating. The evidence grade is recorded beside every use. Partial hydrolysis to oligophosphates counts as condensed; only the orthophosphate fraction is lost.

**C2. Formation criteria (K3 route form).**
- R1 is a falsifying-only test. Omega_AlPP < 1 robustly means the gel cannot form thermodynamically (falsified at that state). Omega > 1 means "not excluded by thermodynamic accessibility", never a pass. Ksp of the Al polyphosphate is a gap, so expect undetermined.
- a(Al3+) is taken in two labelled states: oxide-equilibrium (slurry stage; our Al-O-H Pourbaix) and pit-state (cell stage; higher; literature). Polyphosphate complexation of Al3+ is included in the speciation or flagged as a gap.
- R2 falsifies only where the coacervate binodal map covers the state; outside coverage undetermined.
- Kinetics of gelation versus hydrolysis stays a labelled hypothesis.

**C3. Liquid wetting (K4 route form).** Coacervate-dilute tensions are typically orders of magnitude below solid-water energies (W1 to source), so gamma_nl is negligible and the condition reduces to gamma_sn <= gamma_sl (does the substrate prefer the dense phase over the dilute one). W3 derives the general condition and both limits, and obtains gamma_sl - gamma_sn from polyphosphate adsorption thermodynamics on alumina (Gibbs-Langmuir machinery with the adsorption isotherms W1 found). The spreading coefficient of the coacervate on alumina is reported as a design result. Self-limiting thickness is a descriptor. The insulating bound stays.

**C4. Framings.** The in-situ low-temperature routes R1 to R3 are amorphous, so the AMORPHOUS framing governs their verdict and the crystalline framing is an optimistic upper reference (the glass has higher free energy, so a lower onset). A crystalline pass with an amorphous fail is labelled "requires crystallisation". "Falsified only if falsified under every framing" stays for the nucleus framings (ACP versus apatite). For the baked baselines (unspecified structure) report both. Glass thermochemistry (DfH, S0, glass-to-crystal correction) enters the tier-1 route.

**C5. Baselines accepted.** Comparator rows through K1, K2 and K4 only; no performance claims.
- Tsinghua/Hon Hai baked aluminophosphate (US 8,252,463; 8,821,969).
- Hydro-Quebec Li polyphosphate film (US 6,485,866; 6,844,114; aqueous Li polyphosphate, soluble).
Neither patent family prints a film solubility, so baseline K2 rows are undetermined unless a literature solubility exists for the COMPOSITION (mark such values composition-based). The Hydro-Quebec film's solubility is an inference from chemistry, not a patent statement.

**C6. Matrix rungs.** Organic polymers (chitosan, polydopamine, the chitosan-polyphosphate complex) have no meaningful tier 1; the limit is kinetic and measured, so tier 2 is the only measure. Class A or B below the cutoff: report as the film's ceiling. Class C only, or a gap: a matrix-risk flag, not a ceiling. The matrix never gates by itself. Report both variants if a thermal budget could remove the matrix. Polydopamine is a stated K1 risk, contrary B4.

**Al-salt ladder.** Promote Al(PO3)3 and Al-polyphosphate rungs (both framings per C4). Organic-matrix rungs per C6.

**Evidence consequences.**
1. Every tier-2 row so far is in LiPF6, where fluoride forms AlF3 on aluminium. Such a record may counter-indicate (a service limit below the cutoff stands as evidence against) but cannot support "not excluded, kinetically stabilised" in the fluorine-free regime; it is context only.
2. A tier-1 pass needs the bracketed onset (hydration lower bound for the sink). Hydration free energies of Ca2+, Al3+ and ClO4- are fetched in PH-W1.3, the bracket is computed in PH-W5.1 and vetted in PH-W3.2.
3. GO/NO-GO at the cp5 freeze: if no condensed phosphate has a lower-bound onset above 4.3 V, the headline is the design rule (condense the phosphate; bone mineral fails near 4.1 V) plus the gap map, and the abstract says so. The operator is told plainly and decides whether to post. The route layer stays as a design hypothesis with its screened thermodynamics.
4. NS7 stands only with four qualifiers: in situ; crosslinked and water-insoluble; Al foil; fluorine-free.
5. Corrected pointers: Sci. Rep. 8:17450 pigments are on steel and zinc; RSC Adv. 2017 c6ra28808a is a lysozyme coacervate; US 12,478,560 is a dental polyacrylic-acid coacervate.

**Scope-guard additions** (record only; applied at the cp5 freeze).
- `self-heal(s)` outside hypothesis wording
- `(insoluble|crosslinked) .* film (forms|assembles) (on|at) (aluminium|the foil)`
- `coacervate (wets|forms) on aluminium`
- `(outperforms|better than) (baked|plain|conventional) (coating|aluminophosphate)`
- `polyphosphate (film|gel|glass) (protects|prevents|is stable)`

**First experiment** (replaces the earlier version). Route R1 or R2 film against baked aluminophosphate, hydroxyapatite, bare and carbon-coated foil: (a) water insolubility and aqueous-slurry immersion; (b) anodic potential hold at 4.3 to 4.5 V in a fluorine-free electrolyte. Conditional predictions: hydroxyapatite fails near 4.1 V; condensed phases survive; the gelled or coacervate film resists water where Li polyphosphate dissolves.

**Cut order for the route layer.** R3 first (one sentence); matrix rungs beyond chitosan; the R2 criterion (kept as "undetermined, literature gap" if no binodal data); hero render; beta-TCP and OCP. After silicate: the second framing, then the Al-borate and Al-oxalate rungs. Never cut: the carbonate control, the K1 ladder, the amorphous K1 row, K2 solubility, the baselines through K1 K2 K4, the required-precision map, the R1 thermodynamic test, the predictions.

**Title.** The working wording is unchanged; it is unfrozen and final at cp6.

**Evidence status** (from the PH-W1.2 report). Hydrolysis rates exist only for gamma-Al2O3 at room temperature. Coacervate gamma_nl, binodal, matrix oxidation limits, Al(PO3)3 and the glass-to-crystal correction are gaps. All tier-2 records are in LiPF6 electrolyte. Undetermined verdicts are expected and are reported as such.
