# Fig. 7 caption draft

Built from W4's production run `table_r2` (`results/preprint/screen/table_r2/summary.json`, P0-W4.3), pinned in `figures/src/schemas/upstream.yaml` (`screen_table_r2`): claim C5, its dose window and the C5c scheme tables and cutoff axis, which W4 evaluated on W5's P0-W5.3 documents (`results/preprint/pourbaix/c5/`). C_T values from `lit/params.yaml` (`dic_slurry`). Numbers in the draft are macro names only (rule R5).

## Draft

**Fig. 7** (a) Slurry dissolution verdict over calcium dose Ca_T and dissolved carbonate C_T: feasible (blue), inconclusive (yellow, hatched), excluded (vermillion, cross-hatched); line: median Ω_bulk = 1. (b) Windows against Li⁺/Li per phase: experimental route (black), JANAF (blue) and MP (vermillion) DFT, dashed when corrected; open circle: undetermined; open square: no route. Grey: margin to the \NumCellFalsifiedAbove bound; dashed lines: cathode-class cutoffs.

## Checklist (R4, R5, R6, R7)

- Physical claim: CaCO₃ resists dissolution only where the dose and the carbonate keep the bulk supersaturated; in the cell it is oxidised below the cutoffs of most cathode classes; the aluminium-oxide phases have no determined oxidation limit.
- The figure refuses to build if the two water-activity points disagree, or if a sink outside the crossover has a determined oxidation limit, so the two caption sentences stay true.
- The margin itself is \NumCellMarginExpt (Methods). The LCO and LMO class cutoffs coincide; four lines are drawn for five classes.
- Thermodynamic proxies only: no rate, corrosion, capacity or device wording.
