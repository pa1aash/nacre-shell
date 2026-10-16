# T-D gaps

Routes used: crossref, openalex (worked for the first queries, then hung and was abandoned), europepmc (incl. DOI and PMCID look-ups), pubmed, semanticscholar (one query), arxiv, plus eight logged web searches to locate DOIs or open copies. All queries are in `queries.jsonl`.

## 1. PDA structure (`pda_structure_evidence`, `pda_film_thickness`)
- Searched: Liebscher 2013, Dreyer 2012, Hong 2012, d'Ischia Acc. Chem. Res. 2014, Della Vecchia, "polydopamine eumelanin structure", "non-covalent self-assembly ... polydopamine".
- Found: TD-001 to TD-014 (both sides of the debate: covalent TD-001, TD-008; non-covalent/aggregate TD-002, TD-003, TD-009; mixed/condition-dependent TD-004, TD-005, TD-007, TD-010). Composition number: N/C = 0.10 (TD-006). Thickness: TD-011 to TD-013.
- Missing: Liebscher 2013 (10.1021/la4020288), Dreyer 2012 (10.1021/la204831b), Hong 2012 (10.1002/adfm.201201156), d'Ischia 2014 (10.1021/ar500273y) are paywalled; abstracts only (grade D), so no catechol/quinone/indole ratios or NMR integrals were read. Della Vecchia papers were not located by these queries. Ball et al. 2012 (10.1016/j.jcis.2012.07.030) paywalled: thickness-vs-time data and surface-energy components not read.

## 2. Catechol/PDA adhesion to alumina in water (`w_adh_wet`, owned)
- Searched: Lee/Scherer/Messersmith PNAS 2006, SFA mfp adhesion (Lu 2013, Yu 2011), "mussel adhesive protein adhesion alumina surface forces", "DOPA single molecule force alumina", "catechol adsorption alumina/boehmite/gibbsite", "DFT catechol hydroxylated alumina", web searches for SFA/JKR on sapphire and single-molecule on Al2O3.
- Found: w_adh_wet TD-025 to TD-030, TD-034 (mica and SiO2 only, plus a compiled 3-15 mJ/m2 range and a qualitative contrary row on sapphire); single-molecule forces/energies on TiO2 TD-015 to TD-024; alumina (sapphire) dry O-H interaction energy and derived upper bound TD-031, TD-032; alumina binding modes TD-035 to TD-039 (boehmite, gibbsite, MD on alumina); TD-040 (other oxides).
- Missing: no numeric wet work of adhesion of catechol or PDA on alumina/AlOOH was found; the target is covered only by mica/SiO2 values (grade B for P0 at best). McBride & Wesselink 1988 (10.1021/es00171a014): paywalled and the cached abstract page holds no abstract text; read only through a review (TD-035). Gulley-Stahl 2010 (10.1021/es902040u, no alumina in abstract), Yeh 2015 (10.1021/jp512780s), Yeh 2019 (10.1021/acs.jpcb.9b04473), Simpson 2000 (10.1006/jcis.2000.6999): paywalled, abstract only; no adsorption isotherm constants or adsorption free energies of catechol on alumina were read. No catechol-on-alumina adsorption free energy found in open text.

## 3. Catechol pKa (`pka_catechol`, owned)
- Searched: "protonation constants catechol dopamine L-DOPA potentiometric", "acid dissociation constants catecholamines", "second acid dissociation constant of catechol", computed phenol pKa, web search for catechol pKa1/pKa2.
- Found: TD-042 to TD-047 (dopamine and L-DOPA measured by CZE at I = 0.010 M, 25 °C; compiled dopamine/dopa values). Covered by distinct DOIs, but only for dopamine/DOPA.
- Missing: pKa1 and pKa2 of catechol itself (1,2-dihydroxybenzene) were not found in any open text fetched; Bretti et al. 2013 J. Chem. Eng. Data (dopamine vs I and T) and Bretti 2006 (10.1007/s10953-006-9057-6) paywalled/not fetched. No high-pH (pKa2 near 13) value for catechol read.

