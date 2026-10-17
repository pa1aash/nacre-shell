# Conflicts between sources (complete, P0-W1.3)

Every input of `lit/params.yaml` whose admitted sources disagree beyond their stated uncertainties, or
whose values differ by more than the sources' own scatter suggests: the sources, the values, the
conditions that differ, the physical reason where one is apparent, and how the parameter table resolves
the disagreement. Row ids refer to `lit/evidence_table.csv`; keys to `lit/params.yaml`; clauses (U1, L1,
T1, W1, A1, I1, G1) to the prior-construction rule `lit/corpus/params_README.md`.

The resolution is never to pick a source. Under clause U1 a disagreement makes the prior uniform (L1
log-uniform beyond a decade) over the union of the sources' intervals, so the prior is at least as wide as
the disagreement. A ruling may cut a span at a physical bound (T1) or turn a key into a design axis (G1);
a quantity no source measures gets an ignorance prior (I1) with any measured analog beside it (A1).

Sections 1 to 14 were written on day 2 and are revised where day 3 evidence changed them; sections 15 to
34 are new on day 3. The machine-readable block at the end lists every entry for the SI conflicts table
(`src/nacre/lit/si_table.py`), which prints each key's sourced span from `lit/params.yaml`; the block's
prose carries no numbers.

## 1. Calcite-water interfacial free energy (`gamma_nl_calcite`)

| Source | Value (J m^-2) | Method and conditions |
|---|---|---|
| TC-010 / TC-006 / TC-007 (Sohnel and Mullin) | 0.098 to 0.109 (±0.013) | homogeneous-nucleation rates fitted with CNT, room temperature |
| TC-011 (Liu and Lim 2003) | 0.170 | homogeneous nucleation |
| TC-012 (Royne et al. 2011) | 0.150 | subcritical cracking of the (10-14) face |
| TC-013 (Okayama et al. 1997) | 0.072 | contact angles on (10-14) |
| TC-015 (Costa et al. 2018) | 0.410 | contact angles on (10-14); its compilers advise omitting it |
| TC-008, TC-009 (classical MD) | 0.205, 0.487 | free energy of planar facets {10-14} and {01-12}, one force field, 300 K |

Spread: a factor of 6.8. Physical reasons: CNT fits return an effective energy of a curved, possibly
non-crystalline critical nucleus averaged over facets, while MD and cracking give planar facet
energies of the crystal; facet energies differ by more than a factor of two between {10-14} and
{01-12}; contact-angle routes depend on the probe liquids and on surface contamination. The barrier
scales with gamma_nl cubed, so this spread alone moves DG_hom by a factor of about 300 across the
prior. Excluded rows: TC-014 (inverse gas chromatography, against vapour), TC-017 (not a solid-liquid
free energy), TC-018 (configurational energy), TC-019, TC-020 (grade D).
## 2. ACC-water interfacial free energy (`gamma_nl_acc`)

TC-024 (10.2 mJ m^-2, CNT fit of literature rates, anhydrous ACC assumed) and TC-025 (14 to 25 mJ m^-2,
cluster free energies from simulation) are close. TG-018 (about 330 mJ m^-2, abstract only, grade D,
not admitted under E5) is more than ten times larger. It comes from the size dependence of the apparent
solubility of 66-196 nm ACC particles, which also carries size effects other than the interface
(hydration, compositional change with size). The admitted prior is 10.2 to 25 mJ m^-2; if TG-018 were
read in full and upgraded, the key would span more than a decade.
## 3. Solubility of ACC (`log10_ksp_acc`) and the ACC offset (`acc_offset`)

| Source | log10 Ksp | Method |
|---|---|---|
| TG-001, TG-002 (Gebauer 2008) | -7.51, -7.42 | free-ion product at the onset of ACC in titrations, pH 9 to 10 |
| TG-003, TG-004 (Kellermeier 2014) | about -7.54, -7.48 | activity-corrected product at onset, pH 9 and 10 |
| TC-037, TC-038 (Brecevic and Nielsen 1989, compiled) | -6.39, -6.40 | dissolution equilibrium of separately prepared ACC |
| TC-041 (Clarkson 1992, compiled) | -6.04 | dissolution equilibrium |
| TG-007 (Purgstaller 2019, Mg-free intercept) | -6.278 ±0.046 | dissolution steady state, 24.5 C, I = 0.17 M |
| TC-040 (CNT-inferred second ACC) | -5.87 to -5.51 | critical-size analysis of literature rates |

The titration-onset values lie 1.1 to 1.5 log units below the dissolution values. The reason given by
the sources is polyamorphism: proto-calcite and proto-vaterite ACC formed at low supersaturation are
less soluble than ACC precipitated fast at high supersaturation, which the dissolution experiments
use; Kellermeier also points to stabilisers used in earlier work. The ACC offset inherits the split:
TG-011 (5.38 kJ mol^-1, from Kellermeier) against TC-030, TC-031 (11.9 kJ mol^-1, from
Brecevic-Nielsen) and TG-012 (13.0 kJ mol^-1, from Purgstaller). The prior is uniform over 5.4 to 13.0
kJ mol^-1, and the ACC framing should be read as covering more than one ACC.

