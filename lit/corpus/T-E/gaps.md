# T-E gaps

Thread T-E (methods and benchmarks). 88 rows (TE-001..TE-088). Routes: `fulltext` via Unpaywall/OpenAlex/Europe PMC/arXiv, `abstract` for paywalled works, `search` (arxiv, europepmc, crossref; openalex and semanticscholar searches hung or returned 0 hits), three logged web searches to locate copies. Target quantities owned by T-E: `benchmark_error` (non-target slug, 18 rows, 12 DOIs); T-E also contributed one row to the target `hydration_free_energy_ca` (TE-064, a secondary citation, grade C).

## 1. CNT limits at the nm scale, f(theta), line tension, PNC critiques
- Searched: arxiv "Tolman length curvature dependence...", "line tension heterogeneous nucleation contact angle", "capillarity approximation classical nucleation theory failure small clusters", "prenucleation clusters calcium carbonate nonclassical nucleation"; europepmc "prenucleation clusters calcium carbonate classical nucleation theory"; direct DOIs for Tolman 1949, Fletcher 1958, Auer and Frenkel 2003, Gebauer 2008/2014, Smeets 2017, Henzler 2018, Demichelis 2011, Hu 2012, Karthika 2016.
- Found: TE-001..TE-023 (f(theta) Eq. 36 and limits, generalized Young equation with line tension, line-tension barrier term, Tolman equation and its failure, heptane Tolman length, LJ solid-liquid Tolman fit; CaCO3 CNT applicability for and against).
- Missing: Tolman 1949 (10.1063/1.1747247), Fletcher 1958 (10.1063/1.1744540), Auer and Frenkel 2003 (10.1103/physrevlett.91.015703), Gebauer et al. 2008 (10.1126/science.1164271) and Karthika et al. 2016 (10.1021/acs.cgd.6b00794) are paywalled; read at abstract level only (D). The f(theta) formula comes from the Iwamatsu arXiv preprint and not from Fletcher's original. No numeric Tolman length for a CaCO3 or other mineral-water interface was found. No measured line tension for a mineral nucleus on an oxide was found.

## 2. Variance-based GSA (Sobol, Saltelli, Jansen)
- Searched: direct DOIs for Saltelli 2002, Saltelli et al. 2010, Jansen 1999, Sobol 2001, Archer et al. 1997, SALib (JOSS); arXiv 2009.01147 (Puy et al.), 1404.2405 (Iooss and Lemaitre), 1303.6451 (Janon et al.), 1703.05799 (Saltelli et al. 2017); one web search for a copy of Saltelli 2010.
- Found: TE-024..TE-035 (n(k+2) theorem, n(k+1) first order, Jansen total-order estimator, recommended N_t/k, the 10^4-calls rule of thumb, bootstrap and asymptotic CIs).
- Missing: Saltelli et al. 2010 (10.1016/j.cpc.2009.09.018), Jansen 1999 (10.1016/s0010-4655(98)00154-4) and Sobol 2001 (10.1016/s0378-4754(00)00270-6): paywalled, no abstract returned. Their estimator equations are in the rows only as restated by Saltelli et al. 2017 and Puy et al. (grade C for the formula rows). SALib JOSS (10.21105/joss.00097): no copy could be retrieved. TE-032 (10^4 calls) is derived because the superscript was lost in extraction.

## 3. Pourbaix construction and metastable or amorphous offsets
- Searched: direct DOIs for Persson et al. 2012, Singh et al. 2017, Patel et al. 2019, Aykol et al. 2018, Sun et al. 2016.
- Found: TE-036..TE-045 (ion-reference scheme, about 0.1 eV/atom metastability window, oxide amorphous limits 0.05-0.5 eV/atom, sampling error, 24 meV/atom DFT error, heuristic E_hull cutoffs, metastability medians).
- Missing: Persson 2012 (10.1103/physrevb.85.235438) and Singh 2017 (10.1021/acs.chemmater.7b03980) are paywalled; the abstracts give no correction offsets or Delta G_pbx thresholds. The Al2O3 and CaCO3 amorphous limits sit in Aykol table S1, which was not retrieved. No Materials Project aqueous-ion correction values for Ca2+ or Al species were found in the fetched texts.

