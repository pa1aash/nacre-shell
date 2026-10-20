# Literature corpus and evidence table

This directory holds the evidence that becomes the priors of the P0 thermodynamic screen. Every value
is tied to a DOI and a locator inside that work, with its conditions, its method and a quality grade.
The table records evidence only; the parameter table (`lit/params.yaml`) is built from it in a later
session, and nothing here is a result of the study.

## Layout

| Path | Content | Committed |
|---|---|---|
| `lit/corpus/<thread>/queries.jsonl` | one line per search: `route`, `query`, `date`, `hits`, `dois` | yes |
| `lit/corpus/<thread>/sources.jsonl` | one line per source read: `doi`, `access_route`, `url`, `local_path`, `sha256`, `pages`, `licence`, `retrieved_at` | yes |
| `lit/corpus/<thread>/rows.csv` | the thread's evidence rows (schema below) | yes |
| `lit/corpus/<thread>/gaps.md` | what the thread searched for and did not find, and why | yes |
| `lit/corpus/<thread>/instrument_gaps.csv` | retrieval failures, in the `nacre.retrieval` gap format | yes |
| `lit/evidence_table.csv` | all thread rows merged; numeric rows deduplicated on DOI + locator + quantity + symbol + value (D1), qualitative rows on DOI + locator + quantity across threads | yes |
| `lit/corpus/coverage.yaml` | status of every target quantity | yes |
| `lit/corpus/gaps.md` | all gaps, ordered by physical leverage on the barrier | yes |
| `.local/lit/<thread>/` | full texts, extracted text, abstracts, search metadata, raw cache | **never** |

Threads: T-A binders and fluorine-free processing; T-B aluminium, its oxide and the alkaline slurry;
T-C biomineralisation and nucleation; T-D catechol and polydopamine chemistry; T-E methods and
benchmarks. Day 2 (P0-W1.2): T-F second sources and the three gap targets; T-G direct ACC solubility
and density; T-H Ca2+ binding at templates against the interfacial energy of nucleating CaCO3; T-I
thermochemistry of the stability screens, the R-cell electrolyte and solvation; T-J regime ranges,
nucleation prefactors and process times. Day 3 (P0-W1.3): T-K R-cell thermochemistry (Ca2+, Al3+
and Li+ solvation and transfer, analog entropies for the Ca(ClO4)2 bound, uncertainties of the
experimental route, charge cut-offs by cathode class, Li2CO3 oxidation against equilibrium); T-L the
W3 contract-v3 keys (dry CaCO3 surface energies, speciation and activity-model constants, geometry,
water activity, method errors); T-M the cp3 R8 registrations and the N16 drawing parameters. Day 3, ahead of day 4 (P0-W1.4, decision
D30): T-N the post-cp3 keys (PVDF surface energy, A_patch bounds, template molar mass per group, the Ca2+
radius, primary-drying water activity, stated correlations); T-O anodic stability of other biominerals'
anions (Outlook evidence); T-P the Shapley-effects references and reference-audit support; T-Q the
R-cell film keys (d_max) and the uncertainty budgets of the reduction limits, the solvated sink,
Al(ClO4)3 and boehmite.

## Tools

    uv run python -m nacre.lit search   <thread> --route <crossref|openalex|europepmc|pubmed|semanticscholar|arxiv|openaire|zenodo> --query "<q>"
    uv run python -m nacre.lit meta     <thread> <doi>
    uv run python -m nacre.lit abstract <thread> <doi>
    uv run python -m nacre.lit fulltext <thread> <doi | arXiv id>
    uv run python -m nacre.lit url      <thread> <pdf url> --doi <doi>
    uv run python -m nacre.lit related  <thread> <doi> [--refs]
    uv run python -m nacre.lit grep     <thread> "<regex>" [--doi <doi>]
    uv run python -m nacre.lit validate lit/corpus/<thread>/rows.csv
    uv run python -m nacre.lit merge

Every search and every source read is logged automatically. Full-text routes, in order: Unpaywall
open-access locations, OpenAlex locations, Europe PMC, the archived snapshot of the same open-access
location, then Europe PMC full-text XML. Paywalled works without an open copy are logged as
`paywalled` and can only be graded D from their abstract. Extracted PDF text carries a marker line
`=== pdf page N (label L) ===` per page; `L` is the printed page label when the PDF has one.

## Columns of `rows.csv` and `lit/evidence_table.csv`

