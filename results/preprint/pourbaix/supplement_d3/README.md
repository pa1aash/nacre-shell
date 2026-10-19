# R-cell supplement, Day 3 (P0-W5.4)

Additive documents for cp4 (lane note N29; decision D30). No earlier document was changed. The production
screens read params at `p0-cp3`, and so does this run (`8bc15c8`, equal to the tag; the run checks this).

    uv run python -m nacre.pourbaix.supplement_cache fetch     # once; network (MP key from .env, JANAF, one quote)
    uv run python -m nacre.pourbaix.supplement_d3 --config results/preprint/pourbaix/config/supplement_d3.yaml \
        --w1-poll .local/w5/w1_poll.jsonl

## Files

| File | Content |
|---|---|
| `cell/LiClO4.json`, `cell/LiBOB.json`, `cell/LiPCP.json`, `cell/solvated.json` | Schema v3 R-cell documents (`configs/preprint/results_schema.json` at its last commit), one per registered sink. Windows: `CaCO3` (mp-3953), `Al2O3` (corundum, mp-1143) and `AlOOH` (boehmite, mp-625054). The governing limit is `oxidation`/`reduction`; every scheme's limit is under `*_by_scheme`; verdicts by cathode class, margins and budget gaps are under `extensions.p0-w5`, with the sources list. |
| `cell_d3_summary.json` | Every candidate reaction and scheme; the sink table; the attempts to find sink thermochemistry; the budgets and the W1 poll log; the confirmation against P0-W5.3; the boehmite dehydration threshold; the water-activity slopes; the Al(ClO4)3 sourced value. |
| `cell_schema_checks.json` | Validation of each document against schema v3. |
| `inputs/params_8bc15c8_extra.json` | Additive verbatim snapshot of the W1 keys read beyond the production snapshot, and the requested keys absent from the file (the reduction budget keys). |
| `cache/` | The supplement cache: NIST-JANAF H-064 H2O(g), H-063 H2O(l), H-018 LiOH(cr), H-014 LiH(cr), Al-068 LiAlO2(cr); the stored quote of the Al(ClO4)3 enthalpy. Its manifest records the Li-Al-O-H Materials Project entries (307 entries, all BY-C) by sha256. Those entries are not committed; they are kept under `.local/w5/cache_d3/`. |

## Sources

- Materials Project database 2026.04.13 (mp-api), CC BY 4.0 (Jain et al., APL Mater. 1, 011002, 2013; `../cache/NOTICE.md`). GNoME (CC BY-NC) is excluded, and no entry needed excluding.
- NIST-JANAF tables (URLs in each document's source list).
- NBS 1982 tables via the OCR cache (the Ca(ClO4)2 enthalpy, as in P0-W5.2).
- Krivtsov, Nikitina and Rosolovskii, Bull. Acad. Sci. USSR Div. Chem. Sci. 22, 2560 (1973), doi:10.1007/BF00926423: the standard enthalpy of formation of anhydrous Al(ClO4)3. This is a sourced value but **not yet a W1 params key**. Its limits:
  - it is quoted from the free abstract page; the full text is not open;
  - the reference temperature is not printed and is read as 298.15 K;
  - no ΔfG or S is given.
- W1 params keys, cited per value.

## Results

- **Boehmite window, expt route governing.**
  - Reduction: 2.155 V vs Li+/Li (AlOOH + Li → LiAlO2 + ½ H2). The Li-open DFT comparator gives 1.747 V.
  - Oxidation with the LiClO4 sink: 4.751 V (janaf 4.828 V, mp 4.605 V).
  - The BOB and PCP sinks are undetermined, and the solvated sink is a gap.
- **Corundum, confirmed.**
  - Reduction: 1.221 V (Li-open; LiAl5O8 is not tabulated, so there is no expt cross-check).
  - The LiClO4 sink is now computable: 4.706 V expt (janaf and mp 4.670 V).
- **CaCO3, confirmed.**
  - LiClO4: 3.938 V expt (janaf 4.320 V, mp 3.705 V). This is unchanged from P0-W5.3, and so are the class verdicts.
  - Reduction: the expt route now governs, at 1.776 V. The Li-open DFT value is 1.623 V.
- **Verdicts.**
  - Only CaCO3/LiClO4 has a budget key (m_expt), and it decides as in P0-W5.3.
  - The Al phases' LiClO4 onsets have no budget key, so they are undetermined. A solid-salt pass would be inconclusive in any case.
  - Every reduction limit lacks its own budget key, so every reduction verdict is inconclusive, never a pass. The margin that would decide each verdict is printed.
- **Boehmite dehydration, 2 AlOOH → Al2O3 + H2O.**
  - This is a threshold, not a verdict.
  - ΔG (expt) is +0.134 eV per AlOOH with water at 1 bar, so dehydration is favoured below p(H2O) = 2.9e-5 bar. Against liquid water the limit is a_w = 8.9e-4.
  - The water activity in the electrolyte is not a sourced key, so the threshold is not compared with any state of the cell.
- **Water-state sensitivity.** Water released by boehmite is taken as H2O(g) at 1 bar. With liquid water at unit activity, each onset is 15 mV lower. A lower water activity lowers the onset further, by 4.3 mV per unit of |ln a_w|. That slope is reported and not applied.

Thermodynamic windows only: nothing here is a rate, and a window does not say whether a decomposition happens.