Rows TG-003 and TG-004 are printed in a table column scaled by 1e-8 M^2, so their values (2.90e-8,
3.31e-8) do not appear in the extracted text in that form and the local trace audit lists them as
untraced; the scale is stated in each row's notes.
## 4. ACC density and molar volume (`v_m_acc`)

Pycnometry of dried ACC (TG-013, 2.282 g cm^-3 at 1.1 H2O per CaCO3; TG-014, 2.428 g cm^-3 at 0.5 H2O)
against in-situ SAXS of wet colloidal ACC (TC-054, TC-055: 1.62 g cm^-3; grade D and C, not admitted).
The SAXS value includes interparticle water and porosity and depends on the contrast assumptions, so it
is not the molar volume of the ACC phase. The admitted prior (44.9 to 52.5 cm^3 mol^-1 per CaCO3,
structural water included) varies with the water content; the framing must state whether V_m includes
structural water.
## 5. Template-water interfacial free energy (`gamma_sl0_template`)

Derived from contact angles on polydopamine: TH-049 (-27.0 mJ m^-2, van Oss acid-base model) against
TH-052, TH-054, TH-056 (1.5 to 3.4 mJ m^-2, Owens-Wendt, three deposition times). The sign follows the
model: the van Oss acid-base term can make gamma_SL negative for a strongly hydrophilic surface,
Owens-Wendt cannot. The water contact angle itself differs between the films (16.8 degrees on a
silicon wafer in TH-049, 41 degrees in TH-052 and in TD-064 on PCL), which tracks substrate, film
thickness and roughness. Both readings say polydopamine attracts water strongly.

**Resolution (cp3 ruling R8).** A negative template-water energy would make the film disperse or swell
without limit, so it is an artifact of the van Oss route. `gamma_sl0_template` is U1 cut at zero (T1),
0 to 3.4 mJ m^-2; the uncut span (-27.0 to 3.4 mJ m^-2) is `gamma_sl0_template_untruncated`, a labelled
sensitivity that never decides a verdict.
## 6. Ca2+-catecholate binding (`log10_k_ca_catecholate`)

TD-048 (log beta 4.83 ±0.08 at 0.143 mol dm^-3 NaCl) and TD-049 (3.65 ±0.07 at 0.472 mol dm^-3), one
paper, differ by 1.2 log units, far beyond their uncertainties. The cause is ionic strength (and Na+
competition); the same paper reports non-monotonic values at 0.692 and 0.933 mol dm^-3 (3.95, 5.26).
Tiron (TF-014, TF-015; not admitted) differs by 0.6 log units between NaCl and KCl, which its authors
attribute to Na+ ion pairing. The background electrolyte must be stated with any value used.

**Resolution.** One paper, so the key is single-source: U1 over the span, widened to the method error
m_seq/(R T ln 10) and flagged (W1); the unwidened span is kept in `widening.unwidened`.
## 7. Ca2+-carboxylate binding (`log10_k_ca_carboxylate`, `dg_bind_ca_acetate`, `dg_bind_ca_cooh_monolayer`)

- Solution: acetate log K 0.57 (TF-019, I = 0.1) up to poly(acrylic acid) 4.39 (TF-018, ITC at pH 7);
  maleate 2.40 at I = 0 (TD-051). The spread reflects denticity and polyelectrolyte cooperativity, not a
  disagreement about one quantity; it is kept as the anchor's comparison range.
- Acetate free energy: simulation -9.5 kJ mol^-1 (TH-026) against compiled experiment -7.1 to -4.4
  kJ mol^-1 (TH-029), one paper.
- Carboxyl monolayers: 7 to 12 kJ mol^-1 (TH-033, MD Langmuir analysis), 3 to 16 kJ mol^-1 (TH-034,
  AFM), and 30 to 170 kJ mol^-1 (TH-035, PMF) depending on the PMF method and its reference state. The
  monolayer range spans more than a decade, so its prior is log-uniform.
## 8. Calcite binding to templates against the barrier (B3 framing; `dg_bind_calcite_template`, `gamma_eff_het_organic`)

No source pairs a Ca2+-template binding free energy with gamma_eff on the same surface. The evidence
splits by what binds:

- **Crystal-template binding.** Hamm et al. 2014 (TC-061 to TC-066, TH-001 to TH-005) and Nielsen et al.
  2020 (TH-006 to TH-012) measure the binding of calcite to SAM-terminated tips by force spectroscopy and
  find gamma_eff falling linearly as calcite binding strengthens (slope TH-004). The phosphate SAM, a
  strong Ca2+ binder in solution, binds calcite most weakly and has the highest gamma_eff.
- **Ca2+-binding groups on a hydrophilic film.** Knight et al. 2024 (TH-014 to TH-024) and Giuffre et
  al. 2013 (TC-079 to TC-081, TH-025) find that adding Ca2+-binding (sulfate, carboxylate) groups to
  polysaccharide films raises gamma_eff or leaves it unchanged; Ca2+ stays solvent-separated from the
  groups in MD, and the explanation offered is that water is harder to displace (TH-022 to TH-024,
  contrary = y). Raiteri 2012 (TH-032), Smeets 2015 (TH-045), Tao 2019 (TH-046) and Chevalier 2014
  (TH-047) point the same way for solution additives or analogous systems.