## 4. Ca2+ binding (`logk_ca_catecholate` / `dg_bind_ca_catecholate`, `logk_ca_carboxylate` / `dg_bind_ca_carboxylate`, owned)
- Searched: "calcium catechol stability constant", "calcium complexes of catecholamines", Ca-acetate/malonate/succinate/citrate stability constants, Ca-polyacrylate/alginate ITC, Ca-carboxylate free energy simulations (Kohagen/Mason/Jungwirth), web searches for open stability-constant tables.
- Found: Ca2+-dopamine log beta at several I (TD-048, TD-049; single DOI, grade A) and a weak sequestering index at pH 7.4 (TD-050, contrary); Ca2+-maleate log K0 compiled (TD-051); qualitative polymer binding (TD-052, TD-053).
- Missing: second source for Ca-catecholate (single-source). Ca-carboxylate is single-source and compiled only: Daniele et al. 2008 Coord. Chem. Rev. (10.1016/j.ccr.2007.08.005) paywalled with no abstract; Kohagen 2014 (10.1021/jp5005693), Martinek 2018 (10.1063/1.5006779), Kohagen 2015 (10.1021/acs.jpclett.5b00060), Gindele 2022 (10.1021/acs.langmuir.2c01662) not retrievable or abstract silent on K. Martell & Smith, NIST 46 and the Markich & Brown 1999 ANSTO database (no DOI) were not read. No log K for acetate, malonate, succinate, citrate, aspartate, glutamate, polyacrylate or alginate read in fetched text; no computed Ca-catecholate or Ca-carboxylate binding free energy found.

## 5. Ca2+ hydration free energy (`hydration_free_energy_ca`, owned)
- Searched: Marcus 1991, Schmid/Miah/Sapunov 2000, Kelly/Cramer/Truhlar 2006, divalent-ion force-field papers, arXiv quasichemical work.
- Found: TD-054 to TD-057 (Marcus scale, proton reference -1056 kJ/mol, via two Merz-group papers; computed values are fitted to it), TD-058 (CaCl2 pair sum), TD-059 (proton -265.9 kcal/mol, cluster-pair reference).
- Missing: Marcus 1991 (10.1039/ft9918702995), Schmid 2000 (10.1039/a907160a), Kelly 2006 (10.1021/jp063552y) paywalled; abstracts give no Ca2+ value. So no Ca2+ value on the Tissandier/cluster-pair scale and no independent (non-fitted) computed value was read; both target DOIs trace back to Marcus.

## 6. PDA-templated CaCO3, site density, wetting (`site_density_organic`, `gamma_organic_water`, `water_contact_angle_pda`)
- Searched: "polydopamine calcium carbonate mineralization", "dopamine-induced mineralization vaterite", "polydopamine template CaCO3", "catechol calcium carbonate crystallization", Europe PMC open-access phrase queries, "quantification of catechol and amine groups polydopamine", "polydopamine water contact angle".
- Found: retro rows TD-060, TD-061 (vaterite with dopamine, bulk, abstract only), TD-062, TD-063 (calcium phosphate on PDA vs no PDA), pointer TD-065; contact angle TD-064 (single source).
- Missing: Kim & Park Langmuir 2010 (10.1021/la1027509) and Biomaterials 2010 (10.1016/j.biomaterials.2010.05.004) paywalled; no CaCO3 nucleation on a defined PDA-coated planar surface read in full text. No catechol or amine group density (nm^-2 or mmol/g) on PDA found; Lee et al. 2024 (10.1021/acsami.4c08603) paywalled. No PDA-water interfacial energy found; Ball 2012 surface-energy components paywalled.

## 7. PDA on Al foil in cells (`incell_potential`)
- Searched: "polydopamine coated aluminum current collector", "polydopamine aluminum foil lithium battery interlayer", "dopamine treated aluminum current collector", two web searches.
- Found: nothing usable; hits were PDA on Cu collectors, PDA on Al alloys in NaCl, or patents.
- Missing: no paper reporting PDA-coated Al current collectors with onset/breakdown potentials vs Li+/Li was located by these queries.

## Tool notes
- `search --route openalex` hung without returning for several queries (processes killed after minutes); crossref ranking was poor for topical queries; Europe PMC results are date-sorted.
- `url` on the Europe PMC render link of 10.1126/science.1147241 (PMC2601629) returned "not retrieved".
- 10.1248/cpb.27.247 was cached but is an image-only scan (no extractable text).
