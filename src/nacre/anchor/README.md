# Anchor structures: Ca2+ binding comparison

**Status.** This is a pipeline check, never a screen input. Lane p0-w1 rates both Ca2+–catecholate
(`lit/corpus/coverage.yaml`, target `dg_ca_catecholate`, rows TD-048 and TD-049) and
Ca2+–carboxylate (target `dg_ca_carboxylate`, rows TD-051 and TD-052) as **single-source**. The
computed comparison therefore checks that the pipeline is self-consistent: the dianion should bind
more strongly than the monoanion, and the bidentate–monodentate difference for acetate should come
out sensibly ordered. It is not a source of parameters for C2 or the screen. Nothing about the
method is chosen here; session P0-W5.2 decides.

**Thermodynamic question.** What is the free energy of replacing first-shell waters of
hydrated Ca2+ by a catecholate (mono- or dianion, bidentate) or an acetate (mono- or
bidentate) in water? The pipeline must give this consistently across the four cases.

## Species (`python -m nacre.anchor.build`)

| Name | Species | Charge | Mode | Waters (default) |
|---|---|---|---|---|
| `Ca_catecholate_monoanion_bidentate_w4` | [Ca(HCat)(H2O)4]+ | +1 | bidentate chelate (O−, OH) | 4 |
| `Ca_catecholate_dianion_bidentate_w4` | [Ca(Cat)(H2O)4] | 0 | bidentate chelate (O−, O−) | 4 |
| `Ca_acetate_monodentate_w5` | [Ca(OAc)(H2O)5]+ | +1 | monodentate | 5 |
| `Ca_acetate_bidentate_w4` | [Ca(OAc)(H2O)4]+ | +1 | bidentate | 4 |
| `Ca_aqua_w6` | [Ca(H2O)6]2+ | +2 | aqua reference | 6 |
| `ligand_catecholate_monoanion` | HCat− | −1 | free ligand | 0 |
| `ligand_catecholate_dianion` | Cat2− | −2 | free ligand | 0 |
| `ligand_acetate` | OAc− | −1 | free ligand | 0 |
| `water_w1`, `water_w2` | (H2O)k | 0 | released-water reference | 1, 2 |

All species are singlets. The water counts are parameters (`all_species(...)`). The defaults
keep the starting coordination number at 6 for every complex and for the aqua ion, so each
bidentate cycle releases two waters and the monodentate cycle releases one. The first-shell
size of Ca2+ is itself uncertain: W1 row TE-072 quotes experimental hydration numbers over a
range, and TE-066 notes that the first shell grows from 6 towards 7–8. P0-W5.2 sets the counts.
Each `.xyz` has a `.json` beside it with charge, multiplicity, coordination mode, n_water, seed and
builder version; `index.json` lists them all.

**Geometry.** Ligands are embedded with RDKit (ETKDG, seeded) and relaxed with MMFF94. Ca2+ is
placed on the chelation bisector, or along the C–O bond for the monodentate mode. Waters fill
the remaining sites of a seeded repulsion arrangement. The Ca–O placement distance is the sum of
the ase covalent radii. That is a placement rule, and optimisation replaces it. These are
starting geometries only. A fixed seed reproduces them exactly.

## Binding free-energy cycle in implicit solvent

With m waters on the aqua ion and n on the complex, the reaction in solution is

    [Ca(H2O)m]2+ (aq) + L^q- (aq)  ->  [Ca L (H2O)n]^(2+q) (aq) + (m - n) H2O

    Delta_G_bind = G*[Ca L (H2O)n] + (m - n) G*[H2O] - G*[Ca(H2O)m] - G*[L]

Each solution-phase free energy is G* = E_el + G_RRHO + Delta_G_solv + Delta_G(1 atm -> 1 M):

- **E_el.** The electronic energy at the optimised geometry, with the functional, basis and
  dispersion still to be chosen.
- **G_RRHO.** The thermal free-energy correction from harmonic frequencies, with low modes
  treated quasi-harmonically. The low-mode treatment is to be chosen.
- **Delta_G_solv.** The implicit-solvent free energy of solvation (SMD or ALPB class, to be
  chosen) of the cluster with its explicit waters. This is the cluster-continuum construction:
  the explicit first shell is part of the solute, and the continuum represents everything beyond
  it.