Physical reading: what lowers the barrier is the free energy of the nucleus-template interface (calcite
binding), not the affinity of the template for single Ca2+ ions. Strong Ca2+ binding that comes with
strong hydration of the template raises the cost of displacing water (Delta_gamma_w) and can raise the
barrier. This bears directly on the sign questions of the theory lane (contract v2: Ca2+ binding at
fixed gamma_sn raises the C3 barrier) and is recorded here as evidence, not as a ruling.
## 9. Effective interfacial energies on templates (`gamma_eff_het_organic`)

Optical-rate CNT fits (51 to 102 mJ m^-2; TC-057 to TC-081) against force-spectroscopy and COSMO-RS
conversions on amine and mixed SAMs (110 to 147 mJ m^-2; TH-008 to TH-011, TC-072, TC-073). The latter
are computed for different, less nucleating surfaces at pH 8.2, and the conversion assumes the CNT
cap geometry. Mineral substrates (quartz; TC-084 to TC-092: 12 to 48 mJ m^-2) are lower still and are
not admitted for an organic template.
## 10. Catechol pKa1 (`pka_catechol`)

Measurements of catechol itself with a stated ionic strength (cp3 ruling R8: no proxy, with an
ionic-strength flag): Antikainen 1973 (TM-001, 9.21, I = 0.1 M KCl), Harada 1969 (TM-003, 9.32 by
potentiometry; TM-005, 9.34 by spectrophotometry; I = 0.10), Mirzahosseini 2018 (TM-007, 9.396 +- 0.005,
I = 0.15 M KCl, NMR-pH titration) and the literature values compiled in Antikainen's Table 6 (TM-009 to
TM-017, 9.15 to 9.43 at I = 0.06 to 0.15). These spread over about 0.3 pK units, well beyond the stated
uncertainties of 0.005 to 0.04. Ionic strength explains part (a larger I lowers the apparent pKa through
the activity coefficient of the anion) but not the order, which also follows the method and the
temperature (18 to 25 C). TF-021 (8.83 +- 0.03, Britton-Robinson buffer, I not stated) lies 0.3 below all
of them; the buffer's own ionic strength and the method are the likely cause.

**Resolution.** U1 over the rows that state I (9.15 to 9.43); the rows that do not state I (TF-021,
TF-025, TM-015, TM-018 to TM-026) are comparators. The key carries the flag `ionic_strength`. No source
extrapolates to I = 0.
## 11. Carboxyl pKa (`pka_carboxyl`)

Monomeric acids at I = 0 (acetic 4.756, succinic 4.207, propionic 4.87 to 4.9) against poly(acrylic
acid) at half ionisation (6.1, 6.3, salt-free). The polyelectrolyte shift is physical (charge
accumulation on the chain), and a surface-bound carboxyl layer is expected to shift similarly; no
surface pKa of a COOH monolayer was read.
## 12. Slurry dissolved inorganic carbon (`dic_slurry`, regime key)

TA-019 (4.2 mmol L^-1, 3.7 to 5.4 over washing times) against TF-032 (17.3 mmol L^-1, derived from
6.4 mg Li2CO3 per g of cathode at water:solid 5:1 under argon). Plausible causes: nickel content
(83 against 85 percent), storage history of the powder (surface carbonate grows with air exposure) and
the atmosphere of the wash. Both are washing solutions, not slurries.
## 13. Formation energies of calcite and the decomposition benchmark (`dfg_caco3_calcite`, `drg_caco3_decomposition`)

USGS Bulletin 2131 (TI-002: DfG -1128.5 ±1.4 kJ mol^-1; TI-010: DrG 131.0 ±1.7) against USGS OFR 83-79
(TI-056: -1130.61; TI-051: DrG 132.63 ±0.81). The 1.6 kJ mol^-1 difference in DrG comes from the
calcite formation values and is about the combined 2 sigma; the 1 atm against 1 bar standard state
accounts for only about 0.03 kJ mol^-1. Not a conflict beyond uncertainty, recorded because W5's CO2
reference benchmark uses this number.
## 14. Calcite molar volume (`v_m_calcite`)

TF-008 (36.829 cm^3 mol^-1, neutron refinement of biogenic otolith calcite) lies 0.3 percent below
TF-001 and TC-048 (36.934, 36.91; X-ray, synthetic or geological calcite), outside their stated
uncertainties. Substitution in biogenic calcite (Mg, Sr) changes the cell; the prior spans both.
## 15. Catechol pKa2 (`pka2_catechol`)

TM-002 (11.70, +0.28/-0.36, potentiometry, I = 0.1 M KCl), TM-004 (12.03, potentiometry) and TM-006
(11.92, spectrophotometry; both I = 0.10) against TM-008 (13.26 +- 0.01, NMR-pH titration, I = 0.15 M
KCl). The glass-electrode values near pH 12 carry the alkaline error of the electrode and the
oxidation of catechol in air at high pH, both of which bias the apparent constant; NMR titration under
controlled conditions avoids them. The 1.5-unit spread matters at the top of the slurry pH range, where
it decides whether the catecholate is a monoanion or a dianion.

**Resolution.** U1 over 10.98 to 13.28 with the ionic-strength flag; TF-022 (13.07, I not stated) is a
comparator.

## 16. Slurry pH (`ph_slurry`, regime key)

