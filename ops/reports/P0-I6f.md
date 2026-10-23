# P0-I6f: cp5b close (route A)
Merged PH-W8.2g (w8 90d60c9) and PH-W6.3c/d (w6 01fc7d5) into preprint/p0; seven pytest directories pass, verify --quick passes, regime-table --check up to date. Strict verify runs at cp6 (D75).
F1: applied. Per-pH minimum doses on the crossed decade grid and the stoichiometric ratio grid, passing fractions, Ca:P of passing cells, dose-qualifier text; the sourced H3PO4 dose; the P_T window key is a gap.
F2: applied. Crossed-grid statement in the Methods; ratio grid run as PH-W4.6 (HAp at 1.67, beta-TCP at 1.5, brushite at 1.0, ACP and OCP on both); no pass or fail flips; 43 of 120 groups shift in minimum passing Ca_T only.
F3: applied. gamma_sl 0.184 to 2.88 mJ/m^2, median 1.22, 0.29 % and at most 3.4 %, 24 of 36 within the registered model.
F4: applied.
F5: applied. Sobol half-width 0.098 against 0.02; Shapley carries the ranking; SI statement on the byte-identical 4.0 V file; PH-W6.2 report corrected; symbol_bindings hash entry corrected.
F6: deferred. Patent references; the release guard refuses until supplied; route decided at cp6.
Open items for cp6:
- Dose-rule reading: 0.01 mol/dm^3 is about 15 times below the derivable sourced figure of about 0.15 mol/kg liquid; 0.1 is the same order; the text says "comparable to the order of ..., never equal".
- fig17 omits OCP, Li3PO4, Al(PO3)3 and the Al gel (stated in its caption).
- Al-salt table: all undetermined; the most useful datum to fetch is the Gibbs energy or entropy of solid Al(ClO4)3.
- Pathway schematic and four-conditions diagram (PH-W6.3b, optional); the hero (optional, first to cut).
- Patent references.
Pins: thresholds_screen_ph same_bytes true. regime_table committed pin sha256 aa754f35... equals the merged tree file; pin_upstream.py re-run reads origin/preprint/p0 (pre-push) so reports 146e76a6... until this push; the branch field (preprint/p0-w8) cannot be changed by the integrator.
