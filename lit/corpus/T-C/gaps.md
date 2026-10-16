# T-C gaps

Routes used: openalex (stalled on rate limits mid-session, so most later searches went through crossref), crossref title searches, Europe PMC full-text queries, `fulltext`/`abstract`/`meta`/`url`. No WebSearch was used.

## 1. Nacre formation and ACC as precursor
- Searched: crossref titles (Nassif 2005, DeVol 2015, Weiss 2002, Gong 2012), Europe PMC "amorphous layer aragonite platelets nacre", "ACC precursor aragonite larval shell".
- Found: TC-001 (3-5 nm ACC layer on nacre tablets), TC-002, TC-003, TC-004 (ACC 36% of precursor pixels in forming nacre, CCHH most abundant), TC-005.
- Missing: DeVol 2015 JACS (10.1021/jacs.5b07931) and Weiss 2002 (10.1002/jez.90004) full texts are not open, so abstract only (grade D). Addadi/Raz/Weiner review (10.1002/adma.200390087) and Nudelman nacre-matrix papers are paywalled and were not read.

## 2. ACC-water and calcite-water interfacial free energies (gamma_acc_water, gamma_calcite_water)
- Searched: "calcite water interfacial free energy simulation", Bruno 2013, de Leeuw and Parker 1997, Forbes 2011, Raiteri 2010, Sohnel and Mullin 1982, Europe PMC "amorphous calcium carbonate" AND "interfacial energy" variants.
- gamma_calcite_water found: TC-006 to TC-015, TC-017 to TC-020 (Armstrong 2025 MD 0.205 J/m2; DFT 0.21 J/m2; compiled experimental values 0.055-0.170 J/m2 from nucleation, contact angle, cracking, IGC; Bruno 0.412 J/m2 abstract-only). TC-016 is a calorimetric surface enthalpy (1.48 J/m2), recorded separately.
- gamma_acc_water found: TC-024 (10.2 mJ/m2, CNT re-fit of Sohnel data, grade C) and TC-025 (14-25 mJ/m2, simulation, grade B). Covered, but by only two values and no direct measurement.
- Missing: Sohnel and Mullin 1982 (10.1016/0022-0248(82)90095-1): paywalled, no abstract, so only secondary citations. Forbes 2011 (10.1016/j.gca.2011.09.034), de Leeuw and Parker 1997 (10.1039/a606573b), Raiteri and Gale 2010 (10.1021/ja108508k), Wallace 2013 (10.1126/science.1230915): paywalled with abstracts that give no interfacial energy. Bruno 2013 (10.1021/cg3015817): abstract only. This search found no direct measurement of the ACC-water interfacial free energy.

## 3. ACC excess free energy and solubility (acc_excess_free_energy, ksp_acc)
- Found: calorimetric crystallisation enthalpies TC-026 to TC-029 (Radha 2010: -24, -17, -14.3 kJ/mol and DSC range); free energies TC-030 and TC-031 are grade-C values derived from compiled Ksp values (they share the same original Ksp, so they are not independent); ksp_acc TC-037 to TC-042; ACC solubility varies with mixing rate (TC-114).
- Missing: Brecevic and Nielsen 1989 (10.1016/0022-0248(89)90168-1) and Clarkson 1992 (10.1039/ft9928800243) full texts are paywalled (Clarkson read as abstract, TC-042). Gebauer 2008 (10.1126/science.1164271) and Gebauer 2010 (10.1002/anie.201003220): paywalled, and the abstracts give no Ksp. Kawano 2009 (10.1088/0953-8984/21/42/425102): no retrievable copy, and the abstract has no numbers. This search found no direct measurement of the ACC-calcite free energy difference (only enthalpies, or values derived from Ksp).

## 4. Ksp of calcite, aragonite, vaterite, ACC
- Found: ksp_calcite TC-033 to TC-036 (including 12 and 31 C); ksp_vaterite TC-043, TC-044; ksp_aragonite TC-045, TC-046; ksp_acc as above.
- Missing: the primary source, Plummer and Busenberg 1982 (10.1016/0016-7037(82)90056-4), is paywalled, and no abstract or temperature equation was retrievable. Every calcite, aragonite and vaterite row is therefore a compilation (grade C). The two aragonite rows come from weak tertiary sources. Mucci 1983 (10.2475/ajs.283.7.780) was fetched, but it is a scanned PDF with no text layer, so it was not used.