Unmodified dispersions and slurries of layered oxides span 10.5 (LiCoO2, TA-002; NMC111 with lignin,
TA-012) to 13.0 (NCA, TJ-098). The pH rises with nickel content (NCM111 11.4 to 11.9, NCM622 12.5, NCM811
12.8, NCA 13.0 in one paper, TJ-094 to TJ-098), because surface Li2CO3 and LiOH and lithium leached from
the lattice grow with nickel content and storage time; binders such as lignin buffer it lower.

**Resolution (cp3 ruling R8).** U1 over unmodified slurries (10 to 13) is primary; slurries with pH
modifiers (`ph_slurry_modified`, 6.3 to 12.1) are a labelled sensitivity.

## 17. Potential of aluminium vs SHE in alkaline media (`e_she_slurry`, regime key)

Mixed (Tafel) potentials of Al in 1 M and 4 M NaOH (TJ-023, TJ-024; about -1.46 to -1.34 V vs SHE)
against a near-neutral glycol coolant at pH 8.8 (TJ-025, -0.48 V). The potential of oxide-covered
aluminium rises as the oxide passivates at lower pH and the hydrogen-evolution couple moves with pH;
the slurry pH lies between the conditions. No potential of Al in a cathode slurry was found.

**Resolution.** U1 over the bracket; the absence of a slurry measurement is a gap stated in the key.

## 18. Slurry ionic strength (`ionic_strength_slurry`, regime key)

TA-021 (0.042 mol/kg, NCM washing solution, 1 h) and TJ-104 (0.033, NCM111, 2 h) against TJ-105 (0.23,
NCA, one week). Lithium leaching grows with nickel content and with contact time, so the ionic strength
rises by a factor of about seven between the conditions.

**Resolution.** U1 (0.033 to 0.23 mol/kg). Its upper part reaches into the validity span of the
activity model (section 25).

## 19. Heterogeneous nucleation prefactor (`j0_het`)

ln J0 from four SAM surfaces in one flow cell (TJ-001 to TJ-004; e^39 to e^52 m^-2 s^-1) and a CNT
prefactor on quartz (TJ-006, 2.1e14 m^-2 s^-1): eight decades. The prefactor of a CNT fit absorbs the
attachment kinetics and the site density of each surface, and fits with few points trade it against the
interfacial energy (group `cnt_fit`).

**Resolution.** L1 (log-uniform over the span), as only ln J0 enters the barrier criterion.

## 20. Fluorine-free aluminium oxidation onset (`al_onset_ffree`)

TJ-031 (3.5 V vs Li+/Li, 1 M LiClO4 in PC) against TB-060 (4.25 V, 1 M LiBOB in EC:DMC) and TI-065 (no
attack at 4.2 V for 30 h, LiBOB in a sulfone at 60 C). Perchlorate does not passivate aluminium, so its
pits start low; the bis(oxalato)borate forms a passivating film. The onset is a property of the salt and
solvent, not one number.

**Resolution.** U1 (3.5 to 4.25 V), recorded as a quantity beside the regime range, not as a bound.

## 21. Charge cut-off within a cathode class (`e_cell_max_*`, design axis `e_cell_max`)

Within LiCoO2, conventional protocols (TJ-041, 4.2 V; TK-049, 4.3 V) differ from high-voltage protocols
(TK-044, TK-047, 4.6 V; TJ-042, above 4.6 V); within layered NMC and NCA, 4.25 to 4.5 V (NMC111 is cycled
to 4.5 V in TK-055); LiFePO4 is cut off at 3.6 to 4.2 V. The cut-off is a protocol choice made per study
and per cathode, not a material constant, and the differences between classes are larger still (up to
5.0 V for LiNi0.5Mn1.5O4).

**Resolution (cp3 ruling R2).** `e_cell_max` is a design axis keyed to cathode class (G1); each class key
is U1 over its own rows, and C5 R-cell is reported per class.

## 22. Process times, temperatures and solids fraction (`t_proc_slurry`, `t_drying_primary`, `slurry_solids_fraction`)

Slurry contact from 20 min (TJ-076) to a 14-day stored paste (TJ-091); primary drying from ambient
(TJ-050) to 80 C convection (TJ-062, TJ-082); solids from 37 percent (LiFePO4, TJ-089) to 69 percent
(NMC811, TJ-079). These are process setpoints chosen per study, so they disagree by design, not by
error.

**Resolution.** L1 for the contact time (beyond a decade) and U1 for the others.

## 23. Dry surface energies of the oxide and the template (`gamma_o_alumina`, `gamma_p_pda`)

Anodic Al2O3 from 31.4 to 49.1 mJ m^-2 and after hot-water sealing 54.2 to 56.6 (TH-062 to TH-065); PDA
from 43.3 (three liquids, TH-050) to 61.3 (two liquids, TH-055). The pseudo-boehmite sublayer and the
porosity change the oxide's polar component, and the probe-liquid set changes the split between
dispersive and polar parts for both.

**Resolution.** U1 for both; they set the ignorance bounds of gamma_sn, gamma_ow and gamma_op.

## 24. Dry surface energy of calcite (`gamma_nv_calcite`)

