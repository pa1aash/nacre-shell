# Contrary-evidence dossier, track p0

Session P0-W2.1 (master-plan trace S13). There is one entry for each argument against a link in the P0 chain. The chain is defined in `charter/claim_register.yaml` (register version 1, S02, under the G0 audit):

- C1 anchoring (W_adh,wet);
- C2 sequestration;
- C3 templated nucleation;
- C4 conformality;
- C5 thermodynamic stability.

The regimes R-slurry and R-cell are defined in `charter/regimes.yaml`. This file depends on both charter files as drafted. If G0 changes a claim or a regime, the "regime" field of the affected entries has to be re-checked.

Every source was located by search in this session. The searches are logged in `lit/novelty.md` under the follow-up queries, tags B1 to B8 and X1 to X2. Nothing is cited from memory.

- **Locators.** "Abstract" means the claim rests on the abstract only, because no open full text could be reached headlessly (`lit/novelty.md`, execution note 8). "Title only" means the record was located but neither the abstract nor the full text could be read. Such a record is listed as a pointer and is credited with nothing beyond its title.
- **Full text.** Copies are local-only and are not committed.
- **Day 2 update (P0-W2.2, 2026-10-17).** Entry B13 (lane note N4) was added. B7 and B10 were upgraded to full text, and the full-text retries for B2 and B9 are recorded. The W1 row cross-reference is filled in.

## Field schema and severity scale

Each entry gives:

- **Sources.** DOI plus locator.
- **Evidence.** What the evidence shows.
- **Condition.** The physical condition under which it applies.
- **Regime.** Whether P0's regimes avoid it: yes, no or partly, with the reason.
- **Placement.** Where the paper must address it: Discussion, Limits or Outlook.
- **Severity.**
  - *Blocking*: the preprint cannot be posted until the text addresses it, because it bears directly on a verdict P0 reports or on the premise of the chain.
  - *Material*: it must be addressed, because it changes how a link's result is read or how confident that result is.
  - *Minor*: a note in Limits or Outlook is enough.

## Entries

### B1. CaCO3 scale is associated with more, not less, corrosion of aluminium alloys (C3, C4, C5; premise)

- **Sources.**
  - 10.1021/acsomega.0c01538: Osorio-Celestino, Hernandez, Solis-Ibarra et al., *ACS Omega* 5, 17304 (2020). Read in full text: Abstract; "Material and Methods", subsections Brine Solution 1 and Calcium Carbonate: Brine 2; "Results and Discussion", subsections "Calcium Scales on Steel and Aluminum Coupons Using Brines 2, 3, and 4" and "Mass Losses and Corrosion Rate Comparison for Aluminum and Steel Alloys"; "Conclusions".
- **Evidence.**
  - The test brines are seawater-based (Brine 1 simulates seawater), with calcium and bicarbonate added. Scale was precipitated by heating to 90 °C, and the final pH was about 7.2.
  - PXRD identified calcite (with gypsum in the sulfate brines).
  - Under these scaling conditions, the corrosion of the aluminium alloys AA2024-T3 and AA3003-H14 increased relative to the non-scaling brine.
  - The scales on the aluminium alloys were porous calcium scales with pitting (2024-T3) and crevice corrosion (3003-H14) beneath them. The non-scaling seawater brine also caused pitting or crevice attack on the Al alloys, but the damage was less severe.
  - **Physical reading.** A discontinuous, porous mineral deposit creates occluded cells (differential aeration and local acidification under the deposit), which concentrate attack. It does not form a barrier.
- **Condition.**
  - Fouling scale precipitated homogeneously in bulk and settling onto the metal.
  - Chloride-rich electrolyte, high temperature, about neutral pH.
  - Long immersion (on the order of hundreds of hours).
  - Engineering Al alloys with intermetallics.
  - No organic template, so the deposit is porous and not coherent.
- **Regime.** Partly. Three differences limit the evidence's reach, and one point is not covered by them.
  - **Temperature, chloride and pH.** R-slurry is room temperature to drying temperature and alkaline, with chloride not part of the design. The bulk Ca2+ and carbonate activities are inputs, pending S12.
  - **The film.** The proposed layer is templated heterogeneous nucleation (C3) of a thin film, not a precipitated fouling scale.
  - **R-cell.** It is non-aqueous.
  - **Not covered.** P0 cannot assume the templated film is coherent. Coherence is exactly what C4 (conformality) tests. The distinction between a porous fouling scale and a coherent templated film is the hypothesis's premise and has to be argued from C3 and C4, not asserted.
- **Placement.** Discussion (the porous-scale versus coherent-film distinction, tied to the C3 and C4 verdicts). Limits (P0 computes no corrosion kinetics, and its thermodynamic result cannot rule out under-deposit attack at film defects).
- **Severity.** Blocking. The paper's premise (a CaCO3 layer on Al) faces direct published evidence that CaCO3 on Al accompanies more corrosion. The text must address it before posting. Wording U9 in `lit/novelty.md` follows from this entry.

### B2. The Pourbaix proxy is thermodynamic only (C5)

- **Sources.**
  - 10.1021/acs.jpcc.3c01727: Zagalskaya, Chaudhary, Alexandrov, *J. Phys. Chem. C* 127, 14587 (2023), abstract.
    - Full-text retry, 2026-10-17. Unpaywall and OpenAlex list no open publisher copy.
    - The public-access repository copy (par.nsf.gov, record 10427497) timed out on every request from this network, so the entry still rests on the abstract.
  - 10.1002/maco.202011977: Barthel, Deiss, *Mater. Corros.* 72, 434 (2020), abstract.
  - 10.5006/0010-9312-26.9.397: Lennox, *Corrosion* 26, 397 (1970), title only ("Limitations on the Use of Pourbaix Diagrams to Predict De-Alloying or Other Corrosion Characteristics").
  - 10.1103/PhysRevB.85.235438: Persson, Waldwick, Lazic et al., *Phys. Rev. B* 85, 235438 (2012), abstract. This is the method used to combine computed solids with experimental aqueous reference states.
