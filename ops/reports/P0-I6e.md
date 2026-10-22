# Session report: PH-I6e (integrator, day 6)
Merged w8 09e6576 (PH-W8.2e) and w6 564d630 (PH-W6.3), then w6 c47d30d (figure pins for the regenerated regime table; the integrator lane may not edit the pin file). Seven pytest directories: 1496 passed, 0 failed, 1 skipped. `verify --quick` PASS. `regime-table --check` up to date. Pin thresholds_screen_ph same_bytes true. Strict verify runs at cp6. Tag p0-cp5b NOT created (TAG-NOW: no).
## cp5b fixes
- F1 applied for the frozen grid; PH-W4.6 pending. Per-pH minimum passing Ca_T and P_T, passing fraction and Ca:P range in the regime table (main and SI Tables S2, S3), the first-pass pH names its minimum dose, all 21 cells carry the high-dose flag, generated text on the sourced H3PO4 dose (only 0.15 mol per kg liquid derivable) and the P_T window gap: PH-W8.2e, PH-W1.8, PH-W4.5 (gap-table key accounted in PH-W4.5b).
- F2 applied for the frozen grid; PH-W4.6 pending. The crossed Ca_T x P_T decade-grid statement is in the Methods and SI (main_si.tex line 215, regime_table.tex line 114); the apatite ratios do not occur on it; the ratio-grid run is not yet run and the text says a run is pending.
- F3 applied. Nucleation sentence (results.tex, link falsified at N of M design points) and the carbonate-chain sentence (24 of 36 falsified, 12 inconclusive; gamma_sl median 1.22 mJ/m2), numbers by macro from f3_numbers.json.
- F4 applied. Max-Omega control rule and the dry-run disclosure (pH 12 to 7.65, 0 cells moved) in Methods (methods.tex lines 47, 95) and SI.
- F5 applied. Sobol half-width 0.098 against 0.02 with the Shapley statement in Methods (line 76) and SI; SI statement that the ladder at the sensitivity line is byte-identical to the nominal one (regime_table.tex line 146); the PH-W6.2 report corrected by an appended note (32 precision rows); the symbol_bindings hash deviation entry (p0_deviations.md, 2026-10-22) states both hashes (1eb77f8 state 4d6517f1; 8073c8e and current 416c954b).
- F6 (patents) deferred: the release guard refuses until the four patent references come by a fetched-metadata route (Palaash declined the table; route decided at cp6).
## Open items
1. Wording mismatch: ACP at pH 4.5, ACC at pH 6.5 and 7.5 read "open" in the figure rule, "excluded below first pass" in the regime table: PH-W8.2f.
2. fig17 omits OCP, Li3PO4, Al(PO3)3 and the Al gel (no K1 bound); the caption (figures/src/fig17.py) does not yet say so: PH-W8.2f.
3. Al-salt table request for W8: figures/out/tables/al_salt_ladder.csv (6 rows, all undetermined). Most useful datum to fetch: Gibbs energy or entropy of solid Al(ClO4)3.
4. Dose rule for cp6: 0.01 mol/dm^3 is a factor of about 15 below the only derivable sourced figure (about 0.15 mol/kg liquid); 0.1 is the same order; text says "comparable to the order of", never "equal".
5. Tag p0-cp5b waits on Palaash's go; the ratio grid PH-W4.6 waits on the planning chat.