{10-14} values against vacuum: DFT 0.50 to 0.57 J m^-2 at 0 K (TL-001, TL-016, TL-017), force fields
0.53 and 0.59 (TL-009, TL-008), 0.464 +- 0.018 at 300 K with an estimated vibrational term (TL-018), and
two MD values 0.52 and 0.86 (TL-020, TL-019). The MD values neglect entropy and their potentials differ,
which its compilers note. No experiment gives this free energy: an equation-of-state estimate from contact
angles (TL-023, 0.218) is judged unrealistic by its own authors, inverse gas chromatography gives only
the dispersive part (TL-025 to TL-030), and water spreading on fresh cleavage gives a lower bound above
0.072 (TL-027), consistent with every computed value.

**Resolution.** U1 over the admitted computed values; the experimental rows are comparators. For ACC no
value exists (TL-031); the calcite span is the flagged analog `gamma_nv_acc_calcite_analog`.

## 25. Activity-model constants (`davies_b`, `davies_i_val`, `debye_huckel_a`)

The Davies coefficient is 0.3 in the geochemical codes (TL-047, TL-048) and 0.2 in Davies' original form
(TL-049). The stated validity reaches 0.1 mol/kg with about 2 percent accuracy in Davies' account (TL-050)
and 0.5 mol/kg in a later textbook (TL-051). The A constant differs by 0.3 percent at 25 C between a
dielectric-constant evaluation (TL-038, TL-044) and a code database (TL-046), and rises with temperature
over the slurry span.

**Resolution.** U1 for each. The upper part of the slurry ionic strength (section 18) exceeds the lower
validity bound, so draws there are refused when I_val is drawn low (contract v3).

## 26. Water content of ACC (`acc_hydration_n`)

Synthetic Mg-free ACC from 1.13 to 1.58 water per CaCO3 in one paper's samples (TL-053 to TL-057), 1.1
(TL-059) and 0.98 (TL-062). The water content depends on the synthesis route, washing and drying of each
sample; biogenic ACC (0.25, TL-058) and heated ACC (0.5, TL-060) hold less.

**Resolution.** U1 over the synthetic Mg-free values (0.98 to 1.6).

## 27. Polydopamine film thickness (`template_layer_thickness`)

2 nm without aeration (TL-077) to 40 to 50 nm with aeration or long deposition (TL-080, TL-081). The
oxidative polymerisation rate depends on the oxygen supply and on time, so thickness is a process
outcome.

**Resolution.** L1 (2 to 50 nm).

## 28. Ca2+ site density against its geometric bound (`gamma_s_site_density`, `gamma_s_geometric_bound_analog`)

The sourced site density of COOH monolayers (2.6e-6 to 1.3e-5 mol m^-2) lies inside the geometric bound
rho_L d_layer computed with the analog group density (2.2e-6 to 1.3e-4 mol m^-2) for films thicker than
about 7 to 12 nm (depending on the analog density), but exceeds it for the thinnest films (2 nm). The bound also lacks its footprint term, because
no site footprint area was found (`site_footprint_area`). This is the check that theory/ignorance_priors.md
section 4 asks W1 to make; the violation is flagged, not resolved.

**Resolution.** Flag only: the site density is a monolayer value, the bound an analog for polydopamine;
draws with Gamma_s above rho_L d_layer should be refused by the screen if the analog is used.

## 29. Li2CO3 oxidation: electrochemical against chemical routes (`li2co3_oxidation_onset`)

Both sources measure CO2 and O2 from Li2CO3 starting near 3.8 to 3.9 V vs Li+/Li by gas analysis
(TK-059, TK-062, TI-061), close to the equilibrium potential they print (3.82 V, TK-058, TK-061). In LiPF6
EC/EMC, however, CO2 above 4.3 V comes from a chemical route even when Li2CO3 is separated from the
electrode (TK-064, contrary), and a proton-mediated route gives about 3.5 V (TI-063, grade D). The
electrolyte decides whether the observed carbonate loss is electrochemical.

**Resolution.** U1 over the gas-analysis onsets in fluorine-free glyme electrolytes (3.8 to 3.9 V); the
chemical-route rows are comparators. The equilibrium potential is its own key.

## 30. Analog bound on the entropy of Ca(ClO4)2 (`s_ca_clo4_2_analog_low`, `s_ca_clo4_2_analog_high`)

No table gives S of anhydrous Ca(ClO4)2. The anion-exchange analogs S(CaX2) + 2 [S(MClO4) - S(MX)] give
229 to 265 J K^-1 mol^-1 across X = Cl, NO3 and M = Li, Na, K: the increment from nitrate to perchlorate
is smaller for K than for Li, so the increments are not transferable between cations to better than about
36 J K^-1 mol^-1. The lithium perchlorate entropy itself is an estimate (TK-029). Within one anion the
alkaline-earth entropies rise Mg < Ca < Sr < Ba (TK-014 to TK-021), and the tetrahydrate (TK-023)
lies far above the bound, both as the analog requires.

**Resolution.** The spread is the bound (D1, flagged analog); it enters `exchange_entropy_bound` and the
margin `window_margin_expt` (cp3 ruling R2).

## 31. Hydration free energy of Ca2+ on two proton scales (`dg_hyd_ca_marcus`, `dg_hyd_ca_tissandier`, `hydration_free_energy_ca`)

-1505 kJ mol^-1 (Marcus scale; TD-054, TK-002) against -1602 (cluster-pair scale; TF-051): about 97 kJ
mol^-1 apart. The two scales fix the single-ion split with different proton hydration energies (TF-051
states its proton reference), and for a dication the shift is doubled. Not a disagreement about Ca2+ but
a convention.