- **Standard-state correction.** Gas-phase free energies refer to 1 atm, while solutes in
  solution refer to 1 mol L^-1. Each solute gains Delta_G(1 atm -> 1 M) = RT ln(c° R T / p°),
  with c° = 1 mol L^-1 and p° = 1 atm. The code evaluates this from the CODATA constants at the
  run temperature; no value is typed. For the cycle above, the net correction is
  (number of product species − number of reactant species) × RT ln(c° R T / p°), counted over
  every solute.

**Counting the explicit waters.** Water is the solvent, so its reference state is pure liquid
(activity 1) and not a 1 M solute. Two bookkeeping choices are standard, and P0-W5.2 picks one:

1. **Monomer waters.** Release (m − n) separate H2O molecules. Each carries the 1 atm -> 1 M
   correction plus RT ln([H2O]), which moves it from 1 M to the pure-liquid concentration. The
   water concentration needs the density of water at T, which must come from a W1 row.
2. **Water cluster.** Release one (H2O)(m−n) cluster (`water_w2` for the bidentate cycles). This
   removes most of the cluster-size error. The cluster carries a single standard-state
   correction plus the RT ln([H2O]/(m − n)) term for a cluster of size m − n.

In both choices m and n are counted the same way for every ligand. A comparison across ligands
is only meaningful when the aqua reference and every complex use the same first-shell
convention. Protonation of the free ligand (HCat− versus Cat2− at the slurry pH) is not part of
this cycle. It follows from the catechol pKa (W1 target `pka_catechol`), so the cycle is computed
for each protonation state separately.

## Literature needed to choose functional, basis and dispersion

Cited by W1 row_id where a row exists:

- **Ca2+ complexes against CCSD(T)/CBS.** TE-061, TE-062 and TE-063 (Friedman 2021,
  10.1021/acs.jpcb.0c11077: M06, HSE06 and M06-2X with def2-TZVP, ligands including water and
  acetate).
- **Ca2+ binding and basis requirements.** TE-065 (Corral et al. 2003, 10.1021/jp0363491:
  core–valence basis needed, Ca–X bonds shorten as the basis grows).
- **Ca–water benchmark protocol.** TE-066 (10.1021/acsomega.6c01605, PBE0-D3(BJ)/def2-TZVP).
- **Dispersion correction and general main-group accuracy.** TE-069 and TE-070 (GMTKN55,
  10.1039/c7cp04913g: D3(BJ) recommended). TE-071 (MOR41, 10.1021/acs.jctc.7b01183).
- **Implicit solvation.** TE-067 and TE-068 (SMD, 10.1021/jp810292n; Ca is not among the
  parametrised ions). TE-081 to TE-084 (ALPB with GFN2-xTB, 10.1021/acs.jctc.1c00471).
- **Ca2+ hydration free energy and hydration number (cycle validation).** TE-064 (secondary
  citation; standard-state convention not stated). TE-072 (hydration number).
- **Semi-empirical pre-screening and conformers.** TE-075 to TE-077 (GFN2-xTB). TE-078 to TE-080
  (GFN-FF). TE-087 (conformer benchmark). TE-088 (CREST).
- **Experimental anchors (single-source).** TD-048 and TD-049 (Ca2+–dopamine catecholate
  constants). TD-051 and TD-052 (Ca2+–carboxylate).

Needed from W1 (no row yet): the cluster-continuum and standard-state methodology reference;
the density of water at T (for [H2O]); the quasi-RRHO low-frequency treatment; a def2
basis/ECP reference for Ca; the original source behind TE-064, with its standard-state
convention; and a second independent Ca2+–catecholate and Ca2+–carboxylate determination.

## Conformer tooling

`xtb_env.yaml` pins xtb 6.6.1 and CREST 2.12 from conda-forge, together with the libgfortran
runtime that works on osx-arm64. Create it outside iCloud at `~/.nacre-envs/xtb`.
`python -m nacre.anchor.xtb_smoke` runs one single-threaded GFN2-xTB/ALPB(water) optimisation of
the smallest complex and writes `results/preprint/anchor/xtb_smoke/summary.json`. The smoke
energy is not a binding energy and is used nowhere.