- **Evidence.**
  - **Equilibrium framework (2023).** Pourbaix diagrams rest on equilibrium thermodynamics, while corrosion is "an inherently irreversible interfacial process". The paper lists what lies beyond them: potentiodynamic and transient dissolution, interfacial reactions, metastable phases, strain-induced corrosion, and the kinetics of dissolution and phase transformation.
  - **Kinetics (2020).** The diagram's limits are treated alongside electrochemical kinetics, which it cannot represent.
  - **Persson (2012).** The scheme gives equilibrium phase stability and dissolution in water. It does not give rates, morphology or coverage.
  - **Consequence for P0.** A Pourbaix stability field for CaCO3 or Al2O3 says whether a phase can persist at equilibrium for the given (pH, E, activities). It says nothing about:
    - film coverage or porosity (B1);
    - the metastable ACC that actually forms (B5);
    - dissolution rates;
    - the electrode's mixed potential, which is itself kinetic.
- **Condition.** Any use of an aqueous E–pH diagram as a stability verdict. In particular:
  - for metastable or amorphous phases;
  - for thin films, where surface energies shift the bulk equilibria;
  - under non-equilibrium potentials.
  - Aqueous Pourbaix also has no meaning outside water, so it does not apply in R-cell.
- **Regime.** Partly.
  - **R-cell (avoided).** The charter already confines aqueous Pourbaix to R-slurry. R-cell uses a Li-referenced grand-potential window (`charter/regimes.yaml`, `claim_regimes.C5`).
  - **R-slurry (not avoided).** The blindness to morphology, coverage and kinetics is inherent in the proxy.
  - **Pending.** The slurry's open-circuit potential is itself an input that is still pending (S12).
- **Placement.** Discussion (what a C5 "stable" verdict does and does not license). Limits (no kinetics, morphology or coverage; ACC treated as a bulk phase at best).
- **Severity.** Blocking. C5 is a reported verdict, and stating it without these limits would overstate it.

### B3. Catechol binds Ca2+ weakly near neutral pH; carboxylate competes (C2)

- **Sources.**
  - 10.3390/ijms18010014: Klosterman, Bettinger, *Int. J. Mol. Sci.* 18, 14 (2016). Read in full text: section 2, "Results and Discussion".
  - 10.1016/0039-9140(77)80049-0: Ishimutsu (spelling as in the Crossref record), Hirose, Sakurai, *Talanta* 24, 555 (1977), title only. These are the microscopic acid-dissociation constants of DOPA and related catechols, and the fetch target for the constants.
  - 10.1016/s0003-2670(01)85307-1: Westervelt, Frederick, Malcolm, *Anal. Chim. Acta* 138, 237 (1982), title only. The stability constant of the calcium–catechol-4-sulfonate complex in alkaline aqueous media.
- **Evidence.**
  - **pKa.** Klosterman and Bettinger give the catechol deprotonation pKa of dopamine in PDA as about 9 ("pKa~9", section 2). Below that, catechol is largely protonated and its Ca2+ binding is weak.
  - **Carboxylate is preferred.** Citing ion-exchange work on Sepia melanin, they report that Mg2+ and Ca2+ have a greater affinity for carboxylic acid groups than for catechol groups (the converse holds for Fe3+). They also note that quinone-imine and carboxylate groups, with lower pKa than dopamine, may compete with catechols for metal cations (section 2).
  - **Ca2+ oxidises PDA.** Ca2+ in alkaline CaCl2 accelerates the oxidation of PDA films, consuming dopamine units and generating carboxylic acid groups (section 2, ATR-IR).
  - **Physical reading.** In the slurry, the Ca2+ ligands of a PDA template are not fixed. Near pH 7 to 9 the carboxylates, not the catechols, are the likelier binding sites. At higher pH, deprotonation strengthens catechol binding but also speeds the oxidation that converts catechols into carboxylates.
- **Condition.** Aqueous pH below or near the catechol pKa (about 9), with Ca2+ present. Over longer contact times at alkaline pH, the template chemistry itself evolves.
- **Regime.** Partly.
  - **pH range.** R-slurry has pH ≥ 7, with the upper bound pending S12. The weak-binding window lies inside the regime unless the slurry pH is well above 9. The protonation state of catechol is already named as a pH-dependent input of C1 and C2 (`charter/regimes.yaml`, `R-slurry.inputs.pH.rationale`).
  - **Controls.** The deletion register already contains a carboxylate-substituted control (`charter/deletion_register.yaml`, `carboxylate_substituted`), so P0 can test this argument directly.
  - **Not covered.** The time evolution of PDA (catechol → carboxylate) is not modelled.
- **Placement.** Discussion (which groups carry C2; how the carboxylate control is read). Limits (a static template chemistry is assumed).
- **Severity.** Material.
- **Outstanding.** The two title-only constants papers have to be fetched for numeric values, by p0-w1 for the parameter table, since this lane does not own it.

### B4. Polydopamine is not electrochemically inert at cathode potentials (C4, C5 in R-cell)

- **Sources.**
  - 10.1149/ma2017-01/1/68: Liu, Lee, Kim et al., *ECS Meet. Abstr.* MA2017-01, 68 (2017), abstract.
  - 10.1021/acsami.6b06074: Lee, Han, Cho et al., *ACS Appl. Mater. Interfaces* 8, 21366 (2016), abstract.
  - 10.3390/ijms18010014: Klosterman, Bettinger (2016), full text, section 2. Oxidative evolution of PDA.
