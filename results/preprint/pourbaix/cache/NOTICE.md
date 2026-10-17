# Notice: Materials Project data in this cache

## Source and credit

The `mp_entries_*.json` files hold thermodynamic entries from the **Materials Project**, database
version **2026.04.13**, retrieved through the Materials Project API with the `mp-api` client (no
scraping). Cite the Materials Project as:

> A. Jain, S. P. Ong, G. Hautier, W. Chen, W. D. Richards, S. Dacek, S. Cholia, D. Gunter, D. Skinner,
> G. Ceder and K. A. Persson, "Commentary: The Materials Project: A materials genome approach to
> accelerating materials innovation", *APL Materials* **1**, 011002 (2013),
> https://doi.org/10.1063/1.4812323

(DOI and bibliographic fields confirmed against the Crossref works record on 2026-10-17.)

## Licence

The Materials Project data are used under the **Creative Commons Attribution 4.0 International
licence (CC BY 4.0)**, https://creativecommons.org/licenses/by/4.0/ (legal code:
https://creativecommons.org/licenses/by/4.0/legalcode). These are the terms supplied by Palaash Gang
and ruled on by the planning chat for this study (session P0-W5.3); the terms pages themselves return
HTTP 403 to a headless client, and no licence text is reproduced here.

Materials Project data derived from GNoME are licensed **CC BY-NC 4.0**
(https://creativecommons.org/licenses/by-nc/4.0/) and are **excluded**. Every cached entry carries the
licence tag returned by the API in `data.license`. On 2026-10-17 all 3715 cached entries (1280 unique
material ids, the Day 1 files and the six Day 2 element systems) carry `BY-C`, and a live query of the
thermo documents of all 1280 ids returned `builder_meta.license = BY-C` for each, at database version
2026.04.13. No entry was excluded, because none is BY-NC. `nacre.pourbaix.cache.load_entries` admits only
`BY-C` entries, so a BY-NC entry could not enter any computation even if one were cached later.

## Changes made

The data are not used as retrieved. The changes, in the order the code applies them:

1. **MP2020 compatibility corrections.** Entries are requested with `compatible_only=True`, so the
   client applies the MaterialsProject2020Compatibility energy corrections (anion and GGA/GGA+U mixing
   corrections).
2. **Aqueous-compatible adjustments.** For the aqueous (Pourbaix) diagram the solid entries are further
   processed with MaterialsProjectAqueousCompatibility on top of MP2020 (fitted H2O and O2 reference
   energies, and the hydrate adjustment of hydroxides such as the Al(OH)3 ground state).
3. **Pourbaix entries rebuilt offline.** The Pourbaix entries are rebuilt from the cached solid entries
   and the cached ion reference data by `src/nacre/pourbaix/entries.py`, following the client's own
   procedure (ions placed at their experimental formation free energies, shifted by the DFT-minus-experiment
   difference of their reference solid, after Persson et al. 2012), not downloaded as Pourbaix entries.
   Na-bearing solids are removed from the diagram, as in the client.
4. **ACC offset.** Amorphous calcium carbonate is represented as the Materials Project calcite entry plus a
   sourced free-energy offset (`lit/params.yaml` key `acc_offset`), converted from J mol^-1 to eV per
   formula unit. It is not a Materials Project entry.
5. **Experimental-route corrections.** For the Li-referenced window the all-experimental route (`expt`)
   replaces Materials Project energies with sourced experimental free energies (`lit/params.yaml` keys,
   NIST-JANAF and NBS 1982 tables), and the gas-reference schemes `janaf` and `mp` are compared with
   experiment by a recorded benchmark (`results/preprint/pourbaix/gas_reference.md`; +0.382 and
   −0.233 V per electron on CaCO3 → Ca + CO2 + ½O2).
6. **Storage form.** Each entry dictionary is stored as returned, except that the keys of its free-form
   `data` field are turned into strings so that the file is valid JSON.

## No endorsement

Use of Materials Project data does not imply any endorsement by the Materials Project, its
contributors or its funders of this work, its methods or its conclusions.

## Contributed data: aqueous ion reference project

`mp_ion_reference_data.json` holds the records of the MPContribs project **`ion_ref_data`, "Aqueous Ion
Reference Data"**. It is **contributed data owned by its contributors** ("Various Authors, MP Team.", as
the project states); the project reports its licence as `CCA4` (Creative Commons Attribution 4.0,
https://creativecommons.org/licenses/by/4.0/). Its references are Persson, Waldwick, Lazic and Ceder,
Phys. Rev. B 85, 235438 (2012), https://doi.org/10.1103/PhysRevB.85.235438; NBS Technical Notes 270-1 to
270-8; and M. Pourbaix, *Atlas of Electrochemical Equilibria in Aqueous Solutions*. Each ion record names
its own source in `data.reference`. The records are used as described under change 3.

## Raw entries on public branches

From P0-W5.3 no further raw Materials Project entries are pushed to public branches. Any raw entries
retrieved from now on (for example the licence re-check of 2026-10-17) stay local-only under `.local/` and
are recorded by sha256 in the session report. The entries already committed above were committed before
this rule and are kept so that every committed result stays reproducible from its recorded cache hash.
