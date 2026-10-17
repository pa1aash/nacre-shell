# Attribution wording for the paper (for lane W8)

Draft by lane p0-w5 (P0-W5.3), from `results/preprint/pourbaix/cache/NOTICE.md`. W8 places it and
adjusts the wording to the template; the facts below are what must survive editing. Numbers that
appear in paper text go through generated macros (standing rule R5); the database version and the
counts here are inputs for those macros, not text to paste.

## References W8 adds (with `uv run nacre bib add --bib preprint/paper/refs.bib <doi>`)

- Materials Project: doi:10.1063/1.4812323 (Jain et al., APL Materials 1, 011002, 2013). Not yet in
  `preprint/paper/refs.bib` on 2026-10-17.
- Aqueous ion reference scheme: doi:10.1103/PhysRevB.85.235438 (Persson et al., Phys. Rev. B 85,
  235438, 2012).

## SI, Methods section on thermodynamic data (draft)

> Solid-phase energies were taken from the Materials Project [Jain2013] (database version 2026.04.13),
> retrieved through its API and used under the Creative Commons Attribution 4.0 International licence
> (CC BY 4.0, https://creativecommons.org/licenses/by/4.0/). Entries derived from GNoME, which are
> licensed CC BY-NC 4.0, were excluded; every entry used carries the CC BY tag. We modified the data as
> follows: the MP2020 compatibility corrections and the aqueous-compatibility adjustments were applied;
> the Pourbaix entries were rebuilt offline from the solid entries and the aqueous ion reference data
> following the scheme of Persson et al. [Persson2012]; amorphous calcium carbonate was represented as
> calcite plus a literature free-energy offset; and for the lithium-referenced window an
> all-experimental thermochemical route replaced the computed energies where experimental data exist,
> with the computed gas-reference schemes reported as benchmarked comparators. The aqueous ion
> reference data are the MPContribs project "Aqueous Ion Reference Data", contributed data owned by
> its contributors and licensed CC BY 4.0. Use of these data does not imply endorsement by the
> Materials Project or by the contributors of this work.

## Data availability statement (draft)

> The Materials Project entries used in this work (database version 2026.04.13) are available from the
> Materials Project (https://materialsproject.org) under CC BY 4.0 [Jain2013]; the cached copy used for
> every calculation, its manifest with per-file SHA-256 hashes, and the list of changes made to it are
> in the repository at `results/preprint/pourbaix/cache/` (see `NOTICE.md` there). The aqueous ion
> reference data are from the MPContribs project "Aqueous Ion Reference Data" (CC BY 4.0, owned by its
> contributors). No Materials Project endorsement is implied.

## Points W8 must keep

1. Credit: the Materials Project and Jain et al. 2013, with the database version.
2. The licence named and linked (CC BY 4.0).
3. The changes stated (MP2020 corrections, aqueous adjustments, offline Pourbaix rebuild, ACC offset,
   experimental-route corrections).
4. No endorsement implied.
5. The ion reference project credited as contributed data owned by its contributors.
6. GNoME (CC BY-NC 4.0) data excluded.
