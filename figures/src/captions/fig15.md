# Fig. 15 caption draft (candidate-by-regime heatmap)

Source: `ladder_v3.csv` (K1), `perph.csv` with the cell verdicts of `k2_grid_ph`, `k2_acid_ph2` and `k2_alkaline_ph2` (K2, per pH, post-freeze keys), cutoff classes from the registered thresholds; all pinned in `figures/src/schemas/upstream.yaml`. The regime table (`preprint/generated/regime_table.csv`) is a cross-check: the first-pass pH of every row must agree (brushite and OCP are skipped; the table predates PH-W4.5). A K2 cell takes the regime of its own pH: suitable where any grid cell passes, open where none passes and some are inconclusive, excluded where all are falsified. Dose of a cell set: the larger of the minimum passing Ca_T and P_T. The processing column spans the as-prepared slurry pH values. Blank: not tested in that column.

## Draft

**Fig. 15** Regime of each candidate (rows: slurry phases, cell phases, silicates, carbonates). Columns: K2 in the processing slurry, then in the acid-adjusted slurry by pH, then K1 at the registered cutoff classes (nominal \NumCutoffLfpNominal), crystalline left, amorphous right. Dots: suitable against dissolution, plus vertical lines at a lowest passing dose of at least \NumDoseHigh; plain: undetermined; single hatching: open; cross hatching: thermodynamically excluded. Carbonate K1: calcite row.
