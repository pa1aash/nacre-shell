# PH-I6d: merge W1.8 and W4.5, cp5b deviation entries, ledger (integrator) — DONE

- Ledger (4155390): PH-W1.8, PH-W8.2e, PH-W6.3, PH-I6e, PH-W4.6 added; PH-W4.5 note set to DONE; D76 to D78; PH-W1.8 and PH-W4.5 in the done list.
- Merges (--no-ff, no conflicts): w1 0a1d886 then b653c28 (regenerated SI tables), w4 09e4a10 then ab805e8 (gap-table accounting line for p_total_slurry_h3po4_window).
- Deviation entries (2dad38a), each "Re-audit: cp6": params.yaml (5 keys, none changed; p_total_slurry_h3po4_window is a gap), the *_ph2 result directories, the max-Omega control rule (pH 12 to 7.65 move came from a dry run), and symbol_bindings.yaml. Correction recorded: 4d6517f1 is the file at 1eb77f8 (PH-W4.2f); 416c954b is the file at the pre-run commit 8073c8e and now; the change entered with 8073c8e.
- pytest (seven directories): 1462 passed, 3 failed, 1 skipped. Remaining: tests/preprint/test_preprint_macros.py::test_generated_files_are_git_ignored_not_tracked, test_preprint_regime_table.py::test_regeneration_is_byte_identical and ::test_every_cell_traces_to_a_file_and_its_sha256. All three are regime_table.json staleness against the new lit/params.yaml sha; PH-W8.2e regenerates it.
- `nacre verify --quick`: PASS. No tag created.