| Column | Content and format |
|---|---|
| `row_id` | `<thread letter pair>-<three digits>`, unique: `TA-001`, `TB-014`. The prefix matches the thread. |
| `thread` | `T-A` to `T-R`. |
| `doi` | Bare DOI, lower case, `10.<registrant>/<suffix>`; no `https://doi.org/` prefix. |
| `locator` | Where in the work the value is: `p. 155`, `Table 2`, `Fig. 3b`, `Eq. (12)`, `Section 3.2`, `SI Table S4`, `abstract`. Combine as needed (`p. 4, Table 2`). Use the printed page number when the text shows one, else `pdf p. N`. |
| `quantity` | A lower-case slug. Target quantities use the vocabulary below; other quantities may use any descriptive slug. |
| `symbol` | The symbol as used in the source, or the screen's symbol (`gamma_nw`, `log10 Ksp`, `pKa1`). |
| `value` | A number as reported (`-8.48`, `1.2e-8`, `0.31`), optionally with `<`, `>`, `<=`, `>=`. Empty only when `range_or_uncertainty` holds a `lo..hi` range. For `unit = qualitative`, the observed outcome in a few words. |
| `unit` | A unit string that parses with pint (`mJ m^-2`, `J/m^2`, `kJ mol^-1`, `cm^3 mol^-1`, `nm^-2`, `V`, `degree`, `mol/kg`, `mmol L^-1`), `1` for dimensionless numbers (pH, pKa, log10 K), or `qualitative` for an outcome without a number. Potentials are in `V`; the reference electrode goes in `conditions`. |
| `range_or_uncertainty` | Empty, `±x`, `±x%`, `+a/-b`, or `lo..hi`. Say in `notes` what the uncertainty is (standard deviation, standard error, spread of methods). |
| `conditions` | `T=…; pH=…; I=…; solvent=…; phase=…; surface=…`, plus anything else that decides the value (reference electrode, electrolyte, Ca and carbonate concentrations). Write `n.s.` for an item the source does not state. |
| `method` | `experiment: <technique>`, `computation: <method, level, model>` or `compilation: <what is compiled>` (a secondary citation of another work's value). |
| `grade` | `A`, `B`, `C` or `D` (below). |
| `extraction_route` | `full text`, `SI` or `abstract`: where the value was actually read. |
| `retrieved_at` | UTC timestamp or date of the retrieval the value was read from (`2026-10-16T09:22:55Z`). |
| `contrary` | `y` if the row is evidence against a link of the mechanism or against the screen's framing (for example, CaCO3 scaling on aluminium that is porous or harmful, binding that is weaker than hydration), else `n`. |
| `retro_candidate` | `n`, or `y: <observed outcome>` when the work reports whether mineral formed on a defined surface (`y: calcite formed on COOH-terminated SAM`, `y: no mineral on CH3-terminated SAM`). These rows feed the retrodiction set. |
| `notes` | Paraphrase. Any direct quotation stays under 15 words. Say how the value was derived when it is not read off directly, and name the original work when the row is a secondary citation. |

### Quality grades

| Grade | Meaning |
|---|---|
| **A** | Direct measurement or high-level computation under P0-relevant conditions (aqueous, near 298 K, the relevant phase and surface), with a stated uncertainty. |
| **B** | Direct measurement or computation, but the conditions differ from P0 or no uncertainty is stated. |
| **C** | Indirect or derived: obtained by fitting a model to other data (for example an interfacial energy back-calculated from nucleation rates through classical nucleation theory), estimated, or a compilation of another work's value. |
| **D** | Abstract-only or secondary citation not checked against the original. |

Rules enforced by the validator: rows with `extraction_route = abstract` are capped at D; rows with
`method = compilation: …` are capped at C. "High-level computation" means a method whose level of
theory the source benchmarks or justifies; a force-field number without a benchmark is B at most.

### Target quantity vocabulary

Coverage (`coverage.yaml`) counts rows whose `quantity` is one of these slugs and whose unit is not
`qualitative`. A target is **covered** with at least two independent sources (distinct DOIs; same-group
caveats go in `notes`), **single-source** with one, and a **gap** with none.

| Target | Slugs |
|---|---|
| ACC-water interfacial free energy | `gamma_acc_water` |
| calcite-water interfacial free energy | `gamma_calcite_water` |
| substrate-nucleus interfacial energy, or measured contact angle | `gamma_sub_nuc`, `contact_angle_caco3`, `gamma_eff_het` (effective interfacial energy from heterogeneous nucleation) |
| hydroxylated alumina or oxyhydroxide-water interfacial energy | `gamma_oxide_water` |
| catechol- or carboxyl-bearing surface-water interfacial energy | `gamma_organic_water` |
| solubility products | `ksp_calcite`, `ksp_aragonite`, `ksp_vaterite`, `ksp_acc` (value as log10 Ksp, unit `1`, unless stated otherwise in `symbol`) |
| ACC excess free energy relative to calcite | `acc_excess_free_energy` |
| molar volumes | `molar_volume_calcite`, `molar_volume_acc` (others: `molar_volume_aragonite`, `molar_volume_vaterite`) |
| Ca2+ hydration free energy | `hydration_free_energy_ca` |
| catechol pKa | `pka_catechol` |
| Ca2+-catecholate binding | `dg_bind_ca_catecholate` (free energy) or `logk_ca_catecholate` (log10 K) |
| Ca2+-carboxylate binding | `dg_bind_ca_carboxylate` or `logk_ca_carboxylate` |
| binding-site density on the organic layer | `site_density_organic` |
| wet work of adhesion of catechol or PDA to alumina | `w_adh_wet` |
| slurry pH, ionic strength, Ca, dissolved inorganic carbon | `slurry_ph`, `slurry_ionic_strength`, `slurry_ca`, `slurry_dic` |
| in-cell potential range at the collector | `incell_potential` (V; reference in `conditions`) |

Recommended slugs for other recurring quantities: `pzc_alumina`, `hydroxyl_density_alumina`,
`al_solubility`, `al_onset_potential`, `ca_binding_other`, `templated_mineralisation_outcome`,
`pda_structure_evidence`, `adhesion_force`, `binder_stability_window`, `benchmark_error`.

## Scope

Rows record thermodynamic, structural and potential-window evidence only; kinetic and
device-level quantities are out of scope. The validator applies the forbidden-claim patterns of
`charter/scope_guard.md` to every field, and the same patterns are kept out of every file in this
directory.