## 5. Molar volumes and densities
- Found: calcite density 2.711 g/cm3 from NBS lattice constants (TC-047) plus derived Vm 36.91 cm3/mol (TC-048); molecular volume 6.13e-23 cm3 (TC-049); aragonite density, cell and derived Vm 34.12 cm3/mol (TC-050 to TC-052, Dickens 1970 NBS report); ACC density 1.62 g/cm3 (TC-054 abstract-only, TC-055 secondary, possibly the same original); dense-liquid hydration 4-7 H2O (TC-056).
- Missing: molar_volume_acc (no ACC water content was found alongside a density, so it was not converted); vaterite density or cell (Kabalah-Amitai 2013, 10.1126/science.1232139, paywalled); Effenberger 1981 (10.1524/zkri.1981.156.14.233) and Antao 2009 (10.3749/canmin.47.5.1245) paywalled.

## 6. Heterogeneous nucleation (gamma_eff_het, gamma_sub_nuc, contact_angle_caco3, gamma_organic_water, site_density_organic)
- gamma_eff_het found (27 rows): COOH, SH, PO4 and NH2 SAMs (Hu 2012, Hamm 2014, Nielsen 2020), chitosan and derivatives and compiled Giuffre polysaccharides (Knight 2024), quartz and mica (Jun group, Koishi 2019).
- gamma_sub_nuc: no rows. None of the read works separates the crystal-substrate energy. Hu 2012 SI (TC-095) states that absolute film-solution energies cannot be obtained from MD. Calcite-SAM binding free energies (TC-066, TC-074) are the nearest proxy.
- contact_angle_caco3: only TC-088 (<90 deg, quartz, compiled). TC-093 is an assumed model input, recorded under a separate slug. No measured contact angle of CaCO3 nuclei on organic surfaces was found.
- gamma_organic_water (carboxyl surface-water): gap. The COSMO-RS gamma_sl values are in Nielsen 2020 SI Table S5, but the SI PDF could not be retrieved (the `url` attempt failed). Bain 1989 (10.1021/ja00183a049) is abstract-only with no value. Techane 2011 (10.1021/jp201213g) gives no surface energy.
- site_density_organic: TC-067 (4 nm^-2, derived from the area per molecule) and TC-075 (0.2-0.6 nm2 assumed range). This search found no measured carboxyl density on PDA or chitosan.
- Also missing: Fernandez-Martinez 2012 (10.1021/es3014826), Li 2014 (10.1021/es405141j) and Li 2019 (10.1021/acs.jpcc.9b00378) are paywalled, so they are grade D from abstracts. Hu 2011 MRS (10.1557/opl.2011.1399) is paywalled with no abstract.

## 7. Polypeptide- and chitosan-templated mineralisation
- Found retro rows: SAM series including CH3 and N(CH3)3+ negative controls (TC-098, abstract), oriented SAM faces (TC-099), OH SAMs (TC-065, TC-097), bare Au (TC-096), 1:1 COOH/NH2 SAM with no nucleation (TC-071), chitosan films (TC-076 to TC-083), chitin with nacre peptides (TC-105, TC-106), Langmuir monolayers (TC-107, TC-108), polydiacetylene (TC-100, TC-101), peptoid nanosheets (TC-109), pAsp PILP on glass (TC-102), hydroxylated vs fluorinated mica (TC-094).
- Missing: Aizenberg 1999 Nature (10.1038/19047): no abstract or copy. Gower 1998/2000 PILP (10.1016/s0022-0248(98)00002-5, 10.1016/s0022-0248(99)00749-6): paywalled, no abstract. Giuffre 2013 (10.1073/pnas.1222162110): the PMC copy was listed but could not be retrieved, so its values come only via Knight 2024. Sakamoto 2009 chitin/PAA (10.1295/polymj.pj2009024) and He 2009 chitosan/PAA (10.1016/j.jssc.2008.03.022): paywalled, no abstract. This search found no CaCO3 nucleation experiment on a PDA or PDA-chitosan film; the only catechol row is solution-phase dopamine (TC-110).
