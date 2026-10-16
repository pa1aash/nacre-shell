# Pourbaix and window data cache

Raw responses used by `src/nacre/pourbaix/`. Everything downstream (diagrams, windows, tests)
reads these files and nothing else. The only code that fetches is
`uv run python -m nacre.pourbaix.cache fetch` (the Day 1 set) and `... cache extend` (the
Day 2 additions, written beside the Day 1 files without rewriting them). It reads the Materials Project key from
`.env` and never writes the key here. `uv run python -m nacre.pourbaix.cache verify` checks
every file against `manifest.json`.

## Contents

| File | Source | Request |
|---|---|---|
| `mp_entries_slurry_Al-C-Ca-H-Na-O.json` | Materials Project API, thermo entries | `get_entries_in_chemsys`, `thermo_types = [GGA_GGA+U]`, MP2020-compatible entries |
| `mp_entries_cell_<chemsys>.json` | Materials Project API, thermo entries | same request, one file per element system of the R-cell window |
| `mp_ion_reference_data.json` | Materials Project, MPContribs project `ion_ref_data` | `get_ion_reference_data` (all records) |
| `janaf_O2.json`, `janaf_CO2.json` | NIST-JANAF Thermochemical Tables | HTTP GET of the table text (URL in each file) |
| `janaf_<formula>.json` (Li2CO3, Li2O, Na2CO3, Na2O, CaO, LiClO4, LiCl, CaCl2, AlCl3) | NIST-JANAF Thermochemical Tables, condensed phases | HTTP GET of the table text; added by P0-W5.2 (`extend`) |
| `mp_entries_cell_<chemsys>.json` for Li-Ca-Cl-O, Li-Al-Cl-O, Li-Ca-B-C-O, Li-Al-B-C-O, Li-Ca-C-N, Li-Al-C-N | Materials Project API | as above; the sinks of the registered salts LiClO4, LiBOB and LiPCP; added by P0-W5.2 |
| `nbs1982_ocr.json` | NBS tables (Wagman et al. 1982), scanned PDF at NIST | HTTP GET of the PDF (sha256 stored), pages rendered at 200 dpi and read by tesseract; OCR text of pdf pp. 136, 137 and 276; added by P0-W5.2 |
| `manifest.json` | this cache | database version, client versions, per-file request, retrieval time and sha256; `extensions` lists what each later session added |

Each data file holds `request`, `retrieved_utc` and the raw `response` (or `text`). Each MP
file also holds `mp_database_version` and `client_versions`. The Materials Project entry
dictionaries are stored as returned, with one change: the keys of each entry's free-form
`data` field are turned into strings so that they can be written as JSON. The slurry system
includes Na because the carbonate ions' reference solid in `ion_ref_data` is Na2CO3. The
Materials Project client fetches the same element system. Na-bearing solids are excluded from
the diagram, exactly as in the client.

## Licence and attribution

- **Materials Project data.** Used under the Materials Project terms of use. Every cached entry
  carries the licence tag `BY-C` in its `data.license` field, as returned by the API. A headless fetch of
  the terms page (`https://materialsproject.org/about/terms`) returned HTTP 403 on 2026-10-16,
  and the documentation export does not state the licence. The licence text and the canonical
  citation request are therefore an outstanding action (see `ops/reports/P0-W5.1.md`); no
  licence text is reconstructed here. Work using these data must cite the Materials Project as
  the project requests.
- **Aqueous ion reference data.** The MPContribs project `ion_ref_data` reports its licence as
  `CCA4` and its authors as "Various Authors, MP Team." (both as returned by the API and stored in
  `mp_ion_reference_data.json` under `project`). The project's references are Persson et al.
  2012 (https://doi.org/10.1103/PhysRevB.85.235438), NBS Technical Note 270-1 to 270-8, and
  Pourbaix's *Atlas of Electrochemical Equilibria in Aqueous Solutions*. Each ion record names
  its own source in `data.reference`.
- **NIST-JANAF.** NIST Standard Reference Database 13, NIST-JANAF Thermochemical Tables
  (https://janaf.nist.gov). Cite the tables for the gas-phase entropies and formation enthalpies
  used in the R-cell oxidation reactions.

- **NBS tables.** Wagman, Evans, Parker, Schumm, Halow, Bailey, Churney and Nuttall, *The NBS
  tables of chemical thermodynamic properties*, J. Phys. Chem. Ref. Data 11, Suppl. 2 (1982),
  open PDF at https://srd.nist.gov/JPCRD/jpcrdS2Vol11.pdf (erratum doi:10.1063/1.555845). The PDF
  has no text layer, so the pages used are stored as OCR text; `src/nacre/pourbaix/salts.py` names
  each row used and the check made against the page image. The machine-readable NIST release
  (doi:10.18434/M32124) did not download (HTTP 524 and connection resets on 2026-10-17).

## What the cache answers

The cache holds the energies needed for two thermodynamic questions:

1. Which Al-, Ca- and C-bearing species are at equilibrium on the aqueous (pH, E vs SHE) plane?
2. At what potential vs Li+/Li does CaCO3, or an Al oxide, take up Li (reduction) or release O2
   (oxidation)?

Neither answer is a rate. A stable domain or a window is a thermodynamic proxy for the
corrosion and dissolution questions of the study, not a statement about them.
