# Conflicts between sources (initial, P0-W1.2)

Every input of `lit/params.yaml` whose admitted sources disagree beyond their stated uncertainties, or
whose admitted values differ by more than the sources' own scatter suggests: the sources, the values,
the conditions that differ, and the physical reason where one is apparent. Row ids refer to
`lit/evidence_table.csv`; keys to `lit/params.yaml`. Under the prior rule
(`lit/corpus/params_README.md`, clause U1) every conflict listed here makes the key's prior uniform (or
log-uniform) over the union of the sources' intervals; nothing is resolved by picking a source. P0-W1.3
completes this file on Day 3 (conflicts in the R-slurry and R-cell regime keys added by T-J, and a
ruling proposal for each entry).

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

## 6. Ca2+-catecholate binding (`log10_k_ca_catecholate`)

TD-048 (log beta 4.83 ±0.08 at 0.143 mol dm^-3 NaCl) and TD-049 (3.65 ±0.07 at 0.472 mol dm^-3), one
paper, differ by 1.2 log units, far beyond their uncertainties. The cause is ionic strength (and Na+
competition); the same paper reports non-monotonic values at 0.692 and 0.933 mol dm^-3 (3.95, 5.26).
Tiron (TF-014, TF-015; not admitted) differs by 0.6 log units between NaCl and KCl, which its authors
attribute to Na+ ion pairing. The background electrolyte must be stated with any value used.

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

## 10. Catechol pKa (`pka_catechol`)

TF-021 (catechol pKa1 8.83 ±0.03, spectrophotometric, ionic strength not stated) lies below the compiled
literature range 9.14 to 9.43 (TF-025). For dopamine, TF-024 (8.91) is below TD-042 (9.12 ±0.03 at
I = 0.010 M). The likely cause is the uncontrolled ionic strength of the buffer and the method; the
prior spans 8.77 to 9.43.

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

## Not yet assessed (P0-W1.3)

- Regime keys from thread T-J (slurry pH, potential of Al vs SHE, temperatures and times, R-cell
  potential limits, nucleation prefactors and densities), whose conflicts are added on Day 3.
- Hydration free energy of Ca2+ on the two proton scales (`dg_hyd_ca_marcus`, `dg_hyd_ca_tissandier`):
  not a conflict but a convention; the anchor must state its proton scale.