- **Evidence.**
  - **Redox activity.** PDA is redox-active as an organic cathode material. DFT and cyclic voltammetry show PDA interacting with electrolyte cations and anions over about 2.5 to 4.1 V vs Li (2017).
  - **Oxidation at cathode potentials.** Dopamine added to a carbonate electrolyte is electrochemically oxidised on the cathode during high-voltage operation (up to 4.5 V), forming a PDA-containing surface layer (2016).
  - **Instability in salt solutions.** As-deposited PDA films are non-equilibrium materials that oxidise further in salt solutions (2016).
  - **Physical reading.** In R-cell, the catechol/quinone groups of a PDA template sit inside the cathode's potential window. They will be oxidised to quinones and can be consumed, changing whatever template–mineral interface formed in the slurry.
- **Condition.** The collector interface at anodic potentials of roughly 3 to 4.5 V vs Li during charge, with electrolyte access to the template.
- **Regime.** Partly.
  - **R-slurry.** Avoided: no applied potential.
  - **R-cell.** Not avoided. The anodic potential is the regime's defining input (E ≥ 4 V vs Li+/Li, provisional).
  - **Limitation in the charter.** P0 claims only C4 and C5 in R-cell, and anchor retention in the cell is explicitly not claimed (`charter/regimes.yaml`, `claim_regimes.C1`). The R-cell stability window covers the mineral and the oxide, not the organic template.
- **Placement.** Limits (template stability in the cell is not evaluated). Outlook (an R-cell computation that includes PDA oxidation states).
- **Severity.** Material.

### B5. ACC is short-lived and transforms during processing (C3, C4, C5)

- **Sources.**
  - 10.1039/c0nr00589d: Rodriguez-Blanco, Shaw, Benning, *Nanoscale* 3, 265 (2011), abstract.
  - 10.1021/acs.cgd.6b00630: Tobler, Rodriguez Blanco, Sørensen et al., *Cryst. Growth Des.* 16, 4500 (2016), abstract.
  - 10.1038/ncomms4169: Ihli, Wong, Noel et al., *Nat. Commun.* 5, 3169 (2014). Read in full text: Abstract; "Crystallization of silica-coated ACC particles"; "Discussion".
  - 10.1073/pnas.1009959107: Radha, Forbes, Killian et al., *PNAS* 107, 16438 (2010), abstract.
  - 10.1021/acs.cgd.6b00906: Konrad, Gallien, Gerard et al., *Cryst. Growth Des.* 16, 6310 (2016), abstract.
  - Countervailing: 10.1021/cg301759t (Wang, Xu, *Cryst. Growth Des.* 13, 1937, 2013, abstract).
- **Evidence.**
  - **In solution.** Additive-free ACC dehydrates and crystallises to vaterite and then calcite, in two stages (Rodriguez-Blanco 2011, 7.5 to 25 °C). The second stage is about 10 times slower than the first.
  - **pH.** At pH about 10.5, vaterite and calcite formed in under 2 min. ACC lifetime increased with synthesis pH up to 12.7, and the product then went directly to calcite (Tobler 2016).
  - **Dehydration.** ACC dehydrates before crystallising, both in solution and in air, and loss of the final water fraction triggers crystallisation. At room temperature crystallisation must be started by local dissolution and reprecipitation mediated by surface water, and its rate depends on ambient humidity (Ihli 2014, abstract and Discussion).
  - **Energetics.** Hydrated ACC → less hydrated ACC → anhydrous ACC → vaterite → aragonite → calcite is an energetically downhill sequence. ACC is much more metastable relative to calcite than the crystalline polymorphs are (Radha 2010).
  - **In air.** ACC in air transforms only after a critical level of physisorbed water, about four monolayers, is reached. Calcite, vaterite and aragonite form together, in proportions set by water exposure (Konrad 2016).
  - **Countervailing evidence.** PDA shells stabilised ACC for at least one year in the solid state (Wang and Xu 2013).
  - **Physical reading.** The film P0 nucleates in the slurry is, at best, a metastable ACC. The drying step of R-slurry is exactly the dehydration that the literature links to crystallisation. Crystallisation changes volume and morphology, so a conformal amorphous film may not survive drying as a conformal film.
- **Condition.** Any aqueous ACC without strong stabilisers, on timescales from minutes to hours. Dehydration on drying, and humidity exposure.
- **Regime.** Partly.
  - **Not avoided.** R-slurry explicitly includes "casting and drying" with falling water activity a_w (`charter/regimes.yaml`, `R-slurry.inputs.water_activity`), and C3 treats ACC structural water as a function of a_w.
  - **Mitigation.** Stabilisation by PDA is reported, and alkaline pH lengthens ACC lifetime.
  - **Not covered.** P0 computes no kinetics, so it cannot predict whether ACC survives drying.