## 4. Li-referenced electrochemical stability windows
- Searched: direct DOIs for Ong 2008, Zhu/He/Mo 2015 and 2016, Richards 2016, Xiao 2019; one web search "first-principles electrochemical stability window Al2O3 AlF3 LiAlO2 Li2CO3 coating"; copies of Yu et al. 2019 and Xie et al. 2017 from author pages.
- Found: TE-046..TE-060 (grand-potential method; windows of Li3PS4, LLZO, LiAlO2 from two works, Li5AlO4, LiAl5O8, Li3AlF6, LiAlF4; the 0.005 eV/atom hull tolerance).
- Missing: no window for CaCO3, Al2O3, AlF3 or Li2CO3 was read. The binaries are in Yu et al. Table S1 (SI not retrieved). Richards 2016 Table 1 (10.1021/acs.chemmater.5b04082) and Zhu 2015 (10.1021/acsami.5b07517) are paywalled and their abstracts give no numbers. Ong 2008 (10.1021/cm702327g) is paywalled; abstract only. No collector potential (`incell_potential`) was recorded, by design.

## 5. DFT benchmarks for Ca2+ with O-donor ligands; solvation; hydration
- Searched: openalex/europepmc "benchmark density functional calcium ion ligand binding energies", "calcium carboxylate complexes DFT benchmark CCSD(T)", "alkaline earth metal ion binding benchmark density functional" (the openalex calls hung); crossref "calcium ion hydration number coordination EXAFS", "hydration free energy calcium ion density functional cluster continuum", "calcium binding carboxylate density functional benchmark"; europepmc "calcium hydration shell coordination number ab initio molecular dynamics"; one web search; direct DOIs for SMD, GMTKN55 and MOR41.
- Found: TE-061..TE-074 (functional MUEs 1.40-1.90 kcal/mol against CCSD(T)/CBS for Ca/La exchange with water, acetate, acetamide and imine; SMD ion MUE of 4 kcal/mol; GMTKN55 WTMAD-2; MOR41; Ca(H2O)2+ binding energy; Ca hydration number from SCAN-ML (6.85), from experiment (8, abstract) and the experimental range 6-10).
- Missing: no benchmark of Ca2+-catecholate or Ca2+-ether binding against a high-level reference was found. No implicit-solvent (SMD/COSMO) error specific to Ca2+ complexes was found; the SMD parametrisation does not include Ca. Corral et al. 2003 (10.1021/jp0363491) is paywalled and its abstract has no error numbers. The Mg/Ca carboxylate study (10.1021/acs.jpcb.1c06108) is paywalled and its abstract has no energies. MOR41 (transition metals) is abstract-only. Absolute Ca2+ hydration free energy: only one secondary citation (TE-064), so this target is not covered by T-E.

## 6. xtb and CREST protocols
- Searched: direct DOIs for GFN2-xTB 2019, GFN-FF 2020, CREST 2020, ALPB 2021, xTB review 2021 and CREST 3.0 2024.
- Found: TE-075..TE-088 (GFN2-xTB S30L and conformer MADs, GFN-FF MADs, ALPB/GBSA hydration MADs for neutrals, cations and anions, CREST default E_win 6.0 kcal/mol and its thresholds, 6-10 kcal/mol for entropy).
- Missing: CREST 2020 (10.1039/c9cp06869d) is paywalled and its abstract has no accuracy numbers; the defaults come from CREST 3.0 (2024). The xTB review (10.1002/wcms.1493) is abstract-only. No xTB benchmark specific to Ca2+ complexes was found. The GFN2-xTB text is a preprint version, so locators use preprint pdf pages.

## Tool notes
- OpenAlex and Semantic Scholar search routes hung or returned 0 results; I stopped those calls. Some Wayback fetches took about 7 minutes.
- arXiv full texts are logged with doi `arxiv:<id>`, which the validator does not accept. I re-fetched them with `url --doi 10.48550/arxiv.<id>`, and the rows cite those DOIs.
- Two author-page PDFs were first fetched without a DOI (sources.jsonl entries with doi None) and then re-fetched under their DOIs.