**Resolution.** Separate keys; any use states its proton scale. The relative quantity
Delta_G(Ca2+) - 2 Delta_G(Li+) is free of the convention when both ions are on one scale, as in
`solvation_ca_vs_li_water_analog`.

## 32. Water wetting of aluminium oxide (`gamma_ow_ignorance`)

Water contact angles on alumina run from 0 (UV-cleaned sapphire, TM-040; simulated hydroxylated
surfaces, TH-061) to 80 and 90 degrees (as-received or aged surfaces, TM-043, TM-046, contrary).
Adventitious carbon and surface hydroxylation decide the angle; air-formed native oxide on foil is not
the clean hydroxylated surface of the simulations.

**Resolution.** The weaker ignorance bound gamma_ow <= gamma_o + gamma_w is kept (I1); the complete-wetting
bound would assume the clean case.

## 33. Wet adhesion of catechol films on oxides (`w_adh_wet_catechol_oxide_analog`)

0.1 to 15 mJ m^-2: mussel-protein films on mica and silica (TD-025 to TD-028, TM-034 to TM-036), a
catecholic surfactant on silica and copper oxide (TM-038, TM-039), and a compiled range (TD-030). Adhesion
falls when pH oxidises DOPA to quinone (TM-035, contrary) and depends on contact time and the substrate's
hydroxyls.

**Resolution.** L1 over the span, as a flagged analog of the C1 work (A1), run beside the C1 route.

## 34. Bond length of carbonate in ACC (`c_o_bond_length_acc`)

1.32 Angstrom from a structure model fitted to scattering data of Mg-ACC (TM-032) against about 1.27
Angstrom from the first pair-distribution peak (TM-033), and 1.281 in calcite (TM-030). A fitted model
can move the C-O distance to compensate for disorder, which a first-peak reading does not.

**Resolution.** U1 (1.27 to 1.32 Angstrom); the calcite value is its own key.

## Notes that are not conflicts

- **Formation energies of calcite** (section 13): within the combined uncertainty.
- **CaCO3 window margin from e_form.** `window_margin` uses the per-atom mean absolute error of corrected
  formation energies. W5's benchmark (gas_reference.md, B3) finds the Materials Project calcite energy
  75.5 kJ mol^-1 below experiment, which is about three times the per-atom error for its five atoms; the
  carbonate anion has no fitted correction. That is a computed comparison, not a row, and is recorded for
  the scheme ruling rather than as a conflict between sources.
- **LiClO4 formation enthalpy** (`dfh_liclo4`): JANAF and NBS agree within the JANAF uncertainty.
- **Debye-Hueckel A**: a temperature span, not a disagreement (section 25).

## Machine-readable block