- **Placement.** Discussion (C3 and C5 verdicts for ACC versus crystalline polymorphs; the regime's a_w axis). Limits (no transformation kinetics). Outlook (in situ experiments on the ACC-to-crystal transition during drying).
- **Severity.** Material.

### B6. An insulating carbonate film impedes electron transfer to the collector (C4, R-cell)

- **Sources.**
  - 10.1149/2.0451904jes: Pritzl, Bumberger, Wetjen et al., *J. Electrochem. Soc.* 166, A582 (2019), abstract.
  - 10.1016/j.ssc.2025.116092: Mirza, Salih, Abdullah, *Solid State Commun.* 404, 116092 (2025), title only (a DFT study, with the HSE06 functional, of the electronic properties of the CaCO3 polymorphs).
  - 10.1016/j.carbpol.2019.115054: Zhu, Chen, He et al., *Carbohydr. Polym.* 223, 115054 (2019), abstract.
- **Evidence.**
  - **Contact resistance dominates.** In high-voltage LNMO cathodes, the main growth of cathode impedance is a contact resistance between the Al current collector and the cathode electrode, not a surface-film resistance. It develops in the presence of protic species (HF) (Pritzl 2019).
  - **Interface electronic structure.** Chitosan–calcite interfaces were computed to be either conductive or insulating depending on the monomer (Zhu 2019).
  - **CaCO3 as an insulator.** The charter states this as a limitation (`charter/scope_guard.md`, "Stated limitation: insulating film thickness"). No fetched source in this dossier yet gives a band-gap value.
  - **Physical reading.** Any added interphase between the coating and the Al adds series resistance at exactly the interface already known to dominate cathode impedance growth. Conformality cannot be bought with thickness.
- **Condition.** Film thickness beyond the range where electrons tunnel or leak through. Cathodes under cycling, where the collector–electrode contact is already a failure point.
- **Regime.** No. This is inherent to R-cell, and the charter already makes it a stated limitation with a coarse thickness-versus-resistance bound (C4, Phase 7 item 18).
- **Placement.** Limits (as in the scope guard). Discussion (when the C4 item 18 bound is reported).
- **Severity.** Material.
- **Outstanding.** A fetched band-gap value with a locator, for the parameter table (p0-w1), and the full text of Mirza 2025.

### B7. Classical nucleation theory may not describe nanometre nuclei or sub-nanometre templates (C3)

- **Sources.**
  - 10.1126/science.1164271: Gebauer, Völkel, Cölfen, *Science* 322, 1819 (2008), abstract.
  - 10.1126/science.1254051: Nielsen, Aloni, De Yoreo, *Science* 345, 1158 (2014), editor's summary.
  - 10.1126/science.aaa6760: De Yoreo, Gilbert, Sommerdijk et al., *Science* 349, aaa6760 (2015). Read in full text: structured abstract (BACKGROUND, ADVANCES) and the free-energy-landscape discussion with Fig. 4.
  - Countervailing:
    - 10.1039/c2fd20124k: Hu, Nielsen, Freeman et al., *Faraday Discuss.* 159, 509 (2012). Read in full text (2026-10-17): the accepted manuscript in the White Rose repository; page numbers are those of the manuscript PDF.
    - 10.26434/chemrxiv-2024-16j0s: Li, Lin, Tseng et al., ChemRxiv (2024), abstract.
- **Evidence.**
  - **Against CNT.** Dissolved CaCO3 contains stable prenucleation ion clusters even in undersaturated solution, which challenges the classical picture of metastable clusters (Gebauer 2008). Liquid-cell TEM shows direct nucleation from solution coexisting with transformation of ACC into and between crystalline polymorphs (Nielsen 2014). Particle-based pathways "exceed the scope of classical theories, which assume that a new phase appears via monomer-by-monomer addition to an isolated cluster" (De Yoreo 2015, structured abstract).
  - **For CNT, on templates.** On carboxyl-terminated self-assembled monolayers, template-directed calcite nucleation is "described well in purely classical terms through a reduction in the thermodynamic barrier due to decreased interfacial free energy". The cluster-aggregation model "does not provide a universal description" (Hu 2012, abstract, pdf p. 2).
    - **Hu 2012, full text.** The rate data give α = 72 mJ/m2 (MHA, C16) and 81 mJ/m2 (MUA, C11) against 109 mJ/m2 in bulk solution. The mid-range barriers are 19 kT, 27 kT and 105 kT, and nucleation "proceeds as expected from CNT" (pdf p. 9, Section 3).
    - **Simulation agrees.** Crystallisation simulations give interfacial energies of 56 and 102 ± 6 mJ/m2 for the even and odd SAMs (pdf p. 11, Section 4).
    - **What it does not rule out.** The authors cannot rule out nuclei built from pre-critical clusters (pdf p. 14). On the OH-terminated MUO SAM, ACC forms homogeneously and dissolves while calcite nucleates elsewhere (pdf p. 12, Section 5).
    - **Limits of the support.** The classical support is direct only for ionised carboxyl SAMs, and it is the same evidence that retrodiction cases RC06 (`preprint/retrodiction/cases.yaml`) and RX03 rest on. Carbonate nanodroplets near critical size conform to CNT (Li 2024, non-aqueous ethanol and triethylamine system).
  - **Physical reading.** C3's barrier uses Young energies and capillary geometry, which are macroscopic quantities applied to nuclei of a few nanometres on templates with sub-nanometre features. The classical description is contested for bulk CaCO3, but it has direct experimental support for template-directed nucleation on carboxylate surfaces.
- **Condition.**
  - Nuclei of order 1 to a few nm, where interfacial energies become size-dependent and the sharp-interface model breaks down.
  - Template features smaller than the nucleus.
  - Solutions where cluster or dense-liquid pathways compete.
- **Regime.** No. This is inherent to the C3 method. It is partly mitigated by the template-directed CNT evidence (Hu 2012), which is the closest experimental analogue to P0's templated case.
- **Placement.** Discussion (the template-directed CNT evidence as the basis for C3; the barrier as a ranking quantity, not an absolute rate). Limits (size-dependent interfacial energies; non-classical pathways). Outlook (non-classical free-energy calculations).
- **Severity.** Material.

### B8. The structure of polydopamine is uncertain (C1, C2, C3)

- **Sources.**
  - 10.1021/la4020288: Liebscher, Mrówczyński, Scheidt et al., *Langmuir* 29, 10539 (2013), abstract.
  - 10.1002/adfm.201201156: Hong, Na, Choi et al., *Adv. Funct. Mater.* 22, 4711 (2012), abstract.
  - 10.3390/ijms18010014: Klosterman, Bettinger (2016), full text, Abstract and section 4, "Conclusions".
- **Evidence.**
  - **Covalent model (Liebscher 2013).** "Its structure is still under discussion". The authors assign dihydroxyindole and indoledione units with different degrees of unsaturation, covalently linked by C–C bonds, plus open-chain dopamine units, and they argue against a purely non-covalent model.
  - **Mixed model (Hong 2012).** A physically self-assembled (dopamine)2/DHI trimer coexists with covalent polymerisation.
  - **Non-equilibrium films (Klosterman 2016).** As-deposited PDA films are heterogeneous and non-equilibrium, and their composition depends on post-processing.
  - **Physical reading.** No single molecular model of PDA is established. Any fragment model fixes the ratio of catechol, quinone, indole and amine groups and their accessibility. The C1 to C3 observables depend on that choice.
- **Condition.** Any atomistic model of PDA.
- **Regime.** No. This is inherent to modelling PDA in either regime. It is mitigated by the fragment controls in the deletion register (catechol-only, chitosan-only, carboxylate-substituted).
- **Placement.** Limits (fragment models and their uncertainty). Discussion (verdicts reported per fragment, and robust only if the controls agree).
- **Severity.** Material.

### B9. Water competition weakens catechol adhesion on hydroxylated alumina (C1). Found in this session's search

- **Sources.**
  - 10.1021/acs.jpcb.9b04473: Yeh, Lenhart, Orlicki et al., *J. Phys. Chem. B* 123, 7024 (2019), abstract.
  - 10.1021/acs.langmuir.5c02791: Shrestha, Kojio, Shiota et al., *Langmuir* 41, 23672 (2025), abstract.
  - Full-text retry for Yeh 2019 and Shrestha 2025 (2026-10-17).
    - Neither has an open copy on Unpaywall, OpenAlex, Semantic Scholar or Europe PMC (PMIDs 31313924 and 40853215 are not open access), so both stay at "abstract".
    - The Shrestha abstract gives the chemisorption energy on the dehydroxylated surface as "−233.5 kJ/mol per surface model", with physisorption by hydrogen bonding on the hydroxylated surface. No number is given for the hydroxylated case.
  - 10.1021/jp512780s: Yeh, Lenhart, Rinderspacher et al., *J. Phys. Chem. C* 119, 7721 (2015), abstract (partly countervailing).
- **Evidence.**
  - **Weakened in water (Yeh 2019).** Catechol-bearing oligomers adsorb strongly on hydroxylated alumina in anhydrous conditions. In water, "the adsorption interactions were significantly weakened because of the competition with the water molecules", and catechol hydrogen bonding "is not the sole factor".
  - **Physisorption on the relevant surface (Shrestha 2025).** On hydroxylated γ-Al2O3(110), catechol binds mainly by hydrogen-bonded physisorption. This is weaker than on the dehydroxylated surface, where chemisorption with proton and electron transfer occurs.
  - **Partly countervailing (Yeh 2015).** Among phenolics on hydroxylated alumina in water, catechol showed the strongest adsorption, through cooperative hydrogen bonds.
  - **Physical reading.** The surface relevant to R-slurry, the hydroxylated oxide in water, is the one on which catechol binding is weakest and most contested by water.
- **Condition.** Hydroxylated oxide in liquid water: exactly the R-slurry contact.
- **Regime.** No, but the method is built for it. The C1 observable W_adh,wet is defined as a potential of mean force in explicit water, so that water displacement is part of the measurement (`charter/claim_register.yaml`, C1 physics). This evidence is a prior expectation that C1 may come out weak, not a flaw in the method.
- **Placement.** Discussion (C1 against these simulations, crediting them). Limits (force-field dependence of hydrogen-bond-dominated adhesion).
- **Severity.** Material.

### B10. Polydopamine coatings reduce CaCO3 deposition (C3). Found in this session's search

- **Sources.**
  - 10.3390/coatings13020306: Yu, Wang, Xu et al., *Coatings* 13, 306 (2023). Read in full text (2026-10-17): 13 pp., MDPI copy through an archived snapshot of the open-access location.
  - 10.1007/s11998-016-9898-x: Li, Peng, Deng et al., *J. Coat. Technol. Res.* 14, 1095 (2017), abstract (partly countervailing).
    - Full-text retry, 2026-10-17: there is no open copy, and the publisher page refuses headless clients.
- **Evidence.**
  - **Fewer deposits on PDA (Yu 2023).** An electroplated PDA coating cut CaCO3 deposition compared with bare carbon steel, with scale-inhibition efficiencies of 55.02% at 70 °C and 66.96% at 90 °C after 12 h in supersaturated CaCO3 solution. Their MD attributes initial deposition to dense water adsorption layers on hydrophilic metal surfaces, which are absent on PDA, so CaCO3 is less likely to adsorb there.
  - **Full text of Yu 2023.**
    - *Coating.* The coating is electroplated from 1.2 g/L dopamine at 15 V with a nickel anode for 3 min, and EDS shows Ni in it (Section 2.2, p. 3; Fig. 4). It is not pure PDA.
    - *Scale test.* Ca2+ and CO3 2- were each 360 mg/L, with static immersion for 12 h; pH, background salts and replicates are not stated (Section 4.1.4, p. 7).
    - *Deposit mass.* After 12 h, bare steel carried 0.667 (70 °C) and 0.672 mg/cm2 (90 °C), and PDA carried 0.300 and 0.222 mg/cm2 (p. 8, Fig. 7).
    - *Polymorph.* No XRD is reported, so the polymorph is not identified.
    - *Contact angles.* Water contact angles are 72.01 ± 0.3° on steel and 60.45 ± 0.3° on PDA (Section 4.1.2, p. 5). The PDA surface is the more hydrophilic one.
    - *MD interaction energies.* CaCO3–plate: Fe −1.53 eV, PDA-coated −0.29 eV. CaCO3–adsorbed water layer: Fe −84.22 eV, PDA −0.35 eV (Section 4.2.3, pp. 10–11).
    - *Internal inconsistency.* The water–PDA interaction energy is −5.69 eV in the abstract and −7.51 eV in Table 2.
    - *Mechanism.* The authors attribute scaling to a dense adsorbed water layer on the steel. They do not reconcile this with the lower contact angle of PDA.
    - *Use in retrodiction.* This study is retrodiction case RC12 (a negative catechol case). Its assumptions, configurational MD energies read as adhesion and deposit mass read as nucleation, are flagged there.
  - **PAA needed on PDA (Li 2017).** A continuous CaCO3 film on PDA was obtained only with poly(acrylic acid) in solution.
  - **Physical reading.** A PDA surface is not automatically a nucleation-promoting template. Under some conditions it is an anti-scaling surface, which is the opposite of what C3 needs.
- **Condition.**
  - Electroplated PDA on steel.
  - Hot (70 to 90 °C), supersaturated CaCO3 solutions over 12 h.
  - Deposition measured by mass, which mixes nucleation on the surface with adhesion of bulk-formed particles.
  - A coating containing Ni, with the polymorph not identified, and pH not reported (full text).
- **Regime.** Partly.
  - **Different conditions.** R-slurry is at room temperature on an Al oxide.
  - **What C3 measures.** C3 evaluates the heterogeneous nucleation barrier on the template, not the adhesion of bulk-precipitated particles.
  - **Not covered.** The core of the finding, that PDA lowers mineral deposition, bears directly on the sign of C3's template effect.
- **Placement.** Discussion (as the experimental counter-case to C3; the bare-oxide and deletion controls decide whether PDA promotes or suppresses nucleation in the computed system).
- **Severity.** Material.

### B11. The native oxide may be lost before the template anchors (C1, R-slurry). Found in this session's search

- **Sources.**
  - 10.1002/maco.201608843: Li, Church, *Mater. Corros.* 67, 978 (2016), abstract.
  - 10.1016/j.jpowsour.2013.10.039: Doberdò, Löffler, Laszczynski et al., *J. Power Sources* 248, 1000 (2014), abstract.
  - 10.1016/j.electacta.2019.05.141: Bauer, Çetinel, Müller et al., *Electrochim. Acta* 317, 112 (2019), abstract.
- **Evidence.**
  - **pH and time (Li 2016).** Slurry pH and immersion time are the principal factors in Al corrosion in aqueous cathode slurries. The oxide passive film degrades into hydroxide, and localised corrosion initiates at galvanic couples with intermetallic particles.
  - **Serious corrosion (Doberdò 2014).** The high pH of CMC-based NMC slurries caused serious Al corrosion during electrode manufacture.
  - **pH 9–10 (Bauer 2019).** Li+/H+ exchange raises the slurry pH. The best electrode properties lay at pH 9 to 10, outside the Al-stable region.
  - **Physical reading.** C1 presupposes an intact hydroxylated Al2O3/AlOOH surface to anchor to. In the alkaline slurry that surface is being dissolved, and intermetallic sites corrode locally, during the same minutes in which the template is supposed to adsorb. Whether anchoring and nucleation outrun dissolution is a kinetic race that a thermodynamic chain does not settle.
- **Condition.** Alkaline slurries, above roughly pH 9 to 10 (the Al-stable bound is to be fetched by S12 and p0-w1), on commercial Al foil with intermetallics, over the slurry contact time.
- **Regime.** No. This is the R-slurry corrosion mode itself (`charter/regimes.yaml`, `R-slurry.corrosion_mode`). The oxide's state is an input, and its dissolution rate is not computed.
- **Placement.** Limits (the substrate is modelled as an intact hydroxylated oxide, and dissolution kinetics are not computed). Discussion (the C5 aqueous screen places the oxide in pH-E space and should be read against these observations).
- **Severity.** Material.

### B12. "Fluorine-free" imide electrolytes release fluoride (C5, R-cell). Found in this session's search

- **Sources.**
  - 10.1149/2.081302jes: Krämer, Schedlbauer, Hoffmann et al., *J. Electrochem. Soc.* 160, A356 (2013), abstract.
  - Background: 10.1016/j.ensm.2025.104569 (Du, Song, Ning et al., *Energy Storage Mater.* 82, 104569, 2025, title only), coatings against Al corrosion in LiTFSI batteries.
- **Evidence.**
  - **What happens in LiTFSI.** Aluminium "corrosion" in 1 M LiTFSI in EC:DEC is an anodic dissolution of Al, preceded by an activation period of about 6 h with strong electrolyte oxidation.
  - **Products.** LiTFSI decomposes, and F− is the main decomposition product. The solvent also decomposes, giving CO2 and ethoxyethanol.
  - **Physical reading.** Electrolytes described as "LiPF6-free" or "PVDF-free" often still use fluorinated imide salts. These release fluoride and protic species at the cathode potential, which would convert or dissolve a carbonate film (CaF2 formation, acid attack).
- **Condition.** R-cell with a fluorinated imide salt (TFSI or FSI) at high potential.
- **Regime.** Yes, if the salt is strictly fluorine-free, as R-cell defines it (`charter/regimes.yaml`, `R-cell.medium`, and the `pH_analogue` rationale: "no HF contribution"). No, if the electrolyte chosen in S12 is an imide salt. The window construction must then include fluoride phases.
- **Placement.** Limits (the electrolyte definition). Outlook (fluorinated-imide electrolytes).
- **Severity.** Minor, provided S12 fixes a truly fluorine-free salt. Material otherwise.

### B13. Chitosan is not dissolved in a strongly alkaline slurry (C1, C2, C3; template premise). Lane note N4, added 2026-10-17

- **Sources.**
  - 10.3390/md13031133: Younes, Rinaudo, *Mar. Drugs* 13, 1133–1174 (2015). Read in full text, Section 3.2 (pdf p. 16) and Section 3.3 (pdf p. 17).
  - 10.3390/polym13193256: Aranaz, Alcántara, Civera et al., *Polymers* 13, 3256 (2021). Read in full text, Section 1 (pdf p. 2), Section 2.1 (pdf pp. 2–3) and pdf p. 7.
  - 10.1021/acs.cgd.4c00602: Knight, Mondal, Han et al., *Cryst. Growth Des.* 24, 6338–6353 (2024). Read in full text, Section 2.4.1 (pdf p. 5).
  - 10.1073/pnas.1222162110: Giuffre, Hamm, Han, De Yoreo, Dove, *Proc. Natl. Acad. Sci. USA* 110, 9261–9266 (2013). Read in full text, Materials and Methods (PMC3677451).
  - 10.1016/s0008-6215(99)00263-3: Kubota, Tatsumoto, Sano, Toya, *Carbohydr. Res.* 324, 268–274 (2000), abstract.
  - 10.1016/j.carres.2009.03.002: Fan, Hu, *Carbohydr. Res.* 344, 944–947 (2009), abstract.
  - 10.1016/j.carbpol.2015.07.072: Chang, Lin, Wu, Tsai, *Carbohydr. Polym.* 134, 74–81 (2015), abstract.
  - 10.1002/celc.202500327: Maffre, Liu, Markowski et al., *ChemElectroChem* (2025). Read in full text; it gives the slurry pH.
- **Evidence.**
  - **Acid-soluble only.** Chitosan is "soluble in acetic acid or hydrochloric acid at pH lower than 6 (its intrinsic pK being around 6.5)" (Younes and Rinaudo 2015, Section 3.2). Alkaline media are the standard way to precipitate it: films are "immersed in an alkaline solution (in which they precipitate)" (Section 3.3).
  - **Higher Mw is insoluble.** Its "pKa value is approximately 6.5" (Aranaz 2021, Section 2.1). "Chitosan samples with higher Mw are only soluble in acidic aqueous media even at high deacetylation degrees" (Section 1), and solubility is "poor … above pH 6.5" (pdf p. 7).
  - **Routes to wider solubility stop near neutral pH.**
    - Chitosan oligomers are soluble "from acidic to basic ones (i.e., physiological pH 7.4)" (Aranaz 2021, Section 1).
    - Half re-acetylation expands solubility "until pH 7.4" (Section 2.1).
    - The water solubility of half N-acetylated chitosan increases with decreasing molecular weight (Kubota 2000, abstract).
    - Chitosans above 29.2 kDa showed low solubility at pH 7.0 (Chang 2015, abstract).
    - No source located in this session reports dissolved chitosan chains at pH 10 to 12.
  - **Dissolving it in alkali needs harsh conditions.** Chitosan dissolves in aqueous LiOH/urea only through freeze–thawing, with 4.8 wt% LiOH and 8.0 wt% urea as the optimal solvent (Fan and Hu 2009, abstract). That is roughly 2 M LiOH, far more alkaline than a slurry and including a freezing step. The molarity is this lane's arithmetic, not a sourced value.
  - **The templating studies used solid films.**
    - In the chitosan–calcite nucleation experiments, "Chitosan is insoluble at the experimental pH of 10 and remains a stable surface in solution without treatment (i.e., does not dissolve)". The more soluble sulfated chitosans had to be cross-linked into "a thin, insoluble film" (Knight 2024, Section 2.4.1).
    - Giuffre et al. (2013) electrodeposited chitosan films onto gold before nucleating calcite at pH 10.8.
    - Neither study used chitosan dissolved in the mineralising solution.
  - **The slurry is strongly alkaline.** Aqueous cathode slurries reach pH 9.7 (LNMO) and 12.5 (NMC622) without additive (Maffre 2025, p. 5, Fig. 3F). The W1 rows TA-005, TA-006, TA-010 and TA-013 report pH 11.4 to above 12.
  - **Physical reading.**
    - At pH 10 to 12, the amines of ordinary chitosan (pK about 6.5) are essentially all deprotonated. The chain is near-neutral and precipitates or aggregates instead of dissolving.
    - Chitosan added to such a slurry would reach the Al oxide as a colloidal or precipitated deposit, not as dissolved chains that adsorb and order.
    - The literature support for a chitosan template, its low calcite nucleation barrier, belongs to a pre-cast, insoluble chitosan film.
    - Keeping chitosan dissolved at high pH would need a charged derivative (carboxymethyl, quaternised or sulfated). That changes the near-neutral surface chemistry to which that low barrier is attributed: Knight 2024 finds γ_net rises with sulfation, and Giuffre 2013 finds charge-dense polysaccharides give higher barriers.
- **Condition.** Chitosan of ordinary molecular weight and degree of acetylation in aqueous media at pH above about 7.4. In particular, the R-slurry pH (alkaline, upper bound pending S12) with no acid added.
- **Regime.** No, for R-slurry if the template is meant to be dissolved chitosan in the slurry.
  - **Not affected.** The physics of C1–C3 as computed is unaffected: P0 models a chitosan fragment at an interface, not its dissolution.
  - **Affected.** The premise of how the template reaches the collector is affected. A chitosan film pre-cast from mildly acidic solution and then exposed to the slurry is consistent with the sources. A chitosan additive dissolved in the slurry is not.
  - **The chitosan-only control.** This control (`charter/deletion_register.yaml`, `chitosan_only`) is a surface fragment, which matches the film reading.
  - **The retrodiction cases.** RC07–RC10 (`preprint/retrodiction/cases.yaml`) are films, consistent with this entry.
- **Placement.**
  - *Introduction.* The Introduction must not assume dissolved chitosan in the slurry (lane note N4). It describes the chitosan template as a pre-formed film, or states the solubility constraint.
  - *Limits.* The template's delivery and its state in the alkaline slurry are not modelled.
  - *Outlook.* Soluble derivatives, and the change in barrier that their charge implies.
- **Severity.** Material. It changes how the chitosan link and its control are read, and it constrains the Introduction's premise. It is not blocking, because no P0 verdict depends on chitosan being dissolved.

## Summary by severity

| Severity | Entries |
|---|---|
| Blocking | B1, B2 |
| Material | B3, B4, B5, B6, B7, B8, B9, B10, B11, B13 |
| Minor | B12 (material if the R-cell salt is a fluorinated imide) |

## Cross-reference with p0-w1

Updated 2026-10-17 (P0-W2.2), against `lit/evidence_table.csv` as merged into `preprint/p0` by P0-I1 (W1.1 merged; 396 rows, 73 with contrary = y). Each contrary row is assigned to exactly one entry; the assignment was checked by script, with all 73 rows assigned and none twice.

| Entry | W1 rows (contrary = y) | What the rows add |
|---|---|---|
| B1 | TB-001, TB-002, TB-003, TB-004, TB-005 | CaCO3 scale on Al alloys is porous and accompanies more corrosion |
| B2 | TE-043 | equilibrium and hull-distance stability metrics miss metastable phases |
| B3 | TD-042, TD-044, TD-046, TD-047, TD-050 | catechol pKa near 9 to 10.5; weak Ca2+ binding by dopamine near neutral pH |
| B4 | TA-038, TA-039, TA-040, TA-042, TA-043, TA-044 | catechol/quinone binders are redox-active or oxidised in the cathode window |
| B5 | TC-032, TC-114, TC-116 | ACC is size-stabilised, has no single solubility, and calcite-ACC interfaces are costly |
| B7 | TC-019, TC-112, TC-113, TE-003, TE-004, TE-006, TE-008, TE-011, TE-012, TE-013, TE-014, TE-018, TE-019, TE-020, TE-021, TE-022, TE-023 | non-classical pathways, size-dependent interfacial energy, line tension and Tolman corrections |
| B9 | TD-018, TD-019, TD-021, TD-029, TD-034, TD-035, TD-037, TD-039, TD-040 | catechol adhesion on oxides weakened by water and by oxidation to quinone; irreproducible forces; binding on alumina |
| B10 | TC-071, TC-094, TC-098, TC-101, TC-102, TC-103, TC-104, TC-111 | surfaces or polymers that bind Ca2+ yet suppress or bypass direct nucleation |
| B11 | TA-005, TA-006, TA-010, TA-013, TA-016, TA-023, TA-024, TA-035, TA-036, TA-046, TB-014, TB-019, TB-020, TB-022 | alkaline slurries dissolve the native oxide, release H2 and change pH; carbonate captured in Li-Al species |
| no entry | TB-057, TB-058, TC-001, TC-016, TE-082 | input uncertainty for the parameter table (lane p0-w1, lit/conflicts.md) or the anchor (p0-w5), not an argument against a link |

Notes on the assignment:

- **TC-111** (10.1021/acs.langmuir.3c01629). An oxygen-rich (carboxyl/hydroxyl) two-dimensional surface binds Ca2+ and inhibits nucleation. It is the sharpest W1 row against the C2 → C3 premise, that sequestering Ca2+ promotes nucleation. It is recorded under B10. The Discussion of B10 should cite it beside Yu 2023.
- **TC-071, TC-094 and TC-098.** These are also retrodiction candidates: RC05 is usable, while RX08 and RX11 are excluded (`preprint/retrodiction/cases.yaml`). Their use there does not change their contrary reading.
- **Entries with no W1 row.** B6, B8, B12 and B13 have no flagged W1 row. B13 draws on full texts read in this session.
- **Rows assigned to no entry.** TB-057, TB-058, TC-016 and TE-082 are uncertainty in input values: oxide–water and calcite surface energies, and a solvation benchmark error. TC-001 is a nacre ACC observation. They belong to the parameter-conflict log (p0-w1) or the anchor (p0-w5), not to this dossier.

## Outstanding for this dossier

1. **B3.** Numeric catechol pKa values and the Ca–catecholate stability constant, from the two title-only sources (10.1016/0039-9140(77)80049-0 and 10.1016/s0003-2670(01)85307-1), for the parameter table (p0-w1). W1 has since fetched pKa and log K rows (TD-042 to TD-049), which can replace them.
2. **B6.** A fetched CaCO3 band gap with a locator (10.1016/j.ssc.2025.116092 or another source).
3. **Full text still outstanding after the day-2 open-route retry.**
   - B2: Zagalskaya 2023. The repository copy at par.nsf.gov/servlets/purl/10427497 timed out; retry from another network.
   - B9: Yeh 2019 and Shrestha 2025. There is no open copy.
   - B10: Li 2017. There is no open copy.
   - These need an operator or library route.
   - B7 (Hu 2012) and B10 (Yu 2023) are now read in full.
4. **B13.** The pKa-versus-degree-of-acetylation values of Sorlier et al. (2001, 10.1021/bm015531+, abstract only), and the solvent and pH used by chitosan-binder electrode papers, remain unsourced.
