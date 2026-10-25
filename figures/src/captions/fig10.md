# Fig. 10 caption draft (DFT benchmark)

Source: `benchmark_w51.csv` and `benchmark_w51.json` (lane p0-w5, PH-W5.1), pinned in `figures/src/schemas/upstream.yaml` (keys `benchmark_w51`, `benchmark_w51_summary`). Rows without a like-for-like formation enthalpy (formation free energy only) are not drawn. Explanation of the outside rows: the Materials Project correction puts one fitted oxide term on every oxygen, whatever it bonds to (ph_w51.md, reading).

## Draft

**Fig. 10** DFT minus tabulated formation enthalpy per atom for each phase with a like-for-like value, grouped by family (phosphates, silicates, Al-O-H phases, sink salt). Grey band: registered error band, \NumDftTolerance\ per atom. Filled circle: inside the band; open square: outside; open diamond: tabulated phase is a glass. The outside rows are consistent with one oxide correction, \NumMpOxideCorr\ per O, applied to every oxygen.