```conflicts
- title: Calcite-water interfacial free energy
  keys: [gamma_nl_calcite]
  rows: [TC-010, TC-011, TC-012, TC-013, TC-015, TC-008, TC-009]
  reason: Nucleation fits give an effective energy of a small, possibly non-crystalline nucleus averaged over facets; molecular dynamics and cracking give planar facet energies; facets differ; contact-angle routes depend on probe liquids and contamination.
  resolution: Uniform over the union of the sourced intervals (U1); no source is preferred.
- title: ACC-water interfacial free energy
  keys: [gamma_nl_acc]
  rows: [TC-024, TC-025, TG-018]
  reason: The much larger value comes from size-dependent solubility of nanoparticles, which also carries hydration and composition changes with size; it is read from an abstract only.
  resolution: Uniform over the admitted fit and simulation (U1); the abstract-only value is a named comparator (E5).
- title: ACC solubility and the ACC offset
  keys: [log10_ksp_acc, acc_offset]
  rows: [TG-001, TG-002, TG-003, TG-004, TC-037, TC-041, TG-007, TC-040]
  reason: Polyamorphism; proto-calcite and proto-vaterite ACC formed at low supersaturation are less soluble than ACC precipitated fast for dissolution experiments; stabilisers in earlier work.
  resolution: Uniform over all polyamorphs (U1); the ACC framing covers more than one ACC and the offset inherits the span.
- title: ACC density and molar volume
  keys: [v_m_acc, rho_acc]
  rows: [TG-013, TG-014, TC-054, TC-055, TM-027, TM-028, TM-029]
  reason: Pycnometry of dried ACC measures the phase with its structural water; scattering of wet colloids includes interparticle water and porosity; magnesium-stabilised, biogenic and simulated ACC differ in composition.
  resolution: Uniform over the two hydration states measured by pycnometry (U1); the other values are comparators.
- title: Template-water interfacial free energy
  keys: [gamma_sl0_template, gamma_sl0_template_untruncated]
  rows: [TH-049, TH-052, TH-054, TH-056]
  reason: The sign follows the surface-energy model; the van Oss acid-base term can turn negative for a strongly hydrophilic film, the Owens-Wendt form cannot; a negative value would mean unbounded swelling.
  resolution: Cut at zero by the ruling (T1); the uncut span is a labelled sensitivity.
- title: Calcium-catecholate binding constant
  keys: [log10_k_ca_catecholate]
  rows: [TD-048, TD-049]
  reason: Ionic strength and sodium competition change the apparent constant; the same paper reports non-monotonic values at higher salt.
  resolution: Single source widened to the method error and flagged (W1).
- title: Calcium-carboxylate binding
  keys: [log10_k_ca_carboxylate, dg_bind_ca_acetate, dg_bind_ca_cooh_monolayer]
  rows: [TF-019, TF-018, TD-051, TH-026, TH-029, TH-033, TH-034, TH-035]
  reason: Denticity and polyelectrolyte cooperativity in solution; for monolayers, the potential-of-mean-force method and its reference state.
  resolution: Uniform for solution constants (U1), log-uniform for monolayers (L1); the acetate free energy is widened as a single source (W1).
- title: Calcite binding to templates against the effective barrier energy
  keys: [dg_bind_calcite_template, gamma_eff_het_organic]
  rows: [TC-061, TC-066, TH-001, TH-004, TH-014, TH-022, TH-024, TC-079]
  reason: Crystal binding to the template lowers the effective energy, while strong single-ion binding by a hydrated film raises the cost of displacing water and can raise it.
  resolution: Recorded as evidence for the sign of the Gibbs term, not as a prior; the binding key is a flagged single source.
- title: Effective interfacial energies on organic templates
  keys: [gamma_eff_het_organic]
  rows: [TC-057, TC-072, TH-008, TH-009, TH-010, TH-011]
  reason: Optical-rate fits on nucleating monolayers against force-spectroscopy conversions for less nucleating amine and mixed monolayers at lower pH, which assume the cap geometry.
  resolution: Uniform over organic templates (U1); mineral substrates are comparators.
- title: Catechol first dissociation constant
  keys: [pka_catechol]
  rows: [TM-001, TM-003, TM-005, TM-007, TM-009, TM-010, TM-013, TM-017, TF-021]
  reason: Ionic strength, method and temperature differ between measurements; the low buffer value has no stated ionic strength.
  resolution: Uniform over catechol itself at stated ionic strength (U1) with the ionic-strength flag; values without stated ionic strength are comparators.
- title: Catechol second dissociation constant
  keys: [pka2_catechol]
  rows: [TM-002, TM-004, TM-006, TM-008]
  reason: Glass-electrode titrations near the top of the pH scale carry the alkaline error and the air oxidation of catechol; nuclear magnetic resonance titration avoids both.
  resolution: Uniform over the measurements at stated ionic strength (U1) with the ionic-strength flag.
- title: Carboxyl dissociation constant
  keys: [pka_carboxyl]
  rows: [TF-026, TF-027, TF-028, TF-029]
  reason: Charge accumulation on a polyelectrolyte shifts the apparent constant above that of monomeric acids; a surface layer is expected to shift similarly.
  resolution: Uniform from monomer to polymer (U1).
- title: Slurry dissolved inorganic carbon
  keys: [dic_slurry]
  rows: [TA-019, TF-032]
  reason: Nickel content, storage history of the powder and atmosphere of the wash; both are washing solutions, not slurries.
  resolution: Uniform over both (U1).
- title: Calcite molar volume
  keys: [v_m_calcite]
  rows: [TF-008, TF-001, TC-048]
  reason: Substitution of magnesium and strontium in biogenic calcite changes the cell.
  resolution: Uniform over both kinds of calcite (U1).
- title: Slurry pH
  keys: [ph_slurry, ph_slurry_modified]
  rows: [TA-002, TA-012, TJ-094, TJ-097, TJ-098]
  reason: Surface lithium compounds and lattice lithium leaching grow with nickel content and storage; cobalt-rich and lignin-bound slurries sit lower.
  resolution: Unmodified slurries are primary (U1, ruling R8); slurries with pH modifiers are a labelled sensitivity.
- title: Potential of aluminium against SHE in alkaline media
  keys: [e_she_slurry]
  rows: [TJ-023, TJ-024, TJ-025]
  reason: Mixed potentials measured in sodium hydroxide and in a near-neutral coolant bracket the slurry pH; passivation and the hydrogen couple move with pH; no slurry measurement exists.
  resolution: Uniform over the bracket (U1); the missing slurry measurement is stated as a gap.
- title: Slurry ionic strength
  keys: [ionic_strength_slurry]
  rows: [TA-021, TJ-104, TJ-105]
  reason: Lithium leaching grows with nickel content and contact time.
  resolution: Uniform over the span (U1).
- title: Heterogeneous nucleation prefactor
  keys: [j0_het]
  rows: [TJ-001, TJ-004, TJ-006]
  reason: The prefactor of a classical fit absorbs attachment kinetics and site density of each surface and trades off against the interfacial energy.
  resolution: Log-uniform over the span (L1), as only its logarithm enters.
- title: Fluorine-free aluminium oxidation onset
  keys: [al_onset_ffree]
  rows: [TJ-031, TB-060, TI-065]
  reason: Perchlorate does not passivate aluminium while the bis(oxalato)borate forms a passivating film; solvent and temperature differ.
  resolution: Uniform over the span (U1), recorded beside the regime range and not as a bound.
- title: Charge cut-off within a cathode class
  keys: [e_cell_max]
  rows: [TJ-041, TK-044, TK-047, TK-049, TK-055, TJ-038, TK-041]
  reason: The cut-off is a protocol choice per study and per cathode; conventional and high-voltage protocols differ within a class, and classes differ more.
  resolution: Design axis keyed to cathode class (G1, ruling R2); uniform over each class's rows.
- title: Process times, temperatures and solids fraction
  keys: [t_proc_slurry, t_drying_primary, slurry_solids_fraction]
  rows: [TJ-076, TJ-091, TJ-050, TJ-062, TJ-089, TJ-079]
  reason: Process setpoints chosen per study, which differ by design rather than by error.
  resolution: Log-uniform for the contact time (L1) and uniform for the others (U1).
- title: Dry surface energies of the anodic oxide and polydopamine
  keys: [gamma_o_alumina, gamma_p_pda]
  rows: [TH-062, TH-063, TH-064, TH-065, TH-050, TH-053, TH-055, TH-057]
  reason: The sealing sublayer and porosity change the polar component of the oxide; the probe-liquid set changes the dispersive and polar split for both.
  resolution: Uniform for both (U1); they set the ignorance bounds of the contact energies.
- title: Dry surface energy of calcite
  keys: [gamma_nv_calcite, gamma_nv_acc_calcite_analog]
  rows: [TL-001, TL-008, TL-009, TL-016, TL-017, TL-018, TL-019, TL-020, TL-023, TL-027]
  reason: Every admitted value is computed; molecular dynamics values neglect entropy and their potentials differ; no experiment measures the free energy against vacuum, and the contact-angle estimate is judged unrealistic by its authors.
  resolution: Uniform over the computed values (U1); for ACC the calcite span is a flagged analog (A1).
- title: Activity-model constants
  keys: [davies_b, davies_i_val, debye_huckel_a]
  rows: [TL-047, TL-048, TL-049, TL-050, TL-051, TL-038, TL-046]
  reason: Geochemical codes and the original Davies form use different linear coefficients; stated validity differs between the original and later accounts; the limiting slope rises with temperature.
  resolution: Uniform for each (U1); draws beyond the drawn validity bound are refused.
- title: Water content of ACC
  keys: [acc_hydration_n]
  rows: [TL-053, TL-054, TL-057, TL-059, TL-062]
  reason: Synthesis route, washing and drying of each sample set the structural water.
  resolution: Uniform over the synthetic magnesium-free values (U1).
- title: Polydopamine film thickness
  keys: [template_layer_thickness]
  rows: [TL-077, TL-080, TL-081]
  reason: Oxidative polymerisation depends on oxygen supply and deposition time.
  resolution: Log-uniform over the span (L1).
- title: Binding-site density against its geometric bound
  keys: [gamma_s_site_density, gamma_s_geometric_bound_analog]
  rows: [TC-067, TF-036, TL-072, TL-076, TL-077]
  reason: The monolayer site density exceeds the bound computed with the analog group density for the thinnest films; the footprint term of the bound is missing.
  resolution: Flagged, not resolved; the screen refuses draws above the bound when the analog is used.
- title: Lithium carbonate oxidation, electrochemical against chemical routes
  keys: [li2co3_oxidation_onset, li2co3_oxidation_equilibrium_potential]
  rows: [TK-059, TK-062, TI-061, TK-064, TI-063]
  reason: In fluorine-free glyme electrolytes gas evolution starts near the printed equilibrium potential; in hexafluorophosphate carbonate electrolytes carbon dioxide also comes from chemical routes.
  resolution: Uniform over the gas-analysis onsets (U1); chemical-route rows are comparators.
- title: Analog bound on the entropy of calcium perchlorate
  keys: [s_ca_clo4_2_analog_low, s_ca_clo4_2_analog_high, exchange_entropy_bound]
  rows: [TK-012, TK-015, TK-027, TK-028, TK-029, TK-065, TK-068, TK-070, TK-023]
  reason: Anion-exchange increments taken from different alkali cations are not transferable; the lithium perchlorate entropy is itself an estimate.
  resolution: The spread over the analogs is the bound (D1, flagged analog), carried into the experimental-route margin (ruling R2).
- title: Hydration free energy of calcium on two proton scales
  keys: [dg_hyd_ca_marcus, dg_hyd_ca_tissandier]
  rows: [TD-054, TF-051, TK-002]
  reason: The two scales assume different proton hydration energies; the difference is a convention, not a measurement disagreement.
  resolution: Separate keys with the scale stated; relative quantities take both ions from one scale.
- title: Water wetting of aluminium oxide
  keys: [gamma_ow_ignorance]
  rows: [TM-040, TH-061, TM-043, TM-046]
  reason: Adventitious carbon and the state of hydroxylation decide the contact angle; aged native oxide is not the clean hydroxylated surface.
  resolution: The weaker ignorance bound is kept (I1).
- title: Wet adhesion of catechol films on oxides
  keys: [w_adh_wet_catechol_oxide_analog]
  rows: [TD-025, TD-030, TM-034, TM-035, TM-038, TM-039]
  reason: Oxidation of catechol to quinone, contact time and the substrate's hydroxyls change adhesion; no film was measured on aluminium oxide.
  resolution: Log-uniform over the span (L1) as a flagged analog of the anchoring work (A1).
- title: Carbonate bond length in ACC
  keys: [c_o_bond_length_acc]
  rows: [TM-032, TM-033]
  reason: A fitted structure model can move the bond length to absorb disorder, which a first-peak reading does not.
  resolution: Uniform over both (U1); calcite is a separate key.
```
